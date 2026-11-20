"""Convert a 256x224 picture into a Lufia II battle background.

Output (what BattleBackgroundPrepare $81:B9C7 loads):
  graphics  up to 256 4bpp tiles (8 KB), uploaded to VRAM word $3000; tilemap tile numbers are 256 + i
  tilemap   32x32 words, palette 2 or 3; stored as deltas: word0, then word[k-1] - word[k]
  palette   64 bytes: CGRAM rows 2 and 3 (16 BGR555 colours each; colour 0 is transparent)
Only the top part is visible in battle (the windows cover rows 17+), but the whole 32x28 is filled.

Transparency (for backdrop gradients): pass mask (224x256 bool, True = see-through). Masked pixels
become colour 0, so the backdrop colour (CGRAM 0, set per scanline by a gradient) shows there.
A tile that is entirely see-through costs nothing: it uses one shared all-zero tile.

    from bbg_convert import convert
    gfx, tilemap, palette, preview, ntiles = convert(image, max_tiles=256, mask=None, backdrop=None)
    backdrop: optional list of 224 RGB tuples drawn behind the preview (the gradient).
"""
import numpy as np
from PIL import Image
from sklearn.cluster import KMeans

ROWS_VISIBLE = 28        # rows 0-16 always visible, 17-21 during turns, 22-27 faintly through the windows
EXTRA_BASE = 86          # extra tiles (beyond 256) use tile numbers 86-255 (VRAM $2560-$2FFF, see bgext.asm)
MAX_TILES_EXT = 256 + 256 - EXTRA_BASE    # 426


def tile_number(k):
    """Tilemap tile number of the k-th output tile: 256-511 for the first 256 (VRAM $3000), then 86-255."""
    return 256 + k if k < 256 else EXTRA_BASE + (k - 256)
CLEAR = np.array([400.0, -300.0, 400.0])    # feature value for see-through pixels (keeps merges apart)


def to555(rgb):
    rgb = np.clip(np.round(np.asarray(rgb, float) / 255 * 31), 0, 31).astype(int)
    return rgb


def from555(c):
    return (np.asarray(c, float) * 255 / 31)


def _palette(pixels, k, seed=0, weight=None):
    """k colours (5-bit) for an Nx3 float RGB pixel array (optional per-pixel weights)."""
    if len(pixels) == 0:
        return np.zeros((1, 3), int)
    uniq = np.unique(to555(pixels), axis=0)
    if len(uniq) <= k:
        return uniq
    km = KMeans(n_clusters=k, n_init=4, random_state=seed).fit(pixels, sample_weight=weight)
    return np.unique(to555(km.cluster_centers_), axis=0)


def _map(tile, pal, m=None):
    """tile 8x8x3 float -> indices into pal (1..len), 0 where m (see-through), and squared error."""
    pc = from555(pal)
    d = ((tile.reshape(-1, 1, 3) - pc[None]) ** 2).sum(2)
    idx = d.argmin(1)
    e = d[np.arange(64), idx]
    idx = idx + 1
    if m is not None:
        mm = m.reshape(-1)
        idx[mm] = 0
        e[mm] = 0
    return idx, e.sum()


def _coherent(errs, smooth):
    """Pick a palette per tile, but penalise neighbours that disagree: switching palette between
    two adjacent tiles changes the colours at the 8x8 boundary and shows as a square edge.
    Iterated conditional modes on cost = tile error + smooth * median error * disagreements."""
    n = len(errs); rows = n // 32
    grp = errs.argmin(1)
    if smooth <= 0:
        return grp
    lam = smooth * float(np.median(np.abs(errs[:, 0] - errs[:, 1])) + 1e-9) * 4
    for _ in range(10):
        changed = 0
        for i in range(n):
            y, x = divmod(i, 32)
            nb = [grp[j] for j in (i - 32 if y else -1, i + 32 if y < rows - 1 else -1,
                                   i - 1 if x else -1, i + 1 if x < 31 else -1) if j >= 0]
            cost = [errs[i, g] + lam * sum(1 for v in nb if v != g) for g in (0, 1)]
            g = int(np.argmin(cost))
            if g != grp[i]:
                grp[i] = g; changed += 1
        if not changed:
            break
    return grp


