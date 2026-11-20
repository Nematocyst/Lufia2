# Lufia II — battle backgrounds (traced 2026-10-28)

## Selection
- `$7F:F8A0` = background id for the next battle. BattleLoadEncounter (`$81:81EA`) copies it to `$11E1`.
- Who sets it:
  - map scene scripts, op `$74 xx` (`$80:B2AA`);
  - map load clears it to 0 (`$83:B311`);
  - overworld: 0 on tile class `$10`, else 4 (`$86:9D79`);
  - sea encounters: 3 (`$86:9CEC`);
  - Ancient Cave floors: `$80:ABCD[theme]` = `$17`, `$09`, `$01` (`$80:ABC4`);
  - `$84:9CD7/9CDC` and `$86:C5F0` change it during battle or for special battles.
- Id `$18` = black screen (special-cased at `$81:B9CB`).

## Loading (BattleBackgroundPrepare `$81:B9C7`)
- Record = 4 bytes at `$97:FD40 + id×4`: tilemap index, graphics index, palette index, effect.
  - Tilemap: resource `$179 + n`, decompressed to `$7E:2000` (2 KB = 32×32 words, stored as deltas; see Budget).
  - Graphics: resource `$16C + n`, decompressed to `$7E:C000`. Queued to VRAM word `$3000`, `$2000` bytes = 256 4bpp tiles (BattleQueueTilesAt3000 `$85:9ADD`).
  - Palette: 64 bytes at `$97:CD58 + 64×n` → CGRAM rows 2 and 3 (2 × 16 colours).
  - Effect (byte 3): 0 none, 1 BattleInitializeRipple, 2 `sub_85A76E` (used by `$0F`), 3 (used by `$12`/`$13`). Id 0 also gets the ripple at `$81:8BAE/BAC1`.
- 24 backgrounds (`$00–$17`) share 13 graphics sets (resources 364–376, 1.9–8 KB decoded, 1.5–6 KB compressed) and 20 tilemaps (377–396, 2 KB decoded, 0.1–0.4 KB compressed). Several ids reuse graphics `$0B` with different tilemaps and palettes (the cave/forest family `$0B–$14`).
- Catalog image: scratchpad `bbg/all_bbg.png` (each id forced through `$7F:F8A0` before a cave battle).

## Budget (measured 2026-10-28)
- Battles run in BG mode 1. The background tilemap is at VRAM word `$0000` (32×32). Its tiles are numbered 256 and up, from char data at VRAM word `$3000` (8 KB = 256 4bpp tiles).
- Palettes: the 64-byte entry fills CGRAM rows 2 **and** 3 (`BattleLoadPalette` advances Y). So a background has 2 × 15 colours, plus colour 0 transparent (backdrop). Desert `$00` has two identical halves and uses only row 2; others use both.
- Rows 4–7 were empty in a plain battle. Spell effects can load palettes anywhere through effect op 44 (`BattleEffectLoadPaletteRange`, scripts in bank `$95`, table `$95:8000`), and restore them from the master copy at `$7F:F1DB`. Using more than 2 palettes is untested.
- Visible area: rows 0–16 behind the command windows, and rows 0–21 while a turn plays out (the windows shrink). So about 704 tile positions share 256 tiles.
- Tilemap storage: word 0, then `stored[k] = word[k−1] − word[k]` (the loader `$81:BA59` keeps a running subtraction). Verified: a decoded vanilla tilemap matches VRAM 1024/1024.

## Toolchain (2026-10-28, tools/)
- `l2compress.py`: encoder/decoder for the resource format (optimal parse; each encode is verified by decoding). All 680 ROM resources round-trip exactly; re-encoded they total 97.5% of the original size (1,300,311 vs 1,334,019 bytes). Runtime ~12 min in Python for the whole ROM, a few seconds per background.
- `bbg_convert.py`: picture → 2 palettes × 15 colours (tiles pick the better palette), dedupe with flips, k-means merge down to 256 tiles. Rows 0–21 are converted, rows 22–31 repeat row 21. Gives graphics, tilemap (stored form), palette and a preview.
- `bbg_build.py in out ID=png …`: 4 MB ROM.
  - Resource table relocated to `$E0:8000` (1024 entries): `$80:8EA9/8EB1` operands → `$E0`.
  - Graphics base `$81:BA03` → 680 and tilemap base `$81:BA13` → 700 (copies of the original pointers there, so old indices still work).
  - Palette table → `$E0:9000` (`$81:BA33/BA3A`).
  - New resources from `$E1:8000`. Streams may cross banks; the decoder handles it.
- `bbg_testscene.py`: procedural placeholder scene (pipeline test only, not final art).
- 4 MB LoROM verified in snes9x:
  - boots to a new game;
  - a resource moved to `$E0:8000` loads (an inverted control copy shows inverted);
  - background `$04` replaced in battle;
  - `$01/$0B/$0F/$12/$15/$17` pixel-identical to the original.

## Changing them
- **Reassigning existing backgrounds:** change the bytes listed above (script op `$74` operands, `$80:ABCD`, `$86:9D79/9CEC`).
- **Recolouring:** edit the 64-byte palettes at `$97:CD58`.
- **New art:** at most 256 4bpp tiles, a 32×32 tilemap, 2 palettes (30 usable colours). Use the toolchain above: `bbg_build.py` converts, compresses and places it in a 4 MB ROM.

