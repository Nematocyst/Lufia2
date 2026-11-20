# Lufia II — seasonal battle backgrounds: production workflow (2026-11-07)

How to turn a set of 48 seasonal pictures (3 places × 4 seasons × 4 times) into ROM data, made so
that **nothing has to be regenerated twice**: every slow step is preceded by a check that takes
seconds or minutes. Measured on the grassland set (third edition, test builds 1–3).

## Why it is slow, and what the limit really is
- Conversion to SNES tiles is the only slow step: ~2 min per picture, 2 at a time → **~50 min for
  48**. Everything else (prep, build, battle shots, patches) takes seconds to a few minutes.
- **The hard limit is 426 unique 8×8 tiles per picture** (battle VRAM; the 8 MB ROM does not raise it).
  The grassland pictures need 508–638. The converter merges the rest into look-alikes; wherever
  merging lands, it shows as flat 8×8 blocks. Colours: 3 palettes × 15 colours.
- So quality = **where the merging lands**. The settings below steer it away from the ground.

## Settings (current, test build 3)
- Fit: 256 wide (box filter), top 224 rows. Sky mask `sky(f, hmax=100, tol=30)`; night masks
  `hmax=66, tol=20` ∩ dilated day mask. Gradient `bbg_gradient.fit`, sky must end above line 112.
- Floor: `bbg_floor.rebuild_floor(fit, sample=(150,205,32,224), patch=(128,32), min_row=96,
  patch_rows=(130,210), drop_below=168, seamless=True, margin=2, fade=4, anchor=160, low=(128,400))`.
  `seamless` (periodic patch) removed the 128×32 grid; `anchor`/`low` fixed snowy/night floors.
- Convert: `convert_n(npal=3, max_tiles=426, outliers=3, smooth=0.3, focus=(0,27), floor_row=16,
  row_weight=[1]*12+[2]*16)`.
  - `floor_row=16`: tile rows 16+ (y ≥ 128) use palette 3 only, built from the floor alone — the
    floor no longer shares its 15 colours with trees/houses. Floor error −0 to −27 %.
  - `row_weight`: merge weight ×2 for tile rows 12+ (the band below the horizon and the floor).
    Band error −10 to −14 % for +2–8 % scenery error. Tested ×1 / ×2 / ×3-band / focus (12,27)
    (= ×6.7): ×6.7 cleared the band but moved the blocks into mountains, shore and windmill; ×2 is the
    balance.
  - All 48 (test build 2 → 3, converter previews vs prepared pictures): scenery 23.6 → 24.4,
    band 15.4 → 14.9, floor 8.8 → 7.4; winter 25.5/18.3/9.1 → 27.3/17.5/7.6. Visibly fewer flat blocks
    in the band (battle shots). Delivered as `lufia2_backgrounds3_test3.zip`, ROM SHA1
    f963756133170613d614997c655f070ded225c4e, music-off 70b7b3b0f884d9173eb1a49d317e910c8ca9a72b.
  - Tried and dropped: forcing a solid floor up to the scenery edge (`solid_edge`) — saved only
    0–38 tiles and added soft rectangles.

## Tile Check page (2026-11-12)
Artifact "Lufia II Tile Check" (https://claude.ai/artifact/WBFkXYsbx39URCNthPwBmS): the user drops raw
pictures and gets 👍 / ⚠️ / 👎 per picture plus a tile map, in the browser, before a set is made.
- JS port of `seasons_prep.sky()` + `bbg_floor.floor_mask()` (sample (150,205,32,224), min_row 96,
  anchor 160, low (128,400), drop_below 168). Matches Python within 0.7 tiles on the 48 grassland
  pictures. Tiles needed ≈ scenery tiles (any pixel neither sky nor floor) + 88; vs real demand
  r = 0.95, mean −4.
- Forecast = 0.08·tiles + 0.153·detail − 28.5 (detail = mean horizontal colour step in scenery
  pixels), fitted to test-build-3 band error (R² 0.73). Pass ≤ 15.5, borderline ≤ 17.5, else redo;
  also redo if the sky ends below line 112 or the picture is shorter than 224 rows at 256 wide.
  Grassland set: 28 / 12 / 8 (the 8 = winter sunrise/sunset/night).
- Source: scratchpad `checker/` (`core.js`, `template.html`, `validate.js`); the page inlines
  core.js. Assumes the grassland framing (plain ground in the lower part); recalibrate for biomes
  whose ground differs.

## The workflow
1. **Prep** (seconds): `seasons_prep.py` (fit, masks, gradients, floors) — or `seasons_refloor.py`
   to redo floors only (keeps hand-made night masks). Look at the prep sheet.
2. **Check** (seconds): `python3 tools/seasons_pilot.py check prep/` — per picture: unique tiles
   needed, floor coverage at y 112/120 (share of the band that already repeats the floor texture),
   sky end. Flags MANY TILES (> 600), PATCHY BAND (< 50 %), SKY TOO LOW (> 112). Flagged pictures are
   the ones that will show blocks; fix art or prep before converting. Grassland set: 10 flagged —
   all winter sunrise/sunset/night plus Lake Spring Sunset.
3. **Pilot** (~5 min): `python3 tools/seasons_pilot.py pilot prep/ pilot/ 4 ['{json settings}']` —
   converts the 4 hardest pictures, writes previews, `zoom.png` (band below the horizon, 4×) and the
   error per zone (scenery y40–96 / band y96–128 / floor y128–224). Any settings change is judged
   here, never on a full run.
4. **Convert + build** (~50 min cold, ~30 s cached): `build_bg3.py` (cache keyed on picture + mask +
   gradient + settings; a settings change reconverts everything).
5. **Battle shots** (~5 min): `seasons_shoot.py` → sheet of all 48 in real battles.
   Note: emulator screenshots are a bit darker in red/blue (~10 error points everywhere); measure
   quality on converter previews, use shots only to look.
6. **Package** (1 min): `python3 tools/package_bg3.py BUILT_ROM base_rir.sfc OUT/` — BPS clean→all, Restored+Iris+RETRY→all, music-off add-on
   (`asar music.asm` on the backgrounds ROM), verify each with `apply_bps`, boot both ROMs, README
   SHA1s.

## Art brief for new seasonal sets (what converts well)
Each picture has a budget of ~426 tiles; the floor costs ~64, the gradient sky is free.
- **Keep the band just below the horizon simple.** The first ~30 px of ground under the scenery is
  where blocks appear. Ground there should look like the ground lower down — avoid strong colour
  shifts (pink/orange sunset glow, dark night shading) on the snow/grass right at the horizon.
- **Evenly textured ground**, no light pools, footprints, single flowers or puddles in the lower half
  (it is replaced by a repeating texture anyway).
- **Less fine detail in the far scenery**: distant forests, fences, villages and mountain ridges are
  the most expensive tiles. Large shapes and soft distant layers are cheap.
- Plain skies with a few large clouds (sky = gradient, clouds = tiles). Sky must end above ~y 112 of
  the fitted picture (≈ 45 % of the height).
- Winter sunrise/sunset/night were the hardest pictures in the grassland set (570–640 tiles,
  patchy band): give those the simplest horizons.
- Full-height pictures (~1341×1173), same framing across a set.