def _split_global(tiles, tmask, w_rows, seed, smooth):
    keep = ~tmask.reshape(-1)
    px = tiles.reshape(-1, 3)
    if keep.sum() < 30:
        return None
    km = KMeans(n_clusters=30, n_init=4, random_state=seed).fit(px[keep])
    cols = np.unique(to555(km.cluster_centers_), axis=0)
    cf = from555(cols)
    lab = ((px[:, None, :] - cf[None]) ** 2).sum(2).argmin(1).reshape(len(tiles), 64)
    use = np.zeros((len(tiles), len(cols)))
    for i, l in enumerate(lab):
        l = l[~tmask[i].reshape(-1)]
        np.add.at(use[i], l, 1)
    best = None
    rows = len(tiles) // 32
    for r in range(3, rows - 2):
        grp = np.repeat((np.arange(rows) >= r).astype(int), 32)
        for _ in range(6):
            sets = []
            for g in (0, 1):
                cnt = (use[grp == g] * w_rows[grp == g][:, None]).sum(0)
                order = [c for c in np.argsort(-cnt) if cnt[c] > 0][:15]
                sets.append(sorted(order) or [0])
            pals = [cols[s_] for s_ in sets]
            errs = np.array([[_map(t, pals[g], m)[1] for g in (0, 1)] for t, m in zip(tiles, tmask)]) * w_rows[:, None]
            new = _coherent(errs, smooth)
            if (new == grp).all():
                break
            grp = new
        e = float(errs[np.arange(len(tiles)), grp].sum())
        if best is None or e < best[2]:
            best = (grp.copy(), pals, e)
    return best


