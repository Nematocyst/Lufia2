"""Build a 4 MB ROM with replaced battle backgrounds.

    python3 bbg_build.py in.sfc out.sfc ID=picture.png [ID=picture.png ...]
    python3 bbg_build.py in.sfc out.sfc ID=picture.png@mask.png@gradient.npy     (see-through sky + gradient)

Layout of the expansion (LoROM, banks $E0-$FF are new):
  $E0:8000  resource table, 1024 entries x 3 bytes (DecompressResource $80:8EA9/$80:8EB1 repointed)
  $E0:9000  battle-background palettes, 64 bytes each (BattleBackgroundPrepare $81:BA33/$81:BA3A)
  $E0:A000  third palettes (CGRAM row 4), 32 bytes each, same index as the palette table; zeros = none
  $E0:B000  extra-tile table, 5 bytes per graphics index (long pointer, byte count; 0 = none)
  $F3:8000+ extra tiles (beyond 256), uncompressed; bgext.asm copies them to VRAM $2560 (tile numbers 86-255)
  $E0:F100  background records, 64 ids x 4 bytes (tilemap, graphics, palette, effect)
  $E0:F600  gradient pointers, 64 x 3 bytes (long); record effect byte $10+n selects gradient n
  $E0:F6C0  fixed-colour gradient pointers, 64 x 3 bytes (the same gradient for the subscreen)
  $E1:8000+ new compressed resources
  $F2:8000+ gradient HDMA tables (needs gradient.asm applied afterwards to take effect)
Resource ids:
  680-692   copies of the 13 original background graphics sets (364-376) -> graphics index n = id - 680
  800-819   copies of the 20 original tilemaps (377-396)                 -> tilemap index n = id - 800
  new graphics get indices 13+, new tilemaps 20+, new palettes 20+.
Ids above $18 (e.g. $19) are new slots.
"""
import sys
import numpy as np
from PIL import Image
import l2compress as C
import bbg_convert as B
import bbg_gradient as G

NEWTAB, PALTAB, DATA = 0xE08000, 0xDF9000, 0xE18000
# layout v2 (2026-11-06): the record, palette, row-4 palette and gradient-pointer tables live in bank $DF
# with room for 1024 records, 256 palettes and 240 skies; data spills into the free banks $D0-$DE.
DATA_REGIONS = [(0xE18000, 0xF08000), (0xD08000, 0xDC8000)]      # compressed resources ($F0/$F1 = terrain map)
EXTRA_REGIONS = [(0xF38000, 0x1000000), (0xDC8000, 0xDF8000)]    # uncompressed extra tiles
GFXBASE, TMBASE = 680, 800   # graphics 680+ (up to 799), tilemaps 800+; must not overlap
REC = 0x97FD40
RECNEW = 0xDF8000          # record table: 1024 records x 4 bytes; ids $00-$3F as before, records $40+ via variants2.asm
GRADPTR, FIXPTR, GRADDATA = 0xDFF000, 0xDFF300, 0xF28000   # 240 x 3 bytes each
PAL3TAB = 0xDFD000         # row-4 palettes (needs bgext.asm); 256 entries
EXTRATAB, EXTRADATA = 0xE0B000, 0xF38000   # extra tiles (needs bgext.asm)


def lo(a):
    return (a >> 16 & 0x7F) * 0x8000 + (a & 0x7FFF)


