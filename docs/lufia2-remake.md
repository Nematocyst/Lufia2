# Lufia II — battle backgrounds remake with the new toolkit (2026-11-01, seasons 2026-11-06, floor fix 2026-11-06)

Redo of all battle backgrounds using `bgext.asm` (gradient skies, 3 palettes, 426 tiles), plus
random variants. **Built and delivered as a test patch on 2026-11-01** ("backgrounds, second
edition", see Build). Working folder: scratchpad `re/` (sources `re/in/`), build `final/`.

## Third edition: seasonal grasslands (delivered 2026-11-06)
- Delivered `lufia2_backgrounds3_test.zip`: `lufia2_restored_iris_retry_backgrounds3.bps` (clean →
  everything), `addon_backgrounds3_for_restored_iris_retry.bps` (Restored+Iris+RETRY → everything),
  `addon_musicoff_for_backgrounds3.bps`, README, `all_backgrounds.png`, `seasonal_backgrounds.png`.
  All three verified by applying. ROM SHA1 c94f6ca28cac84912aaa6edc25c335d63f5c57bb (CRC 86D09344);
  with music-off caf0cb075eff887cf1732f385223972faf88f7ae.
- 94 pictures = the 46 of the second edition (byte-identical data, unchanged records) + 48 seasonal
  grassland pictures from the user (Lake/River/Farm × Spring/Summer/Fall/Winter ×
  Day/Sunrise/Sunset/Night). Record number = `$40 + place*16 + season*4 + time` (Lake 0, River 1,
  Farm 2; Spring 0, Summer 1, Fall 2, Winter 3; Day 0, Sunrise 1, Sunset 2, Night 3) → `$40–$6F`.
  Each has its own gradient (gradients 16–63).
- Until a seasons mod exists, id 04 (overworld grassland) rotates among all 51 grassland pictures
  (04, 1A, 1B + 48). Rotation test: 30 battles hit 26 different pictures, including 04 and 1B.
- **Layout v2** (`tools/bbg_build.py`): records `$DF:8000` (1024 × 4), palettes `$DF:9000` (256 × 64),
  row-4 palettes `$DF:D000` (256 × 32), gradient pointers `$DF:F000` / fixed-colour `$DF:F300`
  (240 × 3 each), variant table `$DF:F600`. Compressed data `$E1–$EF`, then `$D0–$DB`; extra tiles
  `$F3–$FF`, then `$DC–$DE`. `bgext.asm` limit `cmp #$F0`. Record reads at `$81:B9D5/DC/E3/EA`
  point to `$DF:8000`.
- **variants2.asm** replaces variants_patch.py: hooks `$81:B9C8` (JSL VariantPick2 at `$E0:F300`)
  and `$81:B9D2` (TYX). Table at `$DF:F600`: 64 words = list offsets (0 = none); list = count byte
  + 16-bit record numbers (up to 254 alternates). Same RNG as v1.
- Season prep (`tools/seasons_prep.py`): sky mask `sky(f, hmax=100, tol=30)`; night masks
  `hmax=66, tol=20` ∩ dilate(day mask, 2) so faint mountains stay; floor
  `rebuild_floor(sample=(150,205,32,224), patch=(128,32), min_row=96, patch_rows=(130,210),
  drop_below=168, seamless=True, margin=2, fade=4, anchor=160,
  low=(128,400))` (see test build 2). `seasons_precache.py` fills the conversion cache (~50 min for 48).
  Build: `tools/build_bg3.py` (~25 s with the cache). Battle sheet: `seasons_shoot.py` copies
  records `$40+` into spare ids `$30–$3F`, with the variant table blanked.
- **Space: the 4 MB ROM is now full** — 5 empty banks (`$D7–$DB`) left, extra-tile space ~16 KB.
  The next 48-picture biome needs the 8 MB expansion (six biomes × 48 ≈ 3.9 MB).

## Third edition, test build 3: ground palette + band weighting (delivered 2026-11-07)
- Converter: `floor_row=16` (floor-only palette) and `row_weight=[1]*12+[2]*16` (protect the band below
  the horizon when merging tiles). Workflow, numbers and art brief: `claude/lufia2-season-pipeline.md`.
- `lufia2_backgrounds3_test3.zip`, ROM SHA1 f963756133170613d614997c655f070ded225c4e, music-off
  70b7b3b0f884d9173eb1a49d317e910c8ca9a72b. Patches verified, both ROMs boot.

## Third edition, test build 2: floor fix (delivered 2026-11-06)
- User feedback on test build 1: "a lot of squares in the ground textures". **Rule: seasonal or
  painted floors must not show a tile grid.** Causes and fixes, all in effect now:
  1. The 128×32 floor patch was not seamless, so a seam showed every 128 px across and 32 px down.
     `bbg_floor.periodic()` (Moisan periodic + smooth split) makes the patch tile cleanly:
     `rebuild_floor(..., seamless=True)`.
  2. In about 15 winter and night pictures, `floor_mask` found no floor touching the bottom row, so
     the original floor between rows 96 and 168 stayed and got merged into blocks. Fix:
     `anchor=160` (floor connected to row 160) and `low=(128,400)` (below row 128, non-floor
     blobs smaller than 400 px become floor).
  3. The converter weighted floor rows low (0.25 / 0.08). Seasonal jobs pass
     `dict(focus=(0,27))` as the 6th job element (`bbg_build` now takes per-job converter
     kwargs), so every row gets weight 1.
  4. Margin 4 / fade 8 left a blocky blend band, so it is now margin 2 / fade 4.
- `tools/seasons_refloor.py` regenerates only `prep/<n>_fl.png`. It keeps the masks and grads,
  because `seasons_prep.py` would overwrite the special night masks. Then `build_bg3.py` runs cold
  (~50 min).
- Delivered `lufia2_backgrounds3_test2.zip` (same three patches, README, `floors_before_after.png`,
  sheets). ROM SHA1 2342d1919c4106acf90e36591e33c71225ad1dc8 (CRC 9FDF4F3F); with music-off
  08a509abef59bed79ab94b031507147e5864d33e. All patches verified, both ROMs boot. The 46 older
  pictures are unchanged.
- Music add-on recipe: `asar music.asm` on the backgrounds ROM (default checksum fix). It
  reproduces the v1 SHA1 exactly.

## Build (delivered 2026-11-01)
- Delivered `lufia2_backgrounds2_test.zip`: `lufia2_restored_iris_retry_backgrounds2.bps` (clean
  → everything), `addon_backgrounds2_for_restored_iris_retry.bps` (Restored+Iris+RETRY →
  everything), `addon_musicoff_for_backgrounds2.bps` (optional, on top), README,
  `all_backgrounds.png`. All three patches verified by applying with an independent reader.
- Result ROM 4 MB: CRC CD6C4781, SHA1 053ba80456dac617ce6814e0e827854e729c4b34; with music-off
  CRC 0EB24052, SHA1 f791046613c03146d656532d241bc0ec9c7bb6bb.
- **Base recovered from the user's earlier release zips** (`lufia2_backgrounds_test.zip`):
  apply the clean→old-backgrounds BPS, then rebuild the source of
  `addon_backgrounds_for_restored_iris_retry.bps` from its SourceRead/SourceCopy actions; the 35
  bytes it doesn't reveal are the old build's patch points (clean values) and the header
  checksum (2.5 MB mirrored sum: first 2 MB + 4 × last 0.5 MB). Matches the addon's source CRC
  **4C8ED673** = Restored & Extended v0.4 + Iris v1.1 + RETRY v1.1.
- Script `tools/build_bg2.py` (project `claude/src/tools/build_bg2.py`): converts the 46
  pictures 2 at a time with a disk cache (`final/cache/`, keyed on picture + mask + gradient), then
  bbg_build (npal 3, 426 tiles, outliers 3, smooth 0.3, **keep_orig_pals=False**) → bgext.asm →
  terrain_patch (hill zone = the 1,620 tiles with id 19 in the old ROM's zone map, forest class →
  06) → variants_patch → Tanbel byte `$88:BE43` 04→24 (bytes `4B 19 74 04 53` checked) →
  checksum. ~45 min cold, ~15 s with the cache.
- **Palette table limit**: `$E0:9000` holds 64 palettes; 20 originals + 46 new = 66 → assert.
  `bbg_build(..., keep_orig_pals=False)` drops the originals (allowed only when ids 00–17 all get
  new art). Adding more than 64 pictures needs a bigger palette table.
- Variant table: 00=22,23 01=2A,2B 02=28,15 03=27 04=1A,1B 06=1C,1D 07=20,21 08=25,26 09=2C,2D
  15=02,28 17=2E,2F 19=1E,1F. Slots used: 00–17, 19–28, 2A–2F (46 pictures). 29 (old
  torch-and-pillar entrance) left out by the user.
- Checks: every picture rendered from the ROM data matches its source (mean error 7–18, sky
  excluded); battle shot of all 46 (`final/all_backgrounds_v2.png`); 8 battles on each of the 12
  rotating ids showed every picture of the set; both ROMs boot. Test harness note: the RNG table
  is identical each run, so every set showed the same 5/2/1 split.
- Not tested in this build: spell tints on gradient skies (known limit), real play-through.

## Recipe (per picture)
1. Fit: resize to 256 wide with a box filter, keep the top 224 rows. Pictures must be full height
   (~1341×1173).
2. Sky mask (`re/skymask.py`, `sky_mask(img, bottom, tol)`), checked visually (`show()`); trim
   leaks (3×3 opening, keep top-connected, AND 1-px dilation). **The mask must reach the scenery
   outline**: if it stops at a straight line in open sky, a cloud crossing the line gets a
   rectangle (hills fix: OR with b ≥ 244, 22 ≤ g−r ≤ 62, r ≤ 170 above row 70). Sea horizons
   (`re/ship.py mask(f, hor)`): b ≥ 230, g−r 22–90, r ≤ 180, capped above anything on the horizon.
   Deep-blue sky around an object (`re/tower2.py`): b ≥ 150, b−r ≥ 70, b−g ≥ 25, top/left
   connected. Cloud-texture skies (Daos, 0A tower) and interiors: no gradient.
3. Gradient: `bbg_gradient.fit(fit, mask, smooth=4)`, sky must end above line 112. Desert slot 00
   keeps the heat ripple with a tile sky; gradient pictures in its rotation get the gradient
   (bgext.asm checks the loaded record's effect byte). A picture can't have both.
4. Ground (repeating patch; user's rule: never a straight horizontal cut):
   - `bbg_floor.rebuild_floor(...)` for irregular floor edges (grass, sand; 256-wide patch for
     long diagonal waves; keep accents out of the patch, `re/island.py`);
   - band method for perspective cobbles (`re/town.py`, W = 128);
   - hybrid for slabs/boards and all interiors (`re/interiors.py`): drawn floor kept to row 144,
     8-row fade into one 128×32 patch from rows ~124–166 (x 48–208), corner objects dropped;
   - light on the floor (rays, pools): remove it (`re/daos5.py`), or better use art without it.
5. Floor colour: match variants to the set's main picture only when floors are alike (grassland,
   desert dunes, hills → 04); otherwise keep as drawn (forest, mountains, Daos, interiors).
6. Convert: `npal=3, max_tiles=426, convert_kw=dict(outliers=3, smooth=0.3)` (~2 min/picture).
   Tiny colour accents (town planter flowers) merge away at the tile stage.
7. Test: `gradtest.build(...)` + `hd.start(rom, church.state, bg, 1)`; variants with
   `variants_patch.build`, varying `ram[0x559]`, `ram[0xB50]`, `ram[0xB4F]`; tell variants
   apart by a pixel the monster can't cover. Shared pools work (an id's alternates can be any
   ids).

Art tips for the art department: full-height pictures; evenly lit floors, no light rays or pools;
straight rows of slabs/boards; plain skies with a few large clouds; calm sea; bigger colour
accents.

Screen-edge black strips (6 px left, 5 px right, below the sky) are the original game's own
clipping (same on the unmodified ROM), not a bgext.asm bug.

## Pictures in the build (sources `re/in/`, converted files `re/`)
- Desert: 00 mesas (`00_mesa_fl3`, ripple, tile sky), 22 oasis (`22_oasis_fl3`, gradient),
  23 dunes (`23_dunes_fl3m`, gradient; user chose gradient over shimmer).
- Grassland: 04 lake (`04_lake_rb`), 1A river (`1A_river_rbm`), 1B farmland (`1B_farm_rbm`).
- Forest: 06 deep forest, 1C path, 1D stream (`*_rb`, no sky).
- Mountains: 07 cliff, 20 rope bridge, 21 sea of clouds (`*_fl2`).
- Hills (new art): 19 farmhouse, 1E coast, 1F woodshed (`*_flm`, masks/gradients `*2`).
- Town 24 (`24_town_fl128`): Tanbel fight with Camu's henchmen (map `$1C`, byte `$88:BE43`).
- Daos Shrine: 08 = new art over the old approved slab floor (`08_daos_g`; the old picture's
  warmer sunset palette is noted for the seasons/time-of-day mod), 25 balcony, 26 throne hall.
- Sea: 03 aft deck (`03_ship_fl`), 27 open deck (`27_shipdeck_fl`).
- Sealed Towers: 02 terrace, 28 floating island, 15 entrance hall — all three rotate on both the
  inner floors and the entrance floors.
- Interiors re-converted from the first pass's approved art: 01 cave rock, 05 shrine, 09 dungeon,
  0A tower, 0B cave bridge, 0C Sundletan, 0D river, 0E Lake Cave approach, 0F cave lake,
  10 mossy cave, 11 vine cave, 12 lava, 13 crystal, 14 Ruby Cave, 16 Gratze hall, 17 castle hall.
- Interior variants (new art): 2A ladder cave, 2B torch cave (with 01); 2C waterfall arches,
  2D bone arches (with 09); 2E grand staircase, 2F library (with 17).
- Gratze (16): used only by two scripted fights in map `$D6` "Gratze Kingdom" (soldiers; no random
  encounters); most likely the castle interior.
