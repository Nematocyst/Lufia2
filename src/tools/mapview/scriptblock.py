"""Map script blocks: locate, measure and move them (e.g. into expansion banks).

Map record $87:8010 + 8*map: word w0 + byte b2 = block (base = w0 + $8000, bank = $87 + b2);
word w3 + byte b5 = entry script (same encoding). FieldSelectSceneRecordBase $83:B5AD /
SceneRunMapText $80:BEAF add the bank byte to $87 in 8 bits, so any bank $87-$FF works.
Everything inside a block is relative to its base (gotos, the slot lists), so a block can be
copied verbatim to another bank and only the record changes.
"""
import sys
sys.path.insert(0, '/home/claude/lufia2/tools')
import l2compress as L

REC = 0x878010


def rec_table(rom):
    """$87:8010, or wherever mapext moved it (read from the reader at $83:B5BA)."""
    o = L.lo(0x83B5BA)
    return rom[o + 1] | rom[o + 2] << 8 | rom[o + 3] << 16


def rec(rom, m):
    r = L.lo(rec_table(rom) + 8 * m)
    w0 = rom[r] | rom[r + 1] << 8; b2 = rom[r + 2]; w3 = rom[r + 3] | rom[r + 4] << 8; b5 = rom[r + 5]
    return ((0x87 + b2) << 16 | ((w0 + 0x8000) & 0xFFFF)), ((0x87 + b5) << 16 | ((w3 + 0x8000) & 0xFFFF))


def set_block(rom, m, addr):
    r = L.lo(rec_table(rom) + 8 * m)
    w0 = (addr & 0xFFFF) - 0x8000
    rom[r] = w0 & 0xFF; rom[r + 1] = w0 >> 8 & 0xFF; rom[r + 2] = (addr >> 16) - 0x87


def block_size(rom, m, nmaps=242):
    """Bytes up to the next block (or entry script) that starts after this one."""
    b, _ = rec(rom, m)
    starts = sorted({rec(rom, k)[0] for k in range(nmaps)} | {rec(rom, k)[1] for k in range(nmaps)})
    nxt = [s for s in starts if s > b]
    end = nxt[0] if nxt else (b | 0xFFFF) + 1
    return L.lo(end) - L.lo(b)


def move(rom, m, dest):
    """Copy map m's script block to CPU address dest (free space) and repoint the record."""
    b, _ = rec(rom, m); n = block_size(rom, m)
    s, t = L.lo(b), L.lo(dest)
    assert (dest & 0xFFFF) + n <= 0x10000, 'block would cross a bank'
    assert all(x in (0, 0xFF) for x in rom[t:t + n]), '$%06X not free' % dest
    rom[t:t + n] = rom[s:s + n]
    set_block(rom, m, dest)
    return n