def convert(img, max_tiles=256, seed=0, smooth=1.0, focus=None, mask=None, backdrop=None):
    """focus=(first_row, last_row): 8-pixel rows that get the tile budget first (default: all of 0-16)."""
    img = img.convert('RGB').resize((256, 224), Image.LANCZOS) if img.size != (256, 224) else img.convert('RGB')
    a = np.asarray(img, float)
    tiles = a.reshape(28, 8, 32, 8, 3).transpose(0, 2, 1, 3, 4).reshape(28 * 32, 8, 8, 3)[:ROWS_VISIBLE * 32]
    if mask is None:
        mask = np.zeros((224, 256), bool)
    mask = np.asarray(mask, bool)
    tmask = mask.reshape(28, 8, 32, 8).transpose(0, 2, 1, 3).reshape(28 * 32, 8, 8)[:ROWS_VISIBLE * 32]
    opaque_px = ~tmask.reshape(len(tiles), 64)
    # two palettes of 15 colours. Several starting splits are tried (colour clusters, and every
    # horizontal split such as sky/ground); each is refined, and the one with least error wins.
    feat = np.array([t.reshape(-1, 3)[o].mean(0) if o.any() else CLEAR for t, o in zip(tiles, opaque_px)])
    rows = len(tiles) // 32
    starts = [KMeans(n_clusters=2, n_init=4, random_state=seed).fit_predict(feat)]
    starts += [np.repeat((np.arange(rows) >= r).astype(int), 32) for r in range(3, rows - 2, 2)]
    w_rows = np.repeat(np.array([1.0 if r < 17 else 0.25 if r < 22 else 0.08 for r in range(rows)]), 32)
    # smooth tiles (sky, slopes, gradients) show colour errors as flat squares; noisy tiles hide them
    tex = np.array([np.abs(np.diff(t, axis=1)).mean() for t in tiles])
    w_rows = w_rows * (1 + 6 / (1 + tex / 4))

    def refine(grp, its):
        for _ in range(its):
            pals = []
            for g in (0, 1):
                m = grp == g if (grp == g).any() else np.ones(len(tiles), bool)
                px = tiles[m].reshape(-1, 3)[opaque_px[m].reshape(-1)]
                w = np.repeat(w_rows[m], 64)[opaque_px[m].reshape(-1)]
                pals.append(_palette(px, 15, seed, w if len(w) else None))
            errs = np.array([[_map(t, pals[g], mk)[1] for g in (0, 1)] for t, mk in zip(tiles, tmask)]) * w_rows[:, None]
            grp = _coherent(errs, smooth)
        return grp, pals, float(errs[np.arange(len(tiles)), grp].sum())
    scored = sorted((refine(g0, 1)[2], k) for k, g0 in enumerate(starts))
    best = None
    for e, k in scored[:3]:                       # refine the three best candidates fully
        r = refine(starts[k], 3)
        if best is None or r[2] < best[2]:
            best = r
    grp, pals, _ = best
    alt = _split_global(tiles, tmask, w_rows, seed, smooth)
    if alt is not None and alt[2] < best[2]:
        grp, pals, _ = alt
    idx = np.array([_map(t, pals[g], mk)[0] for t, g, mk in zip(tiles, grp, tmask)])        # (896, 64)
    # fully see-through tiles: palette doesn't matter; put them all in group 0 so they share one tile
    clear = ~opaque_px.any(1)
    grp = np.where(clear, 0, grp)

    def variants(t):
        t = t.reshape(8, 8)
        return [(t, 0), (t[:, ::-1], 1), (t[::-1, :], 2), (t[::-1, ::-1], 3)]
    uniq = {}            # key (pal, bytes) -> list of positions
    for n, (t, g) in enumerate(zip(idx, grp)):
        best = None
        for v, f in variants(t):
            key = (g, v.tobytes())
            if key in uniq:
                best = (key, f); break
        if best is None:
            best = ((g, t.reshape(8, 8).tobytes()), 0)
            uniq[best[0]] = []
        uniq[best[0]].append((n, best[1]))
    keys = list(uniq)
    if len(keys) > max_tiles:
        def wpos(n):
            r = n // 32
            if row_weight is not None:
                return row_weight[r]
            if focus is None:
                return 1.0 if r < 17 else 0.25 if r < 22 else 0.08
            if focus[0] <= r <= focus[1]:
                return 1.0
            return 0.15 if r < 22 else 0.04
        data = {}
        for g in (0, 1):
            ks = [k for k in keys if k[0] == g]
            if ks:
                pc = from555(np.vstack([[0, 0, 0], pals[g]]))
                pc[0] = CLEAR                    # see-through pixels never merge with opaque ones
                X = np.array([pc[np.frombuffer(k[1], dtype=idx.dtype)].reshape(-1) for k in ks])
                w = np.array([sum(wpos(n) for n, f in uniq[k]) for k in ks])
                tex = np.array([np.abs(np.diff(x.reshape(8, 8, 3), axis=1)).mean() for x in X])
                w = w * (1 + 20 / (1 + tex / 4))
                data[g] = (ks, X, w)
        cache = {}

        def fit(g, k):
            if (g, k) not in cache:
                ks, X, w = data[g]
                k = min(k, len(ks))
                km = KMeans(n_clusters=k, n_init=2, random_state=seed).fit(X, sample_weight=w)
                reps, err = [], 0.0
                for c in range(k):
                    m = np.where(km.labels_ == c)[0]
                    d = ((X[m][:, None, :] - X[m][None, :, :]) ** 2).sum(2)
                    r = m[(d * w[m][:, None]).sum(0).argmin()]          # weighted medoid
                    reps.append((m, r))
                    err += (((X[m] - X[r]) ** 2).sum(1) * w[m]).sum()
                cache[(g, k)] = (reps, err)
            return cache[(g, k)]
        if len(data) == 1:
            split = {g: max_tiles for g in data}
        else:
            n0, n1 = len(data[0][0]), len(data[1][0])
            best = None
            for k0 in range(max(1, max_tiles - n1), min(n0, max_tiles - 1) + 1, 8):
                e = fit(0, k0)[1] + fit(1, max_tiles - k0)[1]
                if best is None or e < best[0]:
                    best = (e, k0)
            k0 = best[1]
            for k in range(max(1, k0 - 7), min(n0, k0 + 7, max_tiles - 1) + 1):   # refine
                e = fit(0, k)[1] + fit(1, max_tiles - k)[1]
                if e < best[0]:
                    best = (e, k)
            split = {0: best[1], 1: max_tiles - best[1]}
        out_keys, remap = [], {}
        for g in data:
            ks = data[g][0]
            for m, r in fit(g, split[g])[0]:
                out_keys.append(ks[r])
                for i in m:
                    remap[ks[i]] = ks[r]
        merged = {}
        for k, pos in uniq.items():
            merged.setdefault(remap[k], []).extend(pos)
        uniq = merged
        keys = out_keys
    tile_no = {k: i for i, k in enumerate(keys)}
    gfx = bytearray()
    for k in keys:
        t = np.frombuffer(k[1], dtype=idx.dtype).reshape(8, 8)
        b = bytearray(32)       # SNES 4bpp: rows of planes 0/1 (16 bytes), then planes 2/3 (16 bytes)
        for y in range(8):
            for x in range(8):
                v = int(t[y, x]); bit = 0x80 >> x
                if v & 1: b[2 * y] |= bit
                if v & 2: b[2 * y + 1] |= bit
                if v & 4: b[16 + 2 * y] |= bit
                if v & 8: b[16 + 2 * y + 1] |= bit
        gfx += b
    words = [0] * 1024
    for k, pos in uniq.items():
        for n, f in pos:
            y, x = divmod(n, 32)
            words[y * 32 + x] = int((tile_number(tile_no[k])) | (2 + int(k[0])) << 10 | int(f) << 14)
    for y in range(ROWS_VISIBLE, 32):          # unused rows repeat the last one
        words[y * 32:(y + 1) * 32] = words[(ROWS_VISIBLE - 1) * 32:ROWS_VISIBLE * 32]
    stored = [words[0]] + [(words[k - 1] - words[k]) & 0xFFFF for k in range(1, 1024)]
    tilemap = b''.join(w.to_bytes(2, 'little') for w in stored)
    palette = bytearray()
    for g in (0, 1):
        cols = [(0, 0, 0)] + [tuple(c) for c in pals[g]]
        cols += [(0, 0, 0)] * (16 - len(cols))
        for r, gg, bb in cols:
            palette += int(r | gg << 5 | bb << 10).to_bytes(2, "little")
    # preview of what the SNES will show (backdrop gradient behind see-through pixels)
    back = np.zeros((ROWS_VISIBLE * 8, 256, 3))
    if backdrop is not None:
        back[:] = np.asarray(backdrop, float)[:ROWS_VISIBLE * 8, None, :]
    prev = back.copy()
    for k, pos in uniq.items():
        t = np.frombuffer(k[1], dtype=idx.dtype).reshape(8, 8)
        pc = from555(np.vstack([[0, 0, 0], pals[k[0]]]))
        for n, f in pos:
            tt = t
            if f & 1: tt = tt[:, ::-1]
            if f & 2: tt = tt[::-1, :]
            y, x = divmod(n, 32)
            block = pc[tt]
            sel = tt == 0
            block[sel] = back[y * 8:y * 8 + 8, x * 8:x * 8 + 8][sel]
            prev[y * 8:y * 8 + 8, x * 8:x * 8 + 8] = block
    preview = Image.fromarray(prev.astype(np.uint8))
    return bytes(gfx), tilemap, bytes(palette), preview, len(keys)


