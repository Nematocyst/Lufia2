# Lufia II ROM hack — handoff (updated 2026-11-14, autonomous task run)

Read this first in a new chat, then the topic docs it points to.

## Latest session (2026-11-14): autonomous run, user's order "tackle these in order, leave the parts that need me for last"
1. **Room for map scripts** — DONE. `scriptspace.py` frees bank `$BF` (32 KB) for script blocks;
   scripts must stay in `$80–$BF`. `lufia2-map-editor.md`.
2. **Brand-new maps** — DONE except chests. `mapext.py` gives 13 new map slots (`$F2–$FE`);
   two-room proof dungeon (`mods/newmaps/build_testdungeon.py`, TEST ROM). `lufia2-new-maps.md`.
   Chests not decoded yet (the "treasure table" was a key-door table).
3. **ROM-only map renderer** — DONE. `romrender.py` (no emulator needed; 193/241 maps within 1 %).
4. **Rough edges** — DONE as far as possible without the user:
   - Event decoder: 95 errors → 2 (harmless). Cause: AA is a subroutine *return* (A9 = gosub), not
     "wait parallel". `lufia2-event-scripts.md`.
   - Script op names checked in the emulator: 20 add item (GET ITEM screen), 2B add party member,
     28 full heal, 58/59 fades confirmed; others still tentative. Same doc.
   - Gradient-sky spell tint: diagnosed, not built (needs the background art build to test).
     Two causes: palette-brightness ops skip the gradient (fix: re-tint a RAM copy of the gradient
     with the same formula), and BG3 colour-math flashes like Spark skip the backdrop (fix: enable the
     backdrop in colour math). `lufia2-gradients.md`.
5. **Regression check** — DONE. `src/tools/regress.py` snapshots any ROM (240 maps, 24+ battle
   backgrounds, static checks) and compares builds. Validated on clean, Restored+Iris+RETRY, the
   new-maps ROM and a deliberately broken ROM. First real use needs the combined build (user's ROM
   or layers). `lufia2-build.md`.
6. **PS1 port feasibility** — DONE (study only). `lufia2-ps1-port.md`: possible only as a new PS1
   engine reading the ROM's data (the recompiled SNES code alone is 2.4 MB of MIPS code; PS1 has
   2 MB RAM, 33.9 MHz). Proposed first step: a one-map PS1 proof of concept. Also found: a native PC
   recompilation of Lufia II exists (`ext/Lufia2SNESRecomp`), a cheaper route to "no tile limits" on
   PC/handhelds.
- Waiting on the user: Doom Island landing line + late save; whether to pursue the PS1 proof of
  concept; the combined build (or its layers) for the first regression baseline; background art for
  the spell-tint fix.

## Earlier (2026-11-12, evening): low-input technical groundwork — research only, nothing delivered as a patch
The user asked for work that needs little input; agreed order 1 → 2 → 3, all done:
1. **Restoration survey** — `lufia2-restorations.md`. Doom Island exterior (map $E6) is complete and
   wired, only missing collision + an arrival script: small–medium job, recommended. Gratze castle
   has no interior data at all: wait for a map editor. Field tools `src/tools/field/`.
2. **New-abilities groundwork** — `lufia2-abilities-groundwork.md`. Every battle animation id now has
   a "who uses it" name (weapon swings verified: effect = item word 13 − 1). The animation scripts
   can be moved to a free bank (`src/tools/effect_reloc.py`; all 121 animations pixel-identical in a
   frame-by-frame test), and Bolide plays from a brand-new id (55) through a real attack
   (`fx2/bolide_newid.gif`, sent to the user). For the combined build use a bank from the free map in
   `lufia2-build.md` (e.g. `$D7`), not `$D1` (only tested on the 4 MB backgrounds test ROM).
3. **Field event scripts + opcode names** — `lufia2-event-scripts.md`. The second field interpreter
   (dungeon mechanisms: switches, doors, push blocks, item-on-field triggers) is decoded
   (`src/tools/eventdec.py`, 146 maps; 2 harmless errors left since 2026-11-14), all 191 of its
   opcodes named; the 125 unnamed map-script opcodes now have tentative names (`scriptdec.py` +
   `data/script_op_names_tentative.json`).
- Note: `src/anim/build_test.py` expects the old label `E143` in `bolide.txt`; the file now uses
  `B_IP` / `B_MONSTER` (use `effect_reloc.py --add 55=bolide.txt:B_IP` instead).

## Map editor (2026-11-12, late) — `lufia2-map-editor.md`
- All 241 field maps render from the game data (`src/tools/mapview/`); map cells can be edited and written
  back to the ROM (verified in the emulator). Collision = per-cell wall bits ($0400 top edge, $0800 left edge).
