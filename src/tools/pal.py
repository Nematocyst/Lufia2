"""Palette-row usage logger for battles: which CGRAM rows are non-empty / change, buffer and master."""
from hd import *

def rows(buf):
    return [bytes(buf[32 * k:32 * k + 32]) for k in range(16)]

class Watch:
    def __init__(self, r):
        self.r = r; self.used = set(); self.changed = set(); self.mused = set(); self.mchanged = set()
        self.last = None; self.mlast = None
    def tick(self):
        cur = rows(self.r[0x320:0x520]); mas = rows(self.r[0x1F1DB:0x1F3DB])
        for k in range(16):
            if any(cur[k][2:]): self.used.add(k)          # colour 0 of a row is see-through; ignore it
            if any(mas[k][2:]): self.mused.add(k)
            if self.last and cur[k] != self.last[k]: self.changed.add(k)
            if self.mlast and mas[k] != self.mlast[k]: self.mchanged.add(k)
        self.last, self.mlast = cur, mas
    def report(self, tag):
        f = lambda s: ' '.join('%X' % k for k in sorted(s)) or '-'
        print('%-10s buffer used: %-32s changed: %s' % (tag, f(self.used), f(self.changed)))
        print('%-10s master used: %-32s changed: %s' % ('', f(self.mused), f(self.mchanged)))
