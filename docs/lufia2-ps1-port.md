# Lufia II on the PlayStation — feasibility study (2026-11-14)

The user's idea (2026-11-14): port Lufia II to the PS1, keeping the SNES graphics but losing the SNES
limits (tiles, palettes, VRAM), like other 2D PS1 RPGs (Tales of Destiny). This note answers "can it
be done, how, and what would it cost". Nothing is built.

## Short answer
- **Yes, but not as a port of the SNES program.** Running the game's own code on the PS1 (emulation
  or recompilation) is too slow and too big for the machine (numbers below). A PS1 version has to
  be a **new engine written for the PS1** that reads Lufia II's data (maps, tiles, sprites, scripts,
  monsters, music) and reproduces the game's behaviour. That is a rewrite of the game logic, with
  the original as the reference.
- That is a large project: realistically a year or more of steady work for the core game, longer
  for full parity (every cutscene, puzzle, the Ancient Cave, battle effects). It can be done in
  stages, with something playable early (walk around maps, then battles, then the story).
- Much of the hard groundwork exists: our disassembly and data tools (maps, headers, scripts, events,
  battle effects, monster AI, the cave generator, renderers), and a public C reconstruction of the
  game logic (below) that can serve as a reference.

## What the PS1 would solve
| SNES limit | PS1 |
|---|---|
| 64 KB VRAM (the tile limits: ~426 tiles per battle background, map tilesets) | 1 MB VRAM: every map's whole tileset and many backgrounds fit at once |
| 8 BG palettes of 16 colours on screen | any number of 16- or 256-colour palettes (CLUTs) |
| 128 sprites, 32 per line, fixed sizes | thousands of textured sprites per frame, any size |
| 1-4 MB cartridge | 650 MB CD: full-quality music (CD audio, like our MSU-1 tracks), more art, voice, FMV |
| 128 KB work RAM | 2 MB |
| fixed-colour/HDMA tricks for skies and fades | per-polygon blending and gradients (gradient skies become trivial) |

## Why the SNES program can't simply run there (measured 2026-11-14)
- There is a working native **PC recompilation of Lufia II** (`Lufia2SNESRecomp` by Christopher
  Schreiber, on top of `snesrecomp`; Windows, Linux, Steam Deck and a PS Vita port; checked out in
  `ext/`). It turns the 65816 code into C, instruction by instruction, and draws with an emulated
  SNES PPU.
- I generated its C from the clean ROM here and compiled it for the PS1's CPU (MIPS I, size-
  optimised): **2.4 MB of machine code** for the game logic alone (8.8 MB of C, every function in up
  to four register-width variants). The PS1 has **2 MB of RAM in total** and a 4 KB instruction cache.
  It would not fit, and code that large would run mostly from slow main memory.
- Speed: the PS1 CPU runs at 33.9 MHz with no floating point. Recompiled code spends tens of host
  instructions per 65816 instruction (flags, register widths, memory through helper calls). The Vita
  port (a 444 MHz ARM, ~13× the clock) runs at about 53 fps with its software PPU taking ~10 ms a
  frame and part of the background drawing moved to the GPU; its exact "translate the SNES picture
  for the GPU" path cost 20-36 ms per frame there. The PS1 has no room for any of that.
- Emulating a SNES on a PS1 is out of the question for the same reasons.

## How a PS1 version would be built
1. **Engine in C on the PS1** (open-source PSn00bSDK toolchain; tested in an emulator with an open
   BIOS, then on hardware/ODE by the user). The game state is the game's own (party, items, flags,
   map, events), but kept in native structures, not in a copy of SNES RAM.
