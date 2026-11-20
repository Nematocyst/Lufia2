"""Lufia II battle effect-script disassembler (bank $95, table $95:8000, 281 entries).

    python3 effectdec.py ROM [-o listing.txt] [--json effects.json] [--bank $D1]

The battle animation VM (BattlePlayEffect $81:895E) runs one script per slot: 30 script
slots ($7E:4F8F, $2C bytes) and 64 actor slots ($7E:54B7, $2D bytes) share one command table
($81:8C5C, 256 entries). Scripts live in bank $95 (bank byte $C5); every pointer operand is a
16-bit address in that bank. Operand lengths come from tools/effops.py (static path analysis).

Output: every reachable script, labelled; a coverage report of bank $95.
"""
import sys, json

# opcode: (mnemonic, operand spec). Spec letters: b byte, w word, p script pointer (word),
# s signed byte. Flow: 'end' stops, 'jump' stops after a pointer, 'ret' stops,
# 'party' = 7-word jump table follows (stops).
OPS = {
    0x00: ('end', '', 'end'),
    0x01: ('yield', '', None),
    0x02: ('delay', 'b', None),
    0x03: ('jump', 'p', 'jump'),
    0x04: ('call', 'p', None),
    0x05: ('return', '', 'ret'),
    0x06: ('branch_if_field', 'pbb', None),     # if parent slot[+b1] == b2 goto p
    0x08: ('spawn_script_at', 'pw', None),      # stream, position (x,y bytes)
    0x09: ('spawn_scripts_for_targets', 'p', None),
    0x0A: ('spawn_actor_at', 'pwb', None),      # stream, position, attributes
    0x0B: ('hdma', 'b', None),                  # $81:8E5C table, 18 routines (wave/HDMA modes)
    0x0C: ('spawn_saved_actor_script', 'p', None),
    0x0D: ('spawn_current_target_script', 'p', None),
    0x0E: ('spawn_enemy_scripts', 'p', None),
    0x0F: ('party_jump', '', 'party'),          # 7 words indexed by the party member id
    0x10: ('loop1', 'b', None), 0x11: ('loop2', 'b', None),
    0x12: ('loop3', 'b', None), 0x13: ('loop4', 'b', None),
    0x18: ('next1', '', None), 0x19: ('next2', '', None),
    0x1A: ('next3', '', None), 0x1B: ('next4', '', None),
    0x20: ('change_display', 'bww', None),
    0x21: ('video_register', 'bb', None),
    0x22: ('bg3_map', 'b', None),
    0x23: ('nop23', '', None),
    0x27: ('load_graphics', 'ww', None),        # resource id, VRAM/dest
    0x28: ('restore_palette', 'bw', None),
    0x2C: ('load_palette', 'bbbw', None),
    0x2D: ('clear_window_tiles', '', None),
    0x2E: ('reset_party_tiles', '', None),
    0x30: ('add_bg3_scroll', 'bb', None), 0x31: ('set_bg3_scroll', 'bb', None),
    0x33: ('add_bg1_scroll', 'bb', None), 0x34: ('set_bg1_scroll', 'bb', None),
    0x50: ('copy_tile_rect', 'www', None),
    0x51: ('set_brightness', 'bb', None),
    0x52: ('copy_actor_tiles', 'w', None),
    0x53: ('nop53', '', None),
    0x54: ('adjust_brightness', 'bb', None),
    0x55: ('refresh_turn_display', '', None),
    0x56: ('spawn_script_if_enabled', 'p', None),
    0x59: ('bg_request', 'b', None),
    0x5A: ('bg_release', '', None),
    0x5B: ('bg_copy', '', None),
    0x5C: ('graphics', 'www', None),
    0x5D: ('graphics_alt', 'www', None),
    0x5E: ('circle_radius', 'b', None),
    0x5F: ('window_band', 'b', None),
    0x60: ('target_motion_offsets', 'bb', None),
    0x61: ('portrait_pose', 'b', None),
    0x62: ('prepare_frame', 'b', None),
    0x63: ('skip_arg', 'b', None),
    0x64: ('toggle_party_target', '', None),
    0x65: ('move_target', 'bb', None),
    0x66: ('set_target_status', 'b', None),
    0x67: ('portrait_pose_if_clear', 'b', None),
    0x68: ('toggle_special_target', '', None),
    0x69: ('move_special_target', 'ss', None),        # signed x, y offsets
    0x6A: ('restore_portrait_pose', '', None),
    0x6B: ('rebuild_sprites', 'b', None),
    0x70: ('sound', 'b', None),
    0x71: ('target_popups', '', None),
    0x72: ('sound_if', 'b', None),
    0x80: ('offset_angle', 'b', None),
    0x81: ('rotate_angle', 'b', None),
    0x82: ('aim_at_point', 'ww', None),
    0x83: ('accelerate_at_angle', 'bb', None),
    0x84: ('decelerate_at_angle', 'bb', None),
    0x85: ('decelerate_at_offset_angle', 'bbb', None),
    0x87: ('packed_draw_state', 'w', None),
    0x88: ('alt_packed_draw_state', 'w', None),
    0x89: ('draw_state', 'bbbb', None),
    0x8E: ('spawn_moving_actor', 'pwb', None),
    0x8F: ('clear_draw_dirty', '', None),
    0x90: ('clear_target', '', None),
    0x91: ('randomize_centered', 'bb', None),
    0x94: ('project_from_position', 'bw', None),
    0x95: ('set_velocity', 'ww', None),
    0x96: ('spawn_vector_actor', 'pbwb', None),  # stream, angle, speed, attributes
    0x97: ('vector_from_params', 'bb', None),
    0x98: ('draw_attributes', 'b', None),
    0x99: ('draw_value', 'b', None),
    0x9A: ('draw_mode', 'b', None),
    0x9B: ('copy_draw_value', 'b', None),
    0x9C: ('draw_variant', 'b', None),
    0x9D: ('draw_flag', 'b', None),
    0xC0: ('set_param', 'bw', None),
    0xC1: ('add_to_field', 'bw', None),
    0xC2: ('randomize_param', 'b', None),
    0xD0: ('spawn_stationary', 'p', None),
    0xD1: ('spawn_half_turn', 'p', None),
    0xD2: ('spawn_with_angle', 'pb', None),
    0xD3: ('spawn_offset', 'p', None),
    0xD4: ('spawn_moving', 'p', None),
    0xD5: ('spawn_half_turn_moving', 'p', None),
    0xD6: ('spawn_rightward', 'p', None),
    0xD7: ('spawn_upward', 'p', None),
    0xD8: ('spawn_moving_with_angle', 'pb', None),
    0xD9: ('spawn_with_vspeed', 'pb', None),
    0xDA: ('draw_variant3', 'b', None),
    0xDB: ('use_third_draw_param', '', None),
    0xDC: ('velocity', '', None),
    0xDD: ('palette_preset1', 'w', None),
    0xDE: ('palette_preset2', 'w', None),
    0xDF: ('palette_preset3', 'w', None),
    0xE0: ('wait1', '', None), 0xE1: ('wait2', '', None), 0xE2: ('wait3', '', None),
    0xE3: ('wait4', '', None), 0xE4: ('wait5', '', None), 0xE5: ('wait6', '', None),
    0xE6: ('wait8', '', None), 0xE7: ('wait10', '', None), 0xE8: ('wait20', '', None),
    0xE9: ('spawn_script_zero', 'p', None),
    0xEA: ('spawn_script_centered', 'pb', None),
    0xEB: ('clear_bg_upload', '', None),
    0xEC: ('accelerate_by', 'b', None),
    0xED: ('decelerate_by', 'b', None),
    0xEE: ('accelerate1', '', None), 0xEF: ('accelerate2', '', None),
    0xF0: ('accelerate3', '', None), 0xF1: ('accelerate4', '', None),
}
SIZE = {'b': 1, 's': 1, 'w': 2, 'p': 2}
PARTY_ENTRIES = 7
BANK = 0x95
TABLE = 0x958000
COUNT = 281
SCRIPT_END = 0xE793          # scripts end here; the rest of bank $95 is other battle data
DATA_REGIONS = [
    (0xE793, 0xF08A, 'data between the scripts (not effect scripts; not identified yet - keep in place)'),
    (0xF1EF, 0xFA5A, 'IP effect records: 141 word offsets from $F1EF, then records $F309-$FA5A (IpNamePointer $81:F46B)'),
    (0xFA5B, 0xFFEC, 'spell records: 40 word offsets from $FA5B, then records (SpellTextPointer $81:F446)'),
    (0xFFED, 0xFFFF, 'battle pop-up table (BattleBuildPopupRecord $81:C477)'),
]


