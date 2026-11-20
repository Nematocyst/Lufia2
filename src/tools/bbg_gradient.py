"""Backdrop gradients for Lufia II battle backgrounds.

The SNES backdrop (CGRAM colour 0) shows wherever every layer is see-through. An HDMA channel
rewrites colour 0 at the start of scanlines, so a sky drawn as see-through pixels becomes a smooth
vertical gradient that costs no tiles and none of the background's 30 colours.

    colors = fit(img, mask)               # 224 RGB colours, from the masked (sky) pixels, smoothed
    colors = stops([(0, (40, 80, 200)), (100, (180, 210, 255))])   # or from colour stops
    table  = hdma_table(colors)           # bytes for HDMA mode 3 -> $2121/$2121/$2122/$2122
    sky_mask(img, ...)                    # helper: see-through mask for a sky region

HDMA table format (mode 3, B-bus $21): count, CGADD, CGADD, CGDATA lo, CGDATA hi; count = 1-127 lines
(written once, held for `count` lines); a 0 byte ends the table.
"""
import numpy as np


def to555(rgb):
    return np.clip(np.round(np.asarray(rgb, float) / 255 * 31), 0, 31).astype(int)


def from555(c):
    return np.asarray(c, float) * 255 / 31


def stops(points, lines=224):
    """Linear interpolation between (line, (r, g, b)) colour stops (0-255 RGB)."""
    points = sorted(points)
    ys = [p[0] for p in points]
    out = np.zeros((lines, 3))
    for ch in range(3):
        out[:, ch] = np.interp(np.arange(lines), ys, [p[1][ch] for p in points])
    return out


def fit(img, mask, smooth=6, lines=224):
    """Per-scanline average colour of the masked pixels, gaps filled, then smoothed."""
    a = np.asarray(img.convert('RGB'), float)[:lines]
    m = np.asarray(mask, bool)[:lines]
    rows = [a[y][m[y]].mean(0) if m[y].any() else None for y in range(lines)]
    known = [y for y in range(lines) if rows[y] is not None]
    assert known, 'empty mask'
    out = np.zeros((lines, 3))
    for ch in range(3):
        out[:, ch] = np.interp(np.arange(lines), known, [rows[y][ch] for y in known])
    if smooth:
        k = np.exp(-0.5 * (np.arange(-3 * smooth, 3 * smooth + 1) / smooth) ** 2); k /= k.sum()
        pad = np.pad(out, ((3 * smooth, 3 * smooth), (0, 0)), mode='edge')
        out = np.stack([np.convolve(pad[:, ch], k, mode='valid') for ch in range(3)], 1)
    return out


def hdma_table(colors, end=None):
    """end: first line where the backdrop goes back to black (the game masks the leftmost 8 pixel
    columns with a window, which shows the backdrop; below the sky it should stay black as before)."""
    c = to555(colors)
    if end is not None:
        c[end:] = 0
    words = [int(r | g << 5 | b << 10) for r, g, b in c]
    out = bytearray()
    y = 0
    while y < len(words):
        n = 1
        while y + n < len(words) and words[y + n] == words[y] and n < 127:
            n += 1
        out += bytes([n, 0, 0, words[y] & 0xFF, words[y] >> 8])
        y += n
    out.append(0)
    return bytes(out)


def coldata_table(colors, end=None):
    """HDMA mode 0 table for COLDATA ($2132): the same gradient as the SNES fixed colour, which is what
    the subscreen shows where it is see-through. Translucent windows (results, messages) blend with
    the subscreen, so without this the sky inside them turns black. One byte per line, rotating
    red / green / blue (each channel is refreshed every 3 lines; the gradient changes more slowly).
    Below `end` everything is black again, as in the original game.
    The values are halved: the windows use half colour math, but the SNES skips the halving when the
    subscreen pixel is the fixed colour, so half the sky colour gives the original's darkened look."""
    c = to555(colors) // 2
    n = len(c)
    if end is None:
        end = n
    vals = []
    for y in range(n):
        if y >= end:
            vals.append(0xE0)                    # all three channels 0
        else:
            ch = y % 3
            vals.append((0x20, 0x40, 0x80)[ch] | int(c[y][ch]))
    out = bytearray()
    y = 0
    while y < n:
        if y >= end:                             # constant black: write once, hold
            k = min(127, n - y)
            out += bytes([k, 0xE0]); y += k
            continue
        k = min(127, end - y)
        out.append(0x80 | k); out += bytes(vals[y:y + k]); y += k
    out.append(0)
    return bytes(out)


def quantized(colors, end=None):
    """What the SNES shows: the gradient after 5-bit quantisation (for previews)."""
    c = from555(to555(colors))
    if end is not None:
        c[end:] = 0
    return c


def sky_end(mask):
    """First line below the lowest see-through pixel."""
    rows = np.where(np.asarray(mask, bool).any(1))[0]
    return int(rows.max()) + 1 if len(rows) else 0


def sky_mask(img, bottom, test):
    """See-through mask: pixels in rows < bottom for which test(r, g, b) is true, connected to the
    top edge (4-neighbour flood fill), so sky-coloured spots inside the scenery stay opaque."""
    a = np.asarray(img.convert('RGB')).astype(int)
    h, w = a.shape[:2]
    cand = np.zeros((h, w), bool)
    cand[:bottom] = test(a[:bottom, :, 0], a[:bottom, :, 1], a[:bottom, :, 2])
    m = np.zeros((h, w), bool)
    stack = [(0, x) for x in range(w) if cand[0, x]]
    for p in stack:
        m[p] = True
    while stack:
        y, x = stack.pop()
        for yy, xx in ((y - 1, x), (y + 1, x), (y, x - 1), (y, x + 1)):
            if 0 <= yy < h and 0 <= xx < w and cand[yy, xx] and not m[yy, xx]:
                m[yy, xx] = True; stack.append((yy, xx))
    return m