- Editor page published as the artifact "Lufia II Map Editor" (paint tiles, toggle walls, copy changes);
  the user has `lufia2_map_packs.zip` (open in the editor) and `lufia2_map_renders.zip`.
- Later the same evening: maps/headers that grow move to free space; exits, events, points and character
  positions editable (editor v2, packs regenerated); Doom Island restoration built as a TEST ROM and
  previewed (`mods/doom/build_doom.py`, details in `lufia2-restorations.md`) — not delivered as a patch.
- Doom Island user decisions (2026-11-12): pad = heal HP + MP (DONE, tested); landing line TBD (user is
  exploring an extra dungeon in a shrine outside the main Shrine of Daos); late save "will take a while".
  When approved: add as a layer of the combined build (claim `$D7:8000–$D785FE`).

## Where we stopped before that (2026-11-01)
- Session work: SNES background techniques (Tales of Phantasia style) — gradients, third palette,
  426 tiles all working (`bgext.asm`); "beyond 426" rejected; scrolling bands prototyped and PARKED;
  enhancement chips assessed (MSU-1 the only worthwhile one, PARKED).
- Open candidates, in no fixed order:
  1. Backgrounds remake with the new limits (needs `lufia2_backgrounds_art.zip` re-uploaded).
  2. MSU-1 music — DONE 2026-11-12 (`lufia2-msu1.md`, `src/mods/msu1.asm`): matched to Conn's track
     numbering, tested with the user's real tracks, add-ons delivered: `lufia2_msu1_addon.zip` (music-off ROM) and `lufia2_msu1_addon_bg3.zip`
     (backgrounds test build 3 + music-off; MSU code at `$DB:FC00`, `$D0` is used in build 3).
  3. Spell-tint fix for gradient skies (diagnosed 2026-11-14, see above); band prototype completion (second pass of the ROM hacks).
  4. Earlier queue: new spells/IP abilities (groundwork done 2026-11-12, see above), random background variants (paused).
  5. Parked leads, for a later pass (`lufia2-parked-leads.md`): seasons and time of day
     (`lufia2-seasons.md`), Gratze Kingdom castle restoration, Doom Island exterior + unknown
     shrine restoration (both surveyed 2026-11-12, `lufia2-restorations.md`).

