"""Proof of new maps: a two-room test dungeon in the new map slots $F2 and $F3 (TEST ROMS ONLY).

    python3 build_testdungeon.py IN.sfc OUT.sfc

1. scriptspace: free bank $BF for script blocks (resources $158-$15B -> $D8:8000).
2. mapext: per-map tables -> $DA:8000 with 256 slots; map-data resources for $F2+ = ids $3E0+.
3. $F2 = copy of the cave $06 (layout, walls, objects, its treasure chest: object 0 -> item $01AD),
   exits rewired to $F3; $F3 = copy of the Gratze tower rooms ($D7), stairs and door lead back to $F2.
   Script blocks are new and tiny (in $BF): $F2 has only its chest table.
   Note: per-map state that is keyed by the copied table entries (e.g. the chest's opened state via
   the scene-record entry) is shared with the template map in this proof.
"""
import sys
sys.path.insert(0, '/home/claude/lufia2/tools'); sys.path.insert(0, '/home/claude/lufia2/tools/mapview')
sys.path.insert(0, '/home/claude/lufia2/mods')
import l2compress as L
import mapext, scriptspace, scriptblock
from mapdata import MapData, table_addr
from mapheader import MapHeader

TEMPLATE = 0xD7


def put(rom, a, data):
    p = L.lo(a)
    assert all(b in (0, 0xFF) for b in rom[p:p + len(data)]), '$%06X not free' % a
    rom[p:p + len(data)] = data
    return a + len(data)


def set_resource(rom, rid, addr):
    t = L.lo(table_addr(rom)) + 3 * rid
    v = ((addr >> 16) - 0xA7) << 15 | (addr & 0x7FFF)
    rom[t:t + 3] = bytes([v & 0xFF, v >> 8 & 0xFF, v >> 16])


def header_bytes(exits):
    """A header with only exits (list X=$06)."""
    h = bytearray(0x2C)
    body = bytearray([0xFF])                       # shared empty list at $2C
    ex_off = 0x2C + len(body)
    for e in exits:
        body += bytes(e)
    body.append(0xFF)
    n = 0x2C + len(body)
    h[0] = n & 0xFF; h[1] = n >> 8
    for X in range(2, 0x2C, 2):
        o = ex_off if X == 0x06 else 0x2C
        h[X] = o & 0xFF; h[X + 1] = o >> 8
    return bytes(h + body)


def build(rom):
    rom, _, moved = scriptspace.free_bank(rom, 0xBF, 0xD88000)
    rom, free, info = mapext.extend(rom, free=0xDA8000, newres=0x3E0, template=TEMPLATE)
    T = {int(k, 16): v for k, v in info.items() if len(k) == 6 and k != 'newres'}
    # $F2: copy of "Cave to Sundletan B1" ($06): a cave with a treasure chest (object 0, item $01AD).
    #      All its exits lead to $F3. $F3: copy of the Gratze tower rooms ($D7); its stairs lead back.
    h06 = MapHeader(rom, 0x06)
    h06.lists[0x06] = [[0, 42, 18, 43, 19, 0xF0, 12, 6, 0xF3], [1, 51, 11, 52, 12, 0xF0, 12, 6, 0xF3],
                       [2, 61, 13, 62, 14, 0xF0, 12, 6, 0xF3], [3, 4, 45, 5, 46, 0xF0, 12, 6, 0xF3],
                       [4, 9, 5, 10, 6, 0xF0, 12, 6, 0xF3]]
    maps = {
        0xF2: (0x06, h06.build(),
               # 'PH' + slot lists: slot 2 = [00 -> +16 (end), 03 -> +17 (chest table)], others empty
               b'PH' + bytes([0x0E, 0x00] + [0x15, 0x00] * 5) +
               bytes([0x00, 0x16, 0x00, 0x03, 0x17, 0x00, 0xFF]) + b'\xff' + b'\x00' +
               bytes([0x01, 0xAD, 0x01, 0x00])),       # chest table: object 0 -> item $01AD
        0xF3: (0xD7, header_bytes([[2, 12, 6, 13, 7, 0xF0, 4, 44, 0xF2], [1, 12, 9, 13, 10, 0xF3, 4, 44, 0xF2]]),
               b'PH' + bytes([0x0E, 0x00] * 6) + b'\xff'),
    }
    block_at = 0xBF8000
    for mid, (tpl, hdr, blk) in maps.items():
        for old, size, _ in mapext.BYTE_TABLES:          # every per-map table entry like the template's
            new = T[old]
            mapext.wr(rom, new + mid * size, mapext.rd(rom, new + tpl * size, size))
        mapext.wr(rom, info['enc'] + 2 * mid, mapext.rd(rom, info['enc'] + 2 * tpl, 2))
        mapext.wr(rom, T[0x8F8000] + 3 * mid, b'\xff\xff\x00')        # no field events
        enc = L.encode(bytes(MapData(rom, tpl).data))   # own copy of the map data
        a = free; free = put(rom, free, enc)
        set_resource(rom, info['newres'] + mid - mapext.FIRST_NEW, a)
        a = free; free = put(rom, free, hdr)
        mapext.wr(rom, T[0xCFFCBC] + 3 * mid, bytes([a & 0xFF, a >> 8 & 0xFF, a >> 16]))
        put(rom, block_at, blk)
        r = T[0x878010] + 8 * mid
        w0 = (block_at & 0xFFFF) - 0x8000
        mapext.wr(rom, r, bytes([w0 & 0xFF, w0 >> 8, (block_at >> 16) - 0x87]))
        block_at += 0x40
    return rom, free, info


if __name__ == '__main__':
    rom = open(sys.argv[1], 'rb').read()
    out, free, info = build(rom)
    open(sys.argv[2], 'wb').write(out)
    print('built; free space used up to $%06X' % free)
