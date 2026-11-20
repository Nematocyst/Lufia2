"""Map-id extension: room for new maps $F2-$FE (13 slots).

Map ids are bytes; $F0/$F1 are the Ancient Cave, $FF means "same map" in exits. Every per-map
table stops at $F0 and is followed by other data, so this moves each table to free space with
256 entries (copies of the old ones; new slots filled from a template map) and repoints its
readers. The map-data resource number ($3F + map) runs into the tilesets at $130, so maps $F2+
get resource ids NEWRES + (map - $F2) through a small hook.

Tables (reader addresses):
  $87:8010  8 B  script block / entry script / name     $83:B5BA $83:B5C7 $80:BEB9 $80:BEC6 $80:C894 $82:F4A3
  $CF:F72E  1 B  tileset resource                         $80:EB8B
  $CF:F81E  1 B  scene graphics resource                  $80:F03B
  $CF:F90E  1 B  extra section / alternate tileset        $80:EB4B $80:F217
  $CF:FA08  1 B  palette                                  $80:F2D2
  $CF:FBA6  1 B  scene records                            $80:EFC8
  $CF:FCBC  3 B  header records (24-bit pointer)          $83:B601 $83:B60C $86:9F44 $86:9F4E
  $8F:8000  3 B  field event block                        $80:E86D $80:E88C
  $91:B8B5  2 B  object-condition list offset (index read only; the lists stay)   $80:E85D
  $81:B9AC  2 B  encounter list offset (relative to $81:B9AC)  hook at $81:837B
  resource $3F+map                                        hook at $80:EB23 (CLC / ADC #$003F)
Not moved: $94:C998 (map -> area, only used to count treasures per area for maps < $F1).

    rom, end = extend(rom, free=0xDA8000, newres=0x3E0)
"""
import sys
sys.path.insert(0, '/home/claude/lufia2/tools'); sys.path.insert(0, '/home/claude/lufia2/tools/mapview')
import l2compress as L
from mapdata import table_addr

NMAPS = 0xF2                       # entries kept as they are: maps 0..$F1 (the cave ids read past the end; preserved)
FIRST_NEW = 0xF2

BYTE_TABLES = [  # (old base, entry size, [reader instruction addresses (LDA.l abs,X)])
    (0x878010, 8, [0x83B5BA, 0x83B5C7, 0x80BEB9, 0x80BEC6, 0x80C894, 0x82F4A3]),
    (0xCFF72E, 1, [0x80EB8B]),
    (0xCFF81E, 1, [0x80F03B]),
    (0xCFF90E, 1, [0x80EB4B, 0x80F217]),
    (0xCFFA08, 1, [0x80F2D2]),
    (0xCFFBA6, 1, [0x80EFC8]),
    (0xCFFCBC, 3, [0x83B601, 0x83B60C, 0x869F44, 0x869F4E]),
    (0x8F8000, 3, [0x80E86D, 0x80E88C]),
    (0x91B8B5, 2, [0x80E85D]),
]


def rd(rom, a, n): return bytes(rom[L.lo(a):L.lo(a) + n])


def wr(rom, a, b): rom[L.lo(a):L.lo(a) + len(b)] = b


def long_operand(rom, ins):
    o = L.lo(ins)
    assert rom[o] in (0xBF, 0x7F, 0x6F, 0xAF), 'not a long read at $%06X: %02X' % (ins, rom[o])
    return rom[o + 1] | rom[o + 2] << 8 | rom[o + 3] << 16


def relocate_table_tool(rom):
    """The backgrounds build moves the resource table to $E0:8000 with 1024 slots; do the same on a
    plain ROM so new resource ids exist."""
    if table_addr(rom) == 0xE08000:
        return rom
    assert table_addr(rom) == 0xA78000
    t_old, t_new = L.lo(0xA78000), L.lo(0xE08000)
    assert all(b in (0, 0xFF) for b in rom[t_new:t_new + 0xC00])
    rom[t_new:t_new + 0xC00] = bytes(0xC00)
    rom[t_new:t_new + 680 * 3] = rom[t_old:t_old + 680 * 3]
    for ins in (0x808EA9, 0x808EB1):
        o = L.lo(ins)
        assert rom[o + 3] == 0xA7
        rom[o + 3] = 0xE0
    return rom


