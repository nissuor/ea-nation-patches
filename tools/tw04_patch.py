"""Generate an NTSC-U TW04 PCSX2 or OPL memory patch; Python 3, no dependencies.

Protocol/address research: jeddyhhh/TW04OnlineServer, MIT; see THIRD-PARTY-TW04.txt.
No game, BIOS, account, or other private data is read or bundled.
"""
import argparse
import ipaddress
import pathlib
import struct


# OPL's PS2RD engine replaces this jal (and moves its delay slot) to run codes
# every frame: the game's pad update calling scePadRead (0x00113550). It only
# hooks if the opcode matches, so another revision gets no writes at all.
OPL_HOOK = (0x0020CFC8, 0x0C044D54)


def build(ip, port=10200, relay_client=False, opl=False):
    try:
        ip = str(ipaddress.IPv4Address(ip))
    except ValueError:
        # The lobby address is parsed as digits only (0x002B5BC8); no DNS lookup.
        raise ValueError("%r is not a numeric IPv4 address; TW04 cannot use a hostname" % ip)
    if not 1 <= port <= 65535:
        raise ValueError("Port must be 1..65535")
    if opl and relay_client:
        # The co-host shares the relay's own IP; that only happens with PCSX2.
        raise ValueError("--relay-client is for PCSX2 on the relay machine, not OPL")
    if opl:
        # Codes under "Mastercode" stay enabled even in OPL's cheat select mode.
        lines = ['"Tiger Woods PGA Tour 2004 /ID SLUS_207.57"',
                 "// EA Nation redirect, DNAS, dates and guest peer-address fix",
                 "// SLUS-20757; OPL PS2RD cheat engine, memory only, ISO unchanged.",
                 "// Addresses from jeddyhhh/TW04OnlineServer (MIT).",
                 "Mastercode",
                 "// Hook: the pad update's call to scePadRead.",
                 "9%07X %08X" % OPL_HOOK]
    else:
        lines = ["gametitle=Tiger Woods PGA Tour 2004 (USA)",
                 "comment=EA Nation redirect, DNAS, dates and guest peer-address fix",
                 "// SLUS-20757 CRC 64F9781E; memory only, ISO unchanged.",
                 "// Addresses from jeddyhhh/TW04OnlineServer (MIT)."]
    writes = []
    for address, text, size in ((0x0030FAC0, ip, 16), (0x00311040, ip, 16),
                                (0x0030FAD0, str(port), 8), (0x00311050, str(port), 8)):
        raw = text.encode('ascii').ljust(size, b'\0')
        writes.extend((address+i, struct.unpack_from('<I', raw, i)[0])
                      for i in range(0, size, 4))
    writes += [(0x002E1468, 0x00001821), (0x002BCAEC, 0x28637FFF),
               (0x002BCAF8, 0x24027FFE), (0x002BCD44, 0x28637FFF),
               (0x002BCD50, 0x24027FFE)]
    # After LAN discovery fails, the joining player uses peer+0x20 (FROM/name).
    # Use peer+0x40 (server ADDR) instead. Successful LAN discovery is unchanged.
    # Original 0x26240020 verified in SLUS-20757; guest branch executed offline.
    lines += ['// Internet guest fallback: connect to server ADDR, not opponent name.']
    writes.append((0x0028B5F0, 0x26240040))
    if relay_client:
        # Local co-host only: use the complete connection string supplied in ADDR.
        # _connect helper originally formats "%s%s%s" (ADDR + :3658 + :3658).
        # Select its existing "%s" format instead; no injected code or scratch space.
        # Original instruction 0x24A50FE0 verified against SLUS-20757 ELF.
        lines += ['// Relay co-host: server MUST supply ADDR=ip:localPort:remotePort.']
        writes.append((0x0027AB68, 0x24A50FE8))
    form = '2%07X %08X' if opl else 'patch=1,EE,%08X,word,%08X'
    lines += [form % pair for pair in writes]
    return '\n'.join(lines)+'\n'


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('ipv4')
    parser.add_argument('--port', type=int, default=10200)
    parser.add_argument('--relay-client', action='store_true',
                        help='Co-host only: accept a full relay connection string in ADDR')
    parser.add_argument('--opl', action='store_true',
                        help='Write an Open PS2 Loader cheat file (CHT/SLUS_207.57.cht)')
    parser.add_argument('--out', type=pathlib.Path)
    args = parser.parse_args()
    if args.out is None:
        args.out = pathlib.Path('SLUS_207.57.cht' if args.opl else 'SLUS-20757_64F9781E.pnach')
    try:
        text = build(args.ipv4, args.port, args.relay_client, args.opl)
    except ValueError as e:
        parser.error(str(e))
    args.out.write_text(text, encoding='ascii')
    print('Wrote', args.out)
