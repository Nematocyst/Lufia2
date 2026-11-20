"""Battle test harness for Lufia II.

    python3 bt.py boot  <rom> <state_out>                 new game -> first field control
    python3 bt.py world <rom> <field_state> <state_out>   warp to world map (43,151), save state there
    python3 bt.py battle <rom> <world_state> <bg_id> <png> walk until a battle starts with bg id forced
"""
import sys
from retro import Emu, CORE

MAP = 0x05AC


def w16(r, a):
    return r[a] | r[a + 1] << 8


def boot(rom, out):
    emu = Emu(CORE, rom)
    emu.run(300)
    last = None
    for i in range(400):
        emu.press('START' if i % 7 == 0 else 'A', hold=2, gap=10)
        m = w16(emu.ram, MAP)
        if m != last:
            print('step', i, 'map', hex(m)); last = m
    open(out, 'wb').write(emu.save_state())
    emu.png(out + '.png')


def load(rom, state):
    emu = Emu(CORE, rom)
    emu.run(2)
    emu.load_state(open(state, 'rb').read())
    emu.run(2)
    return emu


def world(rom, state, out):
    emu = load(rom, state)
    r = emu.ram
    r[0x05AE] = 0; r[0x05B8] = 43; r[0x05B0] = 151; r[0x05B3] = 1; r[0x05B5] |= 0x88
    emu.run(200)
    r[0x0582] = 0; r[0x0581] = 0x81
    emu.run(120)
    print('map now', hex(w16(r, MAP)))
    open(out, 'wb').write(emu.save_state())
    emu.png(out + '.png')


def to_battle(emu, bg=None, max_frames=6000, log=None):
    """Walk up/down on the world map until an encounter fires; force the background id.
    Returns the frame at which the battle started (or None)."""
    r = emu.ram
    dirs = ['UP', 'DOWN', 'LEFT', 'RIGHT']
    for f in range(max_frames):
        if bg is not None:
            r[0x1F8A0] = bg
        emu.held = {dirs[(f // 40) % 2]}
        emu.run(1)
        if log is not None:
            log.append(r[0x81])
        if r[0x1F8A3] == 1:
            emu.held = set()
            if bg is not None:
                r[0x1F8A0] = bg
            return f
    emu.held = set()
    return None


if __name__ == '__main__':
    cmd = sys.argv[1]
    if cmd == 'boot':
        boot(sys.argv[2], sys.argv[3])
    elif cmd == 'world':
        world(sys.argv[2], sys.argv[3], sys.argv[4])
    elif cmd == 'battle':
        rom, state, bg, png = sys.argv[2], sys.argv[3], int(sys.argv[4], 0), sys.argv[5]
        emu = load(rom, state)
        f = to_battle(emu, bg)
        print('encounter at frame', f)
        masks = []
        for i in range(600):
            r = emu.ram
            r[0x1F8A0] = bg if i < 60 else r[0x1F8A0]
            emu.run(1)
            masks.append(r[0x81])
        print('HDMA masks seen in battle:', sorted({hex(m) for m in masks}))
        emu.png(png)
