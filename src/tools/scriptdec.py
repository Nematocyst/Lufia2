"""Lufia II (US) text/scene script decompiler.

Script model (from the disassembly, see docs/SCRIPTS.md):
  * Map records at $87:8010 + id*8: word0 + bank byte 2 -> the map's script block
    (base = word0 + $8000 in bank $87+b2); word3 + bank byte 5 -> map entry script.
  * Block: "PH" signature, six word offsets (header slots 2..C) to lists of
    [id, word] pairs ending in $FF; script = base + word.
  * Gotos are relative to the same base. Addresses roll into the next bank
    exactly like SceneScriptSeekRelative ($80:C102).
  * Interpreter $80:9D00: while a text window is open (text_state bit 0),
    bytes $10-$7F are ASCII and $80-$FF dictionary words; otherwise every
    byte is an opcode ($80:CA14 table).

Usage: python3 scriptdec.py            -> docs/scripts/*.txt + build/scriptdec_stats.json
"""
import json
import os
import sys

import rom

d = rom.load()
OUT = '/home/claude/lufia2/docs/scripts'
os.makedirs(OUT, exist_ok=True)
OPS = json.load(open('/home/claude/lufia2/build/script_ops.json'))

# ---------------------------------------------------------------- dictionary
DICT = rom.to_off(0x8EEA00)


def dict_word(i):
    p = d[DICT + 2 * i] | d[DICT + 2 * i + 1] << 8
    o = DICT + p
    s = bytearray()
    while d[o]:
        s.append(d[o])
        o += 1
    return s.decode('latin-1')


DICTW = [dict_word(i) for i in range(0x280)]

# ---------------------------------------------------------------- opcode formats
# b = byte, w = word, T = goto target word (relative to map base)
NAMES = {
    0x00: 'end', 0x01: 'wait_button', 0x03: 'newline', 0x04: 'delay', 0x08: 'window',
    0x09: 'hero_name', 0x0B: 'choice_cursor', 0x05: 'dict0', 0x06: 'dict1', 0x10: 'choice', 0x12: 'switch_var',
    0x13: 'window_ex', 0x14: 'if', 0x15: 'goto_if_flag', 0x16: 'warp', 0x1A: 'set_flag',
    0x1B: 'clear_flag', 0x1C: 'goto', 0x1D: 'set_var', 0x1E: 'add_var', 0x22: 'add_gold',
    0x26: 'sub_gold', 0x2E: 'hide_actor', 0x33: 'actor_move', 0x37: 'wait_frames',
    0x38: 'wait_seconds', 0x3C: 'wait_party_stop', 0x3E: 'forced_blank', 0x3F: 'full_brightness',
    0x41: 'scroll_view', 0x42: 'return', 0x4B: 'music', 0x50: 'typing_sound_off',
    0x57: 'wait_screen_effect', 0x5A: 'shake_start', 0x60: 'ppu_write', 0x68: 'place_actor',
    0x69: 'window_mode', 0x6A: 'goto_if_not_flag', 0x6D: 'title_text', 0x6E: 'title_text_big',
    0x71: 'wait_d0fc', 0x76: 'wait_fade', 0x84: 'yield', 0x8A: 'shake_stop', 0x9E: 'window_m7',
    0xC5: 'stop_fades', 0x0A: 'text_copy', 0x17: 'inn_rest', 0x2D: 'show_actor',
    0x30: 'actor_walk_to', 0x31: 'actor_face', 0x34: 'actor_sprite', 0x3D: 'rebuild_party',
    0x4C: 'sound', 0x54: 'object_anim', 0x6C: 'actor_offset', 0x70: 'fade_out_music',
    0x73: 'spawn_actor', 0x7B: 'place_npc', 0x95: 'coldata_fade', 0x94: 'coldata_fade',
    0x96: 'coldata_fade', 0x97: 'scene_display_reset', 0x98: 'actor_warp', 0xA3: 'actor_action',
    0xA4: 'mosaic_transition', 0x5B: 'scene_cmd', 0x61: 'window_t0', 0x62: 'window_t1',
    0x63: 'window_t2', 0x64: 'window_t3', 0x65: 'window_t4', 0x66: 'window_t5', 0x67: 'window_t6',
    0x89: 'actor_freeze', 0x18: 'open_shop', 0x02: 'far_text',
}
# tentative names (2026-11-12, from handler reads/calls; see lufia2-event-scripts.md)
import os as _os
_T = '/home/claude/lufia2/tools/data/script_op_names_tentative.json'
if _os.path.exists(_T):
    for _k, _v in json.load(open(_T)).items():
        NAMES.setdefault(int(_k, 16), _v)
