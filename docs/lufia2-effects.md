# Lufia II — battle effect scripts (animations) (2026-10-31)

Tools: `src/tools/effectdec.py` (disassembler), `src/tools/effectasm.py` (assembler), `src/tools/effops.py` (operand-length analysis of the command handlers, reads `disasm/bank_81.asm`).
- `python3 effectdec.py ROM -o effects.txt [--json effects.json]` → full listing (≈13,900 lines; regenerate, not stored in the project because it is game data).
- `python3 effectasm.py effects.txt out.bin --verify ROM` → **byte-identical** to bank $95 ($8000–$F1EE, 29,167 bytes). Bank $95 is unchanged by Restored/Iris/RETRY/backgrounds/music-off.

## The VM
- `BattlePlayEffect $81:895E` (A = effect id): pointer from `$95:8000 + 2*id` → script slot 0 (`$7E:4F92`), bank byte `$C5 = $95` (set at `$81:89A4`; pointer read `LDA.l $958000,X` at `$81:899A`).
- 30 script slots at `$7E:4F8F` (stride `$2C`) and 64 actor slots at `$7E:54B7` (stride `$2D`) run the same interpreter: `[$C3]` = script pointer, command byte → `JSR (tbl_818C5C,X)` (256 entries, 136 distinct handlers). Slot +0 active, +1 frame countdown, +2 reload delay, +3 pointer, +5 call return, +7/+A/+D/+10 loop counters.
- All pointers are 16-bit, in the script bank (no bank operands anywhere).
- Command classes: flow 00 end, 01 yield (wait one tick), 02 delay n, 03 jump, 04 call / 05 return, 06 branch if parent field == value, 0F party jump table (7 words), 10–13 loop n / 18–1B next; spawns (first word = script pointer): 08 09 0A 0C 0D 0E 56 8E 96 D0–D9 E9 EA; graphics 20 27 2C 50 5C 5D DD–DF; scroll 30–34; brightness 51 54; HDMA 0B (18 wave/HDMA routines at `$81:8E5C`, bank $85, no extra operands); sound 70 72; motion 80–85 87–89 91 94–97 C0–C2 EC–F1; waits E0–E8.
- Invalid ids: BRK handlers (24–26, 29–2B, 32, 35, 40–4F, 86, 8A, 8B, 92, 93…) and hangs (8C, 8D, 07, 14–17, 1C–1F…): never valid in scripts.
- Gotcha found: `move_special_target` (69) has 2 signed operands — the code after its RTS is dead.

## Contents of bank $95
- `$8000` table, 281 effects: **137 distinct scripts, 140 unused ids** (55–63, 71–95, 115–127, 156–219, 234–239, 242–254, 256–265). Unused ids 55–57 = spells Escape/Reset/Light (field-only, no animation).
- `$8232–$E792` and `$F08B–$F1EE`: scripts, 12,426 commands, 1,032 labels, **28 unreferenced (unused) scripts** (labelled `UNUSED_xxxx`).
- `$E793–$F08A` data, not identified (keep in place). `$F1EF` IP effect records (141), `$FA5B` spell records (40), `$FFED` pop-up table. Bank full (3 free bytes).
- Who plays what: spell k → effect k + $12 (`BattleSpellAction $81:A9BB`); IP record byte 2 = effect id (table `$84:8F10`, 168 IPs); fixed ids in battle code: $0E, $2A, $93, $9A, $DC (number pop-ups), $DD, $DE, $E0, $F0. Unnamed effects (1–9, 11, 13, 15–17, 64–95, …) are probably monster attacks — trace the battle-VM opcode that plays effects next.

