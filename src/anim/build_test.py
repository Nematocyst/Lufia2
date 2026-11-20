"""Assemble an effect script into bank $95 over Stardust blow's area (test ROMs only) and film it."""
import sys, re
sys.path.insert(0, '/root/lufia2/src/tools'); sys.path.insert(0, '/root/lufia2/exp')
import effectasm
LISTING = '/root/lufia2/exp/effects.txt'
START, END = 0xE102, 0xE1FB

def splice(src_text):
    L = open(LISTING).read().split('\n')
    a = L.index('E143:   ; effect 143')
    b = [i for i, l in enumerate(L) if l.startswith('E144:')][0]
    while a > 0 and L[a - 1].strip() == '': a -= 1
    new = L[:a] + ['', 'org $%04X' % START] + src_text.split('\n') + ['', 'org $%04X' % END, ''] + L[b:]
    return '\n'.join(new)

def build(src_path, out_rom, base='/root/lufia2/rom/clean.sfc', spells=True, entry='E143'):
    text = splice(open(src_path).read())
    lo_a, data, labels, filled = effectasm.assemble(text)
    # an overflow past END collides with effect 144 and the assembler reports the overlap
    d = bytearray(open(base, 'rb').read())
    o = 0x15 * 0x8000
    for a in sorted(filled):
        d[o + a - 0x8000] = data[a - lo_a]
    if spells:
        ea = labels[entry]
        for k in range(0x12, 0x37):
            d[o + 2 * k] = ea & 0xFF; d[o + 2 * k + 1] = ea >> 8
    open(out_rom, 'wb').write(d)
    print('script bytes used: %d of %d' % (len([a for a in filled if START <= a < END]), END - START))

if __name__ == '__main__':
    build(sys.argv[1], sys.argv[2], entry=sys.argv[3] if len(sys.argv) > 3 else 'E143')
