# Lufia II — restoration survey: Doom Island exterior, Gratze castle (2026-11-12)

Research only; nothing built. Tools: `src/tools/field/` (`warp2.py`, `allexits.py`, `strip.py`, `collide.py`).
Pictures (scratchpad `survey/`): `doom_island_survey.png`, `gratze_survey.png`.

## Field map facts learned (useful for any map mod)
- **Map data** = resource `$3F + map id` → `$7F:0000` (`FieldLoadMapResources $80:EAE7`). Header 8 bytes, then
  W, H; layers follow, each `W H ?? ??` + W×H cell words (`$7FD008` = per-layer cell base, `$7FD010/18` W/H).
  Cell word: bits 0–9 metatile, high bits = tile attributes (palette/priority; editing them changes graphics).
- **Collision** = byte per cell at `$7E:4000`, built at load by `FieldBuildAttributes $80:ED9C` from the
  tileset's metatile attribute table (`$7FD03E` pointer): attribute & $F0 → cell |= 8 (blocked); 8 → 2; 9 → $80.
  So walls come from the **tileset**, not the map: to block cells, give them a blocking metatile or change
  the tileset attribute. Proven in RAM: setting bit 3 on Doom Island's sky cells stops the party at the edge.
- **Exits** ("area rects", `FieldAreaRects $83:B747`): table at `$7E:F000 + word[$F006]`, 9-byte records
  `id, x0, y0, x1, y1, params, dest x, dest y, dest map ($FF = same map)`, end $FF. **Event rects**
  (`$F00C`): 5 bytes `event id, x0, y0, x1, y1` → map script event slot. Both come from the map's data.
