"""Static operand-length analysis of the battle effect-script commands (table $81:8C5C).

Walks every path through each command handler in the disassembly (bank_81.asm), following
JSR/JMP/branches inside bank $81, and tracks how the script pointer $C3 moves:
  INC $C3            +1
  LDA $C3 / ADC #n / STA $C3   +n
  STA/STX $C3 from anything else -> 'set' (control transfer)
Prints, per opcode, the set of operand lengths seen on the paths that return (RTS) to the loop.

    python3 effops.py DISASM_DIR [--json out.json]
"""
import re, sys, json

INVALID = 'sub_818C5A'


def parse(path):
    ins = {}          # addr -> (mnem, operand, next_addr)
    labels = {}
    order = []
    pending = []
    for line in open(path):
        m = re.match(r'^([A-Za-z_][A-Za-z0-9_]*):', line)
        if m:
            pending.append(m.group(1)); continue
        m = re.match(r'^\t([A-Z]{3})(?:\.[bwl])?\s*([^;]*?)\s*;\s*([0-9A-F]{6})', line)
        if not m:
            if line.strip().startswith(('db', 'dw', 'dl')):
                pending = []
                order.append(None)
            continue
        a = int(m.group(3), 16)
        for p in pending:
            labels[p] = a
        pending = []
        ins[a] = [m.group(1), m.group(2).strip(), None]
        order.append(a)
    for i, a in enumerate(order):
        if a is not None and i + 1 < len(order) and order[i + 1] is not None:
            ins[a][2] = order[i + 1]
    return ins, labels


def target(op, labels):
    op = op.strip()
    if op in labels:
        return labels[op]
    m = re.match(r'^\$([0-9A-F]{4})$', op)
    if m:
        return 0x810000 | int(m.group(1), 16)
    return None


class Analyzer:
    def __init__(self, ins, labels):
        self.ins, self.labels = ins, labels
        self.notes = set()

    def paths(self, start):
        """Return the set of (kind, delta) exits: rts / set / stop / loop-free merges are shared."""
        out = set()
        seen = set()
        work = [(start, 0, (), False, None)]
        while work:
            st = work.pop()
            if st in seen:
                continue
            seen.add(st)
            if len(seen) > 20000:
                out.add(('toomany', 0)); break
            a, delta, stack, lda_c3, added = st
            if a not in self.ins:
                out.add(('unknown', delta)); continue
            mn, op, nxt = self.ins[a]
            if a == 0x818C58:
                out.add(('stop', delta)); continue
            if op == '$C3' and mn == 'INC':
                delta += 1
            elif op == '$C3' and mn == 'LDA':
                lda_c3, added = True, 0
            elif lda_c3 and mn == 'ADC' and op.startswith('#$'):
                added = int(op[2:], 16)
            elif op == '$C3' and mn in ('STA', 'STX', 'STY'):
                if lda_c3 and added is not None and mn == 'STA':
                    delta += added; lda_c3 = False
                else:
                    out.add(('set', delta)); continue
            elif mn == 'LDA':
                lda_c3 = False
            if delta > 64:
                out.add(('runaway', delta)); continue
            def go(t, stk=stack):
                work.append((t, delta, stk, lda_c3, added))
            if mn == 'RTS':
                if stack:
                    go(stack[-1], stack[:-1])
                else:
                    out.add(('rts', delta))
                continue
            if mn in ('RTL', 'RTI'):
                out.add(('rtl', delta)); continue
            if mn == 'JSR':
                t = target(op, self.labels)
                if t is None or op.startswith('('):
                    self.notes.add('indirect JSR at %06X' % a); go(nxt); continue
                if len(stack) > 10:
                    out.add(('deep', delta)); continue
                go(t, stack + (nxt,)); continue
            if mn in ('JMP', 'BRL', 'BRA'):
                t = target(op, self.labels)
                if t is None:
                    self.notes.add('indirect %s at %06X' % (mn, a)); out.add(('indirect', delta)); continue
                go(t); continue
            if mn == 'JML':
                out.add(('jml', delta)); continue
            if mn in ('BEQ', 'BNE', 'BCC', 'BCS', 'BPL', 'BMI', 'BVC', 'BVS'):
                go(target(op, self.labels))
            if nxt is None:
                out.add(('falloff', delta)); continue
            go(nxt)
        return out


def main():
    d = sys.argv[1]
    ins, labels = parse(d + '/bank_81.asm')
    L = open(d + '/bank_81.asm').read().split('\n')
    i = L.index('tbl_818C5C:') + 1
    tab = []
    while L[i].strip().startswith('dw '):
        tab.append(L[i].split()[1]); i += 1
    an = Analyzer(ins, labels)
    out = {}
    for opc, name in enumerate(tab):
        if name == INVALID or name not in labels:   # BRA-to-self hang or a lone BRK
            out['%02X' % opc] = {'name': None}; continue
        res = sorted(an.paths(labels[name]))
        out['%02X' % opc] = {'name': name, 'exits': res}
        print('%02X %-42s %s' % (opc, name, ' '.join('%s:%d' % r for r in res)))
    for n in sorted(an.notes):
        print('note:', n)
    if '--json' in sys.argv:
        json.dump(out, open(sys.argv[sys.argv.index('--json') + 1], 'w'), indent=1)


if __name__ == '__main__':
    main()