## Where each background is used (2026-10-30)
- Source: every `op_74` in the 242 decompiled map scripts (162 maps set one; every map with battles does). Plus the code setters: overworld 00/04, sea 03, Ancient Cave 17/09/01.
- Unnamed maps take the name of the next named map (tower entrances, sealed-tower floors).

| Id | Looks like | Used in |
|---|---|---|
| 00 | desert dunes (heat-ripple effect) | overworld, one terrain class (`$10`, probably desert) |
| 01 | dark cave rock | Phantom Tree Mtn, Flower Mtn, Mtn of No Return, Dragon Mtn, Barnan/Gratze submarine caves, Submarine Cave to Shrine, maps `$EC`/`$EE`, **Ancient Cave B41–B98** |
| 02 | open rooftop: sky and sea horizon, hedges in brick planters, blue cobblestone floor | inner floors of the three island Sealed Towers (maps `$DA–$DC`, `$DE–$E0`, `$E2–$E4`) |
| 03 | open sea, ship deck | sea battles |
| 04 | grassland, forest, mountains | overworld (all other terrain), Tanbel, Small Shrine to Dragon Egg |
| 05 | temple pillars, grey floor | Treasure Sword, Karlloon North, Divine, Vengeance shrines; Ancient Cave final floor |
| 06 | mossy grey rock | **never used** |
| 07 | cliff under open sky | Phantom Tree / Flower / No Return / Dragon mountains (outdoor parts) |
| 08 | big windows onto a golden sky over dark mountains, ribbed grey pillars, purple floor | Shrine of Daos 1F–5F |
| 09 | dark brick, cobbles | Alunze Castle B2–B5, Alunze NW Cave B4, North Dungeon, Dankirk North Cave, Shrine of Vengeance B1, Gratze Castle B1–B4, map `$7C`, **Ancient Cave B21–B40** |
| 0A | tower interior, arched window | Tanbel SE, Gordovan West, Ancient, North Lighthouse, Sacrifice, Northeast, Truth towers |
| 0B | dark grey rock wall, small ferns at the base, plain dark-red earth floor | Cave Bridge, Secret Skills Cave |
| 0C | cave, brown floor | Cave to Sundletan B1–B2 |
| 0D | cave, underground river | Cave to Sundletan B2 (part) |
| 0E | cave, red floor | Lake Cave B1–B3 |
| 0F | cave lake (animated effect) | Lake Cave B3, Submarine Cave to Shrine |
| 10 | cave, olive floor | Alunze NW Cave B1–B2 |
| 11 | cave, hanging vines | Alunze NW Cave B3 |
| 12 | lava floor (animated effect) | Ruby Cave B1–B2, Dragon Mtn, Chaed North Submarine Cave |
| 13 | lava (animated effect) | Ruby Cave B3 |
| 14 | dark cave, vines | Ruby Cave B4 |
| 15 | brown brick wall with round buttresses, lit from above, dark grey cobblestone floor | entrance floors of the three Sealed Towers |
| 16 | round sandstone pillars in front of a tan brick wall with a red tiled band on top, grey-purple cobblestone floor | Gratze Kingdom |
| 17 | castle stone, teal floor | **Ancient Cave B1–B20** |

## Imports (backgrounds v0.1, 2026-10-30)
- User art: 00 desert (1337×1177) and 04 grassland (1634×962), generated with 30-colour palettes. The files as received had 120k–240k colours (smoothed), so they were requantised.
- Fitting:
  - desert: scaled to 256 wide (box filter), top 224 rows kept;
  - grassland: scaled to 176 tall, centre 256 kept, rows 176–223 copied from 128–175.
- Converter v2:
  - all 28 rows converted;
  - tile weights 1.0 (rows 0–16), 0.25 (17–21), 0.08 (22–27, seen through the translucent windows);
  - the tile budget is split between the two palettes by minimum weighted k-means error, with weighted medoids.
