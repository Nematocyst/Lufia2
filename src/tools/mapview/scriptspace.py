"""Make room for map scripts in a bank the script engine can use.

Why: the scene-script engine runs with the data bank = the script's bank and reaches its own
work RAM ($09B7, $09B9, $079E...) with absolute addressing. Only banks $80-$BF mirror low RAM at
$0000-$1FFF, so scripts must live in $80-$BF. Expansion banks ($C0+) can't hold scripts
(tested: a block moved to $D8:8000 never ran). Banks $A7-$CE are packed with compressed
resources reached only through the resource table, so moving the resources that overlap one
bank (e.g. $BF) to expansion space frees that whole bank for scripts.

    python3 scriptspace.py IN.sfc OUT.sfc --bank BF --to D88000
"""
import sys
sys.path.insert(0, '/home/claude/lufia2/tools'); sys.path.insert(0, '/home/claude/lufia2/tools/mapview')
import l2compress as L
from mapdata import table_addr


def entries(rom):
    t = L.lo(table_addr(rom))
    n = 1024 if table_addr(rom) != 0xA78000 else 680
    out = []
    for i in range(n):
        e = rom[t + 3 * i:t + 3 * i + 3]
        if e == b'\x00\x00\x00' and i >= 680:
            continue
        s = L.lo(L.stream_addr(e))
        if s >= len(rom):
            continue
        out.append((i, s))
    return t, out


def free_bank(rom, bank, dest):
    """Move every resource that overlaps bank `bank` to CPU address `dest` (consecutively);
    fill the freed bank with $FF. Returns (rom, end address used, moved ids)."""
    rom = bytearray(rom)
    if len(rom) < 0x400000:
        rom += bytes(0x400000 - len(rom))
    t, ents = entries(rom)
    lo, hi = L.lo(bank << 16 | 0x8000), L.lo(bank << 16 | 0x8000) + 0x8000
    moved = []; ranges = []
    a = dest
    seen = {}
    for i, s in ents:
        data, used = L.decode(rom[s:])
        if not (s < hi and s + used > lo):
            continue
        if s in seen:                                  # two ids sharing one stream
            new = seen[s]
        else:
            new = a
            for b in rom[s:s + used]:
                p = L.lo(a)
                assert rom[p] in (0, 0xFF), '$%06X not free' % a
                rom[p] = b; a += 1
                if a & 0xFFFF == 0:
                    a += 0x8000
            seen[s] = new; ranges.append((s, s + used))
        v = ((new >> 16) - 0xA7) << 15 | (new & 0x7FFF)
        rom[t + 3 * i:t + 3 * i + 3] = bytes([v & 0xFF, v >> 8 & 0xFF, v >> 16])
        assert L.decode(rom[L.lo(L.stream_addr(rom[t + 3 * i:t + 3 * i + 3])):])[0] == data
        moved.append(i)
    # make sure nothing else still points into the moved ranges, then blank them
    _, ents2 = entries(rom)
    for i, s in ents2:
        assert not any(r0 <= s < r1 for r0, r1 in ranges), 'resource %d still in a moved range' % i
    for r0, r1 in ranges:
        rom[r0:r1] = b'\xff' * (r1 - r0)
    return rom, a, moved


if __name__ == '__main__':
    a = sys.argv[1:]
    bank = int(a[a.index('--bank') + 1], 16); dest = int(a[a.index('--to') + 1], 16)
    rom, end, moved = free_bank(open(a[0], 'rb').read(), bank, dest)
    open(a[1], 'wb').write(rom)
    print('moved resources', moved, 'to $%06X-$%06X; bank $%02X is free' % (dest, end - 1, bank))