## Next steps (plan)
1. Name the monster-attack effects (battle VM caller of BattlePlayEffect: `$81:B03A`, `$81:B0C8`, `$81:B158`, `$85:BD57`).
2. New animations: relocate the script bank (patch `$81:899A` pointer read and `$81:89A4` bank byte to an expansion bank, copy bank $95 scripts there with effectasm — the 4 MB backgrounds ROM has free banks `$E7–$EF`, `$F2–$FF`), then add scripts in unused ids. Check first whether anything else reads scripts with DB/bank $95 (palette commands use bank $96 data and WRAM; `$81:8196C7` sets DB $95 but only for WMADD writes).
3. First test: a recoloured/re-timed copy of an existing spell in an unused id, played with a test hook, screenshots before building anything.

## Stardust blow (IP 124), fully traced 2026-10-31
- IP record `$84:9833`: effect record $87, animation $8F (effect 143, script `$95:E102`), type 2, target 0, cost 224 IP. Taught by **Gold eye** (item $189: STR/AGL/INT/MGR... words 4,5,6,10 = +20 each, all characters).
- Effect record `$95:FA07`: select all enemies; L0 = STR + 1000; special attack (op 21, placeholder attribute $0002); then op 1F $0810 overwrites the attack attribute (G39) → **light + thunder**. Same two-element trick: Combo attack (record $84, magic attack INT+450, attribute $0C06 = fire/water/ice/thunder), Gloomsplash ($85, STR+800, fire+dark $0022), Diamond dust ($86, STR+700, water+ice $0404).
- Animation script E143: change_display + 3 palette presets, graphics resource 3 at $3800, dim screen; per target copy_actor_tiles; a brightness-pulse script (L_E14D); 13 passes of two star bursts at random positions (sounds $6F/$11), each burst spawning a falling streak (L_E186: 13 sparks moving down 10 px/step) then random sparkles (L_E1C8, L_E1DC).
- Emulator capture method: test ROM with every spell animation id ($12–$36) pointed at the script, then Tia casts a spell (battle menu: hold UP + A = Magic, A = spell, A A = confirm target). Triggering BattlePlayEffect from the command menu (frame hook) does NOT work: without an action's target list every slot fills (30/30) and nothing draws.
- World map warp for battles: from the Alunze save state set `$05AE`=0, `$05B8`=43, `$05B0`=151, `$05B3`=1, `$05B5`|=$88, then fade in (`$0582`=0, `$0581`=$81); ghost-walk (debug `$057C`=$FF + B) down 140 f, right 140 f, left 60 f, then walk up/down: encounter in ~100 steps (Crow Kelp).

## Writing new animations — what works (2026-10-31, Bolide draft)
- Sources: `src/anim/bolide.txt` (script), `src/anim/build_test.py` (splices a script over Stardust blow's area `$95:E102–E1FA`, 249 bytes, and points every spell animation at it — TEST ROMS ONLY), films with `exp/film.py`/`filmrom.py` (Tia's Spark from `probe.state`).
- Sprite (actor) slot fields: +13.. params (set_param/add_to_field field b → slot +$13+b), so **field $0C = x position (+$1F), $0E = y (+$21)**; +1B/+1D vector; +23 angle; +25 parent ($FF free).
- Angles: 0 = down, $40 = right, $80 = up, $C0 = left (256 units).
- Free actors (spawn_with_angle/spawn_stationary/spawn_actor_at) do NOT move by themselves; the vector only places their children (child pos = parent pos + vector + offset). Move a sprite with `add_to_field $0C/$0E` each frame. `spawn_moving_with_angle` attaches the child to its parent (+25 = parent) — not a free mover.
- packed_draw_state $LLHH: HH = tile, LL bit0 = large (32×32), bits1-3 palette, bits 4-5 priority, bits 6-7 flip. Firebird explosion sprites: resource $1F → `graphics $001F,$4000,$1000` + `palette_preset3 $0024`; frames $0005/$0405/$0805/$0C05/$4005.
- set_brightness/adjust_brightness palette p: 0 normal, toward $40 = white, toward $C0 = black (clamped). Red translucent wash = Firebird's BG3 overlay (`load_graphics $001A,$3800` + `bg_request $01`) with palette 1 brightness: `set_brightness $01,$00` = full, step `adjust_brightness $01,$FE` ×32 to fade.
- Script positions: spawn_script_at pos word = x | y<<8 (unsigned); spawn_actor_at offset word = signed x | signed y<<8.
- Bolide draft (approved? pending): setup from Firebird, 4-sprite comet head from upper left (4 px/2 px per frame, 36 frames) dropping a fading fireball tail, then red flash + 3-column explosion bursts (L_A01D). 218 bytes.

