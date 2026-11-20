"""Make a hi-colour battle background for the PC version (Lufia2SNESRecomp + art override).

    python3 hicolour.py picture.png out.l2hc [--x 0 --y 0]

The picture is shown wherever the game draws its battle background layer (BG1) or the backdrop, at
full colour (no 16-colour palettes, no tile limit). Transparent pixels (alpha 0) keep the game's own
pixel. --x/--y: where the picture's top-left sits on BG1's plane (0, 0 = where the game's own
background starts). Install as <exe dir>/assets/hicolour/battle_NN.l2hc (NN = background id, hex).

File format: "L2HC", u16 width, u16 height, i16 x, i16 y, then width*height u32 0xAARRGGBB (LE).
"""
import sys, struct
import numpy as np
from PIL import Image


def convert(png, out, x=0, y=0):
    im = Image.open(png).convert('RGBA')
    a = np.asarray(im).astype(np.uint32)
    argb = a[..., 3] << 24 | a[..., 0] << 16 | a[..., 1] << 8 | a[..., 2]
    with open(out, 'wb') as f:
        f.write(b'L2HC' + struct.pack('<HHhh', im.width, im.height, x, y))
        f.write(argb.astype('<u4').tobytes())
    return im.size


if __name__ == '__main__':
    a = sys.argv
    x = int(a[a.index('--x') + 1]) if '--x' in a else 0
    y = int(a[a.index('--y') + 1]) if '--y' in a else 0
    print(convert(a[1], a[2], x, y))
