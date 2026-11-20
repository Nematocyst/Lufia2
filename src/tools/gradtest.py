"""Build a gradient test ROM and capture battle frames.

    python3 gradtest.py build out.sfc ID=picture.png@mask.png@gradient.npy ...   (bbg_build + bgext.asm + battletest.asm) [--npal 3] [--tiles 426]
    python3 gradtest.py turn rom.sfc state bg out_prefix                          battle, one turn, results; frames
"""
import sys, subprocess
import numpy as np
from PIL import Image

ASAR = '/home/claude/lufia2/deps/asar/build/asar/bin/asar'
MODS = '/home/claude/lufia2/mods/'
ORIG = '/home/claude/lufia2/rom/orig.smc'


def build(out, specs, base=ORIG, battletest=True, npal=2, max_tiles=256, convert_kw=None):
    import bbg_build
    jobs = []
    for a in specs:
        bid, spec = a.split('=', 1)
        p = spec.split('@')
        job = [int(bid, 0), p[0]]
        if len(p) > 1:
            job += [np.asarray(Image.open(p[1]).convert('L')) > 127, np.load(p[2])]
        jobs.append(tuple(job))
    rep = bbg_build.build(base, out, jobs, npal, max_tiles, convert_kw)
    for asm in ['bgext.asm'] + (['battletest.asm'] if battletest else []):
        subprocess.run([ASAR, '--fix-checksum=off', MODS + asm, out], check=True)
    return rep


def turn(rom, state, bg, prefix, group=1):
    from hd import start, chans
    emu = start(rom, state, bg, group); r = emu.ram
    frames = []
    emu.run(700); frames.append(emu.image())
    for b in ('A',) * 6:
        emu.press(b, hold=4, gap=40)
    for i in range(30):
        emu.run(20); frames.append(emu.image())
    for i, f in enumerate(frames):
        f.save('%s_%02d.png' % (prefix, i))
    return frames


if __name__ == '__main__':
    if sys.argv[1] == 'build':
        args = sys.argv[3:]; npal = 2
        if '--npal' in args:
            i = args.index('--npal'); npal = int(args[i + 1]); del args[i:i + 2]
        mt = 256
        if '--tiles' in args:
            i = args.index('--tiles'); mt = int(args[i + 1]); del args[i:i + 2]
        for r in build(sys.argv[2], args, npal=npal, max_tiles=mt):
            print(r)
    else:
        turn(sys.argv[2], sys.argv[3], int(sys.argv[4], 0), sys.argv[5])
