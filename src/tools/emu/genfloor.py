import sys, json
sys.path.insert(0, '/tmp/claude-0/-home-claude/a299c82d-b96b-5dd0-8703-11d363742157/scratchpad/iris')
from emu_iris import *
ROMF = sys.argv[1] if len(sys.argv) > 1 and sys.argv[1].endswith('.sfc') else '/home/claude/lufia2/rom/orig.smc'
def gen(floor, seed_frames=0, out=None):
    emu = emu_from(S + 'cv3.state', ROMF); r = emu.ram
    r[0x1E696] = floor                      # floor counter (generated floor = this value)
    emu.run(1 + seed_frames)
    emu.held = {'UP'}; emu.run(16); emu.held = set(); emu.run(300)
    X = lambda a: r[0x10000 + (a & 0xFFFF)]
    info = dict(floor=floor, label=X(0xE696) - 1, theme=X(0xE697),
                start=(X(0xE6A9), X(0xE6AA)), stairs=(X(0xE6AB), X(0xE6AC)), extra=(X(0xE6AD), X(0xE6AE)),
                grid=[[X(0xEA00 + 16 * y + x) for x in range(16)] for y in range(16)],
                blocks=[[X(0xEB00 + 16 * y + x) for x in range(16)] for y in range(16)],
                monsters=[(X(0xE6B1 + i), X(0xE6D1 + i), X(0xF966 + i)) for i in range(X(0xE731))],
                chests=[(X(0xE736 + i), X(0xE73E + i), X(0xE746 + 2 * i) | X(0xE747 + 2 * i) << 8) for i in range(X(0xE734))],
                size=(w16(r, 0x05B9), w16(r, 0x05BB)), pos=(r[0x6BA], r[0x6E2]))
    if out:
        open(S + '../cave/' + out + '.state', 'wb').write(emu.save_state())
        emu.png(S + '../cave/' + out + '.png', scale=1)
    return info
if __name__ == '__main__':
    res = []
    for fl, sf in [(1, 0), (1, 7), (5, 3), (15, 1), (25, 0), (35, 2), (50, 0), (75, 4), (95, 5)]:
        i = gen(fl, sf, out='f%02d_%d' % (fl, sf)); res.append(i)
        print(fl, sf, 'theme', i['theme'], 'size', i['size'], 'start', i['start'], 'stairs', i['stairs'], 'extra', i['extra'],
              'mons', len(i['monsters']), 'chests', [(hex(c[2])) for c in i['chests']])
    json.dump(res, open(S + '../cave/floors.json', 'w'))