## Combined edition (2026-11-12) — read `lufia2-build.md` first for any build
- All patches are now built by ONE layered recipe from the clean ROM (`src/tools/build_combined.py`), with
  overlap checks and a free-space map. Two outputs: with / without RETRY (RETRY optional, user's choice).
  Delivered `lufia2_combined_2026-11-12.zip` (with RETRY = build 3 + music-off + MSU-1, SHA1 b4a43e01…).
- New features: claim space in the free-space map, add a layer, rebuild both outputs, run
  `regress.py check` against the previous build, deliver one patch.

## Workspace (it may be wiped between sessions)
- Needed again if wiped: clean ROM (`Lufia_II_-_Rise_of_the_Sinistrals_U.smc`, SHA1 below), the
  disassembly zip (`lufia2-disasm-full.zip`), the user's save (`…_U_patched.srm`), and for
  backgrounds the art zip. The user's lake/mountains test picture was attached in chat on
  2026-10-31 (1341×1173 PNG) — ask for it again if needed.
- Rebuild tools: asar (github RPGHacker/asar, cmake) and snes9x libretro (github libretro/snes9x,
  `make` in libretro/) into `/home/claude/lufia2/deps/`; set `CORE` in `tools/retro.py`.
- All tools and patches are in the project (`claude/src/tools/`, `claude/src/mods/`).

## Base ROM and released mods
- Base: Lufia II - Rise of the Sinistrals (USA), headerless, SHA1 A89931C1F29B161B8BE717DFAB4A4ADB54B42B84.
- Released: **Restored & Extended v0.4**, **Iris Treasures v1.1**, **RETRY-from-start v1.1** (patches for each combination; see `lufia2-mod-notes.md`). The user plays the full combination (restored + iris + retry).
- Sources in the project: `claude/src/mods/` (l2mod.asm, iris.asm, retry.asm, build scripts, mkpatch.py) and `claude/src/tools/`.

## Battle backgrounds project (done, test build delivered)
- Details: `lufia2-battle-backgrounds.md` (engine, budget, converter, every approval, build bugs fixed).
- 25 backgrounds approved: all 23 the game uses (00–05, 07–17) + **06 forest** (new) + **19 hills** (new). ROM expanded to 4 MB.
- Overworld terrain patch (`tools/terrain_patch.py`): forest tiles → 06; grassland within 2 tiles of hills/mountains → 19 (zone map, `hill_zone.npy`); other grass 04, desert 00, sea 03.
- Latest test patch (user has it): `lufia2_backgrounds_test.zip` → `lufia2_restored_iris_retry_backgrounds.bps` (from clean ROM) and `addon_backgrounds_for_restored_iris_retry.bps`. Result SHA1 4D3FB9D1…1911.
- Art: the user has `lufia2_backgrounds_art.zip` (approved 256×224 pictures named `bg_<id>_<name>.png`, originals, `hill_zone.npy`).
- Rebuild recipe:
  1. Restored + Iris + RETRY base ROM: build from `src/mods` (or apply the released patch to the clean ROM).
  2. `python3 bbg_build.py base.sfc out.sfc 0x00=bg_00_….png … 0x19=bg_19_….png` (~7 min; relocates the resource table to `$E0:8000`, palettes `$E0:9000`, background records `$E0:F100`). Extensions: gradient skies `ID=pic.png@mask.png@grad.npy`, third palette `--npal 3`, up to 426 tiles `--tiles 426`; then apply `mods/bgext.asm`.
  3. `python3 terrain_patch.py out.sfc final.sfc --zone hill_zone.npy=0x19`.
  4. Optional: `python3 variants_patch.py final.sfc final2.sfc 04=1A,1B …` (random variants).
  5. `mkpatch.py` for BPS/IPS; check in the emulator (all ids in battle).
- Release patches for the other combinations (backgrounds alone, with Restored only, with Iris only) are not made yet: build when the user asks.

## Background toolkit (2026-10-31, all in `src/mods/bgext.asm`; originals pixel-identical)
- **Gradient skies** — `lufia2-gradients.md`. HDMA ch0 → CGRAM colour 0 per line; ch6 → COLDATA
  (halved) so translucent windows keep the sky; window-frame sliver fix at `$85:A818`. Open: spell
  tints don't reach the gradient (diagnosed 2026-11-14, fix designed, not built).
- **Third palette (row 4)** — `lufia2-palettes.md`. 45 colours. Rows 5–7 = party colours (taken).
- **426 tiles** — `lufia2-tiles.md`. Tile numbers 86–255 (VRAM `$2560–$2FFF`), DMA'd from ROM at
  background load. **426 is the ceiling**: `$6000–$7FFF` is enemy sprite space (mid-screen base
  switch investigated and rejected).
- **Scrolling bands (PARKED)** — `lufia2-bands.md`. Clouds drift over the gradient via an H/V IRQ
  that resets BG1HOFS at the band's bottom line. Working prototype; inert unless a band table
  entry exists. bgext.asm's NMI-exit change (clears the I flag so IRQs can fire; the game never
  did CLI) is always active — tested harmless.
- Art-brief implications (to write when the remake starts): flat single-colour skies (→ gradient),
  more ground detail allowed (426 tiles: 128×32 ground patches or merged original grass), 45
  colours; for bands: no clouds touching the side edges, nothing crossing the band line.
- Tested only with a 2-member party (Maxim, Tia) and small monsters (lizard man, Pierre); boss,
  Ancient Cave, capsule and final battles untested — ask for later saves.

## Enhancement chips (assessed 2026-11-01, PARKED)
- None can lift the background limits (those are PPU/VRAM limits; chips sit on the cartridge).
- SA-1 only if slowdown or RAM shortage ever become real problems (conversion is a big job).
  Super FX, S-DD1/SPC7110, DSP-1, Cx4: no use here. ROM size: 6–8 MB is possible without a chip.
- **MSU-1 = the worthwhile one** — investigated and proven 2026-11-12, see `lufia2-msu1.md`:
  own hook `src/mods/msu1.asm` (code at `$D0:8000`, works with music.asm) passes all emulator
  audio tests; an existing patch by Conn (Zeldix t1833, packs by Relikk / JUD6MENT) targets
  vanilla-size ROMs and likely conflicts with ours; song list in the doc (63 slots, 59 songs).

## Working style agreed with the user
- Previews first; build or package only when the user approves. Throwaway test ROMs for screenshots are fine.
- **Floor rebuilds: never cut at a straight horizontal line** (user, 2026-10-31). Keep the art's own ground edge column by column (`bbg/mvar/edge.py` approach), replace only the plain floor below it and fade in.
- **Variants phase: no patches/zips per variant.** Show previews and battle screenshots only; once all variants are loaded, make ONE combined patch.
- **Abilities: previews (GIFs) only, built later in batches** (user, 2026-10-31) — see `lufia2-effects.md` (Bolide design, capacity of new abilities) and `lufia2-abilities-groundwork.md`.
- Patches must match the exact starting ROM (BPS preferred).
- The user's "art department" is ChatGPT image generation (brief above in the old form: 256×224, ≤30 colours, detail in the top ~40%, plain evenly lit floor, boards/slabs in straight 8/16 px rows, plain skies, repeating bays — to be revised for the new toolkit).
- Explain results in plain language; the user isn't asking for internals unless they ask.
- The user likes parking ideas and returning to them in a "second pass" of the ROM hacks.
- Autonomous runs (2026-11-14): work through the agreed list in order, leave anything needing the user for the end.

