# Lufia II — capsule monster AI (2026-10-27)

Tool: tools/capsule_ai.py → docs/capsule_ai.txt, build/capsule_ai.json. Verified the flee rule by running the real turn scripts in tools/cpu65816.py.

## Data
- Form records: $97:DCB8 word offsets, index = capsule×5 + form−1 (capsules in order Jelze, Flash, Gusto, Zeppy, Darbi, Sully, Blaze). +$00 name; +$0D form; +$0E capsule class bit (Jelze 0, Flash 1, Gusto 2, Zeppy 4, Darbi 8, Sully $10, Blaze $20); +$0F..$11 innate abilities, +$12..$14 learnable abilities (ability-name/message ids, 0 = none); +$15 HP, +$16/+$17 (copied to $1165/$1167), +$18 STR, +$19 AGL, +$1A INT, +$1B GUT, +$1C MGR (base); +$1D..+$22 growth ids for HP STR AGL INT GUT MGR; +$25 turn script, +$27 reaction script (battle VM, offsets from the record).
- Stat at level L = base + Σ(j=1..L−1) table[$A6:F420 + growth×8 + j>>4] / 16; a band (j>>4) equal to the form number counts ½, later bands ¼ ($82:D31C).
- Actions: $97:F63B word offsets (84); byte 0 = name/message id ($A5:DF00 table), byte 1 = flash colour, script at +2. VM op $3E n = capsule action n (action code 11, BattleCapsuleAction $81:AD3B). Messages repeat ("Fang attack", "Head Butt", "Mega trident", "Dash", "Tackle", "Iron claw", "Terminate" exist twice with different effects).
- Learned abilities: one 16-bit word per capsule at $11CA (3 bits per form). VM op $3F b tests bit b (1–3 = learnable slot 1–3). After every won battle (results screen, $81:DCBE) CapsuleTryLearn: 1/8 chance, then a random slot 0–2; learned if that slot has an ability not yet learned (≈1/24 per battle per learnable).

## How a capsule chooses (turn script pattern, all 35 forms)
1. Forms 1–4: courage check (shared routine 37): flee (action 6 = "escapes", leaves the battle) if % of max HP lost ≥ GUT×25/K, K = 17, 35, 50, 60 for forms 1–4. Form 5 never flees.
2. Fixed chance of a plain attack, then (some capsules) a fixed chance to defend.
3. Otherwise routine 38 picks a random starting slot 1–3 and tries up to 3 slots in turn (routine 39); each slot has its own skip chance and may require a learned bit; an upgrade replaces the innate move once learned. If all 3 tries skip → plain attack.
4. Reaction script: shared routine 17 makes every capsule immune to poison, magic freeze, paralysis, confusion and sleep (not death), plus its element traits.

## Per form (probabilities when not fleeing; "learned" = all its learnable abilities known)