def build(src, out, jobs, npal=2, max_tiles=256, convert_kw=None, keep_orig_pals=True):
    """jobs: list of (id, picture) or (id, picture, mask or None, gradient 224x3 or None[, npal[, convert kwargs]]).
    npal 3 = three palettes (CGRAM rows 2, 3, 4); max_tiles up to 426 (tiles beyond 256 go to VRAM
    $2560-$2FFF). Both need bgext.asm applied afterwards."""
    rom = bytearray(open(src, 'rb').read())
    assert len(rom) in (0x280000, 0x400000)
    if len(rom) < 0x400000:
        rom += bytes(0x400000 - len(rom))
    old = rom[lo(C.TABLE):lo(C.TABLE) + 680 * 3]
    table = bytearray(1024 * 3)
    table[:680 * 3] = old
    for k in range(13):
        table[(GFXBASE + k) * 3:(GFXBASE + k) * 3 + 3] = old[(364 + k) * 3:(364 + k) * 3 + 3]
    for k in range(20):
        table[(TMBASE + k) * 3:(TMBASE + k) * 3 + 3] = old[(377 + k) * 3:(377 + k) * 3 + 3]
    pals = bytearray(rom[lo(0x97CD58):lo(0x97CD58) + 20 * 64])
    pal3 = bytearray(20 * 32)              # originals: no third palette (row 4 stays black)
    if not keep_orig_pals:                 # every original id gets new art: free the 20 slots (table holds 64)
        assert {j[0] for j in jobs} >= set(range(0x18)), 'keep_orig_pals=False needs new art for ids 00-17'
        pals, pal3 = bytearray(), bytearray()
    pos = DATA
    regions = list(DATA_REGIONS); xregions = list(EXTRA_REGIONS)
    def span(a, n):                        # address after n bytes written from a (ROM halves $8000-$FFFF only)
        off = (a & 0x7FFF) + n
        return ((a >> 16) + off // 0x8000) << 16 | 0x8000 | (off % 0x8000)
    next_gfx, next_tm = 13, 20
    gpos, ngrad = GRADDATA, 0
    xpos = EXTRADATA
    extratab = bytearray(256 * 5)

    def put_resource(rid, data):
        nonlocal pos
        enc = C.encode(data)
        if span(pos, len(enc)) > regions[0][1]:   # next free region
            regions.pop(0); assert regions, 'out of space for compressed data'
            pos = regions[0][0]
        a = pos
        for b in enc:                      # the decoder reads $8000-$FFFF of each bank
            rom[lo(a)] = b
            a += 1
            if a & 0xFFFF == 0:            # ran past $xx:FFFF into (xx+1):0000
                a += 0x8000                # -> (xx+1):8000, the next bank's ROM half
        L = (pos >> 16) - 0xA7 << 15 | (pos & 0x7FFF)
        table[rid * 3:rid * 3 + 3] = bytes([L & 0xFF, L >> 8 & 0xFF, L >> 16])
        assert C.lo(C.stream_addr(table[rid * 3:rid * 3 + 3])) == lo(pos)
        pos = a
        return len(enc)

    assert not any(rom[lo(0xDF8000):lo(0xDF8000) + 0x8000]), 'bank $DF must be free'
    rom[lo(RECNEW):lo(RECNEW) + 0x64] = rom[lo(REC):lo(REC) + 0x64]   # ids 00-18 as in the original
    report = []
    for job in jobs:
        bid, png = job[0], job[1]
        mask = job[2] if len(job) > 2 else None
        grad = job[3] if len(job) > 3 else None
        n = job[4] if len(job) > 4 and job[4] else npal
        kw = dict(convert_kw or {}, **(job[5] if len(job) > 5 else {}))   # per-picture converter options
        img = Image.open(png) if isinstance(png, str) else png
        end = G.sky_end(mask) if mask is not None else None
        gfx, tm, pal, prev, ntiles = B.convert_n(img, npal=n, mask=mask, max_tiles=max_tiles,
                                                 backdrop=None if grad is None else G.quantized(grad, end),
                                                 **kw)
        g, t = next_gfx, next_tm
        extra = gfx[0x2000:]
        sg = put_resource(GFXBASE + g, gfx[:0x2000])
        if extra:
            assert len(extra) <= 32 * (256 - B.EXTRA_BASE)
            if (xpos & 0xFFFF) + len(extra) > 0x10000:          # keep each set inside one bank
                xpos = ((xpos >> 16) + 1) << 16 | 0x8000
            if xpos >= xregions[0][1]:
                xregions.pop(0); assert xregions, 'out of space for extra tiles'
                xpos = xregions[0][0]
            rom[lo(xpos):lo(xpos) + len(extra)] = extra
            extratab[5 * g:5 * g + 5] = xpos.to_bytes(3, 'little') + len(extra).to_bytes(2, 'little')
            xpos += len(extra)
        st = put_resource(TMBASE + t, tm)
        p = len(pals) // 64
        pals += pal[:64]
        pal3 += pal[64:96] if len(pal) >= 96 else bytes(32)
        effect = 0
        if grad is not None:
            assert end <= 112, 'sky must end above line 112 (window colour math below uses the fixed colour)'
            for ptr, tab in ((GRADPTR, G.hdma_table(grad, end)), (FIXPTR, G.coldata_table(grad, end))):
                assert (gpos & 0xFFFF) + len(tab) <= 0x10000, 'gradient crosses a bank'
                rom[lo(gpos):lo(gpos) + len(tab)] = tab
                q = lo(ptr) + 3 * ngrad
                rom[q:q + 3] = gpos.to_bytes(3, 'little')
                gpos += len(tab)
            effect = 0x10 + ngrad
            ngrad += 1
            assert ngrad <= 240
        r = lo(RECNEW) + 4 * bid
        rom[r:r + 4] = bytes([t, g, p, effect])
        next_gfx += 1; next_tm += 1
        report.append((bid, str(png), ntiles, sg, st, effect))
    assert len(pals) <= 0x4000 and next_gfx <= 0xFF and GFXBASE + next_gfx <= TMBASE and TMBASE + next_tm <= 1024
    rom[lo(NEWTAB):lo(NEWTAB) + len(table)] = table
    rom[lo(PALTAB):lo(PALTAB) + len(pals)] = pals
    assert len(pal3) == len(pals) // 2 and len(pal3) <= 0x2000
    rom[lo(PAL3TAB):lo(PAL3TAB) + len(pal3)] = pal3
    rom[lo(EXTRATAB):lo(EXTRATAB) + len(extratab)] = extratab

    def patch(a, old_bytes, new_bytes):
        p = lo(a)
        assert rom[p:p + len(old_bytes)] == bytes(old_bytes), hex(a)
        rom[p:p + len(new_bytes)] = bytes(new_bytes)
    patch(0x808EA9, [0xBF, 0x00, 0x80, 0xA7], [0xBF, 0x00, 0x80, 0xE0])
    patch(0x808EB1, [0xBF, 0x01, 0x80, 0xA7], [0xBF, 0x01, 0x80, 0xE0])
    patch(0x81BA03, [0x69, 0x6C, 0x01], [0x69, GFXBASE & 0xFF, GFXBASE >> 8])
    patch(0x81BA13, [0x69, 0x79, 0x01], [0x69, TMBASE & 0xFF, TMBASE >> 8])
    patch(0x81BA32, [0xA9, 0x97], [0xA9, PALTAB >> 16])
    patch(0x81BA39, [0xA9, 0x58, 0xCD], [0xA9, PALTAB & 0xFF, PALTAB >> 8 & 0xFF])
    for k in range(4):                                     # BattleBackgroundPrepare: LDA.l $97FD40+k,X
        a = 0x81B9D5 + 7 * k
        patch(a, [0xBF, 0x40 + k, 0xFD, 0x97], [0xBF, (RECNEW + k) & 0xFF, (RECNEW + k) >> 8 & 0xFF, RECNEW >> 16])
    rom[0x7FD7] = 0x0C                                     # 4 MB
    rom[0x7FDC:0x7FE0] = bytes([0xFF, 0xFF, 0, 0])
    s = sum(rom) & 0xFFFF
    rom[0x7FDE:0x7FE0] = s.to_bytes(2, 'little'); rom[0x7FDC:0x7FDE] = (s ^ 0xFFFF).to_bytes(2, 'little')
    open(out, 'wb').write(rom)
    return report


if __name__ == '__main__':
    jobs = []
    npal = 2
    args = sys.argv[3:]
    if '--npal' in args:
        i = args.index('--npal'); npal = int(args[i + 1]); del args[i:i + 2]
    max_tiles = 256
    if '--tiles' in args:
        i = args.index('--tiles'); max_tiles = int(args[i + 1]); del args[i:i + 2]
    for a in args:
        bid, spec = a.split('=', 1)
        parts = spec.split('@')
        job = [int(bid, 0), parts[0]]
        if len(parts) > 1:
            job.append(np.asarray(Image.open(parts[1]).convert('L')) > 127)
            job.append(np.load(parts[2]))
        jobs.append(tuple(job))
    for r in build(sys.argv[1], sys.argv[2], jobs, npal, max_tiles):
        print('background $%02X <- %s: %d tiles, graphics %d B, tilemap %d B compressed, effect $%02X' % r)