FMT = {}
for k, v in OPS.items():
    op = int(k, 16)
    reads = [p for p, e in v['paths'] if e in ('next', 'reload', 'yield', 'ret', 'print') or e.startswith('sub')]
    good = [r for r in reads if '<' not in r and 'S' not in r]
    if good:
        best = max(good, key=lambda r: (sum(2 if c == 'w' else 1 for c in r), r.count('w')))
        FMT[op] = best
    else:
        FMT[op] = ''
FMT.update({
    0x08: '', 0x61: '', 0x62: '', 0x63: '', 0x64: '', 0x65: '', 0x66: '', 0x67: '',
    0x13: 'b', 0x9E: 'b', 0x15: 'bT', 0x6A: 'bT', 0x1C: 'T', 0x7B: 'bb',
    0x04: 'b', 0x33: 'bb', 0x36: 'b', 0x37: 'b', 0x38: 'b', 0x4D: 'b', 0x89: 'b',
    0xA1: 'bb', 0xA2: 'b', 0x5B: 'bb',
})
SPECIAL = {0x10, 0x12, 0x14, 0x41, 0x6D, 0x6E}
TRAPS = {0x11, 0x5C, 0x5D}
OPEN = {0x08, 0x10, 0x13, 0x61, 0x62, 0x63, 0x64, 0x65, 0x66, 0x67, 0x9E}
CLOSE = {0x00, 0x42, 0x01, 0x0B, 0x18, 0x53, 0x5B, 0xBC}
ENDS = {0x00, 0x42, 0x1C, 0x12}
PUNCT = {0x0C: '?', 0x0D: '!', 0x0E: ',', 0x0F: '.'}


# ---------------------------------------------------------------- addressing
def seek(bank, a):
    a &= 0xFFFF
    return (bank << 16) | a if a >= 0x8000 else ((bank + 1) << 16) | (a + 0x8000)


class Reader:
    def __init__(self, a24):
        self.a = a24

    def byte(self):
        v = d[rom.to_off(self.a)]
        bank, addr = self.a >> 16, (self.a & 0xFFFF) + 1
        if addr > 0xFFFF:
            bank, addr = bank + 1, 0x8000
        self.a = (bank << 16) | addr
        return v

    def word(self):
        lo = self.byte()
        return lo | self.byte() << 8


# ---------------------------------------------------------------- maps
REC = rom.to_off(0x878010)
NAME_BANK = rom.to_off(0x878000)


def map_name(i):
    ptr = d[REC + 8 * i + 6] | d[REC + 8 * i + 7] << 8
    out, x = bytearray(), ptr
    while d[NAME_BANK + x]:
        c = d[NAME_BANK + x]
        if c == 0x0A:
            lo, hi = d[NAME_BANK + x + 1], d[NAME_BANK + x + 2]
            src = (rom.to_off(0x878000) + x) & ~0xFFF | ((hi & 0xF) << 8) | lo
            if src > NAME_BANK + x:
                src -= 0x1000
            n = (hi >> 4) + 2
            j = 0
            while j < n and d[src + j]:
                out.append(d[src + j])
                j += 1
            x += 3
            continue
        out.append(c)
        x += 1
    return out.decode('latin-1')


SLOT_NAMES = {2: 'start', 4: 'arrive', 6: 'talk', 8: 'event', 0xA: 'slotA', 0xC: 'slotC'}


