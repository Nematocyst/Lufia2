"""Seasonal battle backgrounds: fast checks before the long conversion run.

    python3 seasons_pilot.py check PREP_DIR
        Seconds. For every prepared picture (<name>_fl.png + _mask.png + _grad.npy): unique 8x8 tiles
        needed (the screen holds 426), floor coverage in the band below the horizon, and where the sky
        ends. Pictures far over budget or with a patchy band are the ones that will show blocks.

    python3 seasons_pilot.py pilot PREP_DIR OUT_DIR [N] ['{"floor_row":16,...}']
        ~5 minutes for N=4. Converts the N pictures with the most unique tiles (the hardest ones) with
        the given settings (default: the current seasonal settings) and writes, in OUT_DIR:
        previews (what the game shows), zoom.png (4x crop of the band below the horizon: source |
        result) and the error per zone (scenery / band / floor). Judge a settings change here, then
        run the full conversion once.

Previews are compared with the prepared picture, not with emulator screenshots: the emulator's
screenshots are slightly darker in red and blue (about 10 points of error everywhere).
"""
import sys, os, glob, json, warnings
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
from PIL import Image

SEASON_KW = dict(focus=(0, 27), floor_row=16, row_weight=[1.0] * 12 + [2.0] * 16)
ZONES = {'scenery': (40, 96), 'band': (96, 128), 'floor': (128, 224)}


def names(prep):
    return sorted(os.path.basename(f)[:-7] for f in glob.glob(os.path.join(prep, '*_fl.png')))


def demand(img):
    a = np.asarray(img.convert('RGB'))[:224].reshape(28, 8, 32, 8, 3).transpose(0, 2, 1, 3, 4).reshape(28 * 32, -1)
    return len({x.tobytes() for x in a})


def check(prep):
    import bbg_gradient as G
    print('%-24s %6s  %-28s %s' % ('picture', 'tiles', 'floor in band y104/112/120', 'sky ends'))
    rows = []
    for n in names(prep):
        img = Image.open(os.path.join(prep, n + '_fl.png'))
        orig = np.asarray(img.convert('RGB'), float)
        mask = np.asarray(Image.open(os.path.join(prep, n + '_mask.png'))) > 127
        # band coverage: share of pixels that belong to the repeating texture (equal to a pixel 32 rows lower)
        same = np.abs(orig[96:136] - orig[128:168]).sum(2) < 6
        cov = [same[y - 96].mean() for y in (104, 112, 120)]
        d = demand(img); end = G.sky_end(mask)
        flag = []
        if d > 600: flag.append('MANY TILES')
        if (cov[1] + cov[2]) / 2 < 0.5: flag.append('PATCHY BAND')
        if end > 112: flag.append('SKY TOO LOW')
        rows.append((d, n))
        print('%-24s %6d  %-28s %4d  %s' % (n, d, ' '.join('%.2f' % c for c in cov), end, ' '.join(flag)))
    return [n for d, n in sorted(rows, reverse=True)]


def _one(args):
    prep, out, n, kw = args
    warnings.filterwarnings('ignore')
    import bbg_convert as B, bbg_gradient as G
    mask = np.asarray(Image.open(os.path.join(prep, n + '_mask.png'))) > 127
    grad = np.load(os.path.join(prep, n + '_grad.npy'))
    r = B.convert_n(Image.open(os.path.join(prep, n + '_fl.png')), npal=3, mask=mask, max_tiles=426,
                    backdrop=G.quantized(grad, G.sky_end(mask)), outliers=3, smooth=0.3, **kw)
    r[3].save(os.path.join(out, n + '.png'))
    return n


def pilot(prep, out, count=4, kw=None):
    from multiprocessing import Pool
    kw = dict(SEASON_KW, **(kw or {}))
    if 'focus' in kw: kw['focus'] = tuple(kw['focus'])
    os.makedirs(out, exist_ok=True)
    pick = check(prep)[:count]
    print('pilot:', ', '.join(pick), flush=True)
    with Pool(min(2, os.cpu_count() or 1)) as P:
        for n in P.imap_unordered(_one, [(prep, out, n, kw) for n in pick]):
            print('converted', n, flush=True)
    print('%-24s %s' % ('error (lower = closer)', '  '.join('%7s' % z for z in ZONES)))
    sheet = Image.new('RGB', (1024, 256 * len(pick)))
    for j, n in enumerate(pick):
        src = Image.open(os.path.join(prep, n + '_fl.png')).convert('RGB')
        prv = Image.open(os.path.join(out, n + '.png')).convert('RGB')
        a = np.asarray(src, float)[:224]; b = np.asarray(prv, float)
        print('%-24s %s' % (n, '  '.join('%7.1f' % np.abs(a[y0:y1] - b[y0:y1]).sum(2).mean() for y0, y1 in ZONES.values())))
        for k, im in enumerate((src, prv)):
            sheet.paste(im.crop((120, 88, 248, 152)).resize((512, 256), Image.NEAREST), (k * 512, j * 256))
    sheet.save(os.path.join(out, 'zoom.png'))
    json.dump(kw, open(os.path.join(out, 'settings.json'), 'w'))


if __name__ == '__main__':
    if sys.argv[1] == 'check':
        check(sys.argv[2])
    else:
        pilot(sys.argv[2], sys.argv[3], int(sys.argv[4]) if len(sys.argv) > 4 else 4,
              json.loads(sys.argv[5]) if len(sys.argv) > 5 else None)
