"""Assembler for Lufia II battle effect scripts (the format effectdec.py writes).

    python3 effectasm.py source.txt out.bin [--verify ROM]

Syntax (one statement per line, ';' starts a comment):
    org $8000              address of the next byte (16-bit, inside the script bank)
    table LABEL | 0        one word of the effect pointer table
    LABEL:                 define a label (E000, L_8C1D, MyBolt ...)
    bytes $01 $02 ...      raw bytes
    command arg, arg ...   a script command; arguments are numbers ($hex or decimal,
                           negative allowed for signed bytes) or labels for pointers
Output: the bytes from the first org to the last byte, plus a JSON symbol file (out.sym.json).
"""
import sys, re, json
from effectdec import OPS, SIZE, PARTY_ENTRIES, lo

BYNAME = {v[0]: (k, v[1], v[2]) for k, v in OPS.items()}


class AsmError(Exception):
    pass


def number(tok, labels=None, line=0):
    t = tok.strip()
    if re.fullmatch(r'-?\$[0-9A-Fa-f]+', t):
        neg = t.startswith('-'); v = int(t.lstrip('-')[1:], 16); return -v if neg else v
    if re.fullmatch(r'-?[0-9]+', t):
        return int(t)
    if labels is not None:
        if t in labels:
            return labels[t]
        raise AsmError('line %d: unknown label %s' % (line, t))
    return None


def parse(text):
    stmts = []
    for n, raw in enumerate(text.split('\n'), 1):
        line = raw.split(';', 1)[0].strip()
        if not line:
            continue
        while True:
            m = re.match(r'^([A-Za-z_][A-Za-z0-9_]*):\s*(.*)$', line)
            if not m:
                break
            stmts.append((n, 'label', m.group(1), []))
            line = m.group(2).strip()
        if not line:
            continue
        parts = line.split(None, 1)
        word = parts[0]
        args = [a.strip() for a in parts[1].split(',')] if len(parts) > 1 else []
        if word == 'bytes':
            args = parts[1].split() if len(parts) > 1 else []
        stmts.append((n, word, None, args))
    return stmts


def size_of(word, args, n):
    if word == 'org':
        return 0
    if word == 'table':
        return 2
    if word == 'bytes':
        return len(args)
    if word not in BYNAME:
        raise AsmError('line %d: unknown command %s' % (n, word))
    op, spec, flow = BYNAME[word]
    want = len(spec) + (PARTY_ENTRIES if flow == 'party' else 0)
    if len(args) != want:
        raise AsmError('line %d: %s takes %d argument(s), got %d' % (n, word, want, len(args)))
    return 1 + sum(SIZE[c] for c in spec) + (2 * PARTY_ENTRIES if flow == 'party' else 0)


def assemble(text):
    stmts = parse(text)
    labels = {}
    pc = None; start = None
    for n, word, name, args in stmts:                    # pass 1: addresses
        if word == 'label':
            if name in labels:
                raise AsmError('line %d: label %s defined twice' % (n, name))
            if pc is None:
                raise AsmError('line %d: label before org' % n)
            labels[name] = pc; continue
        if word == 'org':
            pc = number(args[0])
            if start is None: start = pc
            continue
        if pc is None:
            raise AsmError('line %d: code before org' % n)
        pc += size_of(word, args, n)
    out = {}
    pc = None
    for n, word, name, args in stmts:                    # pass 2: bytes
        if word == 'label':
            continue
        if word == 'org':
            pc = number(args[0]); continue
        def put(v, w):
            nonlocal pc
            for k in range(w):
                if pc in out:
                    raise AsmError('line %d: overlaps earlier output at $%04X' % (n, pc))
                out[pc] = (v >> (8 * k)) & 0xFF; pc += 1
        if word == 'table':
            put(number(args[0], labels, n), 2); continue
        if word == 'bytes':
            for a in args: put(number(a, labels, n), 1)
            continue
        op, spec, flow = BYNAME[word]
        put(op, 1)
        kinds = list(spec) + (['p'] * PARTY_ENTRIES if flow == 'party' else [])
        for c, a in zip(kinds, args):
            v = number(a, labels, n)
            if c in 'bs':
                if not -128 <= v <= 255: raise AsmError('line %d: %s does not fit a byte' % (n, a))
                put(v & 0xFF, 1)
            else:
                if not -0x8000 <= v <= 0xFFFF: raise AsmError('line %d: %s does not fit a word' % (n, a))
                put(v & 0xFFFF, 2)
    lo_a, hi_a = min(out), max(out)
    data = bytearray(hi_a - lo_a + 1)
    filled = set()
    for a, v in out.items():
        data[a - lo_a] = v; filled.add(a)
    return lo_a, bytes(data), labels, filled


def main():
    src, dst = sys.argv[1], sys.argv[2]
    try:
        base, data, labels, filled = assemble(open(src).read())
    except AsmError as e:
        print('error:', e); sys.exit(1)
    open(dst, 'wb').write(data)
    json.dump({'base': base, 'labels': labels}, open(dst + '.sym.json', 'w'), indent=0)
    print('assembled $%04X-$%04X (%d bytes), %d labels' % (base, base + len(data) - 1, len(data), len(labels)))
    if '--verify' in sys.argv:
        rom = open(sys.argv[sys.argv.index('--verify') + 1], 'rb').read()
        o = lo(0x950000 | base)
        orig = rom[o:o + len(data)]
        bad = [base + i for i in range(len(data)) if data[i] != orig[i]]
        holes = [base + i for i in range(len(data)) if base + i not in filled]
        print('verify against ROM bank $95: %s (%d differing bytes, %d unfilled)' %
              ('IDENTICAL' if not bad else 'DIFFERENT', len(bad), len(holes)))
        for a in bad[:10]:
            print('   $%04X: asm %02X rom %02X' % (a, data[a - base], orig[a - base]))


if __name__ == '__main__':
    main()
