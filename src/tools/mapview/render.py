"""Render a Lufia II field map from a WRAM+VRAM dump (first prototype)."""
import sys, numpy as np
from PIL import Image

def w16(b, o): return b[o] | b[o + 1] << 8

def pal(wram):
    c = np.zeros((256, 3), np.uint8)
    for i in range(256):
        v = w16(wram, 0x320 + 2 * i)
        c[i] = [(v & 31) << 3, (v >> 5 & 31) << 3, (v >> 10 & 31) << 3]
    return c

def tile4(vram, base, n):
    """8x8 4bpp tile -> 8x8 array of colour indices 0-15."""
    o = (base + n * 32) & 0xFFFF
    t = np.zeros((8, 8), np.uint8)
    for y in range(8):
        p0, p1, p2, p3 = vram[o + 2*y], vram[o + 2*y + 1], vram[o + 16 + 2*y], vram[o + 17 + 2*y]
        for x in range(8):
            s = 7 - x
            t[y, x] = (p0 >> s & 1) | (p1 >> s & 1) << 1 | (p2 >> s & 1) << 2 | (p3 >> s & 1) << 3
    return t

class Field:
    def __init__(self, wram, vram, charbase=0x0000):
        self.w = wram; self.v = vram; self.cb = charbase
        self.pal = pal(wram); self.cache = {}
        F = 0x10000
        self.mt = w16(wram, F + 0xD03C)
        self.layers = []
        for k in range(4):
            base = w16(wram, F + 0xD008 + 2*k); W = wram[F + 0xD010 + 2*k]; H = wram[F + 0xD018 + 2*k]
            if base and W and H:
                self.layers.append((base, W, H))

    def tile(self, word):
        if word not in self.cache:
            t = tile4(self.v, self.cb, word & 0x3FF)
            if word & 0x4000: t = t[:, ::-1]
            if word & 0x8000: t = t[::-1, :]
            self.cache[word] = (t, (word >> 10) & 7, word >> 13 & 1)
        return self.cache[word]

    def metatile(self, m):
        o = 0x10000 + self.mt + 8 * m
        x = [w16(self.w, o + 2*i) for i in range(4)]
        return [x[0], x[2], x[1], x[3]]          # stored column-major: TL, BL, TR, BR

    def render(self, k):
        base, W, H = self.layers[k]
        img = np.zeros((H * 16, W * 16, 3), np.uint8); mask = np.zeros((H*16, W*16), bool)
        prio = np.zeros((H*16, W*16), bool)
        for cy in range(H):
            for cx in range(W):
                cell = w16(self.w, 0x10000 + base + 2 * (cy * W + cx))
                ws = self.metatile(cell & 0x3FF)
                for i, tw in enumerate(ws):
                    t, p, pr = self.tile(tw)
                    x0 = cx*16 + (i & 1)*8; y0 = cy*16 + (i >> 1)*8
                    img[y0:y0+8, x0:x0+8] = self.pal[p*16 + t]
                    mask[y0:y0+8, x0:x0+8] = t != 0
                    prio[y0:y0+8, x0:x0+8] = pr
        self.last_prio = prio
        return img, mask

    def compose(self, order=(1, 0)):
        """Mode-1 style: back layer low, front low, back high, front high (order = back, front)."""
        L = []
        for k in order:
            if k < len(self.layers):
                img, m = self.render(k); L.append((img, m, self.last_prio))
        H = max(a.shape[0] for a, _, _ in L); W = max(a.shape[1] for a, _, _ in L)
        out = np.zeros((H, W, 3), np.uint8)
        out[:] = self.pal[0]
        for hi in (False, True):
            for img, m, p in L:
                sel = m & (p == hi)
                sub = out[:img.shape[0], :img.shape[1]]
                sub[sel] = img[sel]
        return out

if __name__ == '__main__':
    pre = sys.argv[1]; cb = int(sys.argv[2], 16) if len(sys.argv) > 2 else 0
    F = Field(open(pre + '.wram', 'rb').read(), open(pre + '.vram', 'rb').read(), cb)
    print('metatiles at', hex(F.mt), 'layers', F.layers)
    for k in range(len(F.layers)):
        img, m = F.render(k)
        Image.fromarray(img).save('%s_L%d.png' % (pre, k))