def map_info(i):
    b = d[REC + 8 * i:REC + 8 * i + 8]
    bank = 0x87 + b[2]
    base = ((b[0] | b[1] << 8) + 0x8000) & 0xFFFF
    entry_bank = 0x87 + b[5]
    entry = seek(entry_bank, (b[3] | b[4] << 8) + 0x8000)
    return bank, base, entry


# ---------------------------------------------------------------- decoder
class Script:
    def __init__(self, bank, base):
        self.bank, self.base = bank, base
        self.lines = {}      # a24 -> (text, length)
        self.labels = {}     # a24 -> name
        self.errors = []
        self.text_bytes = 0

    def target(self, w, base=None):
        return seek(self.bank, (self.base if base is None else base) + w)

    def label(self, w, db):
        # Goto ($80:A3C6) sets $09B9 = scene_record_bank but leaves DB alone, and
        # SceneScriptSeekRelative only loads Y for targets >= $8000: execution
        # continues in the bank currently being read (db). Targets that wrap
        # below $8000 land in scene_record_bank + 1.
        A = (self.cur_base + w) & 0xFFFF
        t = (db << 16) | A if A >= 0x8000 else ((self.bank + 1) << 16) | (A + 0x8000)
        self.labels.setdefault(t, ('L_%04X' if self.cur_base == self.base else 'E_%04X') % w)
        return t, self.labels[t]

    def decode(self, start, tag, base=None):
        # entry scripts run with scene_record_base = $8000 ($80:BEDF)
        self.cur_base = self.base if base is None else base
        work = [(start, False)]
        while work:
            a, textmode = work.pop()
            while True:
                if a in self.lines:
                    break
                r = Reader(a)
                op = r.byte()
                if textmode and op >= 0x10:
                    # gather a run of text
                    s = []
                    b = op
                    while True:
                        if b >= 0x80:
                            s.append(DICTW[0x200 + b - 0x80])
                        elif 0x20 <= b < 0x7F:
                            s.append(chr(b))
                        else:
                            s.append('{%02X}' % b)
                        nxt = Reader(r.a).byte()
                        if nxt < 0x10 or (r.a in self.labels):
                            break
                        b = r.byte()
                    ln = (r.a - a) & 0xFFFF if (r.a >> 16) == (a >> 16) else None
                    self.text_bytes += ln or 0
                    self.lines[a] = (''.join(s), r.a, 'text')
                    a = r.a
                    continue
                name = NAMES.get(op, 'op_%02X' % op)
                if op > 0xCC or op in TRAPS:
                    self.lines[a] = ('??? byte $%02X (invalid opcode) [%s]' % (op, tag), r.a, 'op')
                    self.errors.append((a, op, tag))
                    break
                args, flows = [], []
                if textmode and op in (0x05, 0x06):
                    i = r.byte() + (0x100 if op == 0x06 else 0)
                    self.lines[a] = (DICTW[i], r.a, 'text')
                    a = r.a
                    continue
                if op == 0x02:
                    # far text (Iris patch): 02 lo hi bank -> plain ASCII string, $00-terminated
                    fa = r.byte() | r.byte() << 8 | r.byte() << 16
                    rr = Reader(fa); txt = []
                    while True:
                        b = rr.byte()
                        if b == 0:
                            break
                        txt.append(PUNCT[b] + '\\n' if b in PUNCT else '\\n' if b == 3 else chr(b))
                    self.lines[a] = (''.join(txt), r.a, 'text')
                    a = r.a
                    continue
                if op == 0x0A:
                    # back-reference ($80:9E83): copy (hi>>4)+2 bytes starting at
                    # (address after the $0A byte) - 12-bit offset
                    lo, hi = r.byte(), r.byte()
                    n = (hi >> 4) + 2
                    after = a + 1
                    src = (after & 0xFF0000) | ((after & 0xFFFF) - ((hi & 0xF) << 8 | lo))
                    if (src & 0xFFFF) < 0x8000 or src > after:
                        src = (((after >> 16) - 1) << 16) | ((src & 0xFFFF) | 0x8000)
                    rr = Reader(src)
                    raw = bytes(rr.byte() for _ in range(n))
                    txt, j = [], 0
                    while j < len(raw):
                        b = raw[j]
                        if b >= 0x80:
                            txt.append(DICTW[0x200 + b - 0x80])
                        elif 0x20 <= b < 0x7F:
                            txt.append(chr(b))
                        elif b in (0x05, 0x06) and j + 1 < len(raw):
                            txt.append(DICTW[raw[j + 1] + (0x100 if b == 6 else 0)])
                            j += 1
                        elif b in PUNCT:
                            txt.append(PUNCT[b] + '\\n')
                        elif b == 0x03:
                            txt.append('\\n')
                        else:
                            txt.append('{%02X}' % b)
                        j += 1
                    q = ''.join(txt).replace('"', '\\"')
                    if textmode:
                        self.lines[a] = (''.join(txt).replace('\\n', '\n'), r.a, 'text')
                    else:
                        self.lines[a] = ('text_copy $%06X %d ; "%s"' % (src, n, q), r.a, 'op')
                    a = r.a
                    continue
                if textmode and op in PUNCT:
                    self.lines[a] = (PUNCT[op] + '\n', r.a, 'text')
                    a = r.a
                    continue
                if textmode and op == 0x03:
                    self.lines[a] = ('\n', r.a, 'text')
                    a = r.a
                    continue
                if textmode and op == 0x09:
                    self.lines[a] = ('<HERO>', r.a, 'text')
                    a = r.a
                    continue
                if textmode and op == 0x04:
                    v = r.byte()
                    self.lines[a] = ('<delay %02X>' % v, r.a, 'text')
                    a = r.a
                    continue
                if op == 0x10:      # choice: n, n targets
                    n = r.byte()
                    args.append('%d' % n)
                    for _ in range(n):
                        t, lb = self.label(r.word(), r.a >> 16)
                        args.append(lb)
                        flows.append((t, False))
                elif op == 0x12:    # switch on var: var, n, n targets
                    v, n = r.byte(), r.byte()
                    args += ['var$%02X' % v, '%d' % n]
                    for _ in range(n):
                        t, lb = self.label(r.word(), r.a >> 16)
                        args.append(lb)
                        flows.append((t, False))
                elif op == 0x14:    # condition list
                    terms = []
                    while True:
                        T = r.byte()
                        if T == 0xFF:
                            break
                        if T < 0xC0:
                            kind = T & 0x30
                            if kind == 0x00:
                                terms.append('%sflag$%02X%s' % ('!' if T & 1 else '', r.byte(),
                                             ' &' if T & 0x80 else ' |' if T & 0x40 else ''))
                            elif kind == 0x10:
                                x1, x2 = r.byte(), r.byte()
                                terms.append('t%02X(%02X,%02X)' % (T, x1, x2))
                            else:
                                t, lb = self.label(r.word(), r.a >> 16)
                                terms.append('%s->%s' % ('then' if kind == 0x20 else 'else', lb))
                                flows.append((t, False))
                        else:
                            k = T & 0xF8
                            n = 4 if k == 0xC0 else 3 if k in (0xC8, 0xD0, 0xD8) else 2
                            terms.append('t%02X(%s)' % (T, ' '.join('%02X' % r.byte() for _ in range(n))))
                    args.append('[' + ', '.join(terms) + ']')
                elif op == 0x41:
                    b1, b2 = r.byte(), r.byte()
                    args += ['$%02X' % b1, '$%02X' % b2]
                    if b2 != 0xFF and (b1 & 0xF0) == 0x60:
                        args.append('$%02X' % r.byte())
                elif op in (0x6D, 0x6E):
                    pos = r.word()
                    s = bytearray()
                    while True:
                        c = r.byte()
                        if c == 0:
                            break
                        s.append(c)
                    args += ['$%04X' % pos, '"%s"' % s.decode('latin-1')]
                else:
                    for c in FMT.get(op, ''):
                        if c == 'b':
                            args.append('$%02X' % r.byte())
                        elif c == 'w':
                            args.append('$%04X' % r.word())
                        elif c == 'T':
                            t, lb = self.label(r.word(), r.a >> 16)
                            args.append(lb)
                            flows.append((t, False))
                if op in (0x1A, 0x1B, 0x15, 0x6A) and args:
                    args[0] = 'flag' + args[0]
                if op == 0x05 or op == 0x06:
                    i = int(args[0][1:], 16) + (0x100 if op == 0x06 else 0)
                    args.append('; "%s"' % DICTW[i])
                self.lines[a] = (('%s %s' % (name, ' '.join(args))).rstrip(), r.a, 'op')
                for t, tm in flows:
                    work.append((t, tm))
                if op in ENDS:
                    break
                if op in OPEN:
                    textmode = True
                elif op in CLOSE:
                    textmode = False
                a = r.a

    def render(self):
        out = []
        prev_end = None
        buf, buf_a = [], None

        def flush():
            nonlocal buf, buf_a
            if buf:
                txt = ''.join(buf).replace('"', '\\"').split('\n')
                out.append('  %06X      "%s' % (buf_a, txt[0]) + ('"' if len(txt) == 1 else ''))
                for k, t in enumerate(txt[1:], 1):
                    out.append('              %s%s' % (t, '"' if k == len(txt) - 1 else ''))
            buf, buf_a = [], None

        for a in sorted(self.lines):
            text, end, kind = self.lines[a]
            gap = prev_end is not None and a != prev_end
            if gap or a in self.labels or kind != 'text':
                flush()
            if gap:
                out.append('')
            if a in self.labels:
                out.append('%s:  ; $%02X:%04X' % (self.labels[a], a >> 16, a & 0xFFFF))
            if kind == 'text':
                if buf_a is None:
                    buf_a = a
                buf.append(text)
            else:
                out.append('  %06X      %s' % (a, text))
            prev_end = end
        flush()
        return out


