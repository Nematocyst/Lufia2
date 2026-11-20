"""Tiny assembler for Lufia II scene scripts (the inverse of scriptdec.py).

    a = Asm(base=0x8AEB1C, org=0x8AF026)          # base = the map's script block base
    a.label('TOP')
    a.op(0x14, 0x01, 0xC8, 0x40, 0xD2); a.target(0x20, 'NEXT'); a.op(0xFF)   # if [...] then->NEXT
    a.window('Hello,\\nthere!')                    # $08 + compressed text
    a.op(0x01)                                     # wait_button
    a.goto('TOP')
    data = a.assemble()                            # bytes; a.addr['TOP'] = CPU address

Text compression, in the order the game supports it:
  * $80-$FF  = dictionary word $200+(b-$80), 1 byte
  * $05 xx / $06 xx = dictionary word $000-$1FF, 2 bytes
  * $0C-$0F  = "?" "!" "," "." followed by a new line, $03 = new line
  * $0A lo hi = copy (hi>>4)+2 raw bytes from (address of $0A + 1) - (hi&F:lo), i.e. a
    back-reference into earlier text of this assembly (2..17 bytes, up to 4095 back).
    References only cover plain ASCII bytes, as in every vanilla script: the copy length is
    counted in text-engine steps, not bytes, so dictionary words, $05/$06 pairs, new lines
    and punctuation codes break it.
"""
import sys
sys.path.insert(0, '/home/claude/lufia2/tools')
import scriptdec as SD

DICT = SD.DICTW                     # 0x280 words
PUNCT = {'?': 0x0C, '!': 0x0D, ',': 0x0E, '.': 0x0F}


def options(s, i):
    """(raw token, chars consumed, decoded text) choices at s[i]."""
    c = s[i]
    opts = []
    if c == '\n':
        opts.append((bytes([0x03]), 1))
    elif c in PUNCT and i + 1 < len(s) and s[i + 1] == '\n':
        opts.append((bytes([PUNCT[c]]), 2))
    if c != '\n':
        assert 0x20 <= ord(c) < 0x7F, repr(c)
        opts.append((bytes([ord(c)]), 1))
    for w, k in WORDS:
        if s.startswith(w, i):
            tok = bytes([0x80 + k - 0x200]) if k >= 0x200 else bytes([0x05 if k < 0x100 else 0x06, k & 0xFF])
            opts.append((tok, len(w)))
    return [(t, ln, s[i:i + ln]) for t, ln in opts]


WORDS = [(w, i) for i, w in enumerate(DICT) if w and all(0x20 <= ord(c) < 0x7F for c in w)]


def encode_text(s):
    """Text -> list of tokens (raw byte strings), minimal size via DP over ASCII and dictionary."""
    n = len(s)
    best = [None] * (n + 1)          # best[i] = (cost, tokens) for s[i:]
    best[n] = (0, [])
    words = [(w, i) for i, w in enumerate(DICT) if w and all(0x20 <= ord(c) < 0x7F for c in w)]
    for i in range(n - 1, -1, -1):
        c = s[i]
        opts = []
        if c == '\n':
            opts.append((bytes([0x03]), 1))
        elif c in PUNCT and i + 1 < n and s[i + 1] == '\n':
            opts.append((bytes([PUNCT[c]]), 2))
        if c != '\n':
            assert 0x20 <= ord(c) < 0x7F, repr(c)
            opts.append((bytes([ord(c)]), 1))
        for w, k in words:
            if s.startswith(w, i):
                tok = bytes([0x80 + k - 0x200]) if k >= 0x200 else bytes([0x05 if k < 0x100 else 0x06, k & 0xFF])
                opts.append((tok, len(w)))
        cand = []
        for tok, ln in opts:
            c2, t2 = best[i + ln]
            cand.append((c2 + len(tok), [tok] + t2))
        best[i] = min(cand, key=lambda x: (x[0], len(x[1])))
    return best[0][1]


def encode_far(s):
    """Far text (script op $02): plain ASCII, new lines and punctuation codes, $00-terminated.
    No dictionary words: printing one would overwrite the far text's return address."""
    out = bytearray()
    i = 0
    while i < len(s):
        c = s[i]
        if c == '\n':
            out.append(0x03)
        elif c in PUNCT and i + 1 < len(s) and s[i + 1] == '\n':
            out.append(PUNCT[c]); i += 1
        else:
            assert 0x20 <= ord(c) < 0x7F, repr(c)
            out.append(ord(c))
        i += 1
    return bytes(out) + b'\x00'


