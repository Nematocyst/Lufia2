# Lufia II — PC version route (Lufia2SNESRecomp) — started 2026-11-14

User decisions (2026-11-14): go the PC route instead of a PS1 port; **backgrounds are done for the
PC version** (full colour, no SNES limits; the user keeps a pixel style); **abilities and the other
mods keep being made as SNES patches**, and the PC version is built from the patched ROM (below).

## What it is
- `Lufia2SNESRecomp` (Christopher Schreiber, on `snesrecomp` by Matthew Stan): the game's 65816
  code recompiled to C at build time from a ROM, ~1,900 routines replaced by hand-written C
  ("decomp bindings"), and an emulated SNES picture/sound chip in plain C. Windows, Linux, Steam
  Deck, PS Vita. Licence: PolyForm Noncommercial (free fan use and changes OK with the notices; no
  selling).
- Upstream it only accepts the clean ROM (SHA checks at build and run time).

## Our patched ROM in the PC version — WORKS (2026-11-14)
- Build option `-DLUFIA2_MODDED_ROM=ON -DLUFIA2_ROM=<patched.sfc>`: skips the clean-ROM check,
  the executable expects the patched ROM's SHA-1, and the built-in US shrine graphics repair (a
  BPS made for the clean ROM) is skipped for it. The recompiler then translates **our** code too
  (Restored/Iris/RETRY routines show up in the generated C, e.g. `$86:FC85` Iris stat totals,
  `$85:FEE5` Iris regen, `$86:FFF0` RETRY, `$81:FD10` Restored).
- **Catch found and fixed:** a patch that changes one of the ~1,900 hand-written routines is
  ignored, because the C version runs instead. First test: RETRY did not appear (its hook is in
  `$82:E998`, replaced by `Lufia2TitleLoadSaveSelectionBits`). Fix: `src/pcport/mod_bindings.py
  CLEAN MODDED decomp_bindings.toml out.toml` drops every binding whose code bytes (reachable from
  its entry in the clean ROM, branches followed, calls not) differ in the patched ROM; the build
  takes the filtered file with `-DLUFIA2_DECOMP_BINDINGS=out.toml`. For Restored+Iris+RETRY: 20 of
  1,889 dropped (title selection, map-name decoder/banner, stat totals, battle round tick, encounter
  lookup, Ancient Cave enter/exit, ...).
- Verified with `lufia2_restored_iris_retry.sfc` (SHA1 5e9fc716…):
  - RETRY: title file menu shows START + RETRY (clean build: START only), same as snes9x.
  - Restored: map-name fix — Capsule Monsters' Cave banner reads correctly (clean build shows the
    garbled "U e MoV T Cave").
  - User's save loads; party records, inventory, gold and capsule flags byte-identical to snes9x on
    the same ROM.
  - Hi-colour backgrounds + Spark tint work on this build too.
  - Not yet exercised at run time: Iris set effects (need a stat recompute after equipping —
    equip menu or level-up; poking equipment before a battle doesn't recompute, in snes9x either).
- Rule for future SNES patches: they carry over automatically as long as the build is redone with
  the new ROM and `mod_bindings.py` is re-run. Data-only changes always carry over.
- Watch: the PC version's own C bug fixes (spell cost, equip names, drop text, HP/MP cap, cave eggs
  and stairs) are separate hooks; if a patch of ours touches the same routines, check both.

## Hi-colour battle backgrounds — WORKING (2026-11-14)
- While a battle shows background id N and `assets/hicolour/battle_NN.l2hc` exists next to the
  executable, the picture is drawn at **full colour** wherever the game draws its background layer
  (BG1) or the backdrop. No tiles, no palettes, no 426-tile ceiling (6,000–22,000 colours on screen
  with the approved art).
- How: a per-pixel "art override" in the emulated PPU's compositor (`snesrecomp`
  `runner/src/snes/ppu.c`/`ppu.h`, `PpuArtOverride` / `PpuArtColour` / `PpuArtComposeSpan`). The
  game still loads its own tiles; only the colours the player sees change. Sprites, windows, text,
  damage numbers, colour math (translucent status box), master brightness (fades) and scrolling
  (shakes, desert ripple) keep working. `src/lufia2_hicolour_bg.c` arms it once per frame from the
  battle state (`$11E1` = background id); `LUFIA2_HICOLOUR=0` turns it off. The new renderer path is
  used only while art is active (`FramePpuFlags`).
- **Spell tints work on the art**: it follows the game's palette brightness for row 2 (`$7E:1BF3`,
  same formula as `BattlePaletteBrightness`). Verified with Tia's Spark (`hicolour_spark07.gif`).
