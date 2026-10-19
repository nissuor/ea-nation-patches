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

    pe_offset = struct.unpack_from("<I", before, 0x3c)[0]
    checksum_offset = pe_offset + 24 + 64
    struct.pack_into("<I", after, checksum_offset, pe_checksum(after, checksum_offset))
    # Exclusive creation also prevents accidentally overwriting the source.
    with output.open("xb") as handle:
        handle.write(after)
    print(f"Created {output}")
    print(f"SHA-256: {hashlib.sha256(after).hexdigest()}")


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
    patch.add_argument("--server", required=True, type=ipaddress.IPv4Address)
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