## Bolide design (proposal, 2026-10-31) — previews only, no patches yet (user: build abilities in batches later)
- Draft 2 script `src/anim/bolide.txt`: two entries — E143 slot in tests = IP version (comet lands at x128 y72, enemy row), `B_MONSTER` = monster version (lands at x88 y140, party). Comet: 4-sprite head from target−(128,96), +4/+3 px per frame for 32 frames, fading tail; then red flash + explosions on every target (`spawn_scripts_for_targets` → L_A01D ×5). 221 bytes for both.
- Gotchas: a script has ONE return slot (+5): no nested calls (calling a routine that calls L_9204 loses the return). `spawn_current_target_script` does NOT start at the target's position (gave ~(20,19)); `spawn_scripts_for_targets` does (centre of each target, e.g. (152,72) for Crow Kelp). `branch_if_field p, $13, v` tests the slot's own param 0 (set with set_param $00).
- IP: all enemies, special attack STR+800, fire+wind ($0003; op 21 placeholder + 1F $0003), 196 IP (tier of Combo/Gloomsplash/Diamond dust; Stardust 224 / STR+1000).
- Monster: **Copper Dragon** ($A1, L59, Ancient Cave floors ~ pool 164–183, no drop today). Turn script `$96:B937` already has a special: `32 05 / 21 0800 0258 00 / 1E 34 / 5A 86` = thunder special power 600, message $34 ("Cinder blast", only user), animation $86 (shared with one other monster at `$96:B81C`). Bolide = change attribute to $0003, animation to the new id, rename message $33 entry "Cinder blast" → "Bolide" (shorter, in place). Message ids are 1-based (`$85:954A` DEC).
- Drop: new jewel "Copper rock" (like Gold eye/Silver eye/Gorgan rock: +20 to four stats, ~55000 G), 4% listed (≈1% real), added to the Ancient Cave carry-out list (Iris moved it to `$84:FE00`).

## Capacity of new abilities (measured 2026-10-31 on the 4 MB ROM)
- Free ROM: ~1.2 MB (banks $D0–$DF, $E8–$EF, $F2–$FF empty; $E7 27 KB) minus the grass variants. Not a constraint.
- Per ability: animation 150–500 B (Bolide 221; existing median 210, mean 325, max 1769), IP record ~20 B, IP effect record ~22 B, description ~40 B, item record ~21 B + 12 B name, carry-list 2 B, drop entry 4 B → ~350 B.
- Limits: items — only 2 spare ids (Key30 $1CA, PURIFIA $1CD); ids go to 9 bits → expand table 467→511 (+45) needs relocating name/record tables. Animation scripts — one bank ($C5): relocated copy of $8000–$F1EE leaves ~3.6 KB + 2.3 KB (data region not needed in the copy) ≈ 25 Bolide-size animations; more needs per-effect bank support (small engine patch). Effect ids — byte: 130 free below 256 (55–63, 71–95, 115–127, 156–219, 234–239, 242–254). IP effect records — Restored hook ids $F0+: 13 left in its table (extendable). IP table — 168, 6 never taught (25, 43, 57, 65, 135, 139); records must be in bank $84 (full) unless IpRecordPointer `$81:F45E`, `$82:FF15` and callers get a long pointer. Descriptions `$97` table 168 entries. Monsters — bank $96 full: new moves only by replacing existing ones in place, unless a "far script" VM op is added.