- **Warp by RAM** (like taking an exit): `$05B4 = $05AC`, `$05AE` = map, `$05B0/$05B1` = x/y,
  `$05B2` = params (e.g. $F0), `$05B3 = 2`, `$05B5 |= $80`. Script op 16 `warp map, arrival, mode`
  instead sets `$05B8` = arrival id (runs the map's "arrive" script).
- **All 241 maps' exits and events** dumped (`allexits.py` → `all_exits.json`, game data, not in the project):
  a full map-connection graph; regenerate when needed (~3 min, 8 emulators in parallel).
- Debug walk-through-walls (`$7E:057C = $FF` + hold B) also skips event/contact probes, but exits still fire.

## Doom Island (map $E6) — the exterior exists and is complete
- Fully drawn map, 32×48 cells, wraps around (sky repeats): floating island, Doom Castle on top, a staircase
  down to a smaller rock with a **glowing teleporter pad** (the "unknown shrine"), sky all around.
- Wiring today: Shrine of Daos 1F (`$E7`) has a working exit at x14–15 y43–44 → E6 (15,17), right outside
  the castle door; E6's only exit (x14–17 y15–17) → E7 (14,42). One tile before that exit, event 03
  (x14–15 y42–43) plays "We can't run away." and stops the player.
- How the game uses E6: arrival `$63` (from the Sinistrals' scene in `$EB`) hides the party, shows one
  sprite, fades, and immediately warps into E7 arrival `$62` ("Is everyone ok?" in the dark). The ending
  (`$EC`) uses arrival 01 for the island scene. Arrivals 00/02 reset the game (no script → crash path).
- **Missing**: collision. The map has no walls — the party walks straight into the sky (tested).
  The pad does nothing.

### What a restoration takes (estimate: small–medium, 1–2 sessions, no art needed)
1. Collision: mark sky cells blocked — either give sky cells a blocking metatile in a re-encoded map
   resource (relocated to free space, resource table already relocated by the backgrounds build), or add a
   blocking attribute in E6's tileset if no other map shares it. Hand-check the edges (stalactite cells are
   drawn on layer 2 but must stay blocked; stairs and pad walkable).
2. Arrival: rewrite E6 arrival `$63` to land the party on the teleporter pad (fade in, maybe the
   "Is everyone ok?" lines moved here), then free control. Walking up the stairs into the castle door uses
   the existing exit. E7's arrival `$62` cutscene would need to move to E6 or be triggered once on entry.
3. Remove or soften E7 event 03 so the party can step back outside (Doom Island is still a dead end, so the
   story isn't broken). Optional: make the pad a healing/save spot (simple script), since it can't lead
   anywhere without breaking the endgame.
4. Test in the emulator with a late save (needs a save at Doom Island — or a debug warp + flags).

### Restoration built (2026-11-12, test ROM, preview only) — `mods/doom/build_doom.py`
- Walls drawn around the island top, staircase and teleporter rock (`doom_walls.py`, 103 cells; map
  data grows 14 bytes → moved to `$D7:8000`). Walking tests: party stops at every edge, the stairs work,
  walking up into the castle door enters the shrine.
- Header: new point 06 = the pad (15,30). `$EB`'s warp `16 E6 63 01` → `… 06`: the party lands on the pad.
- E6 arrival `$63` → `rebuild_party, fade in, end` (no flight into the castle, no warp into the dark shrine).
- Shrine `$E7`: event 03 (`$8E:853D`) → `goto L_0038` (the original arrival scene, which ends at once when
  flag `$82` is set), and the event rectangle just inside the door (x11–18, y41; was event 02, an empty
  script) now runs event 03. So the dark "Is everyone ok?" … Light … Daos scene plays on the first step
  in, and afterwards the party can walk back out to the island ("We can't run away." is gone).
- Checked: re-entry plays nothing; the ending's Doom Island scene (`$EC` → E6 arrival 01) is unchanged.
- **Healing pad** (user, 2026-11-12: heal + replenish MP): header event 01 = the pad's centre (15,30);
  E6 script block slot 8 → `[01 → +$28]`; script in the bytes freed from the old arrival `$63`
  (`$8E:81D8`): `28` (HP+MP of living members, clears statuses) `4C 6F` (sound) `95 FF 00 1E` (colour
  flash) `37 20` `97` (restore the map's colours) `00`. Tested: HP/MP refilled, player free afterwards.
  Gotchas: a fade out/in (`58`/`59` + `76`) in an event froze the player; Iris' far op `$02` is a far
  TEXT call (shares `$1252/$1254` with dictionary words) and is not usable for command scripts.
- Uses `$D7:8000–$D785FE` of free space. Works on the clean ROM and on Restored+Iris.
- Open (user, 2026-11-12): a landing line is TBD — the user is considering an **extra dungeon in the
  shrine/area outside the main Shrine of Daos**, which may change what happens on the island. A late
  save for a real playthrough will take a while.

## Gratze castle — mostly used already; the "restorable" part has no data
- Maps: `$D6` courtyard (48×44, full castle front, drawbridge, moat), `$D7` two tiny tower rooms (18×16),
  `$D2–$D5` dungeons B1–B4, `$D1` submarine cave.
- Story use today: Dankirk North Cave B5 (`$90`) → left tower room (D7) → courtyard (D6): the capture
  scene (event 01: "Let's make them sleep!", Drowsy → dungeon B4) and the tank scene after the escape
  (event 02). Right tower room ↔ dungeon B1. So the exterior is NOT unused; it's only seen in cutscenes.
- Unused/broken bits (matches TCRF): the castle's main door has no exit (no interior map exists anywhere);
  the drawbridge exit works (→ world map 201,33), but the world-map entrance is walled off by mountains
  (TCRF: a tile east of Gratze in the mountains warps to the drawbridge). ~20 courtyard NPCs have empty
  talk scripts. Map name strings for Gratze maps display garbled ("3y Kingdom").
- **What a restoration takes (large)**: a real visitable castle needs NEW interior maps (throne room,
  halls). We have no map editor yet (map/tileset format only partly known, see above), and the castle is
  destroyed by the story, so it could only be visited in the short window before that. Small pieces that
  are cheap: fix the garbled map names, fill the empty NPC talk lines in the courtyard scene, open the
  world-map path to the drawbridge for the pre-destruction window (needs story-flag checks to keep the
  guards' capture scene consistent).

## Recommendation
- Doom Island: worth doing — all graphics exist, the work is collision + scripts, testable.
- Gratze: wait until a map editor exists (decode tileset/metatile format; render maps; edit cells), which
  is also what seasons, swamps and other painted areas would need.
