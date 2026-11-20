# Lufia II — Ancient Cave floor generator (traced 2026-10-28)

Entry: any map change into `$F0` from another map runs AncientCaveGenerateFloor `$83:9E31` (from `$83:B26D`, sets `$05B6` bit 0). It picks the theme, loads the map header, and runs the generator `sub_839013`. It then increments the floor counter `$7F:E696`. When the counter is `$63` (99), it sends you to the fixed map `$F1` instead.

## Themes (table at `$83:9F3F`)
- The theme comes from `$83:9F4F[(floor−1)/10]` = 0,0,1,1,2,2,2,2,2,2. So there are three themes: B1–B20, B21–B40 and B41–B98.
- Per theme, indexed 0/1/2:

  | Data | Table | Values |
  |---|---|---|
  | map data resource (`$7F:E69B`) | `$9F49` | `$013B`, `$0139`, `$0134` |
  | block template resource (`$E699`, decompressed to `$7E:4000`) | `$9F59` | `$0169`, `$016A`, `$016B` |
  | tileset resource (`$E69D`) | `$9F5F` | `$0156`, `$0154`, `$014F` |
  | song | `$9F65` | 5, 8, `$17` |
  | scene record list (`$E6A2`) | `$9F6B` | |
  | map header (`$E6A5`, 3 bytes) | `$9F73` | `$94:D54E`, `$94:D2BF`, `$94:D61F` |

  A 4th header pointer, `$94:EFE8`, follows in the same table, but nothing indexes it.
- Palette: base `$9F7F[theme]` = 30/18/6, plus `(floor & 6)×1.5`. Each theme has 4 palette slots that change every 2 floors. Theme 1's four slots are the same palette; themes 0 and 2 have four different ones.
- Screens: theme 0 = green/teal stone tiles; theme 1 = brown earth with dark stone walls; theme 2 = dark rock with olive grass.

## Loot pre-roll (`$83:9074–91E4`, 8 entries at `$7F:E746`)
- **Item pools.** All items whose record has b0 bit 1 set, b0 bit 5 clear and b1 bit 5 clear, and whose price is below 1000×(floor+1) (no cap from B60). They split into list A (`$7F:0000`) or B (`$7F:1000`) by record word +7 bit 0.
- **Entry 0 (Iris).** RandomByte < 5 (≈2%): a random Iris piece k from `$91:FFCA`, unless already rolled this run (`$7FE75E`) or found (flag `$C8+k`). It is marked `$0200`.
- **Entry 0 (Providence).** Otherwise, from B21: Providence (`$022D` = item `$2D` | `$0200`) if random(60) < floor, until it has been obtained (`$7FE75B` bit 7).
- **Remaining entries (RandomByte r):**

  | r | Share | Contents |
  |---|---|---|
  | ≥ `$AE` | 32% | list A |
  | `$81–$AD` | 18% | list B |
  | `$63–$80` | 12% | a spell (random 0–34, high byte `$80`), if no party member has it; else a potion |
  | `$5E–$62` | 2% | blue-chest item from `$94:EEA0` (41), high byte `$40` |
  | `$24–$5D` | 23% | potion/magic table `$91:FFDC` (9, centre-weighted) |
  | < `$24` | 14% | misc consumables `$94:F13D` (31: balls, boomerangs, gourds, stat potions, Ex-Magic…) |

## Layout
- **Cell grid.** `$7F:EA00` is a 16×16 grid of room ids, one byte per cell; index = y×16 + x. A cell is 6×6 tiles, with origin tile = (6x, 6(y−1)) (CaveResolveCellOrigin `$83:9B48`). The map is 96×84 tiles = 16×14 cells.
- **Rooms** (`$83:91E7`). Rectangles of 1–4 × 1–4 cells (CaveDrawRandomMean). The generator scans x from 1 while x+w < 9 and y from 4 while y+h < 15, and stops at 7 rooms (`$56` < 8). **Only cell columns 1–8 are ever used: the right half of the map is always empty.**
- **Joining.** CaveMergeRoomCells ×8, CaveLinkRoomCells and the neighbour pass `$83:9284–9363` join rooms. Cells on the E6F1 list get block `$39` (wall door decoration).
- **Drawing.** Each cell's 8-neighbour mask maps through `$93:D59B` to a block id in `$7F:EB00` (`$1C` = empty). Blocks are copied from the template. Decorations: each tile has a 3/16 chance to be swapped for a variant from header records type `$0A`.
- **Start and stairs.** Start = `$E6A9/AA` (+3, +2 inside the cell); its upper tile is cleared. Stairs = `$E6AB/AC` (template tile `$4458`), placed in a different room.
- **Extra tile.** 1 floor in 16 places a second special tile at `$E6AD/AE` (template tile `$4390`). Nothing reads its position after generation. In a test with it forced onto the start tile, the player could not step back onto that spot. Not identified yet.
- **Monster room** (`$83:949D`). On 1 floor in 16 (RandomByte < `$10`), the first 2×2-cell room found (50% per candidate) gets up to 13 extra monsters and 8 chest attempts. Forcing the roll gave a monster room on 20/20 floors (15 monsters, 8 chests).
- **Monsters.** 4–7 attempts (random(4)+4), one per random room cell; formation as in CavePick. At most 20 objects (`$E731` < `$14`).
- **Chests.** One per 2×2 room block (CaveTryPlaceRoomChest), up to 8. Contents come from the pre-roll. The tile is a red chest (`$474E`) or a blue chest (`$4754`, value bit `$4000`).

## Measured (snes9x, 60 generated floors, vanilla)
- Rooms 1–7 (7 on 40% of floors); 9–47 cells in use; 3–8 cells wide, 3–10 tall.
- 3–7 monsters, 1–4 chests. Extra tile on 5/60 floors.
- How to get there: tools in the scratchpad `cave/genfloor.py` set `$7F:E696` before stepping through the lobby's right door (state `iris/cv3.state`).

## Extension points
- **Table-only:**
  - theme per decile `$83:9F4F`;
  - palettes `$9F7F+`; songs `$9F65`;
  - loot thresholds `$83:9142–9158`; Iris chance `$83:90D4`; Providence start floor and roll `$83:9125/9129`;
  - monster count `$83:9515–951B`; monster-room chance `$83:94A1`; extra-tile chance `$83:9476`.
- **Wider floors:** `CMP #$09` at `$83:9213` and `$83:924E` → `$0F`. The test gave layouts up to 13 cells wide, but more 1–2-room floors because the 7-room cap is reached sooner; it needs a higher room cap too. Walkability was not checked.
- **New special objects:** the contact hook from v0.4 (`$83:B96F` → CaveContact) already runs scene scripts on cave floors. A virtual formation could mean an NPC (merchant/healer) instead of a battle.
- **New themes** need new template and map resources in the cave's block format, plus ROM space; the hardest option.