2. **Data from the ROM, converted at build time** (the user supplies the ROM; the build makes the
   disc image — same no-ROM-redistribution model as our patches):
   - maps: cells, metatiles, walls, headers (exits/events/points/NPCs) — `mapdata.py`,
     `mapheader.py`, `romrender.py` already decode all of it;
   - graphics: SNES 4bpp planar tiles → PS1 4bpp textures (straight conversion) + palettes → CLUTs;
   - battle backgrounds, monster sprites, character sprites, fonts, windows;
   - scripts (dialogue/cutscenes), field events (puzzles), battle effect scripts, monster AI —
     decoders exist (`scriptdec.py`, `eventdec.py`, `effectdec.py`, enemy AI); the PS1 engine runs
     them with its own interpreters (they are bytecode, so this is the natural way to keep every
     cutscene and puzzle without rewriting them by hand);
   - music: the SNES sound engine's sequences re-played by a small sequencer on the PS1 sound chip
     (same designer lineage as the SNES DSP: ADPCM samples, ADSR, pitch, echo/reverb — the samples
     convert offline), or CD audio tracks for music (the MSU-1 pack) with the SPU for sound effects.
3. **Renderer drawn from the game's data, not from SNES registers**: each map layer is drawn as
   16×16 textured sprites from the metatiles (like `romrender.py` does), sorted by priority in the
   PS1's ordering tables; sprites the same way. Colour math maps to the PS1's blend modes (average,
   add, subtract, quarter-add). Per-line effects (heat ripple, waves) become strips; Mode 7 (the
   intro flyover, and per the PC project's notes parts of the world map) maps onto textured
   polygons, which the PS1 does natively.
4. **Loading**: data streams from CD per map/battle (2× CD, ~300 KB/s) → short pauses on map change
   and battle start, as in PS1 RPGs of the time; the RAM budget holds the engine, the current map,
   the party/battle data and caches.

## Reference material for the logic
- Our disassembly + notes (battle formulas, AI, effects, events, cave generator, item/spell data).
- `Lufia2Decomp` (inside the PC project): portable C reconstruction of the game logic, **1,922
  functions verified** against the original ROM by differential testing. Written to stay faithful
  to SNES state (it still works on SNES RAM and registers), so it is a reference for what each
  routine does rather than code to drop in. Licence: PolyForm Noncommercial (non-commercial use and
  changes allowed with the notices) — fine for reading; any code copied would carry that licence.

## Effort and risks
- Biggest jobs, in order: battle system (commands, formulas, AI, 136 effect scripts drawn on the
  PS1), field + events + cutscenes (two script VMs), menus/shops/status screens, Ancient Cave,
  sound. Graphics conversion and the map renderer are comparatively small (tools exist).
- Risks: exact parity (timing, RNG, edge-case bugs players expect), the battle effects (many use
  SNES-specific tricks), and testing a whole game. Mods we made (Restored, Iris, RETRY, Doom Island,
  backgrounds, MSU-1) would be re-done as engine features or data, not as patches.
- What could stay the same: every graphic, map, script, monster and number — the PS1 version reads
  them from the ROM.

## A cheaper route to the same goal (for comparison)
The PC recompilation already runs the whole game natively. Its emulated PPU is plain C, so its VRAM
and palette limits could be raised there (more tiles, more palettes, extra layers) far more easily
than writing a PS1 engine — but only on PC/handhelds, not on a PS1, and our code patches would need
re-recompiling (it recompiles the ROM's code at build time; data-only changes carry over as they are).

## How the measurement was made (to repeat it)
- `ext/Lufia2SNESRecomp` + pinned `snesrecomp` (678b065), `recomp-ui` (1b3292f), SDL 3.4.14 cloned
  with git (the build's tarball downloads and crates.io are blocked here); the Rust analyzer built
  offline against its 11 crates cloned from GitHub (`[patch.crates-io]` paths). CMake's recompile
  step then writes `build/linux/lufia2-gen/*.c`. The SDL part stops on missing X11 headers (not
  needed for the measurement).
- Compiled with `clang -Os --target=mipsel-unknown-elf -march=mips1 -msoft-float -G0 -ffreestanding`
  and stub libc headers; `llvm-size` → 2,403,246 bytes of text over bank00/80–86/8E + dispatch.

## Suggested first step (if the user wants to pursue the PS1)
A **PS1 proof of concept**: one Lufia II map (e.g. a town) converted from the ROM and drawn by a tiny
PS1 program — scrolling, both layers, priorities, one walking sprite — running in a PS1 emulator,
shown as a GIF. It answers the practical questions (toolchain, texture conversion, draw cost per
frame, CD loading) before any commitment. Then a battle background + monster on the PS1 as step two.