| Form | Flees when HP lost ≥ (Lv1 / Lv20) | Nothing learned | All learned |
|---|---|---|---|
| Jelze 1 Foomy S | 30% / never | attack 55%, Foomy punch 35%, defend 11% | — |
| Jelze 2 Foomy M | 23% / 90% | attack 60%, Foomy punch 31%, defend 9% | attack 53%, Foomy punch 27%, Head Butt 11%, defend 9% |
| Jelze 3 Foomy L | 22% / 69% | attack 58%, Foomy punch 23%, Head Butt 11%, defend 8% | attack 54%, Foomy punch 18%, Tackle 10%, Head Butt 10%, defend 8% |
| Jelze 4 Foomy H | 23% / 62% | attack 61%, Foomy punch 15%, Tackle 9%, Head Butt 8%, defend 7% | attack 61%, Mega punch 15%, Tackle 9%, Head Butt 8%, defend 7% |
| Jelze 5 Gold Fox | never | attack 71%, Fang attack 16%, Bubble blow 7%, defend 6% | attack 68%, Fang attack 12%, Tail smash 7%, Bubble blow 7%, defend 6% |
| Flash 1 Shaggy | 33% / never | attack 57%, Spear revive 38%, defend 5% | — |
| Flash 2 Sprite | 25% / 92% | attack 64%, Healing kiss 30%, defend 5% | attack 51%, Healing kiss 26%, Wink 17%, defend 5% |
| Flash 3 Cupid | 24% / 70% | attack 54%, Sacred song 22%, Restoration 19%, defend 5% | attack 46%, Sacred song 17%, Restoration 17%, Thunderbolt 15%, defend 5% |
| Flash 4 Twinkle | 25% / 64% | attack 45%, Thunderbolt 17%, Sacred song 17%, Restoration 17%, defend 5% | attack 48%, Bolt attack 16%, Holy energy 16%, Purification 16%, defend 5% |
| Flash 5 Unicorn | never | attack 59%, Antler stab 21%, Dash 16%, defend 4% | attack 59%, Dash 13%, Holy thunder 13%, Healing aura 11%, defend 4% |
| Gusto 1 Hard Hat | 7% / 69% | attack 59%, Fang attack 41% | — |
| Gusto 2 Bluebird | 7% / 40% | attack 54%, Beak bash 31%, Iron claw 14% | attack 49%, Beak bash 24%, Spiral wave 13%, Iron claw 13% |
| Gusto 3 Winged Horse | 8% / 31% | attack 56%, Air attack 25%, Finale 19% | attack 53%, Air attack 19%, Finale 17%, Electro bolt 11% |
| Gusto 4 Green Titan | 9% / 28% | attack 72%, Iron fist 15%, Twister 13% | attack 66%, Iron fist 12%, Twister 12%, Sonic blast 10% |
| Gusto 5 Sky Dragon | never | attack 71%, Electro bolt 10%, Tornado blow 10%, Dragon fang 10% | attack 72%, Dragon fang 10%, Electro bolt 10%, Cyclone wave 9% |
| Zeppy 1 Red Fish | 13% / 92% | attack 59%, Fish kick 41% | attack 49%, Fish kick 36%, Bubble blast 15% |
| Zeppy 2 Toadie | 12% / 55% | attack 48%, Frog kick 24%, Frog song 15%, Iron trident 13% | attack 48%, Frog kick 24%, Frog song 15%, Mega trident 13% |
| Zeppy 3 Sea Giant | 12% / 42% | attack 55%, Energy wave 21%, Iron trident 13%, Hail attack 11% | attack 55%, Energy wave 21%, Mega trident 13%, Hail attack 11% |
| Zeppy 4 Blue Titan | 13% / 38% | attack 72%, Thunderblast 15%, Thunder fist 13% | attack 72%, Thunderblast 15%, Power fist 13% |
| Zeppy 5 Fish Head | never | attack 66%, Fish kick 23%, Dive attack 11% | attack 60%, Magic freeze 16%, Hyper kick 14%, Diving claw 9% |
| Darbi 1 Myconido | 4% / 35% | attack 59%, Trancemaker 41% | attack 48%, Trancemaker 36%, Shriek 16% |
| Darbi 2 Wolfman | 5% / 21% | Wolf fang 42%, attack 39%, Wolf punch 19% | Wolf fang 42%, attack 39%, Sizzle smash 19% |
| Darbi 3 Mini Imp | 5% / 17% | attack 37%, Dark flame 21%, Destruction 21%, Mega trident 21% | attack 37%, Terminate 21%, Destruction 21%, Mega trident 21% |
| Darbi 4 Big Imp | 6% / 15% | attack 37%, Dark thunder 21%, Sizzle smash 21%, Terminate 21% | attack 37%, Evil aura 21%, Sizzle smash 21%, Terminate 21% |
| Darbi 5 Red Dragon | never | attack 77%, Dash 13%, Dragon blast 11% | attack 72%, Dash 10%, Dragon blast 10%, Eliminator 9% |
| Sully 1 Raddisher | 16% / never | attack 53%, defend 24%, Radish kick 23% | — |
| Sully 2 Red Cap | 15% / 74% | attack 54%, defend 32%, Perish punch 14% | attack 46%, defend 32%, Perish punch 13%, Glow knuckle 10% |
| Sully 3 Giant | 15% / 57% | attack 42%, defend 32%, Fist 12%, Shakedown 7%, Heel drop 7% | attack 42%, defend 32%, Fist 12%, Battle anger 7%, Heel drop 7% |
| Sully 4 Stonehead | 17% / 51% | attack 49%, defend 32%, Battle anger 11%, Head Butt 9% | attack 45%, defend 32%, Battle anger 8%, Head Butt 8%, Stone crush 7% |
| Sully 5 Centaur | never | attack 45%, defend 32%, Battle bow 16%, Hammer punch 7% | attack 43%, defend 32%, Battle bow 12%, Tackle 7%, Hammer punch 7% |
| Blaze 1 Armor Dog | 8% / 70% | attack 59%, Tail 41% | — |
| Blaze 2 Winged Lion | 8% / 41% | attack 64%, Tail 36% | attack 55%, Tail 32%, Burning fang 13% |
| Blaze 3 Wing Lizard | 10% / 33% | attack 60%, Fang attack 27%, Iron claw 13% | attack 56%, Fang attack 21%, Flame breath 12%, Iron claw 12% |
| Blaze 4 Blaze Dragon | 13% / 32% | attack 65%, Flame breath 12%, Flame punch 12%, Burning fang 12% | attack 65%, Terminate 12%, Flame punch 12%, Burning fang 12% |
| Blaze 5 Firebird | never | attack 64%, Burning rain 20%, Tailspin 17% | attack 64%, Burning rain 13%, Tailspin 12%, Inferno 11% |

