"""Field EVENT script decompiler (the second field interpreter, table $80:E5A4, 191 opcodes).

    python3 eventdec.py [ROM] [-o DIR]       -> DIR/event_XX.txt per map + summary on stdout

What these scripts are: per-map "mechanism" scripts run by up to 8 event slots
(FieldEventTimerTickWithServices $80:CBAE, each frame): switches, pressure plates, doors,
pushable blocks, bombs/arrows hitting things, etc. They are separate from the map's dialogue
scripts (scriptdec.py).

Data: $8F:8000 + 3*map = word offset (+$8000) and bank delta (+$8F); $FFFF = no events.
Block = 16 header words (offsets from the block base) -> 16 lists of [id byte, word offset] ending $FF.
FieldStartEvent(X = 2*list, Y = 2*id) runs base+word. List 0 = trigger kinds started by field code
(id = Y/2 at the call sites: 0, 2, 3 position, 4, 5, ...); list 5 (X=$0A) = condition lists
(data read by FieldTestConditionList, not scripts). Pointer operands are offsets from the block
base (they may cross into the next bank).

Operand lengths: tools/event_ops.py (static analysis) + the overrides below (list operands).
Spec letters: b byte, w word, p pointer (offset from base), L byte list ending $FF.
"""
import sys, json, os
sys.path.insert(0, '/home/claude/lufia2/tools')
import rom as R

J = json.load(open('/home/claude/lufia2/build/event_ops.json'))
NAMES = json.load(open('/home/claude/lufia2/tools/data/event_op_names.json')) \
    if os.path.exists('/home/claude/lufia2/tools/data/event_op_names.json') else {}

OVERRIDE = {
    0x04: 'bbp', 0x70: 'bbp', 0x05: 'bb',
    0x12: 'bp', 0x14: 'bp', 0x16: 'bp', 0x18: 'bp', 0x6D: 'bp', 0x6E: 'bp', 0x6F: 'bp',
    0x73: 'bp', 0x74: 'bp',
    0x13: 'b', 0x15: 'b', 0x17: 'b', 0x72: 'b',
    0x1E: 'pp',
    # $41-$54: point arrays (x, y, x2, y2 at $7F:D1A3/D1E3/D223/D263) x (set, add, sub, inc, dec)
    **{0x41 + 5 * a + k: ('bb' if k < 3 else 'b') for a in range(4) for k in range(5)}, 0x20: 'Lp', 0x26: 'Lp', 0x27: 'Lp', 0xA9: 'Lp',
}


def spec_from_paths(k):
    v = J['%02X' % k]
    paths = [p for p, e in v['paths'] if e not in ('trap', 'var')]
    best = None
    for p in paths:
        s = p.replace('wS', 'p').replace('S', '')
        if '<' in s:
            continue
        if best is None or len(s.replace('p', 'pp')) > len(best.replace('p', 'pp')) or \
                (len(s.replace('p', 'pp')) == len(best.replace('p', 'pp')) and 'p' in s):
            best = s
    return best or ''


SPEC = {}
FLOW = {}
for k in range(191):
    SPEC[k] = OVERRIDE.get(k, spec_from_paths(k))
    v = J['%02X' % k]
    ends = {e for p, e in v['paths']}
    if v['handler'] == '80CC42':
        FLOW[k] = 'end'
    elif all(p.endswith('wS') for p, e in v['paths'] if e == 'next') and ends <= {'next'} and k not in OVERRIDE:
        FLOW[k] = 'jump'
    else:
        FLOW[k] = None
FLOW[0xAA] = 'end'     # return from gosub (A9): pops the call record ($80:D849)


def opname(k):
    return NAMES.get('%02X' % k, {}).get('name') or 'ev_%02X' % k


