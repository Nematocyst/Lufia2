"""Build editor "map packs" (JSON with a metatile atlas) from the emulator dumps + the ROM.

    python3 mappack.py ROM DUMPDIR OUTDIR [map ids...]      (DUMPDIR '-' = ROM-only graphics)
DUMPDIR holds map_XX.wram / map_XX.vram (from batch.py: warp in, dump WRAM + VRAM).
Pack: {map, name, layers:[{w,h,cells}], ntiles, atlas (PNG data URL, 32 metatiles per row),
       backdrop}. Cells come from the ROM (MapData), graphics from the dump.
"""
import sys, os, json, io, base64
import numpy as np
from PIL import Image
sys.path.insert(0, '/home/claude/lufia2/tools/mapview'); sys.path.insert(0, '/home/claude/lufia2/tools')
import render as R
from mapdata import MapData
from mapheader import MapHeader


def atlas(F, n):
    cols = 32; rows = (n + cols - 1) // cols
    img = np.zeros((rows * 16, cols * 16, 4), np.uint8)
    for m in range(n):
        x0 = (m % cols) * 16; y0 = (m // cols) * 16
        for i, tw in enumerate(F.metatile(m)):
            t, p, pr = F.tile(tw)
            sub = img[y0 + (i >> 1) * 8:y0 + (i >> 1) * 8 + 8, x0 + (i & 1) * 8:x0 + (i & 1) * 8 + 8]
            sub[..., :3] = F.pal[p * 16 + t]; sub[..., 3] = np.where(t != 0, 255, 0)
    b = io.BytesIO(); Image.fromarray(img, 'RGBA').save(b, 'PNG', optimize=True)
    return 'data:image/png;base64,' + base64.b64encode(b.getvalue()).decode()


def pack(rom, dumpdir, mid):
    """Graphics from the emulator dump when there is one (exact, incl. runtime palettes), else from
    the ROM alone (romrender: base palette; works for new maps $F2+ and any edited ROM)."""
    wp = os.path.join(dumpdir, 'map_%02X.wram' % mid) if dumpdir else ''
    md = MapData(rom, mid)
    if wp and os.path.exists(wp):
        w = open(wp, 'rb').read()
        v = open(os.path.join(dumpdir, 'map_%02X.vram' % mid), 'rb').read()
        F = R.Field(w, v, 0x8000)
        n = (R.w16(w, 0x1D03E) - F.mt) // 8            # metatiles before the attribute table
        coll = w[0x5AA] // 2
    else:
        import romrender
        F = romrender.ROMField(rom, mid)
        tsfull = romrender.resource(rom, 0x130 + romrender.table_byte(rom, 0x80EB8B, mid))
        n = ((tsfull[4] | tsfull[5] << 8) - 0x10) // 8
        coll = 1
    n = max(1, min(n, 1024))
    try:
        import scriptdec
        name = scriptdec.map_name(mid)
    except Exception:
        name = ''
    layers = []
    for k, (o, W, H, sid) in enumerate(md.layers):
        layers.append({'w': W, 'h': H, 'cells': [c for row in md.grid(k) for c in row]})
    return {'map': mid, 'name': name, 'layers': layers, 'ntiles': n, 'atlas': atlas(F, n),
            'backdrop': '#%02x%02x%02x' % tuple(F.pal[0]), 'collisionLayer': coll,
            'header': MapHeader(rom, mid).to_json()}


if __name__ == '__main__':
    rom = open(sys.argv[1], 'rb').read(); dd = sys.argv[2]; out = sys.argv[3]
    if dd in ('-', 'none'):
        dd = None                                  # ROM-only packs
    os.makedirs(out, exist_ok=True)
    ids = [int(x, 16) for x in sys.argv[4:]] or (sorted(int(f[4:6], 16) for f in os.listdir(dd) if f.endswith('.wram'))
                                                  if dd else [m for m in range(0xF0)])
    for mid in ids:
        try:
            p = pack(rom, dd, mid)
            json.dump(p, open(os.path.join(out, 'map_%02X.json' % mid), 'w'))
        except Exception as ex:
            print('map %02X: %s' % (mid, ex))
    print('packs:', len(os.listdir(out)))