def decompile_all():
    stats = {'maps': 0, 'scripts': 0, 'errors': 0, 'bytes': 0, 'text_bytes': 0}
    errors = []
    index = []
    for i in range(0xF2):
        bank, base, entry = map_info(i)
        s = Script(bank, base)
        o = rom.to_off(seek(bank, base))
        if d[o:o + 2] != b'PH':
            continue
        stats['maps'] += 1
        hdr = [d[o + 2 * k] | d[o + 2 * k + 1] << 8 for k in range(7)]
        entries = []
        for k in range(1, 7):
            r = Reader(s.target(hdr[k]))
            while True:
                key = r.byte()
                if key == 0xFF:
                    break
                w = r.word()
                t = s.target(w)
                s.labels.setdefault(t, 'L_%04X' % w)
                entries.append((2 * k, key, w, t))
        # map entry script (separate pointer, not base-relative)
        s.labels.setdefault(entry, 'ENTRY')
        s.decode(entry, '%02X entry' % i, base=0x8000)
        treasure = []
        for slot, key, w, t in entries:
            if slot == 2 and key == 3:
                # not a script: chest table read by $8E:B6E0 ([object+1, item word], 0-terminated)
                r = Reader(t)
                while True:
                    k = r.byte()
                    if k == 0:
                        break
                    treasure.append((k - 1, r.word()))
                continue
            s.decode(t, '%02X slot%X id%02X' % (i, slot, key))
        nm = map_name(i)
        lines = ['; Map $%02X  %s' % (i, nm),
                 '; script block $%02X:%04X, entry script $%06X' % (bank, base, entry), '']
        for slot, key, w, t in entries:
            lines.append('; %-6s id $%02X -> %s' % (SLOT_NAMES[slot], key, s.labels[t]))
        if treasure:
            lines.append('; treasure (start id $03 table): ' +
                         ', '.join('obj $%02X -> item $%04X' % tr for tr in treasure))
        lines.append('')
        lines += s.render()
        fn = 'map_%02X.txt' % i
        open(os.path.join(OUT, fn), 'w').write('\n'.join(lines) + '\n')
        index.append('%02X\t%s\t%d entries\t%d errors' % (i, nm, len(entries), len(s.errors)))
        stats['scripts'] += len(entries) + 1
        stats['errors'] += len(s.errors)
        stats['text_bytes'] += s.text_bytes
        errors += [('%06X' % a, '%02X' % op, tag) for a, op, tag in s.errors]
        for a, (_, e, _k) in s.lines.items():
            stats['bytes'] += (e - a) & 0xFFFF if (e >> 16) == (a >> 16) else 0
    open(os.path.join(OUT, 'INDEX.txt'), 'w').write('\n'.join(index) + '\n')
    write_dialogue()
    write_opcode_reference()
    json.dump({'stats': stats, 'errors': errors}, open('/home/claude/lufia2/build/scriptdec_stats.json', 'w'), indent=1)
    return stats, errors


