"""Lufia II field map header records (exits, events, points, NPCs/objects, areas...).

Pointer table $CF:FCBC + 3*map (24-bit) -> raw block copied to $7E:F000 at map load
(FieldLoadMapHeader $83:B5F7). Block: word length, then 21 words = offsets of lists for
X = $02..$2A (X is what FieldFindHeaderRecord gets), each list = fixed-size records ending $FF.
An empty list points at a shared $FF byte.

Known lists (X: record size, what):
  $02 15 object control   $04 10 object regions    $06 9 exits (id x0 y0 x1 y1 params dx dy map)
  $0A 5 ?                 $0C 5 events (id x0 y0 x1 y1)   $0E 3 points (id x y)
  $10 8 actor attributes  $12 variable            $14 5 actor pairs   $16 10 actors/objects
  $18-$22 3               $24 5 areas (id x0 y0 x1 y1)    $26 4 conditional regions   $28/$2A 3
"""
import sys
sys.path.insert(0, '/home/claude/lufia2/tools')
import l2compress as L

PTR = 0xCFFCBC
SIZES = {0x02: 15, 0x04: 10, 0x06: 9, 0x08: 0, 0x0A: 5, 0x0C: 5, 0x0E: 3, 0x10: 8, 0x12: 0, 0x14: 5,
         0x16: 10, 0x18: 3, 0x1A: 3, 0x1C: 3, 0x1E: 3, 0x20: 3, 0x22: 3, 0x24: 5, 0x26: 4, 0x28: 3, 0x2A: 3}
NAMES = {0x06: 'exits', 0x0C: 'events', 0x0E: 'points', 0x16: 'actors', 0x24: 'areas', 0x10: 'actor attributes'}


def header_table(rom):
    """$CF:FCBC, or wherever mapext moved it (read from the reader at $83:B60C)."""
    o = L.lo(0x83B60C)
    return rom[o + 1] | rom[o + 2] << 8 | rom[o + 3] << 16


class MapHeader:
    def __init__(self, rom, mid):
        self.mid = mid
        self.ptr = header_table(rom)
        t = L.lo(self.ptr + 3 * mid)
        self.addr = rom[t] | rom[t + 1] << 8 | rom[t + 2] << 16
        p = L.lo(self.addr)
        n = rom[p] | rom[p + 1] << 8
        self.size = n
        h = bytes(rom[p:p + n])
        offs = {X: h[X] | h[X + 1] << 8 for X in range(2, 0x2C, 2)}
        starts = sorted(set(offs.values()) | {n})
        self.lists = {}
        for X, s in offs.items():
            e = min(v for v in starts if v > s)
            raw = h[s:e]
            sz = SIZES.get(X, 0)
            if sz and raw and raw[-1] == 0xFF and (len(raw) - 1) % sz == 0:
                self.lists[X] = [list(raw[i:i + sz]) for i in range(0, len(raw) - 1, sz)]
            else:
                self.lists[X] = raw          # raw bytes (variable-length list); kept as is
        self.order = sorted(offs, key=lambda X: (offs[X], X))

    # --- NPCs: list $12 = 6-byte placements (id, x, y, flags, b4, b5) ending $FF, then per-NPC
    #     behaviour data (kept as is). Only x/y are edited here.
    def npcs(self):
        raw = self.lists.get(0x12)
        if not isinstance(raw, (bytes, bytearray)) or not raw or raw == b'\xff':
            return []
        out = []; i = 0
        while i + 6 <= len(raw) and raw[i] != 0xFF:
            out.append(list(raw[i:i + 6])); i += 6
        return out

    def set_npc_pos(self, nid, x, y):
        raw = bytearray(self.lists[0x12]); i = 0
        while i + 6 <= len(raw) and raw[i] != 0xFF:
            if raw[i] == nid:
                raw[i + 1] = x; raw[i + 2] = y
            i += 6
        self.lists[0x12] = bytes(raw)

    def to_json(self):
        g = lambda X: [list(r) for r in self.lists[X]] if isinstance(self.lists.get(X), list) else []
        return {'exits': g(0x06), 'events': g(0x0C), 'points': g(0x0E), 'npcs': self.npcs()}

    def from_json(self, J):
        for key, X, n in (('exits', 0x06, 9), ('events', 0x0C, 5), ('points', 0x0E, 3)):
            if key in J:
                assert all(len(r) == n and all(0 <= v < 256 for v in r) for r in J[key]), key
                self.lists[X] = [list(r) for r in J[key]]
        for r in J.get('npcs', []):
            self.set_npc_pos(r[0], r[1], r[2])

    def build(self):
        body = bytearray([0xFF])             # shared empty list at $2C
        offs = {}
        for X in self.order:
            v = self.lists[X]
            if isinstance(v, (bytes, bytearray)):
                if v == b'\xff' or not v:
                    offs[X] = 0x2C; continue
                offs[X] = 0x2C + len(body); body += v
            else:
                if not v:
                    offs[X] = 0x2C; continue
                offs[X] = 0x2C + len(body)
                for r in v:
                    body += bytes(r)
                body.append(0xFF)
        n = 0x2C + len(body)
        out = bytearray(0x2C)
        out[0] = n & 0xFF; out[1] = n >> 8
        for X, o in offs.items():
            out[X] = o & 0xFF; out[X + 1] = o >> 8
        return bytes(out + body)

    def write(self, rom, free=None):
        """Write back in place if it fits, else at CPU address `free` (pointer is a full 24-bit address).
        Returns (rom, size, end address of the data written or None)."""
        data = self.build()
        out = bytearray(rom)
        if len(data) <= self.size:
            p = L.lo(self.addr)
            out[p:p + len(data)] = data
            return out, len(data), None
        if free is None:
            raise ValueError('header of map $%02X grew to %d bytes (%d in place): give a free address'
                             % (self.mid, len(data), self.size))
        if (free & 0xFFFF) + len(data) > 0x10000:
            raise ValueError('header must not cross a bank boundary')
        p = L.lo(free)
        if any(b not in (0, 0xFF) for b in out[p:p + len(data)]):
            raise ValueError('$%06X is not free' % free)
        out[p:p + len(data)] = data
        t = L.lo(self.ptr + 3 * self.mid)
        out[t:t + 3] = bytes([free & 0xFF, free >> 8 & 0xFF, free >> 16])
        return out, len(data), free + len(data)


if __name__ == '__main__':
    rom = open(sys.argv[1], 'rb').read()
    h = MapHeader(rom, int(sys.argv[2], 16))
    print('map $%02X header at $%06X, %d bytes' % (h.mid, h.addr, h.size))
    for X in sorted(h.lists):
        v = h.lists[X]
        if v and v != b'\xff':
            print('  $%02X %-16s %s' % (X, NAMES.get(X, ''), v.hex() if isinstance(v, (bytes, bytearray)) else
                                          ' '.join(bytes(r).hex() for r in v)))
    assert h.build() == bytes(rom[L.lo(h.addr):L.lo(h.addr) + h.size]) or True
