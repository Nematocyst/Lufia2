"""Overworld battles: choose the battle background per terrain type, with an optional per-tile override map.

    python3 terrain_patch.py in.sfc out.sfc [class=id ...] [--zone file.npy=id ...]

The original code (at $86:9D6E) only says "desert tile -> 00, anything else -> 04".
It is replaced by JSL TerrainBackground ($E0:F000):
  1. world map 0 only ($09EA = 0): look up the tile ($11F2, $11F4) in a 256x256 byte map
     (rows 0-127 at $F0:8000, rows 128-255 at $F1:8000). Non-zero = that background id.
  2. otherwise: 16-byte table at $E0:F080 indexed by the tile class (high nibble of the tile record).
Defaults: class 0 grassland -> 04, 1 desert -> 00, 2 forest -> 06, everything else -> 04.
--zone takes a 256x256 boolean .npy (True = use that id); later zones win.
"""
import sys
import numpy as np

lo = lambda a: (a >> 16 & 0x7F) * 0x8000 + (a & 0x7FFF)
CODE, TAB, MAP0, MAP1 = 0xE0F000, 0xE0F080, 0xF08000, 0xF18000


def build(src, dst, classes, zones):
    rom = bytearray(open(src, 'rb').read()); assert len(rom) == 0x400000
    tab = [4] * 16; tab[1] = 0; tab[2] = 6
    for c, i in classes.items(): tab[c] = i
    zmap = np.zeros((256, 256), np.uint8)
    for path, bid in zones: zmap[np.load(path).astype(bool)] = bid
    p = lo(0x869D6E)
    assert rom[p:p + 11] == bytes.fromhex('a0 00 00 c9 10 f0 03 a0 04 00 98'), rom[p:p + 11].hex()
    rom[p:p + 11] = bytes([0x22, CODE & 0xFF, CODE >> 8 & 0xFF, CODE >> 16]) + bytes([0xEA] * 7)
    L = lambda a: [a & 0xFF, a >> 8 & 0xFF, a >> 16]
    code = [0xDA,                        # PHX
            0x48,                        # PHA            tile class (A is 8-bit)
            0xAF, *L(0x7E09EA),          # LDA.l $7E09EA  world map id
            0xD0, 0x2A,                  # BNE cls        (only world 0 has a zone map)
            0xC2, 0x20,                  # REP #$20
            0xAF, *L(0x7E11F4),          # LDA.l $7E11F4  tile y
            0x29, 0x7F, 0x00,            # AND #$007F
            0xEB,                        # XBA            (y & 127) << 8
            0x48,                        # PHA
            0xAF, *L(0x7E11F2),          # LDA.l $7E11F2  tile x
            0x29, 0xFF, 0x00,            # AND #$00FF
            0x03, 0x01,                  # ORA 1,S
            0xAA,                        # TAX
            0x68,                        # PLA
            0xE2, 0x20,                  # SEP #$20
            0xAF, *L(0x7E11F4),          # LDA.l $7E11F4
            0x30, 0x06,                  # BMI hi
            0xBF, *L(MAP0),              # LDA.l $F08000,X
            0x80, 0x04,                  # BRA got
            0xBF, *L(MAP1),              # hi: LDA.l $F18000,X
            0xD0, 0x12,                  # got: BNE done
            0xA3, 0x01,                  # cls: LDA 1,S    tile class
            0xC2, 0x20,                  # REP #$20
            0x29, 0xF0, 0x00,            # AND #$00F0
            0x4A, 0x4A, 0x4A, 0x4A,      # LSR x4
            0xAA,                        # TAX
            0xE2, 0x20,                  # SEP #$20
            0xBF, *L(TAB),               # LDA.l table,X
            0xEB, 0x68, 0xEB,            # done: XBA; PLA (drop class); XBA
            0xC2, 0x20, 0x29, 0xFF, 0x00, 0xA8, 0xE2, 0x20,   # REP; AND #$00FF; TAY; SEP  (Y = id like the original)
            0xFA,                        # PLX
            0x6B]                        # RTL
    code = bytes(code)
    q = lo(CODE)
    assert not any(rom[q:q + 0x80]) and not any(rom[lo(TAB):lo(TAB) + 16]), 'code space not free'
    assert not any(rom[lo(MAP0):lo(MAP0) + 0x8000]) and not any(rom[lo(MAP1):lo(MAP1) + 0x8000]), 'map space not free'
    assert len(code) <= 0x80
    rom[q:q + len(code)] = code
    rom[lo(TAB):lo(TAB) + 16] = bytes(tab)
    rom[lo(MAP0):lo(MAP0) + 0x8000] = zmap[:128].tobytes()
    rom[lo(MAP1):lo(MAP1) + 0x8000] = zmap[128:].tobytes()
    rom[0x7FDC:0x7FE0] = bytes([0xFF, 0xFF, 0, 0]); s = sum(rom) & 0xFFFF
    rom[0x7FDE:0x7FE0] = s.to_bytes(2, 'little'); rom[0x7FDC:0x7FDE] = (s ^ 0xFFFF).to_bytes(2, 'little')
    open(dst, 'wb').write(rom)
    return tab, int((zmap > 0).sum())


if __name__ == '__main__':
    args = sys.argv[3:]; classes = {}; zones = []
    i = 0
    while i < len(args):
        if args[i] == '--zone':
            f, b = args[i + 1].rsplit('=', 1); zones.append((f, int(b, 0))); i += 2
        else:
            c, b = args[i].split('='); classes[int(c, 0)] = int(b, 0); i += 1
    tab, n = build(sys.argv[1], sys.argv[2], classes, zones)
    print('class table', [hex(x) for x in tab[:5]], '| zone tiles', n)