def write_dialogue():
    """All text, map by map, in script order, without the opcodes."""
    out = []
    for fn in sorted(f for f in os.listdir(OUT) if f.startswith('map_')):
        lines = open(os.path.join(OUT, fn)).read().split('\n')
        blocks, cur, label = [], None, ''
        for ln in lines:
            if ln and not ln.startswith(' ') and ln.endswith(tuple('0123456789ABCDEF')) and ':  ; $' in ln:
                label = ln.split(':')[0]
            body = ln[14:] if len(ln) > 14 and ln[:2] == '  ' else ''
            if ln.startswith('  ') and ln[2:8].strip() and body.startswith('"'):
                cur = [label + ': ' + body.lstrip('"').rstrip('"')]
                if body.endswith('"') and len(body) > 1:
                    blocks.append(cur); cur = None
            elif cur is not None and ln.startswith('              '):
                t = ln.strip()
                cur.append('    ' + t.rstrip('"'))
                if t.endswith('"'):
                    blocks.append(cur); cur = None
        if blocks:
            out.append('=' * 60)
            out.append(lines[0].lstrip('; '))
            out.append('=' * 60)
            for b in blocks:
                out += b
                out.append('')
    open(os.path.join(OUT, 'ALL_DIALOGUE.txt'), 'w').write('\n'.join(out) + '\n')