## Emulator testing
- snes9x libretro via `tools/retro.py` (`Emu`; core options supported: `emu.layers(hide=(3,))`),
  helpers `tools/bt.py`, `hd.py` (HDMA logger), `pal.py` (palette rows), `vram.py` (VRAM census /
  stamp test), `gradtest.py` (build + play a turn), `shots.py`, `tools/emu/`, `regress.py`.
- **Battles on demand:** test ROMs with `mods/battletest.asm`; from a field state set `$7F:FFF1` =
  monster group and `$7F:FFF0` = 1 (`hd.start(rom, state, bg, group)`). Group `$01` lizard man,
  `$10` Pierre; `$30`, `$50`, `$60` start story scenes. Field state from the user's save: reset with
  SRAM, START, UP, LEFT, A, A, A, then B ×5 (Alunze church). `regress.py` adds an equivalent hook to a
  copy of any ROM by itself.
- Battle menus: Maxim A, A, (UP), A; Tia hold UP 20 frames then UP+A = magic list, A, A, A casts.
- Effect-id logger (2026-11-12): hook `$81:8960` → JSL to a routine that appends A to a ring at
  `$7F:FF00` (count) / `$7F:FF01+`; shows every animation id a battle plays.
- Frame-identical checks: run the same scripted input on two ROMs and compare md5 of every 3rd frame
  (deterministic within one process).
- Writing VRAM through the libretro pointer needs `emu.load_state(emu.save_state())` afterwards,
  or snes9x keeps showing its cached tiles.
- Field warps by RAM: `$5AE` map, `$5B0/$5B1` x/y, `$5B2` = $F0, `$5B3` = 2, `$5B5 |= $88` (bit 3 is
  clear right after a new game's intro; without it the warp is ignored). Raw world-map warps leave the
  map unloaded (no encounters) — use battletest instead. `src/tools/field/warp2.py`.

## Other queued work (older)
1. **CONFIG: music OFF** — DONE (`src/mods/music.asm`, `lufia2-music-off.md`); delivered as an add-on for the backgrounds test ROM.
2. **Random background variants** — PAUSED. Mechanism `src/tools/variants_patch.py`; approved variant pictures were in the scratchpad (`bbg/final/`, likely gone — the user should have them; ask). Build ONE combined patch when resumed.
3. **New spells / IP abilities / animations** — groundwork DONE 2026-11-12 (naming table, relocated script bank, new id proven). Next: first batch (Bolide IP + Copper Dragon + Copper rock), previews first.
- Lead: extra painted areas (swamps, snow, beaches) via the terrain zone map.
- Parked leads (`lufia2-parked-leads.md`): seasons and time of day (`lufia2-seasons.md`), restoring Gratze Kingdom castle, restoring Doom Island's exterior + unknown shrine (`lufia2-restorations.md`).

## Other project docs
- `lufia2-ps1-port.md` (new 2026-11-14), `lufia2-new-maps.md` (new 2026-11-14), `lufia2-restorations.md`, `lufia2-abilities-groundwork.md`, `lufia2-event-scripts.md`, `lufia2-build.md`, `lufia2-map-editor.md`, `lufia2-msu1.md`, `lufia2-parked-leads.md`, `lufia2-seasons.md`, `lufia2-gradients.md`, `lufia2-palettes.md`, `lufia2-tiles.md`, `lufia2-bands.md`, `lufia2-effects.md`, `lufia2-music-off.md`, `lufia2-mod-notes.md` (released mods), `lufia2-iris-gear.md`, `lufia2-capsules.md`, `lufia2-cave-generator.md`, `lufia2-battle-notes.md`, `lufia2-data-formats.md`, `lufia2-disasm-status.md`, `lufia2-leads.md`, `lufia2-battle-backgrounds.md`, `lufia2-remake.md`.
- The disassembly lives in the workspace (`/home/claude/lufia2/disasm`), not the project; if the workspace is gone the user re-uploads the disasm zip. Generated listings (`docs/scripts`, `docs/events`, `build/effect_names.txt`) are game data: regenerate, keep private.
