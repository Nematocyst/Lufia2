# Lufia II (SNES) — Disassembly Starting Leads

Source: TCRF main page, Notes page, Proto page (fetched 2026-10-20). All addresses US ROM unless noted.

## Mapping
- **LoROM** confirmed from TCRF examples: SNES `$BB:AAAA` → file `(BB & 0x7F) * 0x8000 + (AAAA - 0x8000)`.
  - `$878000` → 0x038000, `$86C13E` → 0x03413E, `$97B3A5` → 0x0BB3A5
- Needed: clean, headerless US ROM (same requirement as Lufia2SNESRecomp).

## Code entry points
- `$80:C9C0–$80:CA13` — map-name decompress handler (full annotated listing on TCRF Notes page)
- `$80:9E5F` — dialogue control-code dispatcher: `JMP ($CAFB,x)` → **jump table at `$80:CAFB`** (indexed by control code ×2)
- `$80:9FB3` — dialogue `$0A` (LZ-style back-copy) handler (JP addresses; find US equivalent)
- `$80:C1C2` — read-next-script-byte subroutine (JP)
- Debug enable: GG `206A-4FAA` / PAR `8380C7D4` → patches `$80:C7D4`; debug flag RAM `$7E057C = $FF`

## Data
- `$878000` bank: map names. Pointer = `$878016 + locID*8`. ASCII, `$00`=end, `$0A xx yy` = copy (low 12 bits = addr+$878000, high 4 bits = len-2). Known bugs: IDs D2–D7, D9, EF read wrong 4KB page; E1/E5 off-by-one; 61–67 length overflow.
- Error/debug strings at file 0x28523 ("Illigal event number" …).
- Dialogue `$0A`: low 12 bits = bytes to jump back from (addr after $0A), high 4 bits = len-2.
- JP font table on TCRF Notes ($00–$0F control codes, $10 space, kanji via $05/$06/$07 prefix). US table still to be built.
- SPC music: decompressed blocks start with `"S2C"` + 12-char name. Load-screen song: PAR `82E942xx` (US) → `$82:E942`.
- Palette: PAR `96BF1D01` → Dark Warrior palette index at `$96:BF1D`.
- Item graphics: coin pile is first entry of item sprite table.
- "S2" 2-byte marker used for various data sets — search ROM for it.

## RAM
- `$7E057C` debug flag
- `$7FF080–$7FF168` Forfeit Island pawn-shop item bits
- `$7E0054–56` scratch used by decompressors
- EV flags 0–255 and EV registers documented on TCRF Notes page (party, story, Iris treasures 200–219)

## Other
- SRAM check: exactly 8KB, anti-piracy loop otherwise
- Unused: item 0170 Uni Jewel, King Hidora, 4th Gades, Tanbel SE Tower 3F rooms, Gratze Castle exterior
- Prototype: JP proto has RAM/ROM monitor in debug menu

## Existing community work
- **Cellenseres/Lufia2SNESRecomp** (GitHub, Sept 2026) — full native recompilation, fully playable. Likely contains function boundaries/labels; check before re-deriving anything.

## Mod ideas and feasibility notes (2026-10-30)

### Random background variants (investigated, not built)
- Idea (user): zone → terrain → *list* of backgrounds, one picked at random per battle (e.g. grassland → 04 / 1A / 1B), to avoid monotony.
- Hook point: `BattleBackgroundPrepare $81:B9D2` = `ASL ASL TAX` (bytes `0A 0A AA`), right before the 4 record reads (now at `$E0:F100+k,X`). Replace with `JSL` to a routine that looks up a variant list for the id (count n + ids), picks `RandomScale(n)` (`$80:...`, A = n → 0..n−1) and returns X = 4 × chosen id. `$11E1` itself stays unchanged, so the id-0 ripple (`$81:8BAE/BAC1`) and the `$86:D0DC` special case keep working.
- Callers: `$81:86C0` (battle start) and `$84:9CDF` (preview selection, changes id mid-battle). Only the first should randomise; the second could reuse the last pick.
- Works for every id (dungeons too, e.g. two Ancient Cave halls). Each variant is a normal background (own 256 tiles); ROM space is plentiful (banks `$E7–$EF`, `$F2–$FF` free).

