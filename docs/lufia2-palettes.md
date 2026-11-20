# Lufia II — battle palettes: a third background palette (2026-10-31)

Technique #2 from the Tales of Phantasia list. Result: **CGRAM row 4 is free in battle**, so
backgrounds can use 3 palettes (45 colours) instead of 2 (30). Rows 5–7 are not free.

## Status
- Working in test ROMs (lake/mountain picture from the user, slot 04): converter, builder and game
  patch (`src/mods/bgext.asm`). Row 4 loads with the background, tiles using palette 4 show it, and
  it survives commands, attacks, Spark, spell/item/equipment lists, messages and results.
- All 23 other original backgrounds pixel-identical with the patch.
- On the lake picture: error on the drawn (non-sky) parts 11.9 (2 palettes) → 10.5 (3) → 9.4
  (3 + gradient). Most useful on pictures with several colour families (greens + blues + browns).
- The tile limit (256) is unchanged — that is the user's bigger problem (the ground). Next
  candidates: #5 more tiles (needs a battle VRAM map), #4 second layer.

## Battle CGRAM map (traced + tested)
- Master copy `$7F:F1DB` (16 rows × 32 bytes) + buffer `$7E:0320`; effects restore from the master
  (`restore_palette`, `$81:968A`). `BattleLoadPalette $81:B974` (row in A, source Y, bank `$24`)
  writes the master and records the source at `$12B3 + 3·row` (address, row number).
- Row 0: windows (`$97:FDE6` / `$FE06`). Row 1: BG3/effects (`$97:FE46`; effect presets).
  Rows 2–3: the background. **Row 4: unused** (loud test colours: no screen change anywhere, never
  overwritten). Rows 5–7: party colours for actors drawn on BG2 during effects — copied from the
  party palette buffer `$7E:4820` (96 bytes) by `BattleColorsMonster $85:8B22` and `$85:97D7`
  (phase `$15B7` = 5 → rows 5–7, 9 → rows 9–B); refreshed every turn. Rows 8–F: sprites.
- Effect scripts' palette writes (all 281 scripts scanned with effectdec.py): rows 1, 9, A, E only.
  `load_palette row, index, count, source` (op `$2C`): source = bank `$96`, `$8000 + 32·source`;
  presets `$DD/$DE/$DF` load rows 1 / 9 / 10.
- BG2's tilemap (`$0400`, BG2SC stays at the field's `$04`) is full of stale field tiles, many tagged
  palette 4, but BG2 only shows inside the window shapes; none of them appeared in any tested screen.

## How it is built
- `bbg_convert.convert_n(img, npal=3, mask=, backdrop=)`: palettes for rows 2..1+npal; starting
  splits = colour clusters + horizontal band pairs; tile budget moved between palettes while the
  error drops. `convert()` (2 palettes) is unchanged, so approved art converts identically.
- `bbg_build.py ... --npal 3` (or job tuple `(id, pic, mask, grad, 3)`): rows 2–3 go to the palette
  table `$E0:9000 + 64p` as before; row 4 to `$E0:A000 + 32p` (zeros for originals and 2-palette
  art = black, as before).
- `bgext.asm` (replaces gradient.asm; same hooks): at `$81:BAB9` also copies `$E0:A000 + 32·p`
  (p = `$11E4`) into row 4 of the buffer and the master, sets `$73` bit 7 (CGRAM upload). Skipped
  for the black screen `$18`.
- Test tools: `src/mods/paltest.asm` (fills rows 4–7 with test colours), `src/tools/pal.py`
  (row-usage logger).
