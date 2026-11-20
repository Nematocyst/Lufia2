# Lufia II — parked leads (return to these in a later pass)

Short notes only; nothing investigated or built unless stated.

## Seasons and time of day (parked 2026-11-01)
- Feasibility notes in `lufia2-seasons.md`.

## Restore Gratze Kingdom castle (parked 2026-11-01)
- Idea (user): restore the Gratze castle (TCRF lists an unused Gratze Castle exterior).
- Related: Restored & Extended already fixed the Gratze map names and gave Gratze region 17 a real encounter list (`l2mod.asm` sections 1–2).
- Surveyed 2026-11-12 (`lufia2-restorations.md`): no interior data exists; needs new maps. The map editor
  (`lufia2-map-editor.md`) now covers cells, walls, exits, events, points and character positions.

## Doom Island exterior + unknown shrine — restoration built as a test (2026-11-12)
- Details and status in `lufia2-restorations.md` (walls, landing on the pad, healing pad, way back out).
- **New idea (user, 2026-11-12): an extra dungeon in the shrine outside the main Shrine of Daos** (the
  teleporter pad's "unknown shrine"). The landing line on the island is on hold until this is decided.
  Would need: new maps (editor + new map resources), exits/events, encounters, and script space
  (bank $8E/$8F are full: needs a way to run map scripts from expansion banks).
