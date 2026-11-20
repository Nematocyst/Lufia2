"""Lufia II battle background tile check (same rules as the "Lufia II Tile Check" page).

Usage:  python3 lufia2_tile_check.py picture.png [more.png ...]
Needs numpy, scipy, Pillow.

For each picture: fit to the SNES screen (256 wide, top 224 rows), find the sky (becomes a free colour
gradient) and the plain ground (becomes a repeating texture, ~88 tiles), count the 8x8 tiles that hold
scenery, and forecast how blocky the band below the horizon will look after conversion (426 tiles max).
Verdict: PASS (forecast <= 15.5), BORDERLINE (<= 17.5), REDO (above, sky below line 112, or too short).
Calibrated on 48 converted grassland pictures. Writes <name>_tilemap.png next to each picture:
red = costs its own tile, blue = repeating ground, grey = free sky.
"""
import sys, os
import numpy as np
from PIL import Image
from scipy import ndimage

W, H, BUDGET = 256, 224, 426


def fit(img):
    img = img.convert('RGB'); w, h = img.size
    fh = round(h * W / w)
    if fh < H:
        return None
    return img.resize((W, fh), Image.BOX).crop((0, 0, W, H))


def _top(m, row=0):
    lab, _ = ndimage.label(m)
    return np.isin(lab, [l for l in np.unique(lab[row]) if l])


def sky_mask(a, hmax=100, tol=30):
    sm = ndimage.uniform_filter(a, (3, 3, 1))
    gm = np.abs(np.diff(sm, axis=0, prepend=sm[:1])).sum(2) + np.abs(np.diff(sm, axis=1, prepend=sm[:, :1])).sum(2)
    cand = gm < 18; cand[hmax:] = False
    cand = _top(cand)
    ref = np.zeros((hmax, 3)); ok = np.zeros(hmax, bool)
    for y in range(hmax):
        px = a[y][cand[y]]
        if len(px) >= 16: ref[y] = np.median(px, 0); ok[y] = True
    ys = np.where(ok)[0]
    if len(ys) == 0: return np.zeros(a.shape[:2], bool)
    for c in range(3): ref[:, c] = np.interp(np.arange(hmax), ys, ref[ys, c])
    m = np.zeros(a.shape[:2], bool)
    m[:hmax] = np.sqrt(((a[:hmax] - ref[:, None, :]) ** 2).sum(2)) < tol
    m[:hmax] &= np.arange(hmax)[:, None] <= ys.max()
    m = _top(m)
    k = _top(ndimage.binary_opening(m, np.ones((3, 3))))
    return m & ndimage.binary_dilation(k)


def floor_mask(a, sample=(150, 205, 32, 224), min_row=96, thr=3.0, min_obj=40, anchor=160, low=(128, 400), drop_below=168):
    y0, y1, x0, x1 = sample
    sm = ndimage.uniform_filter(a, size=(5, 5, 1))
    ref = sm[y0:y1, x0:x1].reshape(-1, 3)
    mu = ref.mean(0); inv = np.linalg.inv(np.cov(ref.T) + np.eye(3) * 4)
    d = sm - mu
    fl = np.sqrt(np.maximum(0, np.einsum('...i,ij,...j->...', d, inv, d))) < thr
    fl[:min_row] = False
    fl = ndimage.binary_opening(fl, np.ones((3, 3)))
    obj = ~fl
    lab, n = ndimage.label(obj)
    sizes = np.r_[0, ndimage.sum(obj, lab, range(1, n + 1))]
    fl |= (lab > 0) & (sizes[lab] < min_obj)
    big = (lab > 0) & (sizes[lab] < low[1]); big[:low[0]] = False
    fl |= big
    fl[:min_row] = False
    fl = _top(fl, anchor)
    fl[drop_below:] = True
    return fl


def check(path):
    img = fit(Image.open(path))
    if img is None:
        return dict(verdict='REDO', reasons=['Picture too wide for its height: needs full-height framing (about 1341x1173).'])
    a = np.asarray(img, float)
    sky, fl = sky_mask(a), floor_mask(a)
    other = ~(sky | fl)
    t_other = other.reshape(28, 8, 32, 8).any((1, 3))
    t_sky = sky.reshape(28, 8, 32, 8).all((1, 3))
    tiles = int(t_other.sum()) + 88
    step = np.abs(np.diff(a, axis=1)).sum(2)
    detail = float(step[other[:, 1:]].mean()) if other[:, 1:].any() else 0.0
    rows = np.where(sky.any(1))[0]; sky_end = int(rows.max()) + 1 if len(rows) else 0
    forecast = 0.08 * tiles + 0.153 * detail - 28.5
    verdict = 'REDO' if forecast > 17.5 or sky_end > 112 else 'BORDERLINE' if forecast > 15.5 else 'PASS'
    reasons = []
    if sky_end > 112: reasons.append(f'Sky reaches line {sky_end}; it must end above line 112. Raise the horizon.')
    if tiles > 500: reasons.append(f'A lot of scenery: ~{tiles} tiles for a budget of {BUDGET}. Raise the ground or simplify the band just below the horizon.')
    elif tiles > 480: reasons.append(f'Scenery on the heavy side: ~{tiles} tiles for a budget of {BUDGET}.')
    if detail > 38: reasons.append('Lots of fine detail in the scenery (thin branches, fences, small trees, glints). Use larger, softer shapes.')
    # tile map
    g = a.mean(2, keepdims=True)
    tk = np.repeat(np.repeat(np.where(t_other, 2, np.where(t_sky, 0, 1)), 8, 0), 8, 1)[..., None]
    out = np.where(tk == 2, g * 0.55 + np.array([255, 60, 40]) * 0.45,
          np.where(tk == 1, g * 0.55 + np.array([70, 130, 255]) * 0.45, g * 0.35 + np.array([150, 165, 190])))
    Image.fromarray(out.clip(0, 255).astype(np.uint8)).resize((512, 448), Image.NEAREST).save(os.path.splitext(path)[0] + '_tilemap.png')
    return dict(verdict=verdict, tiles=tiles, forecast=round(forecast, 1), sky_end=sky_end, reasons=reasons)


if __name__ == '__main__':
    for p in sys.argv[1:]:
        r = check(p)
        print(f"{os.path.basename(p)}: {r['verdict']}" + (f"  tiles ~{r['tiles']}/{BUDGET}  forecast {r['forecast']}  sky ends {r['sky_end']}" if 'tiles' in r else ''))
        for s in r['reasons']: print('   - ' + s)