class Asm:
    def __init__(self, base, org, far_org=None):
        self.base, self.org = base, org
        self.far_strings = {}         # encoded far string -> label
        self.far_refs = []            # (offset in output, label)
        self.items = []              # ('raw', bytes) | ('target', label) | ('text', tokens)
        self.labels = {}

    # -------------------------------------------------------------- building
    def label(self, name):
        self.items.append(('label', name))

    def op(self, *bs):
        self.items.append(('raw', bytes(bs)))

    def target(self, prefix, name):
        if prefix is not None:
            self.items.append(('raw', bytes([prefix])))
        self.items.append(('target', name))

    def goto(self, name):
        self.target(0x1C, name)

    def far(self, text):
        """Far-text op $02 (inside a window): the ASCII string is emitted separately with a
        label; the 3-byte pointer is written symbolically (see far_refs / far_strings)."""
        enc = encode_far(text)
        if enc not in self.far_strings:
            self.far_strings[enc] = 'IrisFar%d' % len(self.far_strings)
        self.items.append(('raw', b'\x02'))
        self.items.append(('farptr', self.far_strings[enc]))

    def far_window(self, *parts):
        """$08 window; each part is a far string, or ('text', s) for in-place compressed text."""
        self.items.append(('raw', b'\x08'))
        for p in parts:
            if isinstance(p, tuple):
                self.items.append(('text', p[1]))
            else:
                self.far(p)

    def window(self, text):
        self.items.append(('raw', b'\x08'))
        self.items.append(('text', text))

    # -------------------------------------------------------------- output
    def assemble(self, max_len=None):
        # pass 1: back-references (sizes are final after this) and label addresses
        history = []                  # (address, token bytes) of plain text tokens emitted so far
        layout = []
        pc = self.org
        for kind, v in self.items:
            if kind == 'label':
                self.labels[v] = pc
                continue
            if kind == 'raw':
                layout.append(v); pc += len(v); continue
            if kind == 'target':
                layout.append(('T', v)); pc += 2; continue
            if kind == 'farptr':
                layout.append(('F', v)); pc += 3; continue
            text = v
            n = len(text)
            # DP over characters: literal tokens or references to earlier text (by decoded text)
            cost = [0] * (n + 1); choice = [None] * (n + 1)
            for i in range(n - 1, -1, -1):
                best = None
                for tok, ln, t in options(text, i):
                    c = len(tok) + cost[i + ln]
                    if best is None or c < best[0]:
                        best = (c, ('lit', tok, ln, t))
                for h in range(len(history)):
                    a0 = history[h][0]
                    if pc + 1 - a0 > 0xF00:
                        continue
                    nb, nc, k = 0, 0, h
                    while k < len(history) and history[k][0] == a0 + nb:
                        tk, tt = history[k][1], history[k][2]
                        if nb + len(tk) > 17 or not text.startswith(tt, i + nc):
                            break
                        nb += len(tk); nc += len(tt); k += 1
                        if nb >= 4 and 3 + cost[i + nc] < best[0]:
                            best = (3 + cost[i + nc], ('ref', a0, nb, nc))
                cost[i], choice[i] = best
            i = 0
            out = []
            while i < n:
                ch = choice[i]
                if ch[0] == 'ref':
                    _, a0, nb, nc = ch
                    off = pc + 1 - a0
                    assert 0 < off <= 0xFFF
                    out.append(bytes([0x0A, off & 0xFF, ((nb - 2) << 4) | (off >> 8)]))
                    pc += 3; i += nc
                    continue
                _, tok, ln, t = ch
                if len(tok) == 1 and 0x20 <= tok[0] < 0x7F:   # vanilla copies only plain ASCII
                    history.append((pc, tok, t))
                out.append(tok); pc += len(tok); i += ln
            layout.append(b''.join(out))
        data = bytearray()
        for x in layout:
            if isinstance(x, tuple) and x[0] == 'F':
                self.far_refs.append((len(data), x[1])); data += b'\x00\x00\x00'
            elif isinstance(x, tuple):
                t = self.labels[x[1]] - self.base
                assert 0 <= t <= 0xFFFF
                data += bytes([t & 0xFF, t >> 8])
            else:
                data += x
        if max_len is not None:
            assert len(data) <= max_len, 'script too long: %d > %d' % (len(data), max_len)
        assert (self.org & 0xFFFF) + len(data) <= 0x10000, 'crosses a bank'
        return bytes(data)

    def _plan(self, history, toks, pc0):
        """Back-to-front DP: literal token or a reference into earlier windows."""
        n = len(toks)
        cost = [0] * (n + 1)
        choice = [None] * (n + 1)
        for i in range(n - 1, -1, -1):
            cost[i] = len(toks[i]) + cost[i + 1]; choice[i] = None
            for a0, ntok, nb in self._refs(history, toks, i, pc0):
                if 3 + cost[i + ntok] < cost[i]:
                    cost[i] = 3 + cost[i + ntok]; choice[i] = (a0, ntok, nb)
        return choice

    @staticmethod
    def _refs(history, toks, i, pc):
        out = []
        for h in range(len(history)):
            a0 = history[h][0]
            if pc + 1 - a0 > 0xF00:          # margin: pc grows within the window
                continue
            n, nb = 0, 0
            while (i + n < len(toks) and h + n < len(history) and history[h + n][1] == toks[i + n]
                   and history[h + n][0] == a0 + nb and nb + len(toks[i + n]) <= 17):
                nb += len(toks[i + n]); n += 1
                if nb >= 4:
                    out.append((a0, n, nb))
        return out

    @staticmethod
    def _find_ref(history, toks, i, pc):
        best = None
        for h in range(len(history)):
            a0 = history[h][0]
            if pc + 1 - a0 > 0xFFF:
                continue
            n, nb = 0, 0
            while (i + n < len(toks) and h + n < len(history) and history[h + n][1] == toks[i + n]
                   and history[h + n][0] == a0 + nb and nb + len(toks[i + n]) <= 17):
                nb += len(toks[i + n]); n += 1
            if nb >= 4 and (best is None or nb - 3 > best[2] - 3):
                best = (a0, n, nb)
        return best
