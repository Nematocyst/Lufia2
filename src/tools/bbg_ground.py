"""Rebuild the ground of a 256x224 battle-background picture as an exactly repeating texture.

Generated pictures look tiled but no two 8x8 squares match, so they blow the 256-tile budget.
This keeps everything above `top` (sky, mountains, horizon) and, below it:
  * finds the most seamless W x H patch of the ground (W, H multiples of 8),
  * makes `levels` brightness versions of it, so the picture's light/dark shading stays,
  * paves the ground with them; each row of blocks (or each block, bands=False) picks the
    version nearest its own average brightness,
  * pastes the details (rocks, tufts) back over the texture: pixels whose colour is far from
    the grass, plus their direct neighbours for outlines.

    from bbg_ground import rebuild
    out, info = rebuild(img, top=88)
"""
import numpy as np
from PIL import Image


def _lum(a):
    return a @ np.array([0.299, 0.587, 0.114])


def best_patch(g, sizes=((32, 16), (32, 32), (64, 16), (64, 32)), step=4):
    """g: ground pixels (h, w, 3). Returns (y, x, W, H) of the patch whose wrap-around seams
    are least visible (edge mismatch compared with typical neighbour differences)."""
    h, w, _ = g.shape
    typ = np.abs(np.diff(g, axis=1)).mean() + 1e-6
    best = None
    for W, H in sizes:
        for y in range(0, h - H + 1, step):
            for x in range(0, w - W + 1, step):
                p = g[y:y + H, x:x + W]
                seam = (np.abs(p[:, -1] - p[:, 0]).mean() + np.abs(p[-1] - p[0]).mean()) / 2
                flat = abs(_lum(p).mean() - _lum(g).mean()) / 255        # prefer average-looking patches
                score = seam / typ + 4 * flat + 0.002 * (W * H) ** 0.5   # slight preference for small
                if best is None or score < best[0]:
                    best = (score, y, x, W, H)
    return best[1:]


def rebuild(img, top, levels=3, detail=60.0, patch=None, bands=True, detail_until=None):
    """detail=None drops all rocks/tufts; detail_until=y keeps them only above picture row y."""
    a = np.asarray(img.convert('RGB'), float).copy()
    g = a[top:]
    y, x, W, H = patch or best_patch(g)
    p = g[y:y + H, x:x + W].copy()
    gh, gw = g.shape[0], g.shape[1]
    blocks = [(by, bx) for by in range(0, gh, H) for bx in range(0, gw, W)]
    if bands:   # one brightness per row of blocks: reads as distance shading, no rectangles
        means = np.array([_lum(g[by:by + H]).mean() for by, bx in blocks])
    else:
        means = np.array([_lum(g[by:by + H, bx:bx + W]).mean() for by, bx in blocks])
    pm = _lum(p).mean()
    targets = np.quantile(means, np.linspace(0.15, 0.85, levels)) if levels > 1 else np.array([pm])
    versions = [np.clip(p * (t / pm), 0, 255) for t in targets]
    out = g.copy()
    for (by, bx), m in zip(blocks, means):
        v = versions[int(np.abs(targets - m).argmin())]
        hh, ww = min(H, gh - by), min(W, gw - bx)
        out[by:by + hh, bx:bx + ww] = v[:hh, :ww]
    grass = p.reshape(-1, 3)
    kept = 0
    for ty in range(0, gh - gh % 8, 8) if detail is not None else []:
        if detail_until is not None and ty + top >= detail_until:
            break
        for tx in range(0, gw, 8):
            sq = g[ty:ty + 8, tx:tx + 8].reshape(-1, 3)
            d = np.sqrt(((sq[:, None, :] - grass[None, ::7, :]) ** 2).sum(2)).min(1)
            far = (d > detail).reshape(8, 8)
            if far.mean() > 0.12:
                m = far.copy()
                m[1:] |= far[:-1]; m[:-1] |= far[1:]; m[:, 1:] |= far[:, :-1]; m[:, :-1] |= far[:, 1:]
                blk = out[ty:ty + 8, tx:tx + 8]
                blk[m] = g[ty:ty + 8, tx:tx + 8][m]
                kept += 1
    a[top:] = out
    return Image.fromarray(a.astype(np.uint8)), dict(patch=(y + top, x, W, H), levels=levels, detail_squares=kept)