- Id 0 always gets the ripple (`$81:8BAE`, independent of the record's effect byte); `bbg_build` writes effect 0 for new art.
- snes9x checks:
  - both show correctly in battle;
  - the other 22 ids are pixel-identical to the base ROM;
  - title shows START + RETRY.
- Patches (scratchpad `bbg/pkg`): clean → restored+iris+retry+bg; add-ons from the restored+iris and restored+iris+retry ROMs.

## Converter v3 and the ground method (2026-10-30, current approach)
- **Why generated art fails:** image generators fake a pixel grid (about 6.4 × 6.1 screen px per "pixel", non-integer) and export 100k+ colours. Repeats are never exact. Grassland v2: 862 distinct tiles; sky + mountains alone ≈ 317 > 256.
- **Palette split** (fixed the "square mountains"):
  - try a colour k-means start plus every horizontal split, refine each, keep the least weighted error;
  - neighbouring tiles that disagree on palette are penalised (`_coherent`);
  - smooth tiles weigh more: factor (1 + 6/(1 + tex/4)), tex = mean horizontal pixel step;
  - also tried: a global 30-colour quantise, then a 15/15 split (`_split_global`); it is used only if better.
- **Merge:**
  - weights by row: 1.0 for rows 0–16, 0.25 for 17–21, 0.08 for 22–27;
  - smooth tiles × (1 + 20/(1 + tex/4)); weighted medoids; the budget split between the palettes minimises error;
  - `focus=(r0, r1)` puts the budget on those 8-px rows (others 0.15/0.04). Useful when the horizon is over budget; bad when lower details matter (desert rocks).
- **Ground rebuild** (`tools/bbg_ground.py`, the chosen method for outdoor art):
  - everything above `top` (first full grass row, tile-aligned; grassland v2: top = 88) stays as is;
  - below it, the most seamless 32×16 patch is found and paved, with 3 brightness versions chosen per row of blocks (horizontal bands; per-block versions made rectangles);
  - `detail=None` drops rocks and tufts (the user's choice, matching the original game's plain lower screen). Pasting them back costs about 120 tiles and they got mangled.
  - Grassland v2 result: ground 24 tiles, top 235 after merging.
- **Screen layout** (measured with bg `$18` black; guide image `docs/bg_layout_guide.png`):

  | Rows (of 224) | Share | What is there | Art |
  |---|---|---|---|
  | 0–60 | 27% | always visible | sky and horizon detail |
  | 60–104 | 27–46% | monsters' feet at about 96–104 | moderate detail |
  | 104–133 | 46–59% | foreground | simple |
  | 133–177 | 59–79% | under the command windows; party at y≈115–170 during turns | simple |
  | 177–224 | bottom 21% | always under the translucent windows | plain |

  In short: horizon at 25–40% of the height, bottom ~54% plain repeating ground.
- **Workflow agreed with the user:**
  - previews only (fitted source | SNES result) until the user approves; never package or build releases unasked;
  - throwaway test ROMs for battle screenshots are fine;
  - the user's "art department" is ChatGPT image generation, asked for 30-colour palettes.
- **Status:** 00 desert (v1 art) and 04 grassland v2 (clean ground) previewed. The v0.1 patch (old art) is in the scratchpad only; not final.
- 2026-10-30, later:
  - **04 grassland v3 approved as final** by the user (`scratchpad bbg/in/grass3.png`): ground rebuilt from top = 88, no details; 24 ground tiles plus 279 above, merged to 256.
  - **00 desert v2** remade: sand from y 89, top = 96, 20 ground tiles plus 300 above. **Approved as final** (`in/shrine1_clean.png`); the user dropped the floor veins on purpose (has a plan for them later).
  - Keep the user's source PNGs, since the workspace may be wiped. They are not stored in the project yet.
  - **00 desert v2 approved as final** (`in/desert2.png` → `in/desert2_clean.png`, top = 96). The user likes the shimmer at the horizon.
  - **09 dungeon v1 approved as final** (version A; `in/dungeon1.png` → `in/dungeon1_clean.png`): blue-lit prison corridor drawn for the Alunze Castle basement. Wall band ≈ 288 tiles; floor rebuilt from top = 72 with a 32×16 patch taken from the lower floor (search ≥ 48 px below top), no details, 312 distinct → 256. Torch-glow floor reflections dropped (too costly; a kept glow row looked fragmented). Version B (64×32 cobbles) was rejected: seams and repetition.
  - 09 is shared, so this art also appears in North Dungeon, Dankirk North Cave, Gratze Castle basement, Alunze NW Cave B4, Shrine of Vengeance B1 and Ancient Cave B21–B40. The user accepted the shared slot.
  - Art tip for the art department: put light glows on the wall under each light source, keep the floor evenly lit.
  - **03 ship deck v1 approved as final** (version B; `in/ship1.png` → `in/ship1_clean.png`, script `scratchpad bbg/ship/deck2.py` `make2`). Top 96 rows kept (384 distinct, merged). Deck planks synthesized, not patch-paved: one source board (full-res rows 1071–1147) resized to 7 px body + 1 px seam (8-px boards, rows 96–143, 2 brightness levels) and 15 + 1 (16-px boards, rows 144–223, perspective), 128-px segment containing a joint, rolled by multiples of 8 per row so joints stagger. ≈64 deck tiles. Version A (all 8-px boards) rejected: busier.
  - Tip: for floors made of boards or bricks, size each board/brick row to 8 or 16 px so it lines up with the tiles.
  - **01 cave v1 approved as final** (version A; `in/cave1.png` → `in/cave1_clean.png`, script `scratchpad bbg/cave/persp.py`, variant g): wall kept above top = 96 (384 distinct, merged; small plants mostly merged away). Floor: best 32×32 patch from rows 140–223, paved from row 128; rows 96–127 use the same patch squashed to 32×16 for perspective; 2 brightness levels. Rejected: running-bond synthetic stones (read as a standing brick wall), 64/128-wide patches (seams; cross-fading blurs).
  - **17 hall v1 (`in/hall1.png`): not usable as is.** Top 80 rows = 320 distinct tiles; the floor's oval medallions grow with depth, so each oval row needs its own repeating band (periods 64/88/88/144 px → 238 floor tiles). Merged, the ovals turn blocky. Trick that worked for the top: repeat one 128-px slice between two pillar centres (x 107–240 resampled to 128) twice → 160 top tiles, looks good (`scratchpad bbg/hall/hall4.py`). Flattening the floor colours made it worse. Asked the art department for a simpler floor.
  - **17 hall v2 approved as final** (version B; `in/hall2.png` → `in/hall2_clean.png`, script `scratchpad bbg/hall/slabs.py`, `make('b', repeat=False)`). The art department replaced the ovals with straight slab rows. Hall kept whole above top = 80 (384 distinct, merged). Floor synthesized like the ship deck: 8-px slab rows 80–127 from full-res rows 742–797 (2 joints per 128 px, 2 brightness levels), 16-px rows 128–223 from rows 1010–1103; ≈64 floor tiles. Version A (one 128-px hall section repeated twice: 224 tiles in total, no merging) was rejected because the repeat shows.
  - **0A tower v1 approved as final** (`in/tower1.png` → `in/tower1_clean.png`, script `scratchpad bbg/tower/slabs.py`): fitted to 256 wide, top 224 rows; view kept above top = 80 (384 distinct, merged); slab floor as on the hall (8-px rows from full-res 690–750, 16-px rows from 952–1033, 2 joints per 128 px). Sunlight stripes on the floor dropped.
  - **07 cliff v1 (`in/cliff1.png`): sent back for a simpler sky.** Above the ground (top = 104) = 416 distinct tiles, the most so far. Tried: flattening the sky dither into 4-px colour bands (mask b−r > 140, b > 215, rows < 70; mountains are bluish too, so a looser mask flattened them): 377 → still over. Converter `focus=(6,13)` keeps the mountains and valley but the clouds turn blocky. Ground rebuild 32×16 patch reads as horizontal stripes. Scripts `scratchpad bbg/cliff/`.
  - **07 cliff v2** (`in/cliff2.png`, plain sky, two small clouds): sky dither flattened into 4-px bands (mask b−r > 140, b > 180, rows < 60); ground rebuilt from top = 112; 337 distinct → merged. Variants: A = 32×16 patch with dark dirt marks (repeating mark visible); B = calm 32×16 patch at (200, 120), chosen by seam + 30 × share of dark pixels (`scratchpad bbg/cliff/cliff4.py`, `cliff2_g0.png`). **Approved as final: version B** (`in/cliff2_clean.png`).
  - **05 shrine v1** (`in/shrine1.png`, 1341×1173 → 256×224): colonnade kept above top = 88 (416 distinct incl. one far floor row, merged); slab floor as on the hall (8-px rows 88–127 from full-res 663–721, 16-px rows from 940–1034). The green marble veins on the floor are lost (the copied slab rows carry little vein; veins differ per slab). **Approved as final** (`in/shrine1_clean.png`); the user dropped the floor veins on purpose (has a plan for them later).
  - **08 Daos v1** (`in/daos1.png`, 1343×1171 → 256×224, top = 112): above the floor = 448 distinct tiles (textured sunset sky + floating castle), the worst so far; the castle and sky come out blotchy. Floor: perspective grid with converging joints, rebuilt as staggered slab rows (8-px rows 112–127 from full-res 646–689, 16-px rows from 762–862, crack-free rows chosen); foreground rubble removed. `focus=(0,14)` erased the floor joints and did not save the castle. Sent back: plainer sky asked for.
  - **08 Daos v2** (`in/daos2.png`, smoother sunset, simpler castle, straight slab rows): top = 112; slab rows from full-res 663–712 (8 px) and 981–1057 (16 px), 2 joints per 128 px (`scratchpad bbg/daos/slabs2.py`). Castle and sky now read cleanly; the sun disc is softened. **Approved as final** (`in/daos2_clean.png`).
  - **02 town square v1** (`in/square1.png`, 1304×1206 → 256 wide, top 224 rows): above top = 88 → 352 distinct (merged). Cobbles rebuilt like the cave: 32×32 patch from rows 156–187, x 136 (search limited to x 48–208 to avoid the corner planters), squashed to 32×16 for rows 88–119; corner planters removed (`scratchpad bbg/roof/sq.py`). The trees lose their green (2 palettes × 15 colours are taken by blues, stone and roof orange). Discarded: the user had thought 02 was a town battle; a tower-top remake is coming.
  - **02 tower terrace v1** (`in/terrace1.png`): sky flattened into 4-px bands (rows < 56) → `in/terrace1_256f.png`; top = 88; slab rows from full-res 634–686 (8 px) and 871–950 (16 px) (`scratchpad bbg/roof/slabs.py`). 259 distinct → 253 after flip dedupe, so **no merging at all**: the first picture to fit as drawn. The big island is faint (its blue shares the sea colours). **Approved as final** (`in/terrace1_clean.png`).
  - **15 fortress entrance v1** (`in/fort1.png`): wall already periodic (one pillar + torch bay ≈ 64 px). A = full wall (384 distinct, merged); B = one 65-px bay from x 46 resampled to 64 and repeated 4× (`scratchpad bbg/fort/slabs.py`): 144 tiles in total, nothing merged. Slab rows from full-res 631–690 (8 px) and 823–911 (16 px), top = 80. **Approved as final: version B** (`in/fort1_clean.png`).
  - **16 Gratze hall v1** (`in/gratze1.png`): bays ≈ 72 px on screen. A = full wall (384 distinct, merged); B = one 73-px bay from x 117 resampled to 72 and repeated (period 72 = 9 tiles; doesn't need to divide 256): 154 tiles in total (`scratchpad bbg/gratze/slabs.py`). Slab rows from full-res 617–677 (8 px) and 814–899 (16 px), top = 80. **Approved: version B** (`in/gratze1_clean.png`; confirmed by the user).
  - **10 mossy cave v1** (`in/moss1.png`, 1337×1177 → 256 wide, top 224 rows): wall kept above top = 88; ground `rebuild(top=88, detail=None)` with the default 32×16 patch (`scratchpad bbg/moss/moss.py`, `moss_a.png`); 376 distinct → merged. The calm-patch variant (64×16) left a darker band at the bottom and was not shown. **Approved as final** (`in/moss1_clean.png`).
  - **11 mossy cave 2 v1** (`in/moss2.png`): same method as 10, top = 88, default 32×16 patch (`scratchpad bbg/moss/moss2.py`, `moss2_a.png`); 376 distinct → merged. Very close to 10 in look. Awaiting the user's verdict.
  - **11 vine cave v2** (`in/moss3.png`, darker, roots/vines, teal glows): same method, top = 88, default 32×16 patch (`moss3_a.png`); 376 distinct → merged; glow sparkles softened. **Taken as approved** (`in/moss3_clean.png`; the user moved on to 14).
  - **14 Ruby Cave v1** (`in/ruby1.png`, 713×735, white 5-px border on the left → cropped x 6–713, fitted to 256 wide, top 224 rows): wall reaches y ≈ 110, so above top = 112 there are 448 distinct tiles. The far cave's soft red glow gradients merge into dark blocks; `focus=(0,14)` and `smooth=0.3` did not help. Sent back: wall to ~40% height, simpler far cave, fewer plants.
  - **14 Ruby Cave v2** (`in/ruby2.png`, 1341×1173, wall to ~39%): top = 88, default ground rebuild (`scratchpad bbg/ruby/ruby2.py`, `ruby2_a.png`); 376 distinct → merged cleanly. The fire plants' green leaves turn orange-brown (no green in the palettes). **Approved as final** (`in/ruby2_clean.png`).
  - **12/13 lava variations v1** (`in/lava1.png` → 12, `in/crystal1.png` → 13; both 713×735 with white edge strips, cropped): wall to ~50% height, 448 distinct above top = 112 → far-cave glow turns blocky, as on Ruby v1. Sent back with the Ruby v2 recipe (wall to ~40%, simple dark back wall with lava cracks). Animation check (snes9x, 240 frames, right-edge strip): vanilla 0F/12/13 backgrounds showed no pixel change. Effect byte → `$11E5` → table `$81:BAD4`: 1 = ripple, 2 = `sub_85A76E`, 3 = RTS (no effect at load), so 12/13's effect 3 does nothing here; 0F's effect 2 still to check.
  - **13 crystal cave v2** (`in/crystal2.png`, 1341×1173, wall to ~40%): top = 96, default ground rebuild (`scratchpad bbg/ruby/crystal2.py`, `crystal2_a.png`); 408 distinct → merged; the back wall loses some lava-crack detail. **Approved as final** (`in/crystal2_clean.png`).
  - **12 lava cave v2** (`in/lava3.png`, 1341×1173, wall to ~40%): top = 96, default ground rebuild (`scratchpad bbg/ruby/lava3.py`, `lava3_a.png`); 408 distinct → merged; a few blocky squares in the stalactites at top right. **Approved as final** (`in/lava3_clean.png`).
  - **0F effect checked:** effect 2 = `sub_85A76E`: copies the 23-byte indirect HDMA table `$85:9F80` → `$7E:4408`, channel to BG1HOFS (mode `$42`): 48 lines normal, then bands of 4/6/9/13 lines (screen rows 48–80) take scroll values from `$7E:4400–4406` = BG1HOFS + phase/8…/1, then normal. The phase `$1B1A` is set to 0 and only the ripple routine (effect 1) advances it, so for 0F the bands sit at the normal scroll: no visible motion (snes9x: 0 changed pixels over 240 frames). New art for 0F can be a still picture; bbg_build writes effect 0 anyway.
  - **0F cave lake v1** (`in/lake1.png`, 1341×1173 → 256×224): lake and shore line end at y ≈ 103; shore rebuilt from top = 104 with a 32×16 patch searched in the centre (x 40–216) to avoid the corner boulders, which are removed (`scratchpad bbg/lake/lake.py`, `lake_a.png`). Above = 416 distinct → merged; the left cave arch and rocks soften. **Approved as final** (`in/lake1_clean.png`).
  - **0B cave bridge v1** (`in/bridge1.png`): wall ends at y ≈ 81; floor rebuilt from top = 88 with `levels=1` (one brightness), patch (152, 172, 32, 16) (`scratchpad bbg/bridge/bridge2.py`, `bridge_b.png`). The art's smooth top-to-bottom floor gradient made visible stripes with 3 or 5 brightness bands, so the floor is flat. Above = ~340 distinct → merged; the green plant tufts turn brown. **Approved as final** (`in/bridge1_clean.png`).
  - Tip: a smooth light-to-dark gradient on a plain floor turns into stripes; use `levels=1` or ask for evenly lit floors.
  - **0C Sundletan cave v1** (`in/sund1.png`): wall ends at y ≈ 64; floor rebuilt from top = 72 with `levels=1` (`scratchpad bbg/sund/sund.py`, `sund_b.png`); above = 288 distinct, barely over → near-lossless. Close in style to the original 0C. **Approved as final** (`in/sund1_clean.png`; the user moved on to 0D).
  - **0D underground river v1** (`in/river1.png`, same wall as 0C plus a river band at y ≈ 64–90): floor rebuilt from top = 96 with `levels=1`; river band rows 64–95 tiled with the most seamless 64-px period (from x 98) (`scratchpad bbg/sund/river.py`, `river_b.png`) → 296 distinct, nearly lossless. **Approved as final** (`in/river1_clean.png`).
  - **0E Lake Cave approach v1** (`in/lakecave1.png`, matches 0F's rock style, three small water trickles): wall ends at y ≈ 79; floor from top = 80, `levels=1` (`scratchpad bbg/lake/lc.py`, `lc_a.png`); ~300 distinct above → merged; the trickles get fainter. **Approved as final** (`in/lakecave1_clean.png`). With this, all 23 used ids (00–05, 07–17) have new art; 06 is unused.
- **Test build, 2026-10-30:** all 23 approved pictures (scratchpad `bbg/final/bg_XX.png`) built onto `lufia2_restored_iris_retry.sfc` → 4 MB, SHA1 3c0367ef…d752. Patches: `lufia2_restored_iris_retry_backgrounds.bps/.ips` (from clean) and `addon_backgrounds_for_restored_iris_retry.bps/.ips`; both verified by applying. Build ~6.5 min.
  - **Bug fixed in `bbg_build.py`:** when a compressed stream ran past `$xx:FFFF`, the writer jumped to bank xx+2 instead of (xx+1):8000, so every stream crossing a bank was corrupted (04, 09, 0D, 10, 14 showed garbage). Single-background test builds never crossed a bank, so it went unnoticed. Fixed (`a += 0x8000`); all 23 checked in battle (`bbg/final/all_backgrounds.png`).

## Overworld terrain and new backgrounds (investigated 2026-10-30)
- **How the overworld picks a background** (`$86:9D57`–`9D79`, after an encounter fires): `WorldMapReadTileClass` (`$86:9A71`) → class = high nibble of byte 4 of the tile's 5-byte record; class `$10` → id 00, anything else → id 04. Sea battles take the separate ship path (`$86:9CEC`, id 03). Code: `A0 00 00 C9 10 F0 03 A0 04 00 98 8F A0 F8 7F` at `$86:9D6E`.
- **World map data** (record table `$86:CE32`, 0x12 bytes per world-map resource id `$09EA`):
  - block map = resource 0x28C → `$7F:4000` (0x40-byte header, then 128×128 words, one per 2×2 tiles);
  - tile index = word from `[$DF]` (`$9A:8000`, crossing into `$9B`) at block×8 + quadrant (+2 x odd, +4 y odd);
  - tile record = 5 bytes at `$9E:B000 + 5×tile`: 4 Mode 7 char numbers (TL, TR, BL, BR) + class byte;
  - chars = resource 0x28B (256 × 64 bytes, 8bpp) → `$7F:0000`; palette 2 × 256 bytes at `$A6:B200` and `$A6:BF00`;
  - world 1 (resource 0x28F, tiles `$9B`, records `$A1:A8F5`) only has classes 0, 3, 4.
  - Rendering script: scratchpad `wmclass.py` + `wmrender.py`; `world_terrain.png` = map vs classes.
- **Classes found on world 0** (256×256 tiles): 0 grassland (5,352), 1 desert (1,031), 2 forest (2,205: the dark-green woods), 3 sea (50,364), 4 hills/mountains/rocky shore (6,584). **Forest already has its own class** but falls into the "else 4" branch.
- **Plan to add terrain backgrounds:** replace the 11 bytes at `$86:9D6E` with `JSL` to a small routine in the expansion (class >> 4 → 16-entry table of ids) + NOPs; the following `STA $7FF8A0` stores the result. Y is not used afterwards.
  - Free ids: **06 is unused** (forest can go there with no table change). For more ids, relocate the 24-record table: only 4 reads, `$81:B9D5/B9DC/B9E3/B9EA` (`LDA.l $97FD40..43,X`); `$18` stays the black screen (`CMP #$18` at `$81:B9CB`); ASL ASL in 8-bit A allows ids up to `$3F`.
  - Other users of `$11E1`: `$86:D0DC` (0 = special), `$84:9CD4` preview selection, `$86:C5F0`/`$86:D2ED` setters. No per-id tables found besides the record table.
- **Monster groups are by region, not terrain:** `$7FE000` (resource 0x193, world 0 only) = 64×64 zone grid (x/4, y/4); zone × 10 → 5 (weight, group) pairs at `$97:C493/C494` (`$86:9CF3`). Forest-only monsters would need a similar terrain check there (e.g. a second zone table used when class = 2).
- **Testing needs an overworld save state** (none of the scratchpad states are on the world map; ghost-walking out of Elcid didn't trigger an exit).
- **Terrain backgrounds tested, 2026-10-30** (`tools/terrain_patch.py`): the 11 bytes at `$86:9D6E` → `JSL $E0:F000` + 7 NOPs. Routine: PHX; REP #$20; AND #$00F0; LSR×4; TAX; SEP #$20; LDA.l $E0:F040,X; REP; AND #$00FF; TAY; SEP; PLX; RTL (Y = id like the original). Table at `$E0:F040`, 16 bytes, defaults 0→04, 1→00, 2→06, others 04.
  - Emulator: the user's save (`scratchpad ow/user.srm`, Alunze church) → walk S out of church, then right → world map at (43,151) (`ow/world.state`). Forest tile (44,147) → bg id 06; grassland (42,151) → 04 (`ow/forest.py`, `ow/terrain_test.png`).
  - **Second build bug found and fixed:** `bbg_build.py` put new graphics at resource 693+ and original tilemap copies at 700–719, so with 23 new backgrounds the new graphics overwrote the tilemap copies; only untouched ids (06) showed garbage. Tilemaps now start at 800 (`TMBASE`), with an assert against overlap. Rebuilt ROM SHA1 fbeabff3…701c; all 23 rechecked, 06 shows its original art again.
  - Patches regenerated (same names) + `addon_forest_test.bps` (forest → 06, on top of the backgrounds ROM).
  - **06 forest v1** (`in/forest1.png`): top = 88, `levels=1`, calm 32×16 patch at (180, 184) chosen by seam + stripe penalty (std of row brightness) (`scratchpad bbg/forest/forest2.py`, `forest_c0.png`, copied to `bbg/final/bg_06.png`). The first auto patch had an orange leaf streak that made obvious stripes. Tested from the user's save: forest tile (44,147) → id 06 shows the forest. **Approved as final** (`in/forest1_clean.png`).
- **Test zip updated, 2026-10-30:** backgrounds ROM now includes 06 forest (SHA1 8c8b4bda…2762); `addon_forest_test.bps` → forest tiles use 06 (SHA1 452ee070…9951). 24 backgrounds total (00–17).
- **Hills background and terrain zones, 2026-10-30:**
  - Class 4 (hills/mountains/rocky shore) is **not walkable** on foot (`CMP #$40` checks in the vehicle/landing code; the emulator walker stops at it), so a class-4 background would never be seen. Instead: **grass tiles within 2 tiles of class 4** form a "hill zone" (1,620 of 5,352 grass tiles; `scratchpad hill_zone.npy`, map `bbg/final/hill_zone_map.png`, orange).
  - `bbg_build.py` now **moves the record table to `$E0:F100`** (64 ids; the 4 `LDA.l $97FD40..43,X` reads at `$81:B9D5/DC/E3/EA` repointed; ids 00–18 copied). New slot **$19 = hills** (`in/hills1.png`, top = 88, calm 32×16 patch (116, 80), `levels=1`; `bbg/final/bg_19.png`).
  - `terrain_patch.py` v2: routine at `$E0:F000` (79 bytes): on world 0 (`$09EA` = 0) read a 256×256 byte override map (rows 0–127 `$F0:8000`, 128–255 `$F1:8000`) at (`$11F2`, `$11F4`); non-zero = background id; else the class table at `$E0:F080`. `--zone file.npy=id`.
  - Emulator from the user's save: forest (44,147) → 06, grass next to mountains (42,151) → 19, open grass (41,148) → 04. All 25 backgrounds rechecked after the table move (`bbg/final/all_backgrounds.png`). **Approved**: hills art (`in/hills1_clean.png`) and the 2-tile zone rule as a first approach.

## Random background variants (BUILT as a test, 2026-10-31)
- `tools/variants_patch.py in.sfc out.sfc 04=19,1A …`: each id can have up to 7 alternates; every battle picks one of (id + alternates) with `RandomScale` (`$80:8299`, A = n → 0..n−1).
- Hook: `BattleBackgroundPrepare $81:B9C8` `LDA $11E1 / CMP #$18` (5 bytes) → `JSL $E0:F300` + NOP. The routine returns A = chosen id with B = 0 and flags from `CMP #$18`, so the black-screen check and record reads use the chosen id; `$11E1` is untouched (ripple and `$86:D0DC` see the original id). Table `$E0:F400`, 8 bytes per id (count + ids). Code 63 bytes. Needs a bbg_build ROM (records at `$E0:F100`).
- Applies wherever the id comes from (overworld, map scripts, Ancient Cave), so dungeons can rotate too. Callers: `$81:86C0` battle start and `$84:9CDF` preview selection (also randomises; fine unless an id used there gets variants).
- Test (stand-in: grassland 04 ↔ hills 19) on the backgrounds+terrain ROM (SHA1 4D3FB9D1…1911): 10 grassland battles with different RNG positions (`ram[0x559]`) → 3× hills, 7× grassland; other ids unchanged (01, 17 checked). `scratchpad ow/vtest.py`, `ow/variants_test.png`. RNG note: the game's random table only advances when used, so identical replays give identical picks; real play varies.
- Space: `$E0:F300–F33E` code, `$E0:F400–F5FF` table. No overlap with music-off (`$82/$83`).
- Next: the art department makes variants as normal backgrounds in new slots `$1A+`; build with bbg_build, then list them here.
- **Grassland variants approved for testing, 2026-10-31:** 1A river plain (`in/grassriver.png`), 1B farmland with windmill (`in/grassmill.png`); top = 88, `levels=1`, calm patch search; ~360 distinct → merged. `bg_1A.png`/`bg_1B.png` added to `bbg/final/`.
  - **RNG fix:** the game's RNG is only reseeded at save load/write and advances only when used, so the first version (RandomScale alone) picked 1A in 17 of 22 test battles. The pick now uses `RandomByte` + play-time frames (`$0B50`) + seconds (`$0B4F`), scaled with the hardware multiplier (code 88 bytes). Test with varied RNG index and clock: 2× 04, 5× 1A, 5× 1B of 12.
  - Build: bbg_build (27 pictures) → terrain_patch → `variants_patch 04=1A,1B` → `music.asm` (asar). Final SHA1 BC7F5617…E4FD. Patches: `lufia2_full_test.bps` (clean ROM → everything) and `addon_grassvariants_for_musicoff_rom.bps` (from the music-off ROM E0B53677…E177). Both verified by applying. `scratchpad vpkg/`.
  - Note: the variants' grass is darker than 04's brighter green; matching floor colours is optional.
- **Forest variants (previewed 2026-10-31, awaiting verdict):** 1C path (`in/forestpath.png`, top = 88; floor options: dirt patch `fvar/forestpath_d.png` = path opens into a clearing; grass `forestpath_g.png` = path stops at the floor line; a straight 48-px dirt strip down the floor looked rigid and stripy, rejected), 1D stream (`in/foreststream.png`, top = 96, `foreststream_a.png`). Both ~360–390 distinct → merged. Floors differ from 06's olive (1C brown, 1D bright green). Test ROM `bbg/fv.sfc` (only 06/1C/1D), shots `bbg/forest_variants_battle.png`.
  - 1C redone with `in/forestpath2.png` (path runs sideways behind the bushes; plain grass floor): top = 88, calm patch (204, 116), 360 distinct → merged cleanly. `fvar/forestpath2_a.png`, shot `bbg/forestpath2_preview.png`. Replaces the first path picture.
- **Rotations test build 2 (2026-10-31):** forest variants approved: 1C = `in/forestpath2.png`, 1D = `in/foreststream.png`. Floors matched per set (user's request) by per-channel mean/std transfer of the floor rows (`bbg/match/match.py`): grass 1A/1B → 04's floor colour; forest 06 → the 1C/1D average. Unmatched originals kept in `bbg/final_unmatched/`. `bbg/final/` now holds 29 pictures (00–17, 19, 1A–1D).
  - Build: bbg_build (29) → terrain_patch → `variants_patch 04=1A,1B 06=1C,1D` → music.asm. SHA1 65D44F0A…ADF. Delivered `lufia2_rotations_test.zip`: `lufia2_full_test.bps` (clean), add-ons from the music-off ROM (E0B5…) and from the first grass-variants ROM (BC7F…). All verified.
  - Test note: the harness's RNG table is identical every run, which biases picks (forest showed 1C 15/21). Randomising the table per run (`ow/vtest2.py`, like real play) gave forest 06 ×6, 1C ×3, 1D ×2 and grass 04 ×2, 1A ×1, 1B ×3.
- **Hills variants (previewed 2026-10-31, awaiting verdict):** 1E lone tree (`in/hilltree.png`), 1F winding path (`in/hillpath.png`); top = 88, calm patch, floors matched to 19 (`bbg/hvar/*_m.png`). **Approved as hills variants** (user confirmed): floors matched to 19 (`final/bg_1E.png`, `bg_1F.png` = `hvar/*_m.png`). Planned rotations: 04 = 1A,1B; 06 = 1C,1D; 19 = 1E,1F. Preview only (one patch at the end).
- **Mountain (07) variants (previewed 2026-10-31, awaiting verdict):** 20 rope bridge (`in/mtnbridge.png`, top = 96, 392 distinct), 21 above the clouds (`in/mtnclouds.png`, top = 104, 424 distinct: the cloud sea goes blocky). Floor options: A = new floors matched to 07's orange-brown (`mvar/*_m.png`; seam where the grey ledge rocks meet the floor); B = 07's floor shifted to the grey-brown of the new pair (`mvar/cliff07_grey.png`; seam on 07 instead). Shots `bbg/mtn_variants_preview.png`, `bbg/mtn_floor_options.png`.
  - 21 redone with `in/mtnclouds2.png` (mist band instead of a cloud sea): top = 104, converts cleanly (`mvar/mtnclouds2_a.png` grey floor, `_m.png` orange). Shot `bbg/mtnclouds2_preview.png`. **Approved: option B** (grey floors). 07 floor shifted to the bridge+clouds average (`final/bg_07.png`; original in `final_unmatched/`); 20 = bridge, 21 = clouds v2. Planned rotation 07 = 20,21.
  - Floor fix (user noticed the clouds floor looked square): the 32×16 patch repeat made a regular grid of bumps. 20 and 21 now use a 64×32 patch with 8-px cross-faded edges (`mvar/floorfix.py`, `floorfix_b.py`); 128-wide patches cost more tiles without looking better. 07 re-matched to the new floors. Cost: the bridge's valley behind the bridge merges a bit more (416 distinct). Shot `bbg/mtn_set_final.png`.
  - Tip: on floors with large, low-contrast ripples (dirt, sand), use a 64×32 blended patch; 32×16 reads as a grid.
  - **Straight-line fix (user: "distinctly visible straight horizontal line"):** the floor rebuild cuts at a straight row, and the colour shift of 07 made its straight cut visible. Now: 20/21 keep the original pixels down to the ledge edge found per column (dirt mask, smoothed; `mvar/edge.py`) + 6 px, then fade into the 64×32 floor texture over 10 px (`bridge_edge.png` 450 distinct, `clouds_edge.png` 484). 07: colour shift ramped over rows 88–128 instead of applied below the cut (`cliff07_ramp.png`). Staged in `final/`. Shot `bbg/mtn_set_edge.png`. Awaiting the user's verdict.
  - Lesson: when a floor is recoloured or rebuilt under an irregular edge, follow the edge and fade; a straight cut shows.
  - **Outcome:** user reverted 07 to the original approved cliff (orange floor; `final/bg_07.png` restored) and will have the rope bridge and clouds pictures remade. 20/21 removed from `final/` (kept in `bbg/rejected/`). No mountain rotation for now.
  - **User's rule for floor rebuilds:** never replace the ground below a straight horizontal line; it destroys the contour between foreground and background. Always keep the art's own edge (per-column boundary) and only replace the plain floor well below it, fading in.
- **Rope bridge remake (`in/mtnbridge2.png`, previewed 2026-10-31):** edge-following floor (`mvar/bridge2.py`: dirt mask per column, edge rows 71–95, original kept to edge + 10 px, 12 px fade into a 64×32 blended patch) → contour preserved. Floor colour already close to 07, no matching. Scenery above row 96 alone = 384 distinct, so sky and the layered blue valley merge into blocks/bands; `focus` did not help (sky bands are palette limits). Suggested art fix: plainer sky, fewer valley ridges. Shot `bbg/mtnbridge2_preview.png`.