def write_opcode_reference():
    rows = ['# Text/scene script opcodes ($80:CA14). fmt: b=byte w=word T=goto target (map-relative)',
            '# special: 10 choice (n, n*T)  12 switch (var, n, n*T)  14 condition list (see SCRIPTS.md)',
            '#          41 two bytes (+1 if first&$F0==$60)  6D/6E word + zero-terminated string',
            '#          0A text back-reference (lo, hi): copy (hi>>4)+2 bytes from (addr+1)-(hi&F:lo)',
            'op\tname\tfmt\thandler\tuses']
    counts = {}
    for fn in os.listdir(OUT):
        if fn.startswith('map_'):
            for ln in open(os.path.join(OUT, fn)):
                p = ln[14:].strip().split(' ')[0] if ln.startswith('  ') else ''
                counts[p] = counts.get(p, 0) + 1
    for op in range(0xCD):
        nm = NAMES.get(op, 'op_%02X' % op)
        fmt = {0x10: 'n T*n', 0x12: 'b n T*n', 0x14: 'cond...FF', 0x41: 'bb[b]', 0x6D: 'w z',
               0x6E: 'w z', 0x0A: 'bb'}.get(op, FMT.get(op, ''))
        if op in TRAPS:
            nm, fmt = '(trap: BRK)', '-'
        rows.append('%02X\t%s\t%s\t$%s\t%d' % (op, nm, fmt or '-', OPS['%02X' % op]['handler'], counts.get(nm, 0)))
    open('/home/claude/lufia2/docs/text/script_opcodes.txt', 'w').write('\n'.join(rows) + '\n')
    json.dump({'%02X' % k: v for k, v in NAMES.items()}, open('/home/claude/lufia2/build/script_op_names.json', 'w'))


if __name__ == '__main__':
    st, er = decompile_all()
    print(st)
    for e in er[:40]:
        print(e)