## Actions (capsule side: "enemies" = the monsters)

- 0 Foomy punch — one enemy: special attack physical, power ATP×2
- 1 Mega punch — one enemy: 2×; special attack physical, power ATP×2; special attack physical, power ATP×2
- 2 Fang attack — one enemy: special attack physical, power ATP×3
- 3 Tail smash — one enemy: special attack physical, power ATP×9
- 4 Head Butt — one enemy: physical attack, defense ignored 100%, ×3
- 5 Tackle — all enemies: physical attack, defense ignored 100%, ×2
- 6 Bubble blow — all enemies: DFP -80% for the battle
- 7 Antler stab — one enemy: special attack light, power ATP×2
- 8 Dash — all enemies: light attack, defense ignored 100%, ×2
- 9 Spear revive — random ally: HP +20
- 10 Healing kiss — random ally: HP +60
- 11 Sacred song — random ally: HP +140
- 12 Holy energy — whole party: HP +140
- 13 Healing aura — whole party: HP +180
- 14 Wink — random ally: ATP +80% for the battle
- 15 Restoration — random ally: cure poison; cure magic freeze; cure paralysis; cure confusion; cure sleep
- 16 Purification — whole party: cure poison; cure magic freeze; cure paralysis; cure confusion; cure sleep
- 17 Holy thunder — one enemy: magic attack light, power INT×4 + INT
- 18 Thunderbolt — one enemy: magic attack light, power INT×2 + INT
- 19 Bolt attack — all enemies: magic attack light, power INT×4 + INT
- 20 Fang attack — one enemy: special attack wind*, power ATP×2
- 21 Beak bash — one enemy: special attack wind*, power ATP×2
- 22 Finale — one enemy: special attack wind*, power ATP×2
- 23 Dragon fang — one enemy: wind* attack, defense ignored 100%, ×3.5
- 24 Iron claw — one enemy: wind* attack, defense ignored 100%, ×3
- 25 Iron fist — one enemy: wind* attack, defense ignored 100%, ×3
- 26 Air attack — all enemies: wind* attack, defense ignored 100%, ×2
- 27 Twister — all enemies: wind* attack, defense ignored 100%, ×2
- 28 Spiral wave — all enemies: magic attack wind*, power INT×4 + INT
- 29 Tornado blow — all enemies: magic attack wind*, power INT×2 + INT
- 30 Electro bolt — all enemies: magic attack wind*, power INT×2 + INT
- 31 Cyclone wave — all enemies: magic attack wind*, power INT×4 + INT
- 32 Sonic blast — all enemies: magic attack wind*, power INT×8 + INT
- 33 Fish kick — one enemy: special attack water, power ATP×3
- 34 Hyper kick — one enemy: special attack water, power ATP×5
- 35 Frog kick — one enemy: special attack water, power ATP×2
- 36 Iron trident — one enemy: water attack, defense ignored 100%, ×2
- 37 Thunder fist — one enemy: water attack, defense ignored 100%, ×2
- 38 Power fist — one enemy: 2×; water attack, defense ignored 100%, ×2
- 39 Mega trident — all enemies: water attack, defense ignored 100%, ×2
- 40 Dive attack — all enemies: water attack, defense ignored 100%, ×2
- 41 Diving claw — all enemies: water attack, defense ignored 100%, ×3
- 42 Bubble blast — all enemies: magic attack water, power INT×2 + INT
- 43 Hail attack — all enemies: magic attack water, power INT×4 + INT
- 44 Thunderblast — all enemies: magic attack water, power INT×4 + INT
- 45 Energy wave — whole party: ATP +80% for the battle
- 46 Magic freeze — one enemy: 100% magic freeze
- 47 Frog song — all enemies: DFP -80% for the battle
- 48 Wolf fang — one enemy: special attack dark, power ATP×2; 36% poison
- 49 Wolf punch — one enemy: dark attack, defense ignored 100%, ×2
- 50 Sizzle smash — one enemy: dark attack, defense ignored 100%, ×3
- 51 Mega trident — all enemies: dark attack, defense ignored 100%, ×2
- 52 Dash — all enemies: dark attack, defense ignored 100%, ×3
- 53 Shriek — whole party: cure confusion
- 54 Trancemaker — all enemies: 100% confusion
- 55 Destruction — one enemy: 90% death
- 56 Eliminator — all enemies: 90% death
- 57 Dark flame — all enemies: magic attack dark, power INT×2 + INT
- 58 Dark thunder — all enemies: magic attack dark, power INT×2 + INT
- 59 Terminate — all enemies: magic attack dark, power INT×4 + INT
- 60 Evil aura — all enemies: magic attack dark, power INT×6 + INT
- 61 Dragon blast — all enemies: magic attack dark, power INT×4 + INT
- 62 Fist — one enemy: special attack earth*, power ATP×2; 36% sleep
- 63 Radish kick — one enemy: special attack earth*, power ATP×2
- 64 Battle bow — all enemies: special attack earth*, power ATP×2
- 65 Perish punch — one enemy: earth* attack, defense ignored 100%, ×1.5; 60% death
- 66 Glow knuckle — one enemy: earth* attack, defense ignored 100%, ×3
- 67 Heel drop — one enemy: earth* attack, defense ignored 100%, ×2.5
- 68 Hammer punch — one enemy: earth* attack, defense ignored 100%, ×2; 60% paralysis
- 69 Head Butt — one enemy: earth* attack, defense ignored 100%, ×3.5
- 70 Stone crush — all enemies: earth* attack, defense ignored 100%, ×3
- 71 Tackle — all enemies: earth* attack, defense ignored 100%, ×3; 60% paralysis
- 72 Shakedown — all enemies: magic attack earth*, power (ATP+INT)×2 + INT
- 73 Battle anger — all enemies: magic attack earth*, power (ATP+INT)×4 + INT
- 74 Tail — one enemy: special attack fire, power ATP×2
- 75 Fang attack — one enemy: special attack fire, power ATP×2
- 76 Flame punch — one enemy: fire attack, defense ignored 100%, ×1.5
- 77 Burning fang — one enemy: fire attack, defense ignored 100%, ×3
- 78 Iron claw — one enemy: fire attack, defense ignored 100%, ×2
- 79 Tailspin — one enemy: fire attack, defense ignored 100%, ×3.5
- 80 Flame breath — all enemies: magic attack fire, power INT×2 + INT
- 81 Burning rain — all enemies: magic attack fire, power INT×2 + INT
- 82 Terminate — all enemies: magic attack fire, power INT×4 + INT
- 83 Inferno — all enemies: magic attack fire, power INT×6 + INT

