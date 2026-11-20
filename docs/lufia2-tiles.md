# Lufia II — more battle-background tiles: 426 instead of 256 (2026-10-31)

Technique #5. Result: **backgrounds can use up to 426 tiles** (tile numbers 256–511 as before, plus
86–255). Working in test ROMs; all original backgrounds pixel-identical with the patch.
**426 is the practical ceiling for battle backgrounds** (see "Beyond 426" below).

## Battle VRAM map (word addresses)
- Maps: BG1 `$0000` (32×32), BG2 `$0400` (BG2SC stays at the field's `$04`; stale field tiles,
  only shown inside window shapes), BG3 `$0800`/`$0A00`, message tilemap `$0E00`.
- BG3 chars `$1000` (2bpp; tile numbers 512+ reach `$2000+`). BG1/BG2 chars base `$2000`
  (BG12NBA `$22`): tile numbers 0–255 = `$2000–$2FFF`, 256–511 = `$3000–$3FFF` (the background),
  512–1023 = `$4000–$5FFF` (sprite graphics; BG2 draws actors this way, with palettes 5–7).
  Sprites (OBSEL `$72`/`$6A` per line via HDMA ch3): `$4000+`, second table `$6000+`.
- Stamp test (fill a chunk with `$FFFF` at battle start, force the emulator to re-decode its tile
  caches with save/load state, replay; screen diff + is the stamp still there) for group `$10`
  (menus, spell, attacks, results):
  - `$2000–$2FFF`: never shown, never rewritten. `$3000–$3FFF`: the background (shown, static).
  - `$4000–$5FFF`: rewritten all the time (sprites). `$6000–$63FF`, `$7000–$73FF`: shown, static.
  - `$6400–$6BFF`, `$7400–$7FFF`: not shown/rewritten in that battle only — **NOT free** (enemy
    sprite space, see below). `$6C00–$6FFF`: rewritten.
- Every queued upload in battle code (`battle_vram_queue` destinations) listed: the only one in
  `$2000–$2FFF` is `BattleQueueTilesAt2000 $85:9D61` → `$2000–$255F` ($AC0 bytes from `$7E:C000`),
  from `BattleShowActionMessage $85:9906` (an action-message window, text drawn as BG3 tiles 512+).
  So `$2560–$2FFF` (tile numbers 86–255, 170 tiles) is free.
- Effects: `load_graphics` decompresses to WRAM `$7E:3800` (not VRAM); `graphics` uploads to VRAM
  `$4000`; `graphics_alt` to `$1800`; `video_register` only feeds shadows `$123C+` → W12SEL, WOBJSEL,
  WH1/3, WOBJLOG, TS, TSW, CGADSUB (no tile-base changes).
- Background loader callers: battle start `$81:86C0` (screen off) and the battle preview/debug
  screen `BattleUpdatePreviewBackground $84:9CD4`.
- WRAM staging is not possible: `$7E:C000–$DFFF` holds the main graphics, and `$7E:E200` holds the
  Ancient Cave carry items. Hence the direct ROM→VRAM DMA.

## Beyond 426 (investigated 2026-10-31, rejected)
- One window of 1024 tiles = 16K words from the tile base; the free areas can't share a window, so
  moving the base alone never beats 426 (base `$3000` → 384, `$4000` → 320).
- A mid-screen tile-base switch was the idea (top rows base `$2000`, ground rows base `$6000`):
  battle never uses IRQs (vector `$80:86C0` = RTI), so a V/H-IRQ could switch BG12NBA at the split
  line; the split would have to follow BG1VOFS (`$0596`), because effects shake the background up
  to ±7 px (`set_bg1_scroll`) and one adds 4 px per step (`add_bg1_scroll 1,4`). Wave effects use
  BG3 scroll only.
- **Killed by the VRAM, not the IRQ:** `$6000–$7FFF` is enemy sprite space. `BattleQueueSpriteTiles`
  and `BattleQueueSecondarySpriteTiles` (`$81:86FC/8700`, right after the background loads) upload
  full `$6000–$6FFF` and `$7000–$7FFF` from `$7E:8000`/`$7E:6000`; `BattleInsertEnemy` (`$81:ACED`,
  reinforcements) re-uploads `$7000–$7FFF` (`$85:E4AF/E4BB`). The parts that looked free were free
  only because Pierre's graphics are small. Also `$0800–$0FFF` gets uploads (`$85:9BD0`), so a base
  of `$0000` gains nothing.
- Free background tile memory in battle is therefore `$2560–$3FFF` only. A second background layer
  (#4) would have to share those 426 tiles (it gives parallax/layering, not more tiles).

## Implementation
- `bbg_convert`: `tile_number(k)` = 256+k for k < 256, else 86+(k−256); `max_tiles` up to 426
  (`MAX_TILES_EXT`). Output for ≤ 256 tiles is unchanged.
- `bbg_build.py ... --tiles 426` (or `build(..., max_tiles=426)`): first 8 KB compressed as before;
  the rest stored uncompressed from `$F3:8000` (each set inside one bank); table `$E0:B000`, 5 bytes
  per graphics index (long pointer, byte count; 0 = none).
- `bgext.asm` `LoadExtraTiles` (called with the row-4 loader at `$81:BAB9`, skipped for `$18`): DMA
  channel 6 (the battle's general-purpose DMA channel; done before the gradient enables ch6 HDMA),
  512-byte pieces, each started at the start of vertical blank (`$4212` bit 7), VRAM `$2560+`.
- `bbg_render.py` reads extra tiles and the third palette from built ROMs (verified 100% identical
  to the converter preview).

## Results (user's lake picture, slot 04)
- Original picture: 896 distinct squares (no two alike); without sky 788.
- 3 palettes + 426 tiles, grass rebuilt with the old 32×16 patch: 290 tiles, nothing merged.
- Gradient sky + 3 palettes + grass from a 128×32 patch: 308 tiles, nothing merged, 118 spare for
  ground details. Original grass at 426 tiles (merged) also looks natural.

## Not tested yet
- Boss battles, Ancient Cave, capsule-monster battles, the final battles; the action-message window
  that uses `$2000–$255F` (boundary from code, not observed); the debug preview path.
