# Lufia II: Rise of the Sinistrals (SNES): romhacking notes and tools

Research notes, tools and mod sources for the US version of *Lufia II: Rise of the Sinistrals* (SNES), worked out with Claude.

**This repository contains no game data.** There is no ROM, no disassembly and no extracted text or art. The full disassembly and the dialogue dumps contain game data and are kept private; what is published here is what you need to reproduce the work from your own ROM.

Base ROM: Lufia II (USA), headerless, 2.5 MB, SHA-1 `A89931C1F29B161B8BE717DFAB4A4ADB54B42B84`, LoROM / FastROM.

## What is here

| Folder | Content |
| --- | --- |
| [`docs/`](docs/) | the research notes, with an [index](docs/README.md). Start with [`lufia2-handoff.md`](docs/lufia2-handoff.md) |
| `src/tools/` | Python and JavaScript tools: script and event decompilers, battle effect decompiler and assembler, map viewer and editor, battle background converter, regression checker, a small 65816 interpreter for tests |
| `src/mods/` | assembly sources (asar) of the mods and their build scripts |
| `src/anim/` | a draft battle animation script (Bolide) |
| `src/pcport/` | patches for a separate recompilation project, see the licence note below |

## What the work covers

- **Disassembly and formats.** A byte-identical, annotated disassembly (private) and decoders for the game's scripts (242 maps, 1,587 entry points), a second field-event interpreter (146 maps, 191 opcodes), battle effect scripts, data tables, and the Ancient Cave generator.
- **Mods.** *Restored & Extended* v0.4 (map name fix, Gratze encounters, rare Ancient Cave bosses, restored IP skills and drops, capsule fixes), *Iris Treasures* v1.1 (wearable Iris sets), *RETRY from start* v1.1, music-off, and an MSU-1 hook.
- **Battle backgrounds.** A toolkit that expands the ROM to 4 MB and lifts the background limits: gradient skies, a third palette and 426 tiles, with 25 approved backgrounds in a test build.
- **Maps.** All 241 field maps render from the game data; cells, walls, exits, events and characters can be edited and written back, and brand-new map slots can be added.
- **Build and test.** A layered build with overlap checks and a free-space map ([`lufia2-build.md`](docs/lufia2-build.md)), and `regress.py`, which snapshots any ROM (240 maps, 24+ battle backgrounds) and compares builds.
- **Other platforms.** A PC route through a recompilation project and a PlayStation feasibility study. Nothing is built for either.

## Using the tools

- You need your own clean ROM (see the hash above). Nothing here downloads or ships one.
- Tools are Python 3 scripts; the mod sources need [asar](https://github.com/RPGHacker/asar). Emulator-based tests use the snes9x libretro core.
- Many scripts were run from a working copy at `/root/lufia2` or `/home/claude/lufia2` and still have those paths as defaults (for example `sys.path.insert(0, '/home/claude/lufia2/tools')`). Change them to your checkout, or pass your own paths.
- The patches themselves (`.bps`, `.ips`) and the art are not in this repository, and a few scripts and helper files named in the notes were not preserved. The notes say which each tool needs.

## Licence notes

- The code and notes here are under the MIT licence ([`LICENSE`](LICENSE)).
- `src/pcport/` holds patches for `Lufia2SNESRecomp` (by Christopher Schreiber, built on `snesrecomp` by Matthew Stan), which is under the PolyForm Noncommercial licence. The patches apply to that code and are subject to its terms. Use them only for noncommercial purposes.
- Another public C reconstruction of the game's logic was used only as a reference. It has no licence file, so none of it is included.
- Lufia II is © its respective rights holders. This is an unofficial fan research project.

Thanks to The Cutting Room Floor for the public notes that gave the first leads, and to Conn, whose MSU-1 patch was studied for its track numbering (it is not included).