- Tool: `src/tools/hicolour.py picture.png out.l2hc [--x --y]` (alpha 0 = keep the game's pixel).
- Verified: battle turn on 07 (`hicolour_battle07.gif`); all 23 original ids 00–05, 07–17
  (`lufia2_pc_hicolour_backgrounds.png`). Sent to the user.
- Open: ids 06 forest / 19 hills need the game to pick them — with the patched-ROM build the
  backgrounds terrain patch can come along as a SNES patch again (only the art goes to the PC);
  widescreen art (~400×224); other palette effects (presets, gray fades) case by case.
- Art guides for the PC: `bg_layout_guide_pc.png` (+ widescreen version) — see
  `chatgpt-art-instructions.md` once rewritten.

## Patches and test tools (in the project)
- `src/pcport/snesrecomp_ppu.patch` (on snesrecomp 678b065), `src/pcport/lufia2recomp.patch` (on
  Lufia2SNESRecomp 510fa68: hi-colour module, modded-ROM option, bindings override, CMake, main.c
  hooks, autopilot), `src/pcport/mod_bindings.py`.
- **Autopilot (test only)**: `LUFIA2_AUTOPILOT=script.txt` runs the game from a script at full speed
  and quits: `boot N`, `hold BUTTONS N` (A+UP etc.), `wait N`, `poke ADDR HEX`, `keep ADDR HEX N`,
  `seek/until ADDR VAL MAX`, `shot PATH.ppm`, `dump PATH` (128 KB WRAM), `log`, `quit`
  (`src/lufia2_autopilot.inc`).
- **Battle on demand without changing the ROM:** the game has a debug encounter — WRAM `$057C`
  (debug mode) ≠ 0, then SELECT on the field starts a battle with group `$7F:F8A4`
  (`PlayerSlotStandardUpdateWithServices $83:C1C7` → `FieldEncounterHandoff`). Force the background
  with `$7F:F8A0` for the first frames. Works in snes9x and the PC version.
- Map warp (PC and snes9x): `$5B4`=current map, `$5AE`=map, `$5B0/$5B1`=x/y, `$5B2`=$F0, `$5B3`=2,
  `$5B5` |= $88.
- User's save in the PC version: copy the .srm to `<exe dir>/saves/save.srm`; load = wait 300,
  START, UP, LEFT, A, A, A, A (confirm YES), wait 400, B ×5 → Alunze church. Active party Maxim LV18 +
  Tia LV17 (records: Maxim $0BAD, Selan $0C6B, Guy $0D29, Arty $0DE7, Tia $0EA5, Dekar $0F63,
  Lexis $1021, Jelze $10DF; $BE each). Tia's Spark: in battle hold UP 20, UP+A, A, A, A.
- In snes9x the same save loads with: SRAM into memory id 0 before running, START until the file
  menu appears, A ×3 (150 frames apart), wait 300, B ×5.

## Building here (container notes)
- Clone with git (tarball downloads blocked): snesrecomp @678b065, recomp-ui @1b3292f (+ submodules),
  SDL release-3.4.14; Rust analyzer: 11 crates cloned from GitHub at their Cargo.lock versions and
  wired by `[patch.crates-io]` paths, `CARGO_NET_OFFLINE=true RUSTUP_TOOLCHAIN=stable`.
- `cmake -S . -B build/trace -G Ninja -DCMAKE_BUILD_TYPE=Release -DLUFIA2_SNESRECOMP_ROOT=… -DLUFIA2_RECOMP_UI_ROOT=… -DLUFIA2_SDL3_ROOT=…`
  with SDL X11 extras/Wayland/audio backends OFF and a placeholder `GL/gl.h`
  (`-DOPENGL_INCLUDE_DIR=… -DOPENGL_gl_LIBRARY=libGL.so.1 -DOPENGL_glx_LIBRARY=libGLX.so.0`).
  Patched-ROM build: `build/rir` with the two extra options above (configure ~2 min: recompiles).
- **Re-run the cmake configure step after editing snesrecomp's `ppu.c`**: the build compiles a
  configure-time copy (`generated/lufia2-ppu-fixes/snes/ppu.c`), not the original file.
- Run under `Xvfb :99`, `SDL_AUDIODRIVER=dummy SNESRECOMP_NO_LAUNCHER=1`, config `OutputMethod =
  SDL-Software`, `SkipLauncher = 1`. A battle run (boot + battle) takes ~50 s; runs must be one at a
  time (two in parallel didn't finish).
- On the user's Windows PC the normal README build (Visual Studio 2022 + CMake) applies.

## Possible next steps
1. Exercise Iris at run time (equip menu or level-up) in the patched-ROM PC build.
2. Backgrounds terrain/variant patch + forest/hills art in the patched-ROM build.
3. Widescreen battle art.
4. A Windows build the user can play (patched ROM + art files).
5. Field maps: the same override idea could replace map layers with painted art (bigger job).
