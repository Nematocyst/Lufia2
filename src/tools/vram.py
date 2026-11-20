"""VRAM census for battles: which 16-word (4bpp 8x8) blocks are ever non-zero or change."""
import ctypes as C
import numpy as np
from hd import *

def vram(emu):
    p = emu.lib.retro_get_memory_data(3)
    return np.frombuffer(bytes((C.c_uint8 * 65536).from_address(p)), np.uint16)   # 32768 words

class Census:
    def __init__(self):
        self.used = np.zeros(2048, bool)      # per 16-word block
        self.changed = np.zeros(2048, bool)
        self.last = None
    def take(self, v):
        blk = v.reshape(2048, 16)
        self.used |= blk.any(1)
        if self.last is not None:
            self.changed |= (blk != self.last).any(1)
        self.last = blk.copy()

def battle(rom, state, bg, group, actions, census, every=4):
    emu = start(rom, state, bg, group); r = emu.ram
    emu.run(640)
    census.last = None
    def run(n):
        for i in range(n):
            emu.run(1)
            if i % every == 0: census.take(vram(emu))
    run(60)
    def press(b, gap=40):
        emu.held = {b}; run(4); emu.held = set(); run(gap)
    for a in actions:
        if a == 'attack':
            for _ in range(6): press('A')
        elif a == 'spell':
            press('A'); press('A', 60); press('UP'); press('A'); run(10)
            emu.held = {'UP'}; run(20); emu.held = {'UP', 'A'}; run(6); emu.held = set(); run(40)
            press('A'); press('A'); press('A', 20)
        run(900)
    return emu


def stamp_run(rom, state, bg, group, actions, region=None, value=0xFFFF, shots_every=20, flush=True):
    """Replay a battle; at frame 700 fill VRAM words region=(a, b) with value. Returns (frames, vram at end)."""
    emu = start(rom, state, bg, group)
    emu.run(700)
    if region is not None:
        p = emu.lib.retro_get_memory_data(3)
        arr = (C.c_uint16 * 32768).from_address(p)
        for w in range(region[0], region[1] + 1):
            arr[w] = value
        emu.load_state(emu.save_state())     # make the emulator re-decode its tile caches
    elif flush:
        emu.load_state(emu.save_state())
    frames = []
    def run(n):
        for i in range(n):
            emu.run(1)
            if i % shots_every == 0: frames.append(np.asarray(emu.image()).copy())
    def press(b, gap=40):
        emu.held = {b}; run(4); emu.held = set(); run(gap)
    run(40)
    for a in actions:
        if a == 'attack':
            for _ in range(6): press('A')
        elif a == 'spell':
            press('A'); press('A', 60); press('UP'); press('A'); run(10)
            emu.held = {'UP'}; run(20); emu.held = {'UP', 'A'}; run(6); emu.held = set(); run(40)
            press('A'); press('A'); press('A', 20)
        elif a == 'menus':
            for d in ('UP', 'LEFT', 'DOWN'):
                emu.held = {d}; run(20); emu.held = {d, 'A'}; run(6); emu.held = set(); run(50)
                for _ in range(3): press('B', 30)
        run(900)
    return frames, vram(emu).copy()