### More terrain areas (lead)
- The world-map override map (`terrain_patch.py`, `$F0:8000/$F1:8000`, one byte per tile) can hold any id per tile, so new areas (swamps, snowfields, beaches, ruins, the land around a specific kingdom) only need a painted zone + art. World map classes are only 0–4 (no swamp class exists), so swamps etc. would be painted regions, not terrain types.
- Possible tool: export the world map (`wmrender.py`) as an image, paint zones in colours, convert back to the .npy zone files.
- Monsters stay region-based (`$7FE000` zone grid × `$97:C493`); terrain-specific monsters would need a similar override in `$86:9CF3`.

### CONFIG: music off (investigated, not built)
- Config menu text at `$8E:C8FA` (labels) and option strings `$8E:C93C` (message speed FAST/NORMAL/SLOW), `$8E:C95D` (battle cursor), `$8E:C98C` (status cursor), `$8E:C975` (MUSIC: STEREO / MONO). Drawn by `sub_82A07D`; `sub_82A0C7` highlights option 0–2 (already supports 3 options).
- Settings: `$0B52` message speed (0–2), `$0B53` battle cursor, `$0B76` status cursor, **`$0B54` music mode** (0 stereo, 1 mono). Saved with the game; applied on load (`$82:EAEB`) and new game (`$82:9AD1`) via `SoundDriverWrite0D` (driver mode `$0D`).
- Change handler: `sub_82BFAD` (`$82:BFAD`) = `EOR #$01` toggle. For "OFF" make it cycle 0→1→2 and draw a 3rd string.
- Muting: the driver has a music volume command, `SetMusicVolume` (`$80:9601`, driver mode `$0B`), apparently unused by the game. Plan: when `$0B54` = 2, send volume 0 (and re-send after every `PlaySong $80:93FE`, in case song loads reset the volume); sound effects use separate commands and should stay. Needs an audio-level test in the emulator (the libretro wrapper currently discards audio; capture it to measure).

### New spells / IP abilities and their animations (investigated)
- **IP abilities: proven.** The Restored mod already adds three (Black thunder, Cold stream, Golden mist, `l2mod.asm` bank `$84`): record = effect id word, animation byte (reuses existing effect ids), type, target mode, IP cost, name; effect record `$FF` + battle-VM script. Items teach them via word 15.
- **Spells:** 40 records at `$95:FA5B` (name, kind, element, learner mask, MP, price, battle script from byte 19). Animation id = spell id + `$12` (`BattleSpellAction $81:A9BB`), so a new spell id needs either a new effect script at that id or a small patch mapping spell → animation. The spell list/shops/learning tables also need entries (not yet traced: learn-by-level tables, shop lists).
- **Animations (effect scripts):** `BattlePlayEffect $81:895E` → table `$95:8000` (281 entries, word pointers into bank `$95`, script bank set in `$C5` = `$95`). 127 effect commands, all labelled (`BattleEffect*` in bank `$81`): spawn actors/scripts, move/accelerate/rotate, draw state, palette load/brightness (`LoadPaletteRange`), HDMA, window bands, circle radius, BG copy, sound commands, target popups, `LoadGraphicsResource` (resource index via `$85:EF53` table → decompress to `$7E`).
- Bank `$95` is full (3 free bytes). New effects: relocate the pointer read (`LDA.l $958000,X` at `$81:899A`) and the bank byte (`LDA #$95 : STA $C5` at `$81:89A4`) to an expansion bank, and copy the 281 scripts; or keep bank `$95` scripts and add an "id ≥ 281 → other bank" branch. Scripts may contain absolute in-bank pointers (jumps, spawn targets), so copying them needs a script disassembler first.
- New effect graphics can go through the relocated resource table (1024 entries, `$E0:8000`), already used for backgrounds.
- Next steps: write an effect-script disassembler (`tools/effectdec.py`) to catalogue the 281 scripts and their graphics; then try a recoloured/re-timed copy of an existing spell as the first new animation.
