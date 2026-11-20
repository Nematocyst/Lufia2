"""Keep the PC version's native (decomp) functions away from code our ROM patches change.

The PC version (Lufia2SNESRecomp) replaces ~1,900 game routines with hand-written C ("bindings").
A ROM patch that changes one of those routines would be ignored, because the C version runs
instead of the patched bytes. This writes a copy of the bindings file without every routine whose
code bytes differ between the clean ROM and the modified ROM, so those run from the (patched) ROM.

    python3 mod_bindings.py CLEAN.sfc MODDED.sfc decomp_bindings.toml out.toml [--report r.txt]

A routine's bytes = every instruction reachable from its entry in the clean ROM (branches and
jumps followed, calls not), using the disassembly's instruction table (build/analysis.json).
"""
import sys, json, re

ANALYSIS = '/home/claude/lufia2/build/analysis.json'
STOP = {0x60, 0x6B, 0x40, 0x7C, 0x6C, 0xDC, 0x00, 0xDB, 0xFC, 0x5C}   # returns, indirect jumps, JML
BRANCH = {0x10, 0x30, 0x50, 0x70, 0x90, 0xB0, 0xD0, 0xF0}


def lo(a):
    return ((a >> 16) & 0x7F) * 0x8000 + (a & 0x7FFF)


def cpu(o):
    return ((o // 0x8000) | 0x80) << 16 | (o % 0x8000 + 0x8000)


def extent(rom, insn, entry_off, limit=20000):
    seen = set(); work = [entry_off]; covered = set()
    while work and len(seen) < limit:
        o = work.pop()
        while o not in seen:
            if o not in insn:
                break
            seen.add(o)
            size = insn[o][2]
            covered.update(range(o, o + size))
            op = rom[o]
            pc = cpu(o)
            if op in STOP:
                break
            if op in BRANCH or op == 0x80:
                d = rom[o + 1]; d = d - 256 if d > 127 else d
                work.append(lo((pc & 0xFF0000) | ((pc + 2 + d) & 0xFFFF)))
                if op == 0x80:
                    break
            elif op == 0x82:
                d = rom[o + 1] | rom[o + 2] << 8; d = d - 65536 if d > 32767 else d
                work.append(lo((pc & 0xFF0000) | ((pc + 3 + d) & 0xFFFF))); break
            elif op == 0x4C:
                work.append(lo((pc & 0xFF0000) | rom[o + 1] | rom[o + 2] << 8)); break
            o += size
    return covered


def main(a):
    clean = open(a[1], 'rb').read(); mod = open(a[2], 'rb').read()
    A = json.load(open(ANALYSIS)); insn = {int(k): v for k, v in A['insn'].items()}
    text = open(a[3]).read()
    blocks = re.split(r'(?=^\[\[binding\]\])', text, flags=re.M)
    keep, dropped = [], []
    for b in blocks:
        m = re.search(r'address = "([0-9A-F]{2}):([0-9A-F]{4})"', b)
        if not m:
            keep.append(b); continue
        addr = int(m.group(1), 16) << 16 | int(m.group(2), 16)
        o = lo(addr)
        cov = extent(clean, insn, o) if o in insn else set(range(o, o + 4))
        diff = [x for x in cov if x < len(mod) and clean[x] != mod[x]]
        if diff:
            dropped.append((addr, len(cov), sorted(diff)))
        else:
            keep.append(b)
    open(a[4], 'w').write(''.join(keep))
    rep = ['%d bindings kept, %d dropped (their code is changed by the patch):' %
           (sum(1 for b in keep if 'address' in b), len(dropped))]
    for addr, n, d in dropped:
        rep.append('  $%02X:%04X  %d code bytes, %d changed (first at $%06X)' %
                   (addr >> 16, addr & 0xFFFF, n, len(d), cpu(d[0])))
    txt = '\n'.join(rep) + '\n'
    if '--report' in a:
        open(a[a.index('--report') + 1], 'w').write(txt)
    print(txt)


if __name__ == '__main__':
    main(sys.argv)
