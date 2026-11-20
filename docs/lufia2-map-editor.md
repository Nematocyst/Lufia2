# Lufia II — map viewer and editor (2026-11-12)

Tools in `src/tools/mapview/`: `dump.py` (warp + dump WRAM/VRAM), `batch.py` (all maps, 8 emulators, ~45 s),
`render.py` (renderer), `mapdata.py` (read/write map cells in the ROM), `mappack.py` (editor packs),
`apply_edits.py` (editor changes → ROM + BPS), `lufia2-map-editor.html` (the editor page; also published
as the artifact "Lufia II Map Editor" — it contains no game data, map packs are opened from disk).

## Format (verified)
- Map data = compressed resource `$3F + map` (`l2compress`, table `$A7:8000`) → `$7F:0000`:
  byte 0 = number of layers, 6-byte header, then per layer `word section id, byte W, byte H, W×H cell words`.
  Decoded ROM data is byte-identical to RAM after loading; re-encoding is ~4% smaller than the original,
  so small and medium edits fit in place.
- Cell word: bits 0–9 metatile; **bit 10 ($0400) = wall on the cell's top edge, bit 11 ($0800) = wall on
  its left edge** (proven by walking tests on Doom Island: blocks both directions across that edge).
  Bits 12–15 unused in the maps checked. Walls live on layer 1 (`$05AA` = 2 on every map) and become
  `$10/$20` in the collision array `$7E:4000` (`FieldBuildAttributes $80:ED9C`); `$01` there = actors.
  The tileset attribute table adds `$08/$02/$80` but is all zero in the maps checked.
- Tileset = resource `$130 + $CF:F72E[map]` → metatile table at `$7F:D03C` (= resource base + $10):
  8 bytes per metatile = 4 BG tile words stored column-major (TL, BL, TR, BR). BG characters at VRAM
  byte `$8000`, palettes from the CGRAM buffer `$7E:0320`. Layer 0 is drawn behind layer 1; tile
  priority bits handled in `render.compose()`.
- Renders match the emulator to within sprites on 72 of 117 testable maps; the rest differ only by
  BG3 overlays (clouds/fog), darkness masks, backdrop colour and the submarine maps' colour effects.
  Map $01 is the world map (different system, see the world-map tools).

## Workflow
1. `batch.py` → `maps/map_XX.{png,wram,vram}` (orig ROM + `ow/c2.state`; warps use incoming exit coordinates).
2. `mappack.py ROM maps packs` → `packs/map_XX.json` (cells from the ROM, metatile atlas from the dump).
3. Editor: open packs, paint tiles (from the tileset or picked blocks), toggle walls, copy the changes.
4. `apply_edits.py clean.sfc out.sfc changes.json` → ROM + BPS. Verified: an edit shows up in the game.

## Map header records (2026-11-12) — `mapheader.py`
- Pointer table `$CF:FCBC + 3*map` (full 24-bit, so a grown header simply moves) → block copied raw to
  `$7E:F000`: word length, 21 list offsets for X = `$02..$2A`, lists of fixed-size records ending `$FF`
  (an empty list points at a shared `$FF` at `$2C`). Rebuild is byte-identical on 230 maps; 11 come out
  1 byte shorter with the same lists.
- `$06` exits (9 B: id x0 y0 x1 y1 params destx desty destmap; `$FF` = same map; rectangles are
  x0..x1−1, y0..y1−1), `$0C` events (5 B: id x0 y0 x1 y1 → the map script's "event id" slot),
  `$0E` points (3 B: id x y; `warp map, arrival, POINT` lands on a point), `$12` characters (6-byte
  placements id x y flags b4 b5, `$FF`, then behaviour data), `$16` objects (10 B), `$24` areas (5 B),
  `$02` 15 B, `$04` 10 B, `$10` 8 B, `$14` 5 B, `$26` 4 B, others 3 B.
- Editor: Objects tool shows exits/events/points/characters, drag to move, edit fields, add/delete
  exits, events, points (characters: move only). Changes export as `"header"` lists; `apply_edits.py`
  writes them (in place or to `--free`).

## Limits / next
- A map or header that grows moves to `--free` (resource entry / header pointer repointed). Verified on Doom Island.
- Apply map edits to the clean ROM as the first layer of `build_combined.py` (the backgrounds build
  relocates the resource table to `$E0:8000`; `mapdata.py` reads the original table).
- Not editable yet: adding characters or their behaviour, the map scripts themselves (use scriptasm),
  BG3 overlays, new tilesets/graphics.

## Room for new map scripts (2026-11-14) — `scriptspace.py`, `scriptblock.py`
- Map record `$87:8010 + 8*map`: block = word w0 + byte b2 (base = w0 + $8000, bank = $87 + b2, 8-bit add,
  so any bank `$87–$FF` encodes). Everything in a block is relative to its base → blocks move verbatim
  (`scriptblock.move`).
- **Scripts must stay in banks `$80–$BF`.** The engine runs with DB = script bank and reaches its work
  RAM (`$09B7`, `$09B9`, `$079E`...) by absolute addressing; only `$80–$BF` mirror low RAM. A block moved
  to `$D8:8000` never ran (start script pointer came back as garbage).
- Banks `$A7–$CE` are 100% compressed resources (reached only through the resource table). `scriptspace.py
  --bank BF --to D88000` moves the 4 resources overlapping `$BF` (ids $158–$15B, 45 KB) to expansion space,
  repoints them and blanks the bank → **32 KB of script space in `$BF`**. More banks the same way
  (`$BE`, `$BD`... each ~32 KB).
- Verified: all 241 maps' screenshots identical after the move; Doom Island's blocks moved into `$BF`
  play frame-identical; a NEW scene (dialogue, flag test, branch, set flag) written into `$BF:A000`
  and hooked to an arrival plays, and is skipped on the next visit.
- Combined build: run `scriptspace.py` on the combined ROM (it reads the relocated table at `$E0:8000`);
  claim the destination in the free-space map.

## ROM-only rendering (2026-11-14) — `romrender.py`
- No emulator needed: map cells = resource `$3F+map` (or the new-map hook); metatiles = resource
  `$130 + $CF:F72E[map]` (+`$10`); BG characters = resource `$14B + $CF:F81E[map]` (copied to VRAM byte
  `$8000`); palette = `$9B:(word $CF:FAFA[2*($CF:FA08[map]-1)])` copied to CGRAM from byte `$30`
  (`$20` when the map has no scene graphics), colours 0–23 = boot-time window/font colours.
  All tables are read through their readers' operands, so ROMs with `mapext`'s moved tables work.
- 193 of 241 maps match the emulator renders within 1 % of pixels; the rest differ by things set while
  the map runs (script palettes, e.g. the towers; BG3 cloud/fog layers; animated tiles; the cave `$F0`).
- `mappack.py ROM - OUTDIR [ids]` builds editor packs from the ROM alone (works for new maps `$F2+`);
  with an emulator dump directory it still prefers the exact dump.
- `mapdata`, `mapheader`, `scriptblock` follow relocated tables (resource hook, `$83:B60C`, `$83:B5BA`).
