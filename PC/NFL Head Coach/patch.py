"""Experimental PC NFL Head Coach private-server patch and local login setup."""

import argparse
import getpass
import hashlib
import ipaddress
import struct
import sys
from pathlib import Path


SOURCE_SHA256 = "72c76b161d8b42b4d86a46c604893fcffc69817438f0b8b72d2a9806ee10fe0d"
ACCOUNT_KEY = r"Software\NFLHC\LocalEA"
ACCOUNT_OWNER = "ea-nation-patches"


def add_ini_hook(data, default_address):
    """Replace the address getter with a register-preserving x86 INI reader.

    This fixed-base executable has no relocations. Add one read/execute section;
    the existing writable address slot at VA 0x99753c remains the return buffer.
    Windows APIs are resolved through existing kernel32 imports.
    """
    def align(value, boundary):
        return (value + boundary - 1) // boundary * boundary

    pe = struct.unpack_from("<I", data, 0x3c)[0]
    optional = pe + 24
    count = struct.unpack_from("<H", data, pe + 6)[0]
    table = optional + struct.unpack_from("<H", data, pe + 20)[0]
    header = table + count * 40
    image_base = struct.unpack_from("<I", data, optional + 28)[0]
    section_align, file_align = struct.unpack_from("<II", data, optional + 32)
    last_size, last_rva = struct.unpack_from("<II", data, header - 40 + 8)
    rva = align(last_rva + last_size, section_align)
    raw = align(len(data), file_align)
    if header + 40 > struct.unpack_from("<I", data, table + 20)[0]:
        raise ValueError("No room for an INI hook section header")

    code = bytearray()
    labels, fixups = {}, []

    def emit(hex_bytes):
        code.extend(bytes.fromhex(hex_bytes))

    def label(name):
        labels[name] = len(code)

    def reference(opcode, name, relative=False):
        emit(opcode)
        fixups.append((len(code), name, relative))
        code.extend(b"\0" * 4)

    # pushfd; pushad; reserve a 260-byte path buffer; ebp = buffer.
    emit("9c 60 81ec04010000 8bec")
    # GetModuleFileNameA(NULL, buffer, 240), reserving room for the INI basename.
    emit("68f0000000 55 6a00 ff1584629300 85c0")
    reference("0f84", "fallback", True)
    emit("3df0000000")
    reference("0f83", "fallback", True)
    emit("8d7c05ff")  # edi = buffer + length - 1
    label("slash")
    emit("803f5c")
    reference("0f84", "basename", True)
    emit("3bfd")  # cmp edi, ebp
    reference("0f84", "fallback", True)
    emit("4f")
    reference("e9", "slash", True)
    label("basename")
    emit("47")
    reference("be", "filename")
    emit("b911000000 fc f3a4")  # copy coach-online.ini and NUL
    reference("68", "kernel32")
    emit("ff1580629300 85c0")  # GetModuleHandleA
    reference("0f84", "fallback", True)
    reference("68", "api")
    emit("50 ff1578619300 85c0")  # GetProcAddress
    reference("0f84", "fallback", True)
    emit("55 6a12 683c759900")  # filename, 18-byte buffer size, buffer
    reference("68", "default")
    reference("68", "key")
    reference("68", "section")
    emit("ffd0 85c0")  # GetPrivateProfileStringA
    reference("0f84", "fallback", True)
    emit("83f80f")  # reject overlong/truncated IPv4 strings
    reference("0f87", "fallback", True)
    emit("be3c759900 33db 33d2 33c9")  # address, dots, octet, digits
    label("digit")
    emit("0fb606 85c0")
    reference("0f84", "last_octet", True)
    emit("83f82e")
    reference("0f84", "dot", True)
    emit("83e830")
    reference("0f82", "fallback", True)
    emit("83f809")
    reference("0f87", "fallback", True)
    emit("6bd20a 03d0 81faff000000")
    reference("0f87", "fallback", True)
    emit("41 83f903")
    reference("0f87", "fallback", True)
    emit("46")
    reference("e9", "digit", True)
    label("dot")
    emit("85c9")
    reference("0f84", "fallback", True)
    emit("43 83fb03")
    reference("0f87", "fallback", True)
    emit("33d2 33c9 46")
    reference("e9", "digit", True)
    label("last_octet")
    emit("83fb03")
    reference("0f85", "fallback", True)
    emit("85c9")
    reference("0f85", "done", True)
    label("fallback")
    reference("be", "default")
    emit("bf3c759900 b912000000 fc f3a4")
    label("done")
    emit("81c404010000 61 9d b83c759900 c3")

    for name, value in (
        ("filename", b"coach-online.ini\0"), ("kernel32", b"kernel32.dll\0"),
        ("api", b"GetPrivateProfileStringA\0"), ("key", b"Host\0"),
        ("section", b"Online\0"), ("default", default_address.ljust(18, b"\0")),
    ):
        label(name)
        code.extend(value)
    for offset, name, relative in fixups:
        value = labels[name] - (offset + 4) if relative else image_base + rva + labels[name]
        struct.pack_into("<i" if relative else "<I", code, offset, value)

    # mov eax, 0x99753c -> jmp hook; the hook returns directly to the caller.
    if data[0x310120:0x310126] != bytes.fromhex("b83c759900c3"):
        raise ValueError("Unexpected server-address getter")
    data[0x310120:0x310125] = b"\xe9" + struct.pack("<i", image_base + rva - 0x710d25)
    raw_size = align(len(code), file_align)
    section = struct.pack("<8sIIIIIIHHI", b".hcnet\0\0", len(code), rva,
                          raw_size, raw, 0, 0, 0, 0, 0x60000020)
    data[header:header + 40] = section
    struct.pack_into("<H", data, pe + 6, count + 1)
    struct.pack_into("<I", data, optional + 4, struct.unpack_from("<I", data, optional + 4)[0] + raw_size)
    struct.pack_into("<I", data, optional + 56, align(rva + len(code), section_align))
    data.extend(b"\0" * (raw - len(data)))
    data.extend(code.ljust(raw_size, b"\0"))