class Map:
    def __init__(self, d, m):
        self.d = d; self.m = m
        t = R.to_off(0x8F8000 + 3 * m)
        x = d[t] | d[t + 1] << 8
        self.ok = x != 0xFFFF
        if not self.ok:
            return
        self.base = R.to_off(((0x8F + d[t + 2]) << 16) | ((x + 0x8000) & 0xFFFF))
        self.lists = {}
        for k in range(16):
            off = self.w(self.base + 2 * k)
            p = self.base + off; ent = []
            if off < 0x20 or off > 0x4000:
                continue
            while d[p] != 0xFF and len(ent) < 64:
                ent.append((d[p], self.w(p + 1))); p += 3
            self.lists[k] = ent

    def w(self, off):
        return self.d[off] | self.d[off + 1] << 8

    def decode(self):
        d = self.d
        self.ins = {}; self.labels = {}; self.errors = []
        work = []
        for k, ent in self.lists.items():
            if k == 5:
                continue                     # condition lists: data
            for i, w in ent:
                a = self.base + w
                self.labels.setdefault(a, []).append('list %d id %d' % (k, i)); work.append(a)
        while work:
            a = work.pop()
            while a not in self.ins:
                op = d[a]
                if op >= 191:
                    self.errors.append('bad op %02X at +%04X' % (op, a - self.base)); break
                p = a + 1; args = []
                for c in SPEC[op]:
                    if c == 'b':
                        args.append(('b', d[p])); p += 1
                    elif c in 'wp':
                        v = self.w(p); p += 2
                        args.append((c, v))
                        if c == 'p':
                            t = self.base + v
                            self.labels.setdefault(t, []).append('ref'); work.append(t)
                    elif c == 'L':
                        lst = []
                        while d[p] != 0xFF and len(lst) < 255:
                            lst.append(d[p]); p += 1
                        p += 1; args.append(('L', lst))
                self.ins[a] = (op, args, p - a)
                if FLOW[op] in ('end', 'jump'):
                    break
                a = p
        return self

    def listing(self):
        out = ['; field event scripts, map $%02X (block at $%06X)' % (self.m, R.to_cpu(self.base)), '']
        for k, ent in sorted(self.lists.items()):
            out.append('; list %2d: %s' % (k, ' '.join('%d->+%04X' % (i, w) for i, w in ent)))
        prev = None
        for a in sorted(self.ins):
            op, args, n = self.ins[a]
            if a in self.labels:
                out.append('')
                out.append('E_%04X:   ; %s' % (a - self.base, ', '.join(sorted(set(self.labels[a])))))
            elif prev is not None and a != prev:
                out.append('')
            parts = []
            for c, v in args:
                parts.append('E_%04X' % v if c == 'p' else ('[%s]' % ' '.join('%02X' % x for x in v)) if c == 'L'
                             else '$%04X' % v if c == 'w' else '$%02X' % v)
            raw = self.d[a:a + n]
            out.append('    %-26s %-28s ; +%04X: %s' % (opname(op), ', '.join(parts), a - self.base, raw.hex(' ')))
            prev = a + n
        return '\n'.join(out) + '\n'


def main():
    args = sys.argv[1:]
    rp = args[0] if args and not args[0].startswith('-') else '/home/claude/lufia2/rom/orig.smc'
    outdir = args[args.index('-o') + 1] if '-o' in args else None
    d = open(rp, 'rb').read()
    from collections import Counter
    use = Counter(); maps = 0; nins = 0; errs = []
    for m in range(0xF2):
        M = Map(d, m)
        if not M.ok:
            continue
        M.decode(); maps += 1; nins += len(M.ins)
        for a, (op, args_, n) in M.ins.items():
            use[op] += 1
        errs += ['map %02X: %s' % (m, e) for e in M.errors]
        if outdir:
            os.makedirs(outdir, exist_ok=True)
            open(os.path.join(outdir, 'event_%02X.txt' % m), 'w').write(M.listing())
    print('maps with events: %d, instructions: %d, opcodes used: %d of 191, errors: %d' % (maps, nins, len(use), len(errs)))
    for e in errs[:30]:
        print('  ', e)
    json.dump({'%02X' % k: use[k] for k in range(191)}, open('/home/claude/lufia2/build/event_op_use.json', 'w'))


if __name__ == '__main__':
    main()
