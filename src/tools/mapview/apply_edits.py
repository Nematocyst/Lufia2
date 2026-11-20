"""Apply map edits copied from the Lufia II Map Editor to a ROM and make a BPS patch.

    python3 apply_edits.py IN.sfc OUT.sfc [--free D78000] edits.json [more.json ...]   (writes OUT.bps too)
Each file: {"lufia2_map_edits":1, "map":"D6", "edits":[[layer, x, y, value], ...],
            "header": {"exits":[[id,x0,y0,x1,y1,params,destx,desty,destmap]...], "events":[[id,x0,y0,x1,y1]...],
                       "points":[[id,x,y]...], "npcs":[[id,x,y,...]...]}}   (header optional; lists replace the map's)
Edits are written in place when the re-compressed map fits; otherwise the map goes to --free
(an expansion area; a 2.5 MB ROM is padded to 4 MB first) and its resource entry is repointed.
"""
import sys, json
sys.path.insert(0, '/home/claude/lufia2/tools/mapview'); sys.path.insert(0, '/home/claude/lufia2/mods')
from mapdata import MapData
from mapheader import MapHeader
import mkpatch

def main():
    args = sys.argv[1:]
    free = None
    if '--free' in args:
        i = args.index('--free'); free = int(args[i + 1], 16); del args[i:i + 2]
    src, dst = args[0], args[1]
    rom0 = open(src, 'rb').read(); rom = bytearray(rom0)
    if free and len(rom) < 0x400000:
        rom += bytes(0x400000 - len(rom))
    for f in args[2:]:
        E = json.load(open(f)); mid = int(E['map'], 16)
        if E.get('edits'):
            m = MapData(rom, mid)
            for k, x, y, v in E['edits']:
                m.set(k, x, y, v)
            rom, n, end = m.write(rom, free)
            where = 'in place' if end is None else 'moved to $%06X' % free
            if end is not None:
                free = end
            print('map $%02X: %d cells, %d bytes compressed (%d in place), %s' % (mid, len(E['edits']), n, m.used, where))
        if E.get('header'):
            h = MapHeader(rom, mid); h.from_json(E['header'])
            rom, n, end = h.write(rom, free)
            where = 'in place' if end is None else 'moved to $%06X' % free
            if end is not None:
                free = end
            print('map $%02X header: %d bytes, %s' % (mid, n, where))
    open(dst, 'wb').write(rom)
    open(dst.rsplit('.', 1)[0] + '.bps', 'wb').write(mkpatch.bps(rom0, bytes(rom)))

if __name__ == '__main__':
    main()