def pe_checksum(data, checksum_offset):
    """PE checksum: folded 16-bit sum, excluding the CheckSum field."""
    total = 0
    for offset in range(0, len(data), 2):
        if checksum_offset <= offset < checksum_offset + 4:
            continue
        word = data[offset]
        if offset + 1 < len(data):
            word |= data[offset + 1] << 8
        total += word
        total = (total & 0xffff) + (total >> 16)
    return ((total & 0xffff) + (total >> 16)) + len(data)


def patch_executable(source, output, server):
    before = source.read_bytes()
    if hashlib.sha256(before).hexdigest() != SOURCE_SHA256:
        raise ValueError("Unsupported executable SHA-256; no output written")
    after = bytearray(before)

    def change(offset, old, new):
        if len(old) != len(new) or before[offset:offset + len(old)] != old:
            raise ValueError(f"Unexpected bytes at file offset 0x{offset:x}")
        after[offset:offset + len(old)] = new

    # VA 0x6c31a5: follow the existing successful local administrator-check path.
    change(0x2c25a5, bytes.fromhex("741e"), bytes.fromhex("eb1e"))

    # VA 0x99753c: removing '*' selects plain Aries. TCP port stays 31320.
    endpoint = b"*pccoach06.ea.com\0"
    address = str(ipaddress.IPv4Address(server)).encode("ascii") + b"\0"
    change(0x59653c, endpoint, address.ljust(len(endpoint), b"\0"))

    # VA 0x9bb92c / 0x9bb90c: isolate the credentials from EA's shared key.
    for offset, old in (
        (0x5ba92c, b"SOFTWARE\\Electronic Arts\\Shared\0"),
        (0x5ba90c, b"SOFTWARE\\Electronic arts\\Shared\0"),
    ):
        change(offset, old, (ACCOUNT_KEY.encode("ascii") + b"\0").ljust(len(old), b"\0"))
    # VA 0x913f9d / 0x913fdb: HKEY_LOCAL_MACHINE -> HKEY_CURRENT_USER.
    for offset in (0x51339d, 0x5133db):
        change(offset, bytes.fromhex("6802000080"), bytes.fromhex("6801000080"))

    # VA 0x70fde0: HasLatestRoster uses the installed roster's checksum and
    # returns true. The server does not host a replacement roster.
    old = bytes.fromhex("8b44240850e856feffff50e80053ddff83c408e8e852ddff84c00f95c0c20800")
    new = (b"\xe8" + struct.pack("<i", 0x4e5040 - (0x70fde0 + 5))
           + b"\xa3" + struct.pack("<I", 0xa19dd4) + bytes.fromhex("b001c20800"))
    change(0x30f1e0, old, new.ljust(len(old), b"\x90"))

    add_ini_hook(after, address)
    pe_offset = struct.unpack_from("<I", before, 0x3c)[0]
    checksum_offset = pe_offset + 24 + 64
    struct.pack_into("<I", after, checksum_offset, pe_checksum(after, checksum_offset))
    # Exclusive creation also prevents accidentally overwriting the source.
    with output.open("xb") as handle:
        handle.write(after)
    print(f"Created {output}")
    print(f"SHA-256: {hashlib.sha256(after).hexdigest()}")
    print("Server override: coach-online.ini beside the executable, [Online] Host=IPv4")


