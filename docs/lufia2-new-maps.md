# Lufia II — adding brand-new maps (2026-11-14)

Tools: `src/tools/mapview/mapext.py` (map-id extension), `src/mods/newmaps/build_testdungeon.py`
(proof: two new maps, TEST ROMS ONLY), plus `scriptspace.py`/`scriptblock.py` (script room, see
`lufia2-map-editor.md`).

## Map ids
- Byte ids. 241 story maps `$00–$EF`, `$F0` = Ancient Cave floor (generated), `$F1` = cave final floor.
  `$FF` = "same map" in exits. **Free: `$F2–$FE` (13 new maps).** No unused story map exists (the 13
  maps nothing warps to are entered from the world map).

## Per-map tables (all stop at `$F1`; relocated by `mapext.extend` to 256 slots, readers repointed)
| Table | Size | What | Readers |
|---|---|---|---|
| `$87:8010` | 8 | script block, entry script, name | `$83:B5BA/B5C7`, `$80:BEB9/BEC6`, `$80:C894`, `$82:F4A3` |
| `$CF:F72E` | 1 | tileset resource (`+$130`) | `$80:EB8B` |
| `$CF:F81E` | 1 | scene graphics resource | `$80:F03B` |
| `$CF:F90E` | 1 | extra section / alternate tileset (`$CF:F9FE` pairs) | `$80:EB4B`, `$80:F217` |
| `$CF:FA08` | 1 | palette (`$CF:FAFA`) | `$80:F2D2` |
| `$CF:FBA6` | 1 | scene record list (`$CF:FC98`) | `$80:EFC8` |
| `$CF:FCBC` | 3 | header records (24-bit pointer) | `$83:B601/B60C`, `$86:9F44/9F4E` |
| `$8F:8000` | 3 | field event block | `$80:E86D/E88C` |
| `$91:B8B5` | 2 | object-condition list offset (index read only) | `$80:E85D` |
| `$81:B9AC` | 2 | encounter list offset (relative to `$81:B9AC`) | hook at `$81:837B` |
| resource `$3F+map` | – | map data; collides with tilesets from `$F1` | hook at `$80:EB23`: maps ≥ `$F2` use resource `NEWRES + (map−$F2)` |
- Not moved: `$94:C998` (map → area; only counts treasures per area for maps < `$F1`).
- Needs the 1024-slot resource table at `$E0:8000` (the backgrounds build has it; `mapext` makes it on a
  plain ROM). Test ROM uses ids `$3E0+` — check they are free in the combined table before using them.
- Checked: all 241 maps' screenshots identical after the extension; a Doom Island playthrough differs only
  by a one-frame text delay (the hook costs a few cycles at map load).

## Proof: two-room test dungeon (`build_testdungeon.py`)
- `$F2` = copy of "Cave to Sundletan B1" (`$06`): own map data copy, its header (walls, objects, rooms),
  exits rewired to `$F3`, random encounters (the cave's monsters attacked on arrival).
- `$F3` = copy of the Gratze tower rooms (`$D7`): stairs and door lead back to `$F2` (4,44).
- Script blocks for both are new, tiny, in bank `$BF`. Verified in the emulator: maps load and render,
  cave mouth → tower stairs → back to the cave, encounters work, map names show.
- Copied table entries share state with the template (e.g. scene records), fine for a proof; a real
  dungeon gets its own entries.

## Not done / next
- **Treasure chests:** not the "treasure table" (that is a key-locked door: `FieldTryItemRegion
  $8E:B63B`, script slot 2 id 3 = [object+1, required item]). Chests are header objects (list `$16`,
  10-byte records) opened through `FieldProbeFacingObject` / `FieldApplyObjectRecord $83:F4xx`; their
  contents and opened-state storage are not decoded yet.
- New tilesets/graphics (task: ROM-only renderer), the user's real dungeon design.