def extend(rom, free=0xDA8000, newres=0x3E0, template=0x0D):
    """Returns (rom, next free address, info). `template` = map whose table entries new slots copy."""
    rom = bytearray(rom)
    if len(rom) < 0x400000:
        rom += bytes(0x400000 - len(rom))
    rom = relocate_table_tool(rom)
    a = free
    info = {}
    for old, size, readers in BYTE_TABLES:
        new = a
        tbl = bytearray(rd(rom, old, NMAPS * size))
        for m in range(NMAPS, 256):
            tbl += rd(rom, old + template * size, size)
        assert all(b in (0, 0xFF) for b in rd(rom, new, 256 * size)), '$%06X not free' % new
        wr(rom, new, tbl)
        for ins in readers:
            op = long_operand(rom, ins)
            delta = op - old
            assert 0 <= delta < size, 'reader $%06X reads $%06X, not table $%06X' % (ins, op, old)
            n = new + delta
            o = L.lo(ins)
            rom[o + 1] = n & 0xFF; rom[o + 2] = n >> 8 & 0xFF; rom[o + 3] = n >> 16
        info['%06X' % old] = new
        a = new + 256 * size
    # new maps: no field events, no header beyond the template's (overwritten when a map is added)
    for m in range(FIRST_NEW, 0xFF):
        wr(rom, info['8F8000'] + 3 * m, b'\xff\xff\x00')
    # encounter offsets: 256-entry word table (relative to $81:B9AC) + hook
    enc = a
    tbl = bytearray(rd(rom, 0x81B9AC, NMAPS * 2))
    for m in range(NMAPS, 256):
        tbl += rd(rom, 0x81B9AC + template * 2, 2)
    wr(rom, enc, tbl); a = enc + 512
    # hook code
    code_at = a
    enc_hook = code_at
    # EncLookup: in A16 = map id. Out A8 = group byte (as the original sequence leaves it).
    code = bytearray()
    code += bytes([0x0A, 0xAA])                                              # ASL A ; TAX
    code += bytes([0xBF, enc & 0xFF, enc >> 8 & 0xFF, enc >> 16])            # LDA.l enc,X
    code += bytes([0x18, 0x65, 0x00, 0xAA, 0xE2, 0x20])                      # CLC ; ADC $00 ; TAX ; SEP #$20
    code += bytes([0xBF, 0xAC, 0xB9, 0x81, 0x6B])                            # LDA.l $81B9AC,X ; RTL
    res_hook = code_at + len(code)
    # MapResId: in A16 = map id, out A16 = resource id (C clear like after the original ADC).
    code += bytes([0xC9, FIRST_NEW, 0x00, 0x90, 0x05])                       # CMP #$00F2 ; BCC +5
    d = newres - FIRST_NEW
    code += bytes([0x18, 0x69, d & 0xFF, d >> 8, 0x6B])                      # CLC ; ADC #d ; RTL
    code += bytes([0x18, 0x69, 0x3F, 0x00, 0x6B])                            # + CLC ; ADC #$003F ; RTL
    wr(rom, code_at, bytes(code)); a = code_at + len(code)
    # patch $81:837B: ASL TAX LDA.w $B9AC,X CLC ADC $00 TAX SEP#$20 LDA.w $B9AC,X  (14 bytes)
    assert rd(rom, 0x81837B, 14) == bytes.fromhex('0aaabdacb918650 0aae220bdacb9'.replace(' ', ''))
    wr(rom, 0x81837B, bytes([0x22, enc_hook & 0xFF, enc_hook >> 8 & 0xFF, enc_hook >> 16]) +
       bytes([0x80, 0x08]) + bytes(8 * [0xEA]))                              # JSL ; BRA +8 (to $81:8389)
    # patch $80:EB23 (in FieldLoadMapResources): CLC ; ADC #$003F
    assert rd(rom, 0x80EB23, 4) == bytes.fromhex('18693f00'), rd(rom, 0x80EB23, 4).hex()
    wr(rom, 0x80EB23, bytes([0x22, res_hook & 0xFF, res_hook >> 8 & 0xFF, res_hook >> 16]))
    info['enc'] = enc; info['code'] = code_at; info['newres'] = newres
    return rom, a, info


def add_map(rom, info, mid, *, data, tileset_like, header=None, block=None, names_like=None):
    """Fill slot `mid` ($F2-$FE): map data (bytes, compressed here), the per-map table entries
    copied from map `tileset_like`, optional header bytes (raw block) and script block address."""
    assert FIRST_NEW <= mid < 0xFF
    T = {int(k, 16): v for k, v in info.items() if len(k) == 6 and k != 'newres'}
    for old, size, _ in BYTE_TABLES:
        if old in (0x8F8000,):
            continue
        new = T[old]
        wr(rom, new + mid * size, rd(rom, new + tileset_like * size, size))
    enc = info['enc']; wr(rom, enc + 2 * mid, rd(rom, enc + 2 * tileset_like, 2))
    return rom