def encode_password(password):
    # Stock decoder at VA 0x913de0: one DWORD per character, with 2*index
    # added to its low byte, followed by a zero DWORD. This is not encryption.
    return b"".join(struct.pack("<I", ord(char) + 2 * index)
                    for index, char in enumerate(password)) + b"\0" * 4


def account_text(value):
    # Keep inputs within the tested single-byte decoder's range.
    if not 1 <= len(value) <= 31 or any(not 32 <= ord(char) <= 126 for char in value):
        raise ValueError("Use 1-31 printable ASCII characters for each credential")
    return value


def configure_account(username):
    if sys.platform != "win32":
        raise ValueError("Account setup requires Windows")
    import winreg

    account_text(username)
    password = account_text(getpass.getpass("Private-server password: "))
    if password != getpass.getpass("Confirm password: "):
        raise ValueError("Passwords do not match; registry unchanged")
    access = winreg.KEY_READ | winreg.KEY_WRITE | winreg.KEY_WOW64_32KEY
    with winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, ACCOUNT_KEY, 0, access) as key:
        try:
            owner = winreg.QueryValueEx(key, "ManagedBy")[0]
        except FileNotFoundError:
            owner = None
        if owner != ACCOUNT_OWNER and winreg.QueryInfoKey(key)[:2] != (0, 0):
            raise ValueError("Account key already contains unrelated settings; left unchanged")
        winreg.SetValueEx(key, "ManagedBy", 0, winreg.REG_SZ, ACCOUNT_OWNER)
        winreg.SetValueEx(key, "user", 0, winreg.REG_SZ, username)
        winreg.SetValueEx(key, "pass", 0, winreg.REG_BINARY, encode_password(password))
    print("Saved private-server credentials in HKCU\\" + ACCOUNT_KEY + " (32-bit view)")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    patch = commands.add_parser("patch", help="Create a separate patched executable")
    patch.add_argument("source", type=Path)
    patch.add_argument("output", type=Path)
    patch.add_argument("--server", default="127.0.0.1", type=ipaddress.IPv4Address,
                       help="Fallback IPv4 address when coach-online.ini is missing or invalid")
    account = commands.add_parser("account", help="Save an existing server account for Login")
    account.add_argument("--username", required=True)
    args = parser.parse_args()
    try:
        if args.command == "patch":
            patch_executable(args.source, args.output, args.server)
        else:
            configure_account(args.username)
    except (OSError, ValueError, EOFError) as error:
        parser.exit(1, f"Error: {error}\n")


if __name__ == "__main__":
    main()
