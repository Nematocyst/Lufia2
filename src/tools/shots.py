"""Boot Lufia II to field control, save a state, then warp to maps and capture screenshots.

python3 shots.py boot <rom> <state_out>        # title -> new game -> first field control
python3 shots.py warp <rom> <state> <map> <a> <b> <png> [frames]
"""
import sys
from retro import Emu

CORE = '/tmp/claude-0/-home-claude/a299c82d-b96b-5dd0-8703-11d363742157/scratchpad/snes9x/libretro/snes9x_libretro.so'
MAP = 0x05AC


def boot(rom, out, shots=None):
    emu = Emu(CORE, rom)
    emu.run(300)
    last = None
    for i in range(400):
        # mash through title, file select, name entry and intro text
        emu.press('START' if i % 7 == 0 else 'A', hold=2, gap=10)
        m = emu.ram[MAP] | emu.ram[MAP + 1] << 8
        if shots and i % 40 == 0:
            emu.png('%s_%03d.png' % (shots, i))
        if m != last:
            print('step', i, 'map', hex(m)); last = m
    open(out, 'wb').write(emu.save_state())
    emu.png(out + '.png')


def warp(rom, state, mapid, a, b, png, frames=240, extra=()):
    emu = Emu(CORE, rom)
    emu.run(2)
    emu.load_state(open(state, 'rb').read())
    emu.run(5)
    r = emu.ram
    r[0x05AE] = mapid; r[0x05B2] = 0; r[0x05B8] = a; r[0x05B0] = b
    r[0x05B3] = 1; r[0x05B5] |= 0x88
    out = []
    emu.run(200)
    r[0x0582] = 0; r[0x0581] = 0x81             # fade back in (the warp script normally does this)
    for f in range(frames):
        emu.run(1)
        if f in extra:
            out.append(emu.png(png.replace('.png', '_f%d.png' % f)))
    print('map now', hex(r[MAP] | r[MAP + 1] << 8))
    out.append(emu.png(png))
    return emu


if __name__ == '__main__':
    if sys.argv[1] == 'boot':
        boot(sys.argv[2], sys.argv[3], sys.argv[4] if len(sys.argv) > 4 else None)
    else:
        rom, state, m, a, b, png = sys.argv[2:8]
        frames = int(sys.argv[8]) if len(sys.argv) > 8 else 240
        warp(rom, state, int(m, 16), int(a, 16), int(b, 16), png, frames)
