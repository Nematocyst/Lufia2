"""Lufia II field map data: read and write the cell layers of a map in the ROM.

Map data = compressed resource $3F + map id (FieldLoadMapResources $80:EAE7) -> $7F:0000:
    6-byte header (byte 0 = number of layers/sections), then per layer:
    word section id, byte width, byte height, then W*H cell words (row-major).
Cell word: bits 0-9 metatile number (tileset resource $130 + $CF:F72E[map]); bits 10-15 flags.
Metatile = 4 BG tile words stored column-major (TL, BL, TR, BR), 16x16 pixels.
Collision comes from the tileset's metatile attribute table (FieldBuildAttributes $80:ED9C).

    m = MapData(rom, 0xD6); m.cell(0, x, y); m.set(0, x, y, value); new_rom = m.write(rom)
"""
import sys
sys.path.insert(0, '/home/claude/lufia2/tools')
import l2compress as L


def table_addr(rom):
    """Resource table: $A7:8000 in the original, $E0:8000 after the backgrounds build (read from the code)."""
    o = L.lo(0x808EA9)
    assert rom[o] == 0xBF and rom[o + 1] == 0x00 and rom[o + 2] == 0x80, 'unexpected DecompressResource code'
    return rom[o + 3] << 16 | 0x8000


def resource_off(rom, rid):
    t = L.lo(table_addr(rom)) + 3 * rid
    return L.lo(L.stream_addr(rom[t:t + 3]))


def map_resource(rom, mid):
    """Map-data resource id: $3F + map, or (with mapext's hook at $80:EB23) NEWRES + map - $F2 for new maps."""
    o = L.lo(0x80EB23)
    if rom[o] == 0x22 and mid >= 0xF2:                  # JSL MapResId
        h = L.lo(rom[o + 1] | rom[o + 2] << 8 | rom[o + 3] << 16)
        assert rom[h] == 0xC9 and rom[h + 5] == 0x18 and rom[h + 6] == 0x69
        return mid + (rom[h + 7] | rom[h + 8] << 8)
    return 0x3F + mid


class MapData:
    def __init__(self, rom, mid, table=None):
        self.mid = mid
        self.res = map_resource(rom, mid)
        self.start = resource_off(rom, self.res)
        self.data, self.used = L.decode(rom[self.start:])
        self.data = bytearray(self.data)
        d = self.data
        n = d[0]
        self.layers = []                       # (offset of first cell, W, H, section id)
        p = 6
        for k in range(n):
            sid = d[p] | d[p + 1] << 8; W = d[p + 2]; H = d[p + 3]
            self.layers.append((p + 4, W, H, sid))
            p += 4 + 2 * W * H
        self.tail = p                          # anything after the layers stays as it is

    def cell(self, k, x, y):
        o, W, H, _ = self.layers[k]
        i = o + 2 * (y * W + x)
        return self.data[i] | self.data[i + 1] << 8

    def set(self, k, x, y, v):
        o, W, H, _ = self.layers[k]
        i = o + 2 * (y * W + x)
        self.data[i] = v & 0xFF; self.data[i + 1] = v >> 8

    def grid(self, k):
        o, W, H, _ = self.layers[k]
        return [[self.cell(k, x, y) for x in range(W)] for y in range(H)]

    def write(self, rom, free=None):
        """Re-compress and write back. In place if it fits; otherwise at CPU address `free`
        (an expansion area, e.g. $D7:8000 in the combined build) and the resource table entry is
        repointed. Returns (rom, compressed size, address used or None for in place)."""
        enc = L.encode(bytes(self.data))
        out = bytearray(rom)
        if len(enc) <= self.used:
            out[self.start:self.start + len(enc)] = enc
            return out, len(enc), None
        if free is None:
            raise ValueError('map $%02X: %d bytes compressed, only %d in place: give a free address'
                             % (self.mid, len(enc), self.used))
        a = free
        for b in enc:                      # the decoder runs $8000-$FFFF of each bank, then the next bank
            if L.lo(a) >= len(out):
                raise ValueError('free address $%06X is past the end of the ROM' % a)
            if out[L.lo(a)] not in (0x00, 0xFF):
                raise ValueError('$%06X is not free' % a)
            out[L.lo(a)] = b
            a += 1
            if a & 0xFFFF == 0:
                a += 0x8000
        v = ((free >> 16) - 0xA7) << 15 | (free & 0x7FFF)
        t = L.lo(table_addr(out)) + 3 * self.res
        out[t:t + 3] = bytes([v & 0xFF, v >> 8 & 0xFF, v >> 16])
        assert L.lo(L.stream_addr(out[t:t + 3])) == L.lo(free)
        return out, len(enc), a
