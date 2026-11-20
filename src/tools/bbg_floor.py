"""Edge-following floor rebuild for battle-background pictures (user rule: never cut the ground at a
straight horizontal line).

Instead of replacing everything below a row (bbg_ground.rebuild), this classifies each pixel as
"floor" or not by its local colour, and replaces only the floor that is connected to the bottom
edge, with a repeating texture patch. Rocks, bushes, cairns, ledges (anything that is not floor)
keep their original pixels, and the texture fades in over a few pixels away from them, so the
art's own contours stay intact. Corner rocks lower down are kept too.

    from bbg_floor import rebuild_floor
    out, info = rebuild_floor(img, sample=(140, 200, 64, 192), patch=(128, 32), min_row=60)
"""
import numpy as np
from PIL import Image
from scipy import ndimage
import bbg_ground


def floor_mask(a, sample, min_row, thr=3.0, min_obj=40, anchor=None, low=None):
    """a: HxWx3 float. sample = (y0, y1, x0, x1) region known to be plain floor.
    anchor: keep floor connected to this row (default: the bottom row; use a row inside the sample when
    the floor colour changes towards the bottom). low = (row, size): below that row, non-floor blobs
    smaller than size become floor too (light patches in a painted lawn)."""
    y0, y1, x0, x1 = sample
    sm = ndimage.uniform_filter(a, size=(5, 5, 1))                       # local colour
    ref = sm[y0:y1, x0:x1].reshape(-1, 3)
    mu = ref.mean(0); cov = np.cov(ref.T) + np.eye(3) * 4
    inv = np.linalg.inv(cov)
    d = sm - mu
    dist = np.sqrt(np.einsum('...i,ij,...j->...', d, inv, d))
    fl = dist < thr
    fl[:min_row] = False
    fl = ndimage.binary_opening(fl, np.ones((3, 3)))
    obj = ~fl                                                            # drop tiny non-floor specks
    lab, n = ndimage.label(obj)
    sizes = ndimage.sum(obj, lab, range(1, n + 1))
    small = np.isin(lab, [i + 1 for i, s in enumerate(sizes) if s < min_obj])
    fl |= small
    if low is not None:
        big = np.isin(lab, [i + 1 for i, s in enumerate(sizes) if s < low[1]])
        big[:low[0]] = False
        fl |= big
    fl[:min_row] = False
    lab, n = ndimage.label(fl)                                           # floor touching the bottom
    keep = [l for l in np.unique(lab[-1 if anchor is None else anchor]) if l]
    return np.isin(lab, keep)


def periodic(p):
    """Moisan periodic + smooth decomposition: returns the periodic part of patch p (HxWx3), which tiles
    without seams; only the smooth component that carries the edge jumps is removed."""
    H, W = p.shape[:2]
    v = np.zeros_like(p)
    v[0] += p[-1] - p[0]; v[-1] += p[0] - p[-1]
    v[:, 0] += p[:, -1] - p[:, 0]; v[:, -1] += p[:, 0] - p[:, -1]
    q = np.arange(H)[:, None]; r = np.arange(W)[None, :]
    den = 2 * np.cos(2 * np.pi * q / H) + 2 * np.cos(2 * np.pi * r / W) - 4
    den[0, 0] = 1
    s = np.fft.fft2(v, axes=(0, 1)) / den[..., None]
    s[0, 0] = 0
    return p - np.real(np.fft.ifft2(s, axes=(0, 1)))


def rebuild_floor(img, sample, patch=(128, 32), min_row=60, margin=4, fade=8, thr=3.0, patch_rows=None, drop_below=None,
                  seamless=False, anchor=None, low=None):
    """drop_below: rows from here down become plain floor (objects there sit under the battle windows).
    seamless: make the patch tile without visible seams (soft painted floors)."""
    a = np.asarray(img.convert('RGB'), float)
    H, W = a.shape[:2]
    fl = floor_mask(a, sample, min_row, thr, anchor=anchor, low=low)
    if drop_below is not None:
        fl[drop_below:] = True
    pw, ph = patch
    pr = patch_rows or (sample[0], sample[1])
    g = a[pr[0]:pr[1]]
    gy, gx, _, _ = bbg_ground.best_patch(g, sizes=((pw, ph),), step=8)
    p = g[gy:gy + ph, gx:gx + pw]
    if seamless:
        p = periodic(p)
    tex = np.tile(p, (H // ph + 2, W // pw + 2, 1))
    off = (-min_row) % ph                                                # align rows to the tile grid
    tex = tex[off:off + H, :W]
    # match the texture's brightness per row band to the original floor (keeps distance shading)
    dist = ndimage.distance_transform_edt(fl)                            # distance to non-floor
    alpha = np.clip((dist - margin) / float(fade), 0, 1)[..., None]
    out = a * (1 - alpha) + tex * alpha
    info = dict(patch=(pr[0] + gy, gx, pw, ph), floor_px=int(fl.sum()), replaced=float((alpha > 0.99).mean()))
    return Image.fromarray(np.clip(out, 0, 255).astype(np.uint8)), fl, info
