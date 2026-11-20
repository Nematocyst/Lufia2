"""Move the battle-animation scripts to a free bank and add new animations at unused effect ids.

    python3 effect_reloc.py IN.sfc OUT.sfc [--bank D1] [--org F200] [--add ID=file.txt:LABEL ...]

1. Copies bank $95 verbatim to the target bank (same offsets, so every 16-bit script pointer
   stays valid) and points the effect VM at it (3 code patches in bank $81):
       $81:899A  LDA.l $958000,X  -> table read            (BattlePlayEffect)
       $81:89A4  LDA #$95         -> script bank byte $C5  (BattlePlayEffect)
       $81:9F47  LDA.l $958200,X  -> table tail, ids 256+
   NOT changed: the LDA #$95/PHA/PLB at $81:96C7, $81:97D8, $81:A5BE/A5D6/A5EE. They set the data
   bank only to reach I/O registers (WMADD $2181, multiplier $4202); banks $C0+ have no I/O, so
   pointing them at the new bank breaks palettes (seen in testing). Spell/IP records, names and the
   pop-up table stay in bank $95 and are still read from there.
2. Free space in the copy: $F1EF-$FFFF (3,601 bytes; the records there are read from $95, not the
   copy). New scripts are assembled at --org (default $F1EF) with effectasm; they may call or spawn
   any original routine by its L_xxxx / Exxx label (resolved from effectdec's listing of the ROM).
3. --add ID=file:LABEL points effect ID at LABEL. Only unused ids are accepted (table word 0).

Verified 2026-11-12 on the 4 MB test ROM: all 121 distinct original animations render pixel-
identically from the relocated bank (fx2/all.py, frame hashes every 3 frames over 900 frames).
"""
import sys, re
sys.path.insert(0, '/home/claude/lufia2/tools')
import effectdec, effectasm


def lo(a):
    return (a >> 16 & 0x7F) * 0x8000 + (a & 0x7FFF)


PATCHES = [  # cpu address, original bytes, new bytes (B = target bank)
    (0x81899A, bytes([0xBF, 0x00, 0x80, 0x95]), lambda B: bytes([0xBF, 0x00, 0x80, B])),
    (0x8189A4, bytes([0xA9, 0x95]), lambda B: bytes([0xA9, B])),
    (0x819F47, bytes([0xBF, 0x00, 0x82, 0x95]), lambda B: bytes([0xBF, 0x00, 0x82, B])),
]


def relocate(d, B):
    src = lo(0x958000); dst = lo(B << 16 | 0x8000)
    already = all(d[lo(a):lo(a) + len(new(B))] == new(B) for a, old, new in PATCHES)
    if not already:
        tail = d[dst:dst + 0x8000]
        if any(x not in (0x00, 0xFF) for x in tail) and tail != d[src:src + 0x8000]:
            raise SystemExit('bank $%02X is not free' % B)
        d[dst:dst + 0x8000] = d[src:src + 0x8000]
        for a, old, new in PATCHES:
            if d[lo(a):lo(a) + len(old)] != old:
                raise SystemExit('unexpected code at $%06X' % a)
            d[lo(a):lo(a) + len(old)] = new(B)


def original_labels(d):
    dec = effectdec.Decoder(bytes(d)); dec.run()
    dec.entry_of = {}
    for k, e in enumerate(dec.entries):
        dec.entry_of.setdefault(e, k)
    return {dec.name(a): a for a in dec.labels}


def add(d, B, org, adds):
    labels = original_labels(d)
    text = []
    for name, a in sorted(labels.items(), key=lambda x: x[1]):   # declare the original labels
        text += ['org $%04X' % a, '%s:' % name]
    text.append('org $%04X' % org)
    for path in dict.fromkeys(p for _, p, _ in adds):    # each file once
        text.append(open(path).read())
    lo_a, data, lab, filled = effectasm.assemble('\n'.join(text))
    used = sorted(filled)
    if used[0] < org or used[-1] > 0xFFFF:
        raise SystemExit('new scripts out of range')
    base = lo(B << 16)
    for a in used:
        d[base + a - 0x8000] = data[a - lo_a]
    for eid, path, label in adds:
        t = base + 2 * eid
        if d[t] | d[t + 1] << 8:
            raise SystemExit('effect id %d is in use' % eid)
        v = lab[label]
        d[t] = v & 0xFF; d[t + 1] = v >> 8
        print('effect %d ($%02X) -> $%02X:%04X %s' % (eid, eid, B, v, label))
    print('new script bytes: $%04X-$%04X (%d), free left to $FFFF: %d' % (used[0], used[-1], len(used), 0xFFFF - used[-1]))


def main():
    a = sys.argv[1:]
    src, dst = a[0], a[1]
    B = int(a[a.index('--bank') + 1], 16) if '--bank' in a else 0xD1
    org = int(a[a.index('--org') + 1], 16) if '--org' in a else 0xF1EF
    adds = []
    for i, x in enumerate(a):
        if x == '--add':
            m = re.fullmatch(r'(\d+)=(.+):(\w+)', a[i + 1])
            adds.append((int(m.group(1)), m.group(2), m.group(3)))
    d = bytearray(open(src, 'rb').read())
    relocate(d, B)
    if adds:
        add(d, B, org, adds)
    open(dst, 'wb').write(d)


if __name__ == '__main__':
    main()