def decode_tilemap(stored):
    w = [stored[2 * i] | stored[2 * i + 1] << 8 for i in range(len(stored) // 2)]
    out = [w[0]]
    for x in w[1:]:
        out.append((out[-1] - x) & 0xFFFF)      # $81:BA59: running A -= stored[k]
    return out


# ---------------------------------------------------------------------------------------------
# N-palette conversion (3 palettes = CGRAM rows 2, 3, 4; row 4 is free in battle, see
# lufia2-palettes.md). convert() above stays exactly as it was for 2 palettes, so pictures
# approved with it convert identically.

def _palette_out(pixels, k, seed=0, weight=None, outliers=0):
    """_palette with `outliers` slots reserved for the colours it gets most wrong (small areas of a
    distinctive colour, e.g. red roofs among greens, which plain k-means averages away)."""
    if outliers <= 0 or len(pixels) < 64:
        return _palette(pixels, k, seed, weight)
    base = _palette(pixels, k - outliers, seed, weight)
    if len(base) < k - outliers:
        return base
    d = np.sqrt(((pixels[:, None, :] - from555(base)[None]) ** 2).sum(2)).min(1)
    bad = d > max(40.0, np.quantile(d, 0.985))
    if bad.sum() < outliers:
        return base
    km = KMeans(n_clusters=outliers, n_init=2, random_state=seed).fit(pixels[bad])
    return np.unique(np.vstack([base, to555(km.cluster_centers_)]), axis=0)


def _map_all(tiles, tmask, pal):
    """All tiles at once: indices (N, 64) into pal (1..len, 0 where see-through) and errors (N,)."""
    pc = from555(pal)
    px = tiles.reshape(len(tiles), 64, 3)
    d = ((px[:, :, None, :] - pc[None, None]) ** 2).sum(3)       # (N, 64, P)
    idx = d.argmin(2)
    e = np.take_along_axis(d, idx[..., None], 2)[..., 0]
    m = tmask.reshape(len(tiles), 64)
    e = np.where(m, 0, e)
    return np.where(m, 0, idx + 1), e.sum(1)


def _coherent_n(errs, smooth):
    n, k = errs.shape
    rows = n // 32
    grp = errs.argmin(1)
    if smooth <= 0 or k < 2:
        return grp
    srt = np.sort(errs, 1)
    lam = smooth * float(np.median(srt[:, 1] - srt[:, 0]) + 1e-9) * 4
    for _ in range(10):
        changed = 0
        for i in range(n):
            y, x = divmod(i, 32)
            nb = [grp[j] for j in (i - 32 if y else -1, i + 32 if y < rows - 1 else -1,
                                   i - 1 if x else -1, i + 1 if x < 31 else -1) if j >= 0]
            cost = [errs[i, g] + lam * sum(1 for v in nb if v != g) for g in range(k)]
            g = int(np.argmin(cost))
            if g != grp[i]:
                grp[i] = g; changed += 1
        if not changed:
            break
    return grp


def convert_n(img, npal=3, max_tiles=256, seed=0, smooth=1.0, focus=None, mask=None, backdrop=None, salience=0.0,
              outliers=0, floor_row=None, row_weight=None):
    """Like convert(), with npal palettes of 15 colours (rows 2 .. 1+npal). Returns the same tuple;
    the palette is 32*npal bytes.
    floor_row: tiles in tile rows >= floor_row all use the last palette, which is built from those
    tiles only (a floor-only palette). Tiles above may still pick it when it suits them.
    row_weight: 28 weights (one per tile row) for the tile-merging step; overrides focus there."""
    if npal == 2:
        return convert(img, max_tiles, seed, smooth, focus, mask, backdrop)
    img = img.convert('RGB').resize((256, 224), Image.LANCZOS) if img.size != (256, 224) else img.convert('RGB')
    a = np.asarray(img, float)
    tiles = a.reshape(28, 8, 32, 8, 3).transpose(0, 2, 1, 3, 4).reshape(28 * 32, 8, 8, 3)[:ROWS_VISIBLE * 32]
    if mask is None:
        mask = np.zeros((224, 256), bool)
    mask = np.asarray(mask, bool)
    tmask = mask.reshape(28, 8, 32, 8).transpose(0, 2, 1, 3).reshape(28 * 32, 8, 8)[:ROWS_VISIBLE * 32]
    opaque_px = ~tmask.reshape(len(tiles), 64)
    rows = len(tiles) // 32
    feat = np.array([t.reshape(-1, 3)[o].mean(0) if o.any() else CLEAR for t, o in zip(tiles, opaque_px)])
    w_rows = np.repeat(np.array([1.0 if r < 17 else 0.25 if r < 22 else 0.08 for r in range(rows)]), 32)
    tex = np.array([np.abs(np.diff(t, axis=1)).mean() for t in tiles])
    w_rows = w_rows * (1 + 6 / (1 + tex / 4))
    # starting splits: colour clusters, and horizontal bands (sky / horizon / ground and similar)
    starts = [KMeans(n_clusters=npal, n_init=4, random_state=seed).fit_predict(feat)]
    forced = np.zeros(len(tiles), bool)
    if floor_row is not None:
        forced = np.repeat(np.arange(rows) >= floor_row, 32)
    FP = npal - 1
    import itertools
    for cuts in itertools.combinations(range(3, rows - 2, 3), npal - 1):
        band = np.zeros(rows, int)
        for c in cuts:
            band[c:] += 1
        starts.append(np.repeat(band, 32))
    if forced.any():
        starts = [np.where(forced, FP, np.minimum(s, FP - 1)) for s in starts]

    # salience: small areas of distinctive colour (red roofs among greens) get extra weight, so the
    # palettes keep them. Per-pixel weight x (1 + salience * distance to the 12 main colours / 64)^2.
    pxw = np.ones((len(tiles), 64))
    if salience > 0:
        allpx = tiles.reshape(-1, 3)[opaque_px.reshape(-1)]
        main = KMeans(n_clusters=12, n_init=2, random_state=seed).fit(allpx[::7]).cluster_centers_
        dd = np.sqrt(((tiles.reshape(-1, 1, 3) - main[None]) ** 2).sum(2)).min(1).reshape(len(tiles), 64)
        pxw = (1 + salience * dd / 64) ** 2

    def refine(grp, its):
        for _ in range(its):
            pals = []
            for g in range(npal):
                if forced.any():
                    m = forced if g == FP else (grp == g) & ~forced
                    if not m.any():
                        m = ~forced
                else:
                    m = grp == g if (grp == g).any() else np.ones(len(tiles), bool)
                px = tiles[m].reshape(-1, 3)[opaque_px[m].reshape(-1)]
                w = (np.repeat(w_rows[m], 64) * pxw[m].reshape(-1))[opaque_px[m].reshape(-1)]
                pals.append(_palette_out(px, 15, seed, w if len(w) else None, outliers))
            errs = np.stack([_map_all(tiles, tmask, p)[1] for p in pals], 1) * w_rows[:, None]
            grp = _coherent_n(errs, smooth)
            grp[forced] = FP
        return grp, pals, float(errs[np.arange(len(tiles)), grp].sum())
    scored = sorted((refine(g0, 1)[2], k) for k, g0 in enumerate(starts))
    best = None
    for e, k in scored[:3]:
        r = refine(starts[k], 3)
        if best is None or r[2] < best[2]:
            best = r
    grp, pals, _ = best
    idx = np.zeros((len(tiles), 64), int)
    for g in range(npal):
        ii, _ = _map_all(tiles, tmask, pals[g])
        idx[grp == g] = ii[grp == g]
    clear = ~opaque_px.any(1)
    grp = np.where(clear, 0, grp)

    def variants(t):
        t = t.reshape(8, 8)
        return [(t, 0), (t[:, ::-1], 1), (t[::-1, :], 2), (t[::-1, ::-1], 3)]
    uniq = {}
    for n, (t, g) in enumerate(zip(idx, grp)):
        hit = None
        for v, f in variants(t):
            key = (int(g), v.tobytes())
            if key in uniq:
                hit = (key, f); break
        if hit is None:
            hit = ((int(g), t.reshape(8, 8).tobytes()), 0)
            uniq[hit[0]] = []
        uniq[hit[0]].append((n, hit[1]))
    keys = list(uniq)
    if len(keys) > max_tiles:
        def wpos(n):
            r = n // 32
            if row_weight is not None:
                return row_weight[r]
            if focus is None:
                return 1.0 if r < 17 else 0.25 if r < 22 else 0.08
            if focus[0] <= r <= focus[1]:
                return 1.0
            return 0.15 if r < 22 else 0.04
        data = {}
        for g in range(npal):
            ks = [k for k in keys if k[0] == g]
            if ks:
                pc = from555(np.vstack([[0, 0, 0], pals[g]]))
                pc[0] = CLEAR
                X = np.array([pc[np.frombuffer(k[1], dtype=idx.dtype)].reshape(-1) for k in ks])
                w = np.array([sum(wpos(n) for n, f in uniq[k]) for k in ks])
                tx = np.array([np.abs(np.diff(x.reshape(8, 8, 3), axis=1)).mean() for x in X])
                w = w * (1 + 20 / (1 + tx / 4))
                data[g] = (ks, X, w)
        cache = {}

        def fit(g, k):
            ks, X, w = data[g]
            k = max(1, min(k, len(ks)))
            if (g, k) not in cache:
                if k == len(ks):
                    cache[(g, k)] = ([(np.array([i]), i) for i in range(k)], 0.0)
                else:
                    km = KMeans(n_clusters=k, n_init=2, random_state=seed).fit(X, sample_weight=w)
                    reps, err = [], 0.0
                    for c in range(k):
                        m = np.where(km.labels_ == c)[0]
                        d = ((X[m][:, None, :] - X[m][None, :, :]) ** 2).sum(2)
                        r = m[(d * w[m][:, None]).sum(0).argmin()]
                        reps.append((m, r))
                        err += (((X[m] - X[r]) ** 2).sum(1) * w[m]).sum()
                    cache[(g, k)] = (reps, err)
            return cache[(g, k)]
        gs = list(data)
        sizes = {g: len(data[g][0]) for g in gs}
        # proportional start, then move tiles between palettes while the total error drops
        alloc = {g: max(1, int(max_tiles * sizes[g] / sum(sizes.values()))) for g in gs}
        while sum(alloc.values()) > max_tiles:
            g = max(gs, key=lambda g: alloc[g]); alloc[g] -= 1
        while sum(alloc.values()) < max_tiles:
            g = max(gs, key=lambda g: sizes[g] - alloc[g]); alloc[g] += 1
        for step in (16, 8, 4, 2, 1):
            improved = True
            while improved:
                improved = False
                base = sum(fit(g, alloc[g])[1] for g in gs)
                best_move = None
                for a_ in gs:
                    for b_ in gs:
                        if a_ == b_ or alloc[a_] - step < 1 or alloc[b_] + step > sizes[b_]:
                            continue
                        e = base - fit(a_, alloc[a_])[1] - fit(b_, alloc[b_])[1] \
                            + fit(a_, alloc[a_] - step)[1] + fit(b_, alloc[b_] + step)[1]
                        if e < base - 1e-6 and (best_move is None or e < best_move[0]):
                            best_move = (e, a_, b_)
                if best_move:
                    _, a_, b_ = best_move
                    alloc[a_] -= step; alloc[b_] += step; improved = True
        out_keys, remap = [], {}
        for g in gs:
            ks = data[g][0]
            for m, r in fit(g, alloc[g])[0]:
                out_keys.append(ks[r])
                for i in m:
                    remap[ks[i]] = ks[r]
        merged = {}
        for k, pos in uniq.items():
            merged.setdefault(remap[k], []).extend(pos)
        uniq = merged
        keys = out_keys
    tile_no = {k: i for i, k in enumerate(keys)}
    gfx = bytearray()
    for k in keys:
        t = np.frombuffer(k[1], dtype=idx.dtype).reshape(8, 8)
        b = bytearray(32)
        for y in range(8):
            for x in range(8):
                v = int(t[y, x]); bit = 0x80 >> x
                if v & 1: b[2 * y] |= bit
                if v & 2: b[2 * y + 1] |= bit
                if v & 4: b[16 + 2 * y] |= bit
                if v & 8: b[16 + 2 * y + 1] |= bit
        gfx += b
    words = [0] * 1024
    for k, pos in uniq.items():
        for n, f in pos:
            y, x = divmod(n, 32)
            words[y * 32 + x] = int((tile_number(tile_no[k])) | (2 + int(k[0])) << 10 | int(f) << 14)
    for y in range(ROWS_VISIBLE, 32):
        words[y * 32:(y + 1) * 32] = words[(ROWS_VISIBLE - 1) * 32:ROWS_VISIBLE * 32]
    stored = [words[0]] + [(words[k - 1] - words[k]) & 0xFFFF for k in range(1, 1024)]
    tilemap = b''.join(w.to_bytes(2, 'little') for w in stored)
    palette = bytearray()
    for g in range(npal):
        cols = [(0, 0, 0)] + [tuple(c) for c in pals[g]]
        cols += [(0, 0, 0)] * (16 - len(cols))
        for r, gg, bb in cols:
            palette += int(r | gg << 5 | bb << 10).to_bytes(2, "little")
    back = np.zeros((ROWS_VISIBLE * 8, 256, 3))
    if backdrop is not None:
        back[:] = np.asarray(backdrop, float)[:ROWS_VISIBLE * 8, None, :]
    prev = back.copy()
    for k, pos in uniq.items():
        t = np.frombuffer(k[1], dtype=idx.dtype).reshape(8, 8)
        pc = from555(np.vstack([[0, 0, 0], pals[k[0]]]))
        for n, f in pos:
            tt = t
            if f & 1: tt = tt[:, ::-1]
            if f & 2: tt = tt[::-1, :]
            y, x = divmod(n, 32)
            block = pc[tt]
            sel = tt == 0
            block[sel] = back[y * 8:y * 8 + 8, x * 8:x * 8 + 8][sel]
            prev[y * 8:y * 8 + 8, x * 8:x * 8 + 8] = block
    preview = Image.fromarray(prev.astype(np.uint8))
    return bytes(gfx), tilemap, bytes(palette), preview, len(keys)
