"""Random battle-background variants: each background id can have up to 7 alternates;
every battle picks one of (id, alternates...) at random (game RNG + play-time clock).

    python3 variants_patch.py in.sfc out.sfc 04=19,1A 09=1B ...

Needs a ROM built by bbg_build.py (records at $E0:F100).
Hook: BattleBackgroundPrepare $81:B9C8 "LDA $11E1 / CMP #$18" (5 bytes) -> JSL VariantPick / NOP.
VariantPick returns A = chosen id (B = 0) with flags from CMP #$18, so the rest of the routine
(black-screen check, ASL ASL TAX, record reads) works on the chosen id. $11E1 itself is not
changed, so the id-0 ripple and the other $11E1 checks still see the original id.
Table at $E0:F400: 64 entries x 8 bytes = count, then up to 7 alternate ids.
"""
import sys

lo = lambda a: (a >> 16 & 0x7F) * 0x8000 + (a & 0x7FFF)
CODE, VTAB = 0xE0F300, 0xE0F400
RANDOMBYTE = 0x8082C7             # A = next byte of the game's random table


def build(src, dst, variants):
    rom = bytearray(open(src, 'rb').read()); assert len(rom) == 0x400000
    assert rom[lo(0x81B9D5):lo(0x81B9D9)] == bytes([0xBF, 0x00, 0xF1, 0xE0]), 'needs a bbg_build ROM (records at $E0:F100)'
    p = lo(0x81B9C8)
    assert rom[p:p + 5] == bytes.fromhex('ad e1 11 c9 18'), rom[p:p + 5].hex()
    L = lambda a: [a & 0xFF, a >> 8 & 0xFF, a >> 16]
    rom[p:p + 5] = bytes([0x22, *L(CODE), 0xEA])
    code = bytes([
        0xDA,                          # PHX
        0xAF, *L(0x7E11E1),            # LDA.l $7E11E1   background id
        0xC2, 0x20,                    # REP #$20
        0x29, 0x3F, 0x00,              # AND #$003F
        0x0A, 0x0A, 0x0A,              # ASL x3          8 bytes per entry
        0xAA,                          # TAX
        0xE2, 0x20,                    # SEP #$20
        0xBF, *L(VTAB),                # LDA.l VTAB,X    number of alternates
        0xF0, 0x36,                    # BEQ base
        0x1A,                          # INC A           n = id + alternates
        0x48,                          # PHA
        0x22, *L(RANDOMBYTE),          # JSL RandomByte  game RNG (no time entropy on its own)
        0x18,                          # CLC
        0x6F, *L(0x7E0B50),            # ADC.l $7E0B50   play-time frames (0-59)
        0x6F, *L(0x7E0B4F),            # ADC.l $7E0B4F   play-time seconds
        0x8F, *L(0x004202),            # STA.l WRMPYA    v
        0x68,                          # PLA
        0x8F, *L(0x004203),            # STA.l WRMPYB    n  -> v*n
        0xEA, 0xEA, 0xEA, 0xEA,        # NOP x4          multiply delay
        0xAF, *L(0x004217),            # LDA.l RDMPYH    r = v*n/256 = 0..n-1
        0xF0, 0x14,                    # BEQ base        0 = keep the original id
        0xC2, 0x20,                    # REP #$20
        0x29, 0xFF, 0x00,              # AND #$00FF
        0x48,                          # PHA
        0x8A,                          # TXA
        0x18,                          # CLC
        0x63, 0x01,                    # ADC 1,S
        0xAA,                          # TAX             entry + r
        0x68,                          # PLA
        0xE2, 0x20,                    # SEP #$20
        0xBF, *L(VTAB),                # LDA.l VTAB,X    alternate id
        0x80, 0x04,                    # BRA done
        0xAF, *L(0x7E11E1),            # base: LDA.l $7E11E1
        0xFA,                          # done: PLX
        0xEB, 0xA9, 0x00, 0xEB,        # XBA; LDA #$00; XBA  (B = 0 for the TAX that follows)
        0xC9, 0x18,                    # CMP #$18        flags as the original code
        0x6B])                         # RTL
    q = lo(CODE)
    assert not any(rom[q:q + 0x100]) and not any(rom[lo(VTAB):lo(VTAB) + 0x200]), 'space not free'
    rom[q:q + len(code)] = code
    tab = bytearray(0x200)
    for bid, alts in variants.items():
        assert 0 < len(alts) <= 7 and bid < 0x40 and 0x18 not in alts and bid != 0x18
        tab[bid * 8] = len(alts); tab[bid * 8 + 1:bid * 8 + 1 + len(alts)] = bytes(alts)
    rom[lo(VTAB):lo(VTAB) + 0x200] = tab
    rom[0x7FDC:0x7FE0] = bytes([0xFF, 0xFF, 0, 0]); s = sum(rom) & 0xFFFF
    rom[0x7FDE:0x7FE0] = s.to_bytes(2, 'little'); rom[0x7FDC:0x7FDE] = (s ^ 0xFFFF).to_bytes(2, 'little')
    open(dst, 'wb').write(rom)
    return code


if __name__ == '__main__':
    v = {}
    for a in sys.argv[3:]:
        k, alts = a.split('='); v[int(k, 16)] = [int(x, 16) for x in alts.split(',')]
    code = build(sys.argv[1], sys.argv[2], v)
    print('variants', {('%02X' % k): ['%02X' % x for x in a] for k, a in v.items()}, '| code', len(code), 'bytes')
