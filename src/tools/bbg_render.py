"""Render a battle background straight from a ROM (original or bbg_build output) to a 256x224 PNG.

    python3 bbg_render.py rom.sfc ID out.png
"""
import sys
import numpy as np
from PIL import Image
import l2compress as C
from bbg_convert import decode_tilemap

lo = C.lo


def render(rom, bid):
    # records / tables: built ROMs relocate them (detected through the patched operands)
    def rd(a, n): return rom[lo(a):lo(a) + n]
    rec_base = int.from_bytes(rd(0x81B9D6, 3), 'little')           # LDA.l $97FD40,X operand
    rec = rd(rec_base + 4 * bid, 4)
    gbase = int.from_bytes(rd(0x81BA04, 2), 'little')               # ADC #$016C
    tbase = int.from_bytes(rd(0x81BA14, 2), 'little')               # ADC #$0179
    tab = int.from_bytes(rd(0x808EAA, 3), 'little') & 0xFF0000 | 0x8000   # LDA.l $A78000,X
    pal_bank = rom[lo(0x81BA33)]
    pal_addr = int.from_bytes(rd(0x81BA3A, 2), 'little')
    gfx = C.decode(rom[C.resource(rom, gbase + rec[1], tab):])[0]
    xt = rd(0xE0B000 + 5 * rec[1], 5) if len(rom) >= 0x400000 else bytes(5)   # extra tiles (bgext.asm)
    xcount = xt[3] | xt[4] << 8
    if xcount and rom[lo(0x81BAB9)] == 0x5C:                                   # JML: bgext.asm applied
        gfx = gfx.ljust(0x2000, b'\0') + rd(int.from_bytes(xt[:3], 'little'), xcount)
    tm = decode_tilemap(C.decode(rom[C.resource(rom, tbase + rec[0], tab):])[0])
    pal = rd((pal_bank << 16) | pal_addr + 64 * rec[2], 64)
    if len(rom) >= 0x400000 and rom[lo(0x81BAB9)] == 0x5C:                  # third palette (bgext.asm)
        pal += rd(0xE0A000 + 32 * rec[2], 32)
    cg = np.zeros((8, 16, 3))
    for row in range(2, 2 + len(pal) // 32):
        for i in range(16):
            v = pal[(row - 2) * 32 + 2 * i] | pal[(row - 2) * 32 + 2 * i + 1] << 8
            cg[row, i] = [(v & 31) * 255 / 31, (v >> 5 & 31) * 255 / 31, (v >> 10 & 31) * 255 / 31]
    img = np.zeros((224, 256, 3))
    for ty in range(28):
        for tx in range(32):
            w = tm[ty * 32 + tx]
            t = (w & 0x3FF) - 256
            if t < 0:
                t = 256 + (w & 0x3FF) - 86          # extra tiles: tile numbers 86-255
            p = w >> 10 & 7
            b = gfx[32 * t:32 * t + 32] if 0 <= t < len(gfx) // 32 else bytes(32)
            px = np.zeros((8, 8), int)
            for y in range(8):
                for x in range(8):
                    bit = 0x80 >> x
                    px[y, x] = ((b[2 * y] & bit) > 0) | ((b[2 * y + 1] & bit) > 0) << 1 | \
                               ((b[16 + 2 * y] & bit) > 0) << 2 | ((b[16 + 2 * y + 1] & bit) > 0) << 3
            if w & 0x4000: px = px[:, ::-1]
            if w & 0x8000: px = px[::-1, :]
            img[ty * 8:ty * 8 + 8, tx * 8:tx * 8 + 8] = cg[p][px]
    return Image.fromarray(img.astype(np.uint8)), rec


if __name__ == '__main__':
    rom = open(sys.argv[1], 'rb').read()
    im, rec = render(rom, int(sys.argv[2], 0))
    im.save(sys.argv[3]); print('record', rec.hex())
