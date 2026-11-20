"""Render a Lufia II field map from the ROM alone (no emulator).

What FieldLoadMapResources $80:EAE7 / FieldLoadSceneGraphics $80:EF97 load:
  map cells      resource $3F + map (mapdata.MapData; maps >= $F2 via mapext's hook)
  metatiles      resource $130 + $CF:F72E[map] -> 8-byte metatiles at +$10 (column-major TL BL TR BR)
  BG characters  resource $14B + $CF:F81E[map] -> VRAM byte $8000 (4bpp, tile n at $8000 + 32n)
  palette        $9B:(word $CF:FAFA[2*($CF:FA08[map]-1)]) -> 256 bytes = BG palettes 0-7, colour 0 = black
Tables are read through the readers' operands, so a ROM with mapext's relocated tables works too.

    python3 romrender.py ROM MAP out.png      (MAP hex)
"""
import sys
import numpy as np
from PIL import Image
sys.path.insert(0, '/home/claude/lufia2/tools'); sys.path.insert(0, '/home/claude/lufia2/tools/mapview')
import l2compress as L
from mapdata import MapData, resource_off


def operand(rom, ins):
    o = L.lo(ins)
    return rom[o + 1] | rom[o + 2] << 8 | rom[o + 3] << 16


def table_byte(rom, ins, idx):
    return rom[L.lo(operand(rom, ins) + idx)]


def resource(rom, rid):
    return L.decode(rom[resource_off(rom, rid):])[0]


# Colours 0-23 (and 0-15 when the skip is $20) are the window/font colours loaded at boot; the map's
# palette (FieldCopyScenePalette $80:F338) is copied from its source to CGRAM byte offset `skip`
# ($30 normally, $20 for maps without scene graphics), 256 - skip bytes.
UI = bytes.fromhex('0000314e433c9c7300009c7300009c7300009c73f4768a3d00009c73f4768a3d'
                   '0a280a28df57377f0a280a28df571a4e')


def palette(rom, m):
    k = table_byte(rom, 0x80F2D2, m)                          # $CF:FA08[map]
    t = operand(rom, 0x80F2DB)                                # $CF:FAFA
    o = L.lo(t + 2 * (k - 1))
    src = 0x9B0000 | rom[o] | rom[o + 1] << 8
    skip = 0x30 if table_byte(rom, 0x80F03B, m) else 0x20
    raw = bytearray(UI) + bytes(256)
    raw[skip:256] = rom[L.lo(src):L.lo(src) + 256 - skip]
    pal = np.zeros((128, 3), np.uint8)
    for i in range(128):
        v = raw[2 * i] | raw[2 * i + 1] << 8
        pal[i] = [(v & 31) << 3, (v >> 5 & 31) << 3, (v >> 10 & 31) << 3]
    pal[0] = 0
    return pal


class ROMField:
    def __init__(self, rom, m):
        self.rom = rom; self.m = m
        self.md = MapData(rom, m)
        ts = resource(rom, 0x130 + table_byte(rom, 0x80EB8B, m))
        self.meta = ts[0x10:]
        self.chars = resource(rom, 0x14B + table_byte(rom, 0x80F03B, m))
        self.pal = palette(rom, m)
        self.cache = {}

    def tile(self, word):
        if word not in self.cache:
            n = word & 0x3FF; o = 32 * n
            t = np.zeros((8, 8), np.uint8)
            c = self.chars
            if o + 32 <= len(c):
                for y in range(8):
                    p0, p1, p2, p3 = c[o + 2 * y], c[o + 2 * y + 1], c[o + 16 + 2 * y], c[o + 17 + 2 * y]
                    for x in range(8):
                        s = 7 - x
                        t[y, x] = (p0 >> s & 1) | (p1 >> s & 1) << 1 | (p2 >> s & 1) << 2 | (p3 >> s & 1) << 3
            if word & 0x4000: t = t[:, ::-1]
            if word & 0x8000: t = t[::-1, :]
            self.cache[word] = (t, (word >> 10) & 7, word >> 13 & 1)
        return self.cache[word]

    def metatile(self, mt):
        o = 8 * mt
        x = [self.meta[o + 2 * i] | self.meta[o + 2 * i + 1] << 8 for i in range(4)] if o + 8 <= len(self.meta) else [0] * 4
        return [x[0], x[2], x[1], x[3]]

    def layer(self, k):
        o, W, H, _ = self.md.layers[k]
        img = np.zeros((H * 16, W * 16, 3), np.uint8); mask = np.zeros((H * 16, W * 16), bool)
        prio = np.zeros((H * 16, W * 16), bool)
        for cy in range(H):
            for cx in range(W):
                cell = self.md.cell(k, cx, cy)
                if k > 0 and (cell & 0x3FF) == 0:
                    continue
                for i, tw in enumerate(self.metatile(cell & 0x3FF)):
                    t, p, pr = self.tile(tw)
                    x0 = cx * 16 + (i & 1) * 8; y0 = cy * 16 + (i >> 1) * 8
                    img[y0:y0 + 8, x0:x0 + 8] = self.pal[p * 16 + t]
                    mask[y0:y0 + 8, x0:x0 + 8] = t != 0
                    prio[y0:y0 + 8, x0:x0 + 8] = pr
        return img, mask, prio

    def compose(self):
        L_ = [self.layer(k) for k in range(min(2, len(self.md.layers)))]
        H = max(a.shape[0] for a, _, _ in L_); W = max(a.shape[1] for a, _, _ in L_)
        out = np.zeros((H, W, 3), np.uint8); out[:] = self.pal[0]
        for hi in (False, True):
            for img, m, p in L_:
                sel = m & (p == hi)
                sub = out[:img.shape[0], :img.shape[1]]
                sub[sel] = img[sel]
        return out


if __name__ == '__main__':
    rom = open(sys.argv[1], 'rb').read()
    F = ROMField(rom, int(sys.argv[2], 16))
    Image.fromarray(F.compose()).save(sys.argv[3])
