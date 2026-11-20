"""Lufia II combined edition: build from the clean ROM in fixed layers, with overlap checks.

    python3 build_combined.py CLEAN.sfc OUT.sfc [--no-retry] [--report report.txt]

Layers (in order):
  restored_iris   data   layers/restored_iris.lay    Restored & Extended v0.4 + Iris Treasures v1.1
  retry           asm    src/mods/retry.asm          optional (--no-retry leaves it out)
  backgrounds3    data   layers/backgrounds3.lay     battle backgrounds test build 3 (4 MB)
  musicoff        asm    src/mods/music.asm          CONFIG > MUSIC: STEREO / MONO / OFF
  msu1            asm    src/mods/msu1.asm           MSU-1 music (-DMSUBASE=$DBFC00)
A layer may only change bytes no earlier layer changed, except the header checksum (recomputed
at the end) and overlaps listed in ALLOWED (deliberate takeovers). Any other overlap stops the build.
Data layers (.lay) are byte runs: 'L2LY', then (offset u32, length u32, bytes)*, plus a final size.
"""
import os, sys, struct, subprocess, shutil, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
ASAR = os.environ.get('ASAR', os.path.join(ROOT, 'ext/asar/build/asar/bin/asar'))
SRC = os.path.join(ROOT, 'src/mods')

CHECKSUM = set(range(0x7FDC, 0x7FE0))
ALLOWED = {('msu1', 'musicoff'): set(range(0x1FFBA, 0x1FFBE))}    # $83:FFBA: MSU takes over ApplyMusic's entry

LAYERS = [
    ('restored_iris', 'data', 'layers/restored_iris.lay', None),
    ('retry',         'asm',  'retry.asm', []),
    ('backgrounds3',  'data', 'layers/backgrounds3.lay', None),
    ('musicoff',      'asm',  'music.asm', []),
    ('msu1',          'asm',  'msu1.asm', ['-DMSUBASE=$DBFC00']),
]


def write_layer(path, before, after):
    out = bytearray(b'L2LY')
    n = len(after); i = 0
    while i < n:
        same = lambda k: (before[k] == after[k]) if k < len(before) else after[k] == 0
        if same(i) or i in CHECKSUM:
            i += 1; continue
        j = i
        while j < n and not same(j) and j not in CHECKSUM:
            j += 1
        out += struct.pack('<II', i, j - i) + after[i:j]
        i = j
    out += struct.pack('<II', 0xFFFFFFFF, n)
    open(path, 'wb').write(out)


def read_layer(path):
    d = open(path, 'rb').read(); assert d[:4] == b'L2LY'
    p = 4; runs = []
    while True:
        off, ln = struct.unpack('<II', d[p:p + 8]); p += 8
        if off == 0xFFFFFFFF:
            return runs, ln
        runs.append((off, d[p:p + ln])); p += ln


def apply_data(rom, path):
    runs, size = read_layer(path)
    if len(rom) < size:
        rom += bytes(size - len(rom))
    for off, data in runs:
        rom[off:off + len(data)] = data
    return rom


def apply_asm(rom, name, defines):
    with tempfile.TemporaryDirectory() as t:
        f = os.path.join(t, 'rom.sfc'); open(f, 'wb').write(rom)
        r = subprocess.run([ASAR, '--fix-checksum=off', *defines, os.path.join(SRC, name), f],
                           capture_output=True, text=True)
        if r.returncode:
            sys.exit('asar failed on %s:\n%s%s' % (name, r.stdout, r.stderr))
        return bytearray(open(f, 'rb').read())


def fix_checksum(rom):
    rom[0x7FDC:0x7FE0] = bytes([0xFF, 0xFF, 0, 0])
    size = len(rom); p2 = 1 << (size.bit_length() - 1)
    s = sum(rom[:p2])
    if size > p2:                                 # mirrored remainder (asar's rule)
        rest = rom[p2:]; s += sum(rest) * (p2 // len(rest))
    s &= 0xFFFF
    rom[0x7FDE:0x7FE0] = s.to_bytes(2, 'little'); rom[0x7FDC:0x7FDE] = (s ^ 0xFFFF).to_bytes(2, 'little')


def ranges(offs):
    offs = sorted(offs); out = []
    for o in offs:
        if out and o <= out[-1][1] + 16:
            out[-1][1] = o
        else:
            out.append([o, o])
    return out


def cpu(o):
    return ((o // 0x8000) | 0x80) << 16 | (o % 0x8000 + 0x8000)


def build(clean, skip=(), report=None):
    rom = bytearray(clean)
    owner = {}                                    # offset -> layer that changed it
    lines = []
    for name, kind, src, defines in LAYERS:
        if name in skip:
            lines.append('%-14s skipped' % name); continue
        before = bytes(rom)
        rom = apply_data(rom, os.path.join(HERE, src)) if kind == 'data' else apply_asm(rom, src, defines)
        # new space added by an expansion counts as changed only where it is not zero (zeros = free)
        changed = [i for i in range(len(rom)) if i not in CHECKSUM and
                   (rom[i] != before[i] if i < len(before) else rom[i] != 0)]
        clashes = {}
        for i in changed:
            o = owner.get(i)
            if o and i not in ALLOWED.get((name, o), ()):
                clashes.setdefault(o, []).append(i)
        if clashes:
            for o, offs in clashes.items():
                print('OVERLAP: %s changes bytes of %s at %s' % (name, o, ', '.join('$%06X' % cpu(i) for i in offs[:8])))
            sys.exit('build stopped')
        for i in changed:
            owner[i] = name
        lines.append('%-14s %7d bytes in %s' % (name, len(changed), ', '.join(
            '$%06X-%06X' % (cpu(a), cpu(b)) for a, b in ranges(changed)[:12]) + (' …' if len(ranges(changed)) > 12 else '')))
    fix_checksum(rom)
    if report:
        open(report, 'w').write('\n'.join(lines) + '\n')
    print('\n'.join(lines))
    return bytes(rom), owner


if __name__ == '__main__':
    clean = open(sys.argv[1], 'rb').read()
    skip = ('retry',) if '--no-retry' in sys.argv else ()
    rep = sys.argv[sys.argv.index('--report') + 1] if '--report' in sys.argv else None
    rom, _ = build(clean, skip, rep)
    open(sys.argv[2], 'wb').write(rom)
