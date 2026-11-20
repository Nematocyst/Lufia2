# Lufia II (US) — game data table formats (2026-10-27)

Extractor: tools/gamedata.py → build/gamedata.json; tools/world_regions.py → build/world_regions.json; tools/cave.py → build/cave.json; tools/enemy_ai.py → build/enemy_ai.json; tools/item_effects.py → build/item_effects.json; tools/page_ai.py adds AI, spell effects and item effects to build/page_data.json. Reference page: "Lufia II Data Atlas" artifact (docs/lufia2-data-atlas.html).

## Items ($000–$1D2, 467)
- Names $9E:C7E8 + id*12. Records: $96:CF69 word offsets (relative to $CF69).
- 9 fixed bytes: b0 flags (bit3 cursed, bit5 important/can't sell; $C1/$80 consumables, $22 tools, $20 keys), b3 icon, b4 palette?, b5–6 price, b7 slot (01 wpn 02 armor 04 shield 08 helm 10 ring 20 jewel), b8 equip mask (bits: Maxim, Selan, Guy, Artea, Tia, Dekar, Lexis).
- Then 32-bit mask + one word per set bit. Words 4–10 = ATP DFP STR AGL INT GUT MGR bonus (added at $82:F722), word 15 = IP id, word 13 = use message id, word 14 = always 100.
- Effect scripts (solved 2026-10-26), battle VM, offsets relative to the record start (= jump base): word 0 = menu/field use script, word 1 = in-battle use script, word 2 = equipment script (weapons: runs on every attack; rings Undead/Sea/Dragon: `or G39, bits` adds attack attributes). Scripts sit right after the word list. Fruits (Secret/Holy/… fruit) have no script.
- Verified against pixelguides weapon list (Short sword ATP42/900G/no Tia/Ice attack; Dual blade Wave motion; Egg sword Hardboiled; Gades blade Octo-strike).
- Item $047 "SuhrCustom11": ATP 50, 4980 G, all chars — not on TCRF unused list.

### Effect commands (handlers write battle_action_work $7F:F44E)
- 24 s v b: stat slot s ($85:9F04 → work+20+6s; slots HP MP maxHP maxMP ATP DFP STR AGL INT GUT MGR) += v + random(b) (b scaled by RandomScale at $85:D1CC; RandomScale(n) = n×rand>>8 = 0..n−1). v ≥ 999 = full. Slot values are also VM globals: HP change = G42, MP change = G45 (G42 + 3k for slot k); action flags work+12 = G38.
- 25 s p: stat slot s ±p% for the battle (signed byte); on HP/MP slots probably p% of maximum (Troll +50%, unconfirmed). 26 s 100: cure ailment s. 27 s p: inflict ailment s with p% chance.
- 35 k: menu effect kind $0A62 (1 Warp, 2 Escape/Providence, $22 Smoke ball flee, $24 Reset, $25 Curselifter, $26 Jewel sonar, $21 drain).
- 1F w: set attack attribute (work+14 = $7F:F45C = G39).
- 20 c m: work+16 = chance, +18 = multiplier in 1/16. $85:D1E4: if random(100) < c → defense term ($7F:F4CC) zeroed and multiplier m kept ("Critical Hit"); else multiplier forced to $10 (×1).
- 44 v slot: per-battler byte $14E6[battler*6 + slot] = v (IP guards use 44 02 05, IP "return/mirror" skills 44 03 05).
- Results: Potion 30–40, Hi 80–120, Ex 270–330; Magic jar 8–12 MP, Hi 45–55, Ex 90–110; Charred newt 5–15 HP+MP; stat potions +3–7 permanently (Life maxHP, Spell maxMP, Power STR, Speed AGL, Mind INT, Brave GUT); ciders heal in menu (Pear 8–12 … Apple 150–250) but ATP +10/15/20/25/40% in battle; gourds +30% ATP/INT/MGR; Sleep/Confuse/Freeze balls 100%, Terror ball 50% death; Fire/Ice ball power 200; boomerangs anti-flyer 100/200 all, Ex-boomer 400, Dragon tooth dragon 500; Magic lamp 500 all.
- Weapons: elemental swords 5–10% chance ×2 ignore defense; cursed Deadly sword 50% ×3; Dragon blade 25% ×3; Luck rapier 40% (cursed 100%) ×1; Lucky blade 40%/100% ×1.25; Fortune whip 50% ×⅛. Deadly sword/rod, Fatal pick: dark + death chance (10–25%, cursed 80%). Coma hit/Figgoru hit all enemies with 10% sleep/confusion. Multi sword attacks a second random enemy. Dragon spear = water (not dragon).

### Action flags (work+12; saved copy at $7F:F4E2)
- Spells / magic attacks set $01DC; move_setup and step_setup set $0020.
- $0002 = drain: after all targets are hit, BattleBuildActionAdjustments ($85:CE43 → $85:CF68) sums the target results and applies them negated to the actor (saved work at $7F:F4D6).
- $0008 = magic defense: DEF = target MGR (+$35) + MGR modifier (+$43); otherwise DFP (+$2B) + DFP modifier (+$39).
- $0010 = spell (Mirror bounces it); $0020 = special attack (ailment bit 6 would block it); $0040 = skip row bias; $0080 = ignore defend.
- $0100 = spread over targets ($85:CE94): heals divided by the target count; damage × $85:9E9B[count]/256 = 147, 128, 114, 104 for 2–5 targets (≈ 1/√(count+1)).

### Damage path (partial, $85:D20B)
- P = |power| (work+20), M = multiplier (work+18): A = P×M/16; A += A×random(b)/256 (b = work+22, $20 for scripted moves); D = max(0, A − DEF/2)/2; result = D×(1 − k/256).
- k = work+4 from BattleCalculateActionBias $85:D025: row/group bias ×64, +$60 when the target is defending (+$10 bit 0) unless flag $80.
- Magic attack power (op 22, $85:B96E): P = spell power + caster INT (field 8) + caster INT modifier (field 17); multiplier and DEF/2 as above.
- MP changes ($85:D2CB): loss = |v| + |v|×random(work+28)/256 − DEF/2, no final halving; clamped to the target's current MP ($85:D5D2).
- Still open: how the normal attack builds P from ATP/STR; group/row bias table $97:FE26.

## IP abilities (168)
- $84:8F10 word pointers indexed by id−1 (bank $84); 6-byte header: word0 = effect record id, b2 = palette effect, b5 = IP cost; then zero-terminated name.
- Effect records: $95:F1EF word offsets (141), byte $FF then a battle-VM script (BattleIpAction $81:AB0C runs it at record+1). Several IPs share one record (all 17 "guard" skills → record $4F; all 9 "return/mirror" skills → $5C).

## Capsule monster actions
- $97:F63B word offsets (84 records): word0 = message id, script at +2 (BattleCapsule path $81:AD4B).

## Spells (40)
- $95:FA5B word offsets: name 8 bytes; b8 kind ($81 attack, $82 support, $84 status, $C4 recovery, $48/$08 field); b9 element (1 fire, 2 ice, 3 thunder, 4 water); b10 learner mask (checked by MenuShopSetSpellMemberPose $82:E6BE); b12 MP; b15–16 price; byte 19 onward = battle script (see Battle VM).
- Attack power (op 22 magic attack): Flash 65, Bolt 160, Thunder 480 (thunder); Spark 40, Fireball 120, Firebird 360 (fire); Droplet 50, Vortex 130, Dragon 390 (water); Gale 55, Blizzard 140, Ice Valk 420 (ice); Fry 300, Zap 600 (light).
- Recovery: Strong 20, Stronger 120, Champion full; Rally/Valor revive + 100/full. Status/support: Perish 25% / Destroy 50% death, Drowsy 50% / Coma 80% sleep, Confuse 50%, Deflect 80% magic freeze, Mirror, Dread DFP −20%, Bravery DFP +40%, Courage DFP +60%, Trick ATP +40%, Fake AGL +40%, Shield MGR +40%, Poison/Waken/Release cure poison/sleep/paralysis.
- Absorb (solved 2026-10-27): `op_15 G45, 8; neg G45; set G38, $01DE; set_0A62 $21` = MP change −(caster INT), flags $01DC|$0002 (drain). Target loses INT − MGR/2 (clamped to its MP); caster gains the total. IP Vampire: INT + 30, flags $0002 only → checks DFP instead of MGR.

## Enemies (224)
- $96:85C0 word offsets (relative to $85C0). Name 13; +13 level, +14 ?, +15 sprite, +16 palette, +17 HP, +19 MP, +21 ATP, +23 DFP, +25..28 AGL INT GUT MGR (bytes, doubled when loaded by $81:FC0B), +29 EXP, +31 gold, +33 tags until 0 (3 bytes each): 03 drop (item = w&1FF, chance% = w>>9), 07 turn-script offset, 08 reaction-script offset.
- Drop roll $81:FB1A: random(100) < chance AND random(4)==1 → real rate = listed/4; first drop per battle kept.
- In NO encounter table (dungeon, region, sea, cave, scripted): Kraken, King Hidora, Gades $DE (10000 HP, unused 4th Gades), Goblin $CE, Goblin Mage $CF, Slave $D0, Follower $D1, Groupie $D2 (last five may be script-started).

### Ailments (solved 2026-10-27)
- Ailment slot s ($85:9F0F → work+92+4s; +0 inflict chance written by op 27, +2 cure chance by op 26) = bit s of battler status byte +$0F (BattleBuildRequestedEffectMasks $85:D82C).
- Bits: 0 poison, 1 magic freeze, 2 death/gone (also set by escaping), 3 paralysis, 4 confusion, 5 sleep, 6 special-attack barrier (unused), 7 Mirror.
- Bit 1 = magic freeze: BattleSpellAction $81:A996 fails with "Magic frozen." ($85:F1FE); battle menu $81:CE1C blocks the Magic command. Inflicted by Deflect (80%), IP Magic remover (100%), Seirein (80%), Tank (50%), capsule action 46; cured by IP Free magic / Recovery / Revival sleep and capsule actions 15/16.
- Bit 6: only reader is $85:D0FC. If incoming action flags have $20 and target has bit 6, the action is turned aside (dispatch code 2), the special-attack counterpart of Mirror (bit 7 vs spell flag $10 → code 3, $85:D0E6). Nothing sets or cures it; no icon (icon mask $3B at $85:887A) and no wear-off message → unused.
- Wear-off: BattleResolveRecoverableStatuses $85:8F8A: sleep, confusion, paralysis each clear on random(7)==4 (1 in 7 per turn) (phrase table $85:EFD3: cured, wakes up, escapes, normalizes, defends, can move, loses mirror). Mirror counts down battler slot +6 ($85:90F4).
- Poison tick $81:C67B: damage based on HP/20 with a random term (not fully traced).

## Battle script VM / enemy AI (solved 2026-10-26)
Tools: tools/battledec.py (raw decompiler, `python3 battledec.py <hex ids>`), tools/enemy_ai.py → plain English (docs/enemy_ai.txt; renders ops 24–27 as ailment/stat effects). tools/item_effects.py `describe()` also tracks stat reads/arith into G42/G45 and G38 flags (drain). Atlas has an "Enemy AI" tab plus weak/resist tags on the Enemies tab.
- VM $85:B452, opcode table $85:B483 (93 ops). Loop returns to $85:B45E; $85:B473/$85:B476 end. Cursor DP $BB (24-bit). Readers: $85:BFBF byte, $85:BFCA word, $85:BFD8 value (bit15 = variable), $85:B551 jump (target = $0A42 base + word).
- Variables: byte with bit7 = local counter n (per battler, base+$15+2n); else global $7F:F40E+2n. G35 reflect state, G38 action flags, G39 attack attribute ($7F:F45C), G42 HP change, G45 MP change.
- Enemy scripts: tag 07 turn / 08 reaction offsets relative to the record start (also the jump base). Op $42 n calls shared routine n from $96:FADD (base switches), $43 returns.
- Key ops: 05 bJ chance (random byte < n → n/256); 06–0B bvJ compare = ≠ > < ≥ ≤; 0C–10 set/add/sub/mul/div; 11 random; 1A neg; 13 bb read target stat, 15/4E bb read actor stat; 21 wvb special attack (attribute, power) → action 5; 22 wvb magic attack; 24–27 effect commands (see Items); 28 attack; 29 defend; 2A group; 2B w item; 2C b cast spell, then 04 J "if not possible"; 53 b cast without MP; 2D b call for help; 1E b announce message (table $85:F2D7, 138 entries, string at ptr+1); 32 select target (sub 1 random hero, 4 whole side, 5 all on that side, 6 self, 7 random ally, 8 random party member, 2/3 positional +3 bytes); 41 wait; 3E capsule action; 01 act now. Small ops: 1D clear action work, 51/52 set work+130 bits 2/4, 58/59 clear party/enemy modifiers, 5B clear $7FF8A5, 5C set battle_action_alternate $FF.
- Stat fields ($85:9E47): 0 HP, 1 MP, 2 maxHP, 3 maxMP, 4–10 ATP DFP STR AGL INT GUT MGR (+$29..+$35), 11 level, 12 +$0E, 13–19 battle modifiers for ATP..MGR (+$37..+$43), 20 status.
- Action codes ($81:A867): 0 skip, 1 attack, 2 spell, 3 item, 4 defend, 5 scripted move, 6 collective, 8 IP, 9 uncosted spell, 10 continue, 11 capsule, 12 wait, 13 alt attack, 14 wait long, 15 followup.
- Attribute bits: $0002 fire, $0004 water, $0010 light, $0020 dark, $0400 ice, $0800 thunder; confirmed by weapons: $0040 blunt (maces, rods, Frypan; shells/crabs/beetles/golems weak — previously called earth), $0080 anti-flyer (Flying blow/ax, boomerangs), $0100 dragon/beast (Lizard blow, Dragon ring, Dragon tooth), $0200 insect (Insect crush); $1000 ground (flyers immune; IP Groundshock/Mega quake use it); $2000 added by Sea ring, no enemy script tests it.
- Weaknesses are reaction-script routine calls, not a record field: weak ×2: 0 fire, 1 thunder, 2 water, 3 ice, 4 $0080, 5 light, 12 $0100, 13 dark, 15 blunt, 16 $0200; resist ½: 6 fire, 7 thunder, 8 water, 9 ice, 10 light, 11 physical, 14 dark, 20 all elements, 23 blunt; 18 healing hurts (undead, 21 enemies); 21/25 immune, 22 absorb, 24 limited resist (mask in counter 1); 36 no damage; 40 evade chance; 17 reset temporaries.
- Counts: 204 turn scripts, 187 reaction; all 391 + 41 shared routines decode with 0 errors. Most common: weak fire 78, resists water 42, weak light 42, anti-flyer 39.
- Example: Daos ($C9) uses counters 5/6 as timers: Terror wave (600, all heroes), Dark reflector, Dark fry (800 dark), then Thunder/Firebird/Ice Valk/Dragon rotation.

## Shops
- $97:EE9F word offsets: title byte, flags word; lists per bit: 02/04/08/10 item word lists (0-term), 20 spell byte list (FF-term), 01 = resells sold items (RAM list), 80 = sell option. Opened by script op $18 (shop id → DP $30).
- Prices: AdjustPurchasePrice $82:9918 — selling = half rounded up; buying halved if Selan (party id 1) has Engage ring ($167) in ring slot ($0CD9 = record $0C6B + $6E).

## Encounters
- Formations $97:BE93 + id*8 (enemy ids, FF none). Built by BattleGenerateEncounterRecord $81:839F: first two may swap, rest shuffled, max 3 types, first always present; count = rand(n)+rand(n−1)+1, n = $85:9EA1[party size] = 1,2,3,4,4.
- Map monsters: FieldGenerateEncounter $81:8351, A = actor−$50 (<$20): formation = byte at $97:B9AC + word[$97:B9AC + map*2] + slot. Map $F0 (Ancient Cave) uses RAM $7F:F966.
- Special/scripted battles $97:C53D word offsets: 6 ids, 6×(x,y), 1 byte, bonus EXP word, bonus gold word, 3 bytes. Only Pierre/Daniele have bonus (2000/3000).
- Script op $74 writes $7FF8A0 = battle background.

## Overworld regions (solved 2026-10-26)
- Region grid = resource $0193 (4096 bytes, 64×64, one cell per 4×4 tiles), DecompressResource ($80:8E9D, resource table $A7:8000) into $7F:E000 at $86:CD2E — only when world_map_resource_id $09EA == 0 (surface). $09EA ≠ 0 also disables random battles (seafloor has none).
- Lookup $86:9D0B: index (y/4)*64 + x/4 → region; record $97:C493 + region*10 = 5×(formation, weight).
- Only 17 real records (0–16): $97:C53D (special table) begins 170 bytes after $97:C493. Region 17 (Gratze area, normally unreachable) reads the special-battle pointer table as encounter data (decodes as bats/mushrooms). Table "regions" 18+ are not real.
- Entrances: map $00 header (via $CF:FCBC) section +6, 9-byte records [id, x1, y1, x2, y2, flags, dest_x, dest_y, dest_map], $FF-terminated, 79 records.
- Region → places: 1 Elcid; 2 Sundletan/Lake Cave/Foomy Woods; 3 Alunze; 4 Tanbel; 5 Clamento/Ruby Cave/Tanbel SE Tower; 6 Parcelyte/Treasure Sword Shrine/North Lighthouse; 7 Gordovan/Merix/Cave Bridge; 8 Bound Kingdom/Ancient Tower/North Dungeon; 9 Aleyn/Gruberik/Narcysus/Karlloon/Phantom Tree Mtn/Tower of Sacrifice/Ancient Cave; 10 Treadool/Flower Mtn; 11 Dankirk/Auralio/Forfeit Island; 12 Ferim/Agurio/Northeast Tower; 13 Portravia/Treble/Pico Forest/Mtn of No Return; 14 Barnan/Durale/Eserikto/Divine Shrine/Shrine of Vengeance/Tower of Truth; 15 Chaed/Narvick/Dragon Mtn/Capsule Monsters Shrine; 16 scattered isolated patches (Secret Skills Cave area etc.: dragons, Behemoth, Pug); 17 Gratze.
- Resource extractor: Lufia2Decomp tools/lufia2_resource.c (built at build/lufia2-resource; 680 resources).

## Sea (ship) encounters (solved 2026-10-26)
- WorldMapActivateVehicle $86:A1DA sets $09E1=$FF; WorldMapCheckEncounter then uses ChooseSpecialEncounter instead of the region grid.
- Extra gate: random(100) < 40 else no battle. Formation = $86:9DC7[random(6) + k], k = (Maxim level $0BBB − 30, floored 0, capped 18 if ≥20) >> 1 → 0..9.
- List (15 formations): Seahorse/King Frog ×4, Moray/Evil Fish, Perch, Bolt Fish/Evil Fish/Perch, Angler fish/Bolt Fish, Unicorn/Angler fish, She Viper/Unicorn, Killer Whale/Bolt Fish, Merman/She Viper, White Whale/Killer Whale, Current/Merman, Aqualoi/Merman. First Maxim level: Unicorn 36, Killer Whale 40, Merman 42, White Whale 44, Aqualoi 48.

## Ancient Cave (solved 2026-10-26)
- Floor counter $7F:E696: 0 on cave entry ($84:87AA), set to 1 on entering map $F0 ($83:B264), incremented after each floor is generated ($83:9F39); label shows counter−1 = the generated floor's number. Floors B1–B99 generated; final floor is fixed map $F1.
- Monster placement CavePlaceRandomObject $83:9A1C (during generation sub $83:9013): formation = $94:D95C[(floor−1)*2 + random(6)] → stored $7F:F966[slot] → FieldGenerateEncounter map $F0 path → $97:BE93 formations. Table is 202 bytes (B99 uses entries 196–201).
- 158 distinct enemies; B1 Lizard/Red Jelly/Moth/Mushroom/Bat/Spider → B87–B99 Gold/Silver/Copper Dragon, Dark Summoner. Cave-only incl. Flame/Wind/Earth/Well Genie, Archfiend, Hades, Ice Roge, Great Coca, Gold Dragon, Ghost Ship.
- Side note: from floor 21, random(60) < floor sets special_reward_state and object $022D ($83:9121) — not yet identified.
- Random draws: CaveDrawRandomBelow $83:9E1B = n × random >> 8 (0..n−1).

## Map headers
- $CF:FCBC + map*3 → raw block copied to $7E:F000 by FieldLoadMapHeader $83:B5D3 (not compressed). Word0 = length, then 21 section offsets; section +6 = 9-byte area/entrance rectangles.

## Next
- Damage formula: normal attack power from ATP/STR; row/group bias table $97:FE26. IP skill and capsule action effects into the Atlas (scripts decode cleanly). Poison tick formula; menu-use path for item heals; op 25 on HP/MP; Bunny sword step_setup and RAN-RAN step dance list; cave special object $022D.