def lo(a):
    return (a >> 16 & 0x7F) * 0x8000 + (a & 0x7FFF)


FIXED = {0x0E: 'battle code $81:AE4B', 0x2A: 'battle code $81:AAA1', 0x93: 'battle code $81:B040',
         0x9A: 'battle code $81:B145', 0xDC: 'number pop-ups (battle code, several places)',
         0xDD: 'battle code $81:AE70', 0xDE: 'battle code $81:B0A4', 0xE0: 'battle code $81:AE84',
         0xF0: 'battle code $81:AEB9'}


def users(rom):
    """effect id -> list of who plays it: spells (id + $12) and IP abilities (animation byte)."""
    def w(a): return rom[lo(a)] | rom[lo(a) + 1] << 8
    def text(a, n=None):
        out = ''
        while True:
            c = rom[lo(a)]
            if c == 0 or (n is not None and len(out) >= n): break
            out += chr(c) if 32 <= c < 127 else '?'; a += 1
        return out.rstrip()
    u = {}
    nsp = (w(0x95FA5B) // 2)                          # first offset = size of the pointer table
    for k in range(nsp):
        a = 0x950000 | (0xFA5B + w(0x95FA5B + 2 * k))
        u.setdefault(k + 0x12, []).append('spell %d %s' % (k, text(a, 8)))
    first = w(0x848F10)
    nip = (first - 0x8F10) // 2
    for k in range(nip):
        a = 0x840000 | w(0x848F10 + 2 * k)
        anim = rom[lo(a) + 2]
        name = text(a + 6)
        u.setdefault(anim, []).append('IP %d %s' % (k + 1, name))
    for e, why in FIXED.items():
        u.setdefault(e, []).append(why)
    return u


class Decoder:
    def __init__(self, rom, bank=BANK):
        self.rom = rom
        self.bank = bank
        self.ins = {}          # addr16 -> (op, operands list, length, raw bytes)
        self.labels = {}       # addr16 -> set of reasons
        self.errors = []
        self.owner = {}        # byte addr16 -> instruction start

    def b(self, a):
        return self.rom[lo(self.bank << 16 | a)]

    def w(self, a):
        return self.b(a) | self.b(a + 1) << 8

    def label(self, a, why):
        self.labels.setdefault(a, set()).add(why)

    def decode_from(self, start, why):
        self.label(start, why)
        work = [start]
        while work:
            a = work.pop()
            while True:
                if a in self.ins:
                    break
                if not (0x8000 <= a <= 0xFFFF):
                    self.errors.append('address out of bank: %04X' % a); break
                op = self.b(a)
                if op not in OPS:
                    self.errors.append('invalid opcode %02X at %04X' % (op, a)); break
                name, spec, flow = OPS[op]
                p = a + 1; args = []
                for c in spec:
                    if c == 'b': args.append(('b', self.b(p)))
                    elif c == 's': args.append(('s', self.b(p)))
                    else: args.append((c, self.w(p)))
                    p += SIZE[c]
                if flow == 'party':
                    for k in range(PARTY_ENTRIES):
                        args.append(('p', self.w(p))); p += 2
                length = p - a
                for k in range(a, p):
                    if k in self.owner and self.owner[k] != a:
                        self.errors.append('overlap at %04X (%04X vs %04X)' % (k, self.owner[k], a))
                    self.owner[k] = a
                self.ins[a] = (op, args, length)
                for c, v in args:
                    if c == 'p':
                        self.label(v, 'target')
                        work.append(v)
                if flow in ('end', 'jump', 'ret', 'party'):
                    break
                a = p
        return

    def run(self, orphans=True):
        self.entries = [self.w(0x8000 + 2 * k) for k in range(COUNT)]
        for k, e in enumerate(self.entries):
            if e:                                   # 0 = unused effect id
                self.decode_from(e, 'effect %d' % k)
        self.orphans = set()
        if orphans:                                 # unreferenced scripts between the reachable ones
            while True:
                gaps = [(a, b) for a, b in self.coverage()[4] if b < SCRIPT_END]
                found = False
                for a, b in gaps:
                    trial = Decoder(self.rom, self.bank); trial.entries = []
                    trial.decode_from(a, 'orphan')
                    if trial.errors or any(k in self.owner and self.owner[k] != v for k, v in trial.owner.items()):
                        continue                    # invalid, or misaligned with known code
                    if not all(a <= k <= b for k in trial.owner if k not in self.owner):
                        continue
                    self.decode_from(a, 'orphan'); self.orphans.add(a); found = True
                if not found:
                    break

    # ------------------------------------------------------------ output
    def name(self, a):
        if a in self.entry_of:
            return 'E%03d' % self.entry_of[a]
        if a in self.orphans:
            return 'UNUSED_%04X' % a
        return 'L_%04X' % a

    def listing(self):
        self.users = users(self.rom)
        self.entry_of = {}
        for k, e in enumerate(self.entries):
            self.entry_of.setdefault(e, k)
        out = ['; Lufia II battle effect scripts, bank $95 (generated by effectdec.py)',
               '; Assemble with effectasm.py. Pointers are 16-bit addresses in the script bank.',
               '; Each table line: effect number, the script, and who plays it (spell = id + $12,',
               '; IP = animation byte of the IP record, or fixed ids in battle code).', '',
               'org $8000', '']
        for k, e in enumerate(self.entries):
            who = self.users.get(k, [])
            tail = ('   <- ' + '; '.join(who)) if who else ''
            if not e:
                out.append('    table 0                ; %3d ($%02X) unused%s' % (k, k, tail)); continue
            share = [j for j, f in enumerate(self.entries) if f == e and j != k]
            out.append('    table %-14s ; %3d ($%02X)%s%s' % (self.name(e), k, k,
                       ('  (same script as %s)' % ', '.join(str(j) for j in share)) if share else '', tail))
        out.append('')
        prev_end = None
        for a in sorted(self.ins):
            op, args, length = self.ins[a]
            if prev_end is not None and a != prev_end:
                gap = a - prev_end
                if gap > 0:
                    data = bytes(self.b(prev_end + i) for i in range(gap))
                    out.append('    bytes %s   ; %d unreached byte(s) at $%04X' % (' '.join('$%02X' % x for x in data), gap, prev_end))
                    out.append('')
            if a in self.labels:
                if prev_end is None or a != prev_end or a in self.entry_of:
                    out.append('')
                refs = ''
                if a in self.orphans:
                    refs = '   ; not referenced anywhere (unused animation)'
                if a in self.entry_of:
                    ks = [str(j) for j, f in enumerate(self.entries) if f == a]
                    refs = '   ; effect ' + ', '.join(ks)
                out.append('%s:%s' % (self.name(a), refs))
            name, spec, flow = OPS[op]
            parts = []
            for c, v in args:
                if c == 'p': parts.append(self.name(v))
                elif c == 'w': parts.append('$%04X' % v)
                else: parts.append('$%02X' % v)
            raw = bytes(self.b(a + i) for i in range(length))
            out.append('    %-28s %-34s ; %04X: %s' % (name, ', '.join(parts), a, raw.hex(' ')))
            prev_end = a + length
        out.append('')
        for a, b, what in DATA_REGIONS:
            out.append('; $%04X-$%04X: %s' % (a, b, what))
        return '\n'.join(out) + '\n'

    def coverage(self):
        start = 0x8000 + 2 * COUNT
        covered = set(self.owner)
        lo_, hi_ = min(covered), max(covered)
        used = len(covered)
        gaps = []
        a = start
        while a <= 0xFFFF:
            if a not in covered:
                b0 = a
                while a <= 0xFFFF and a not in covered:
                    a += 1
                gaps.append((b0, a - 1))
            else:
                a += 1
        return start, lo_, hi_, used, gaps


def main():
    rom = open(sys.argv[1], 'rb').read()
    bank = int(sys.argv[sys.argv.index('--bank') + 1].lstrip('$'), 16) if '--bank' in sys.argv else BANK
    d = Decoder(rom, bank)
    d.run()
    text = d.listing()
    outp = sys.argv[sys.argv.index('-o') + 1] if '-o' in sys.argv else None
    if outp:
        open(outp, 'w').write(text)
    start, lo_, hi_, used, gaps = d.coverage()
    print('effects: %d (unique entry points %d)' % (COUNT, len(set(d.entries))))
    print('instructions: %d, labels: %d' % (len(d.ins), len(d.labels)))
    print('script bytes decoded: %d of %d after the table ($%04X-$FFFF)' % (used, 0x10000 - start, start))
    big = [(a, b) for a, b in gaps if b - a + 1 >= 4]
    print('unused (orphan) scripts: %d' % len(d.orphans))
    print('gaps: %d (%d of 4+ bytes, %d bytes total)' % (len(gaps), len(big), sum(b - a + 1 for a, b in gaps)))
    for a, b in big[:40]:
        print('   $%04X-$%04X %5d' % (a, b, b - a + 1))
    print('errors: %d' % len(d.errors))
    for e in d.errors[:40]:
        print('  ', e)
    if '--json' in sys.argv:
        js = {'entries': d.entries,
              'ins': {'%04X' % a: [op, [[c, v] for c, v in args], n] for a, (op, args, n) in d.ins.items()},
              'gaps': gaps, 'errors': d.errors}
        json.dump(js, open(sys.argv[sys.argv.index('--json') + 1], 'w'))


if __name__ == '__main__':
    main()
