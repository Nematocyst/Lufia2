# Lufia II — field event scripts (the second field interpreter) + map-script opcode names (2026-11-12, updated 2026-11-14)

Tools: `src/tools/eventdec.py` (decompiler), `src/tools/event_ops.py` (operand analysis),
`src/tools/data/event_op_names.json` (names), `src/tools/data/script_op_names_tentative.json` +
`src/tools/scriptdec.py` (map-script names). Output listings `docs/events/event_XX.txt` are game data
(keep private, regenerate: `python3 eventdec.py ROM -o docs/events`).

## What they are
The field has two script systems. The known one (`scriptdec.py`, `$80:CA14`) runs dialogue and
cutscenes. The second one runs **dungeon mechanisms**: switches, pressure plates, doors, push blocks,
things hit by arrows/bombs/hook shot, map-load setups, step triggers. Up to **8 event slots** run in
parallel each frame (`FieldEventTimerTickWithServices $80:CBAE`; slot timer `$7F:D18C`, pointer
`$7F:D134/D136`, per-slot variables `$7F:D14C/D154/D15C…`).

## Data
- `$8F:8000 + 3*map` = word (offset, +$8000) + bank delta (+$8F); `$FFFF` = map has no events
  (`FieldInitializeMapEvents $80:E844` → `$7F:D194` base, `$7F:D196` bank). 146 maps have events.
- Block = 16 header words (offsets from the base) → 16 lists of `[id, word]` ending `$FF`.
  `FieldStartEvent $80:E722` (X = 2×list, Y = 2×id) starts base+word in a free slot.
- **List 0 = trigger kinds** (id = who starts it): 0 every update/restore/transition, 1 leader steps
  down (`FieldTryLeaderLowerStep`), 2 pending objects at load, 3 **stepping on a position**,
  4/8 object positions, 5/$C object checks (`sub_83E8A6`), 6 battle transition, 7 **A-button on a
  facing cell**, 9 object sprite frame, $A scene switch, **$B item used on the field** (tools: bombs,
  arrows, hook shot, fire wand…, `FieldDispatchSelectedItemAction`), $D object subcommand, $E object
  event, $F map header load, $10 map transition, $11 menu. List 1 = facing-point events. List 5 =
  condition lists (data used by condition opcodes, not scripts).
- Pointer operands are offsets from the block base (may cross into the next bank).
- Variables: `$7F:D074 + n` (n ≥ $FB = slot variable); local flags `$7F:D100+` (bit per id);
  "points" (x, y, x2, y2) at `$7F:D1A3/D1E3/D223/D263`.

## Opcodes (191, table `$80:E5A4`) — all named in `event_op_names.json`
- Flow: 00/07/2C–2E/56/62/93/9B/AC/AD end; 0A goto; 11 wait n; 27 call (args FF-terminated list +
  target); 26 call if last test true; **A9 gosub** (args FF-terminated list + target; pushes a call
  record at `$7F:D466`, 10 bytes each, with the return position and the slot variables);
  **AA return** (pops it, `$80:D849`). (A9/AA were first read as "start/wait parallel"; the
  handlers show a subroutine call and its return. Fixed 2026-11-14.)
- Flags/vars: 08 set flag, 09 clear, 01/0C goto if flag set/clear; 2F–34 var copy/add/sub/inc/dec/set;
  35–3A goto if var ==, !=, >, <, >=, <= constant; 3B–40 same against another value;
  41–54 point arrays × (set, add, sub, inc, dec).
- Tests (store a result, then goto/if): 12/6D leader at, 13 test leader at, 15–18/6E/6F/72–74 area
  tests, 75–77 claimed object, 87–89 cell bits, 94–96 object record, 04/05/70 object at, 0F/6C cell
  type, 0D/71 facing cell; 20 test actors hidden (FF-terminated list + target); 28 store, 29 flag
  from test, 1E/2B exit if/unless test.
- World: 02/03 object on/off (animated), 06/0E/7A/2A/1F/8D/8E/90–92/A8 place/copy/redraw object
  regions (open doors, move blocks, bridges), 5A–5D push object up/right/down/left, 10 redraw all,
  0B sound, 1C/1D screen shake, 58/59/B4/B5/BE scroll, 19/1A exits (warp), 86 reload map.
- Actors: 60/61 hide/show, 25 spawn at probe, 78 spawn in area, 63–67/7C–81/A3–A6 move/path,
  6A action, 68/5F/6B wait for actor, 8A/8B release, AF–B3 actor flags/object actors, BC set state.
- 8F/B9 condition-list message (debug?), BB begin dialogue event (hands over to the text scripts).

### Decoder status (2026-11-14)
- **2 decode errors left** (was 95): 13,044 instructions over 146 maps, 145 of 191 opcodes in use.
  The 95 errors came from treating AA (return) as an ordinary instruction, so the decoder ran on
  past every subroutine's end into data tables; list operands were also cut at 32 bytes.
- The 2 left are in map $BC: a switch on variable $A1 with 11 cases (values 0–10) has no default, so
  the decoder falls through into the data after it. The game never takes that path. Harmless.
- Names are from what each handler reads/writes; the less used ones (actor_move_6x, actor_path_7x,
  claim_object_9x, actor_A3–A6) need an emulator check to be exact.

## Map-script (text/scene) opcodes: the 125 unnamed ones now have names
- `data/script_op_names_tentative.json`, loaded by `scriptdec.py` (existing names win). All opcodes
  that appear in scripts now have a name (0 `op_XX` left in `docs/scripts`); decompile still 0 errors,
  242 maps, 1,587 scripts; `validate_scripts.py` coverage unchanged (98.0%).
- Highlights: 20/21 add item, 25 remove item, 23 learn spell, 28 full party heal, 2B/2C party add/remove
  member, 49 play song, 53 start battle, 58/59 fade out/in, 5E/83 exit by id, 82 exit here, 87/B4 draw
  object, 8B actor position, 91 exchange balance (casino/coins), A7 exchange item, A8 Ancient Cave
  enter/exit, A9 world-map region, AB count item, B1–B3 face actor toward, B9/BA reset party + reload.
- **Checked in the emulator** (test ROM, the script run from the Doom Island pad, 2026-11-12/14):
  - 20 `add_item` (word item id): opens the GET ITEM screen with that item; when the bag is full it
    offers the drop list. 21 is the same screen (item id + $100 range).
  - 28 `party_full_heal`: HP and MP full.
  - 2B `party_add_member` (member id): the member joins and appears behind the leader at once.
  - 58/59 `fade_out`/`fade_in` (names were swapped before; inside an event they freeze the player:
    use the colour-math fade 94–97 instead).
- Ran without a visible effect from that spot (operand order or preconditions not right yet; not
  wrong names necessarily): 1F, 23 learn_spell, 2C, 49 play_song, 91, 27. Everything else is still
  TENTATIVE (from handler behaviour); confirm before relying on one in a mod.
- Harness: test ROM with the script bytes written at `$8E:81D8` (the pad's heal script), party
  warped next to the pad, walk on, press A a few times, WRAM before/after compared with a noise
  baseline (two plain runs). Frame sheets show what the op put on screen.

## Uses
- Doom Island restoration (`lufia2-restorations.md`): map $E6 has no event block — new mechanisms there
  (pad heal/save) are easier as text-script events; the event VM is for puzzles.
- New puzzles/switches in existing dungeons, seasons/swamp leads that need map changes, Gratze.