Notes: "special attack" (VM op $21) and "magic attack" (op $22) go through the normal damage formula (magic adds INT again); "defense ignored 100%, ×m" = op $20 with 100% chance, so the target's defense term is dropped and damage ×m. *wind ($0001) and *earth ($0008) are the attribute bits Gusto and Sully use; in the original no enemy is weak to them, only the 8 golems with "resists all elements" halve them. Mod v0.3: shared routine 4 (39 flyers) also doubles wind; new routine 27 (resist thunder + double earth) for Wind Genie, Salamander, Bolt Fish, Specter, High Hidora, Silver Dragon, Tengu. Shared routines 22 and 27–32 were unused by every enemy, capsule, item, IP and spell script.

## Findings
- Winged Horse (Gusto form 3): record says Finale + Electro bolt innate, Air attack learnable; its AI uses Finale + Air attack from the start and Electro bolt only once learned (slot 3). Only menu/AI mismatch among the 35 forms. FIXED in the mod (v0.3): record bytes $97:E2E6 = 26, $97:E2EB = 30 (menu now matches the AI).
- Firebird (Blaze form 5): the "tried 3 slots" exit jumps back into the loop instead of to the plain attack (word at $97:EE70 = $0044, the plain attack is $006C), so after the 64% attack roll fails it always ends up using an ability. The only form with this. Kept as is in the mod (user decision 2026-10-28): it is a perk of the final form.
- Darbi has very low GUT (3 → 15 base): Myconido flees after losing 4% HP at Lv1; Big Imp still flees at 16% lost at Lv20. Mod v0.3: Darbi K lowered 17/35/50/60 → 9/20/30/36 (words at $97:E73D/E7C0/E847/E8DB), about twice as brave (Lv20: 66/37/28/26% lost). Other capsules at Lv20 average 112/66/51/46%.
- Gusto/Zeppy/Darbi/Blaze never defend; Sully defends 24–32% of turns.
- Misleading names: Thunder fist/Thunderblast are water (Zeppy), Electro bolt is wind, Spear revive heals 20 HP and revives nobody, Destruction/Eliminator are 90% instant death.

