# Lufia II — backdrop gradient skies in battle (2026-10-31)

Technique #1 from the Tales of Phantasia discussion: the sky is drawn see-through and an HDMA channel
rewrites CGRAM colour 0 (the backdrop) every scanline, so the sky becomes a smooth vertical gradient
that costs no tiles and none of the background's 30 colours.

## Status
- **Working in a test ROM** on the original cliff background (07): sky see-through, deep blue → pale
  gradient, clouds kept as tiles. Tiles 256 → 227. Preview shown to the user (battle, results window,
  fire spell). Not packaged; not applied to the user's approved art yet (their art zip is needed).
- All 23 other original backgrounds are **pixel-identical** with the patch applied (emulator check at
  battle start, incl. the desert ripple).
- Known limitation: **spell tints don't reach the gradient sky** (e.g. Spark: the land and sprites
  go orange, the sky stays blue for ~1 s). See "Spell tints" below for the diagnosis and fix design.

## Spell tints and the gradient (diagnosis 2026-11-14, from the code; fix NOT built)
Battle effects change the picture's colours in two different ways, and each misses the gradient for
its own reason:
1. **Palette brightness** (`set_brightness` / `adjust_brightness`, effect ops $51/$52, ~400 uses,
   almost always rows 2 and 3 together = the background's two palettes). `BattlePaletteBrightness
   $81:B396` rewrites colours 1–15 of the row from the master copy `$7F:F1DB`: amount < 0 darkens
   (c × (amount + $40) / 64), amount ≥ 0 brightens toward white ($7FFF − ($7FFF − c) × ($40 − amount)
   / 64). The current amount per row is kept at `$7E:1BF1 + row`. Colour 0 is never touched, and the
   gradient is written by HDMA anyway, so the sky ignores it.
   **Fix design:** no reference colours needed — the formula and the amount are known. When
   `$1BF1+2` changes, rebuild a WRAM copy of the gradient tables with the same formula per channel
   (colour-0 table and the halved COLDATA table) and point channels 0/6 at the copy; amount 0 →
   point back at the ROM tables. One rebuild only when the amount changes (fades step it a few times
   a second), ~224 colours, well within a frame.
2. **BG3 colour math** (e.g. Spark: loads effect graphics onto BG3, `palette_preset`/brightness on
   row 1 = BG3's palette, `hdma $02` = BG3 vertical wave). The orange comes from colour math adding
   BG3 onto the layers enabled in CGADSUB. The original sky was BG1 pixels (included); the gradient
   sky is the **backdrop**, whose bit (CGADSUB bit 5) is not set. **Fix design:** while a gradient
   background is up, set the backdrop bit whenever the BG1 bit is set (hook the CGADSUB writes, or
   patch the HDMA/register value in the battle NMI). Catch to check: where BG3 is see-through the
   subscreen shows our fixed colour (the halved gradient, needed for translucent windows), which the
   math would then add to the sky; the windows/effects may need COLDATA dropped to 0 while an effect
   layer is up.
- Both need a test ROM with a gradient background and casting in battle (Spark for 2, a darkening
  spell/summon for 1). Free WRAM for the table copy (~1.2 KB) still to be found.
- (Earlier idea, superseded: reference black/white colours in a palette, mapped per frame. Not needed
  for case 1 because the amount is stored; would not help case 2 because no palette changes there.)

## Files
- `src/mods/gradient.asm` — the game patch (apply after `bbg_build.py`). Superseded by `bgext.asm`.
- `src/tools/bbg_gradient.py` — `stops()`, `fit()`, `sky_mask()`, `hdma_table()`, `coldata_table()`.
- `src/tools/bbg_convert.py` — `convert(..., mask=, backdrop=)`: masked pixels → colour 0; fully
  see-through tiles share one empty tile; merge keeps see-through and opaque pixels apart.
- `src/tools/bbg_build.py` — jobs `(id, picture, mask, gradient)`; CLI `ID=pic.png@mask.png@grad.npy`.
- `src/tools/bbg_render.py` — draws any background straight from a ROM (original or built).
- `src/tools/gradtest.py` — build a test ROM (bbg_build + gradient.asm + battletest.asm), play a turn.
- `src/mods/battletest.asm` (TEST ONLY) — field frame hook: `$7F:FFF1` = monster group, `$7F:FFF0` = 1
  → scripted battle (like script op `$53`). Uses `$83:FFBA–FFFF` (the music-off patch also uses it).
- `src/tools/bt.py`, `hd.py` — emulator battle harness and HDMA channel logger.
- `retro.py`: core options supported now; `emu.layers(hide=(3,))` hides BG3 etc. (5 = sprites).

## Battle HDMA (traced)
- Battle NMI (`BattleNmiUploads $85:8DC5`, `sub_858ED2`): config buffer `$1AEF`, 5 bytes per channel
  (DMAP, BBAD, A1TL, A1TH, A1B); `$DA` = channels to (re)enable next NMI; `$D9` = enabled mask →
  HDMAEN. Channel 6's config is re-applied every frame after the VRAM-queue GP-DMA (`ORA #$40`).
  (Field uses `$0081` → HDMAEN in the main NMI instead.)
- Channels in battle:
  - 0: desert ripple only (`BattleInitializeRipple $85:A701`); switched off at every background load
    (`$81:BAB9`), by a script background change (`$81:8BA1`) and the debug pause.
  - 1, 3, 4, 5, 7: command phase — WH2 window, OBSEL, CGWSEL/CGADSUB, TM/TS, BG3VOFS.
  - 2: window colour math during turns (`BattleConfigureLayerColorDma`), results screen
    (`BattleConfigureResultHdma`), transition modes 13/14.
  - 6: VRAM transfers (GP-DMA in NMI) and the circle-window effect (`BattleEnableCircleWindow
    $85:B1F8`, ends at `$81:9A98` with TRB `$D9` #$40).
  - Effects borrow 1, 2, 4, 5, 7 freely (wave effects `$85:ADxx–B1xx`; effect op `hdma n` = table
    `$81:8E5C`, 3-byte pointers; n=2 `BattleEffectBeginWaveFill $85:AEB9` is a BG3 vertical wave on
    channel 1).
- COLDATA is never written in battle by the original (only field debug screens).
- The record's effect byte (`$11E5`) dispatcher at `$81:BACB` is **dead code** (never called): effect
  values 1–3 do nothing. Only background id 0 gets the ripple (id check at `$81:BAC1`).

## How gradient.asm works
- Record effect byte `$10+n` → gradient n. Pointers: `$E0:F600 + 3n` (colour-0 table),
  `$E0:F6C0 + 3n` (COLDATA table). Tables in bank `$F2` (from `$F2:8000`). Code `$E0:F780–F8FF`.
- Hook `$81:BAB9` (JML): original behaviour (ch0 off, ripple for id 0), then `GradientSetup` enables
  ch0 (mode 3 → `$2121/$2121/$2122/$2122`) and ch6 (mode 0 → `$2132`) for gradient backgrounds.
  Skipped for id 0 (ripple owns ch0) and `$18` (black screen).
- Hook `$81:9A9A` (JSL, 4 bytes): after the circle-window effect turns ch6 off, re-enable the COLDATA
  gradient.
- `$85:A818` CPX #$0010 → #$0018 (`BattleBeginPrimaryWave`): lines 8–11 of the BG3 per-line scroll
  pointed at the window frame's bottom edge (map row 19, low priority), always hidden by the opaque
  sky; a see-through sky showed it as dark dashes on lines 9–11. Now those lines show the blank line.
- **Why the COLDATA gradient:** translucent windows (results, spell list, messages) blend BG2 panels
  with the subscreen; where the subscreen is see-through the SNES uses the fixed colour (black) → the
  sky inside windows turned black. COLDATA = the same gradient fixes it. One byte per line rotating
  R/G/B (each channel refreshed every 3 lines). **Halved**: the windows use half colour math, but the
  halving is skipped when the subscreen pixel is the fixed colour.
- Backdrop returns to black below the sky (`end` = first line below the mask): the game masks the
  leftmost 8 columns with a window, which shows the backdrop (it was black). Beside the sky that strip
  now shows the sky colour. The sky must end above line 112 (lines 112–125 use fixed-colour math).

## Art workflow (proposed)
- Art department draws a plain, flat-colour sky (one key colour) — the mask picks it out; clouds,
  moons, birds can stay as tiles over the gradient. Gradient from colour stops (`stops()`) or fitted
  from the art (`fit()`).
- Candidates: 07 cliff, 08 Daos sunset, 02 tower terrace, 04/19/1A–1F grassland/hills, rope-bridge
  remake.

## Test recipe
- Field state: user's save → `Emu(sram=...)`, START, UP, LEFT, A, A, A (loads file 1 in the Alunze
  church; extra A opens the priest menu → B ×5). State in scratchpad `church.state`.
- Battle: `hd.start(rom, state, bg, group)`; group `$01` lizard man, `$10` Pierre (jester). `$30`/`$50`
  start story scenes. Battle UI: Maxim A, A, (UP), A; Tia hold UP 20 f then UP+A = magic; A, A, A cast.
