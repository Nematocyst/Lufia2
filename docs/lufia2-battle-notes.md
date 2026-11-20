# Lufia II (US) — battle mechanics notes (2026-10-27)

Companion to lufia2-data-formats.md (formats, VM, effect commands). This file collects per-feature findings.

## Attack setup ops
- Op 37 ($85:BCED, "normal attack"): action code 1, work+8 = 0; if power slot (work+20) is still 0 → power = −(ATP field 4 + ATP modifier field 13 + work+124); random bonus byte work+22 = $40 (+0–25%). Default weapon script when a weapon has no word-2 script: $85:EF26 (party) / $85:EF24 (enemy) = `37 00` (op 37, end).
- Op 23 w ($85:B9B8, renamed fixed_attack, was step_setup): power = −w (a raw word, no stat added), bonus $20 (+0–12.5%), flags $0020 (special attack). Loads A=5 but never stores it, so the action code stays as it was.
- Op 3C ($85:BD2C): power slot += caster INT (field 8). Used by Strong/Stronger/Champion → heal = base + INT.
- Op 3D b ($85:BD54): BattlePlayEffect b ($81:895E, effect scripts via $95:8000 table) — animation only.
- Op 4C b: BattlePopups b. Op 4F: end with battle_action_disabled = $FF (cancels the action).
- Op 55 b v ($85:B71D): variable b = b / v (24-bit divide, SystemDivide24ByByte).

## Shared power routines used by IP skills
- Routine 33: L0 = user ATP × 3 / 2.
- Routine 35: L0 = user ATP + ATP modifier (same base as a normal attack).
- Routine 34: G42 (HP change) = −(L0 × 2 + target DFP / 2). Called after `op_13 L0, 0` (target's current HP) and `op_55 L0, n`, so damage after defense ≈ target HP / n. Devastation and Ax attack (record $13) n = 8, Battlecry 6, Battle fury 4, Fatal blow 2.

## Attack flow (BattleAttackAction $81:A8A8)
- work+8 = weapon item id → LoadItemRecord → run weapon word-2 script (record_buffer $0B91), else the default script above.
- Then the attacker's ring slot (+$6E) item word-2 script also runs (Undead/Sea/Dragon rings add attribute bits).
- Item record buffer: $0B84 = 9 fixed bytes, word k at $0B8D + 2k (word 0 $0B8D menu use, word 1 $0B8F battle use, word 2 $0B91 attack script, word 3 $0B93 defensive script).

## Bunny sword ($198)
- ATP +500, Selan/Artea/Tia, IP Battle fury. Word-2 script: `23 7800` only = fixed_attack 120, no op 37.
- Normal hits ignore ATP: A = 120 × (1 + random(32)/256) → 120–134; damage ≈ (A − DEF/2)/2, max ≈ 67 before weaknesses. The ATP 500 still counts wherever ATP is read directly (e.g. routine 33/35 IP skills).

## RAN-RAN step ($1D0)
- No stats, all characters, 5000 G. Word-2 script: select 6, select 5 (user's whole party); op 4C 3 (popup); 86 × op 3D with effect ids 00–0E (even), 12–35, 60–6F, 80–99; op 4F.
- 12–35 = spell animations for spells 0–35 (spell animation id = spell id + $12, BattleSpellAction $81:A9BB), Flash … Release; 80–99 and 60–6F match ids used by IP/monster specials (op 5A).
- RAN-RAN is the only script in the ROM using op 3D. Op 4F cancels the action → no damage, no effect. Matches the Reddit claim (no damage, cycles through attack animations).

## IP skills copied from enemy moves (2026-10-27)
Tool: tools/ipmatch.py (matches IP names to enemy announce messages, prints the enemy move block and the IP script). 36 IP names match an enemy move. Teaching item in brackets; most are dropped by that monster.
- Faithful copies (same effect type, element and targets; IP power usually scales with user stats, enemy power is fixed):
  - Do-re-mi [Song rock] = Seirein: all enemies, 50% confusion. Exact.
  - Ninja [Mysto jewel] = Jurahan: attack + 60% instant death. Exact chance.
  - Vampire [Bat rock] = Red Bat/Mosquito/Vampire/Nosferato: MP drain = INT; IP adds +30 and uses DFP instead of MGR (flags 2 vs 478).
  - Magic all-target: Incendiary [Flame jewel] fire 120+INT (enemies 200/500 fixed); Magma blast [Magma rock] fire 400+INT (Magma Gorem 300); Voltage bolt [Thundo jewel] thunder 160+INT (Wind Genie 560); Tidal wave [Tidal jewel] water 140+INT (Current 380); Gloomy [Evil jewel] dark 160+INT (Archfiend 240); Flash [Light jewel] light 600+INT (Wispy 60).
  - Torrent [Aqua sword/Water spear/Zirco ax] water all, ATP×1.5 (Aqualoi 300, Kraken 400); Ten-legger [Kraken rock] water all ATP×1.5 (Kraken 500 single); Buster attack [Camu jewel] fire all ATP×1.5 (Camu 120).
  - Diamond dust [Silver eye] ice(+water) all, STR+700 (Silver Dragon ice 700 all).
  - Single physical, ATP-scaled vs fixed: Bite [Lion fang] ATP×2 (Lion, Gargoyle, T Rex, … 90–450); Frenzy [Horse rock] ATP×1.5; Dive [Eagle rock] ATP×2 anti-flyer (Eagle/Hawk 50, Armour Dait 300); Head attack [Pumkin jewel] ATP×2 blunt (Pumpkin/Mad Head 200/280); Iron kick [Deadly armor] blunt 400 (Deadly Armor 240); Samurai [Samu jewel] (ATP+mod)×2, 20% ×2 crit (Samurai 320, Dark Warrior 340, 20%/40% crit at ×⅛).
  - Scissor slash [Cancer rock] two hits (Cancer 2×142, Red Lobster 2×92; IP two normal attacks).
  - Spiderweb [Spido jewel] AGL −80% all (Tarantula: 30 dmg + AGL −50% single).
  - Sleep stinger [Coma hit, Sleep rod] attack + 100% sleep (Camu: fire 80 + 40% sleep).
- Name only (different mechanics):
  - Ax attack [Gorgon rock], Devastation [Deadly rod]: IP = target HP/8 (routine 34); Minataurus 400 physical, Gades dark 360/1100.
  - Triple attack [Hidora rock]: IP 3 normal attacks; Hidoras/Orky one hit 400–600.
  - Repeat attack (no item): IP 4 attacks on random enemies; Deadly Sword 120 to all.
  - Immobilize [Bee rock]: IP all, 60% paralysis + attack; Armor Bee/Needle Lizard/Stinger deal plain damage to all, no paralysis.
  - Dash [Uni jewel]: IP normal attack with 100% defense-ignoring ×2; enemies fixed 55–480.
  - Dark force [Gloom jewel]: IP all, 40% death + attack; Demise 285 + 80% death single, Rogue Shape dark 300.
  - Groundshock [Earth jewel]: IP ground ($1000) magic 240+INT all; Earth Genie physical 520 all, Behemoth 300.
  - Mega quake [Catfish jwl.]: IP ground magic 140+INT all; Big Catfish water 65 single.
  - Tail attack [Snake rock]: IP blunt magic 200+INT all; Basilisk 400 physical single, Ramia normal attack.
  - Twister [Twist jewel]: IP ice magic 140+INT all (shares Frost record $75); Winger/Serfaco physical 160/320 all.
  - Frost [Water jewel]: IP ice magic 140+INT all; Brinz Lizard ice 280 single, Well Genie water 520 all.
  - Gloomsplash [Black eye]: IP fire+dark ($0022) STR+800 all; Black Dragon dark 400 single.
  - Stardust blow [Gold eye]: IP thunder+light ($0810) STR+1000 all; Gold Dragon physical 800 all.
- Items with no enemy drop: Black eye, Kraken rock, Light jewel, Snake rock, Tidal jewel, Uni jewel, Water jewel.

## Defensive equipment scripts (word 3) — not yet on the Atlas
- Run by BattleRunEquipmentScripts $85:DA11 for a party member being hit (all 6 equipment slots), the party-side equivalent of an enemy reaction script.
- Patterns: `set G78..G88, 0` = ailment immunity (G78 + 2s = inflict-chance slot s: 78 poison, 80 magic freeze, 82 death, 84 paralysis, 86 confusion, 88 sleep); routine 24/25/26 with L1 mask = element resist/immune (e.g. Flame shield fire, Plati shield ice); `div G42, 2` = halve damage; Mega shield/Gauntlet physical cases; Seethru cape/silk call routine 17.
- goto_if_zero $02/$03 tests appear to gate shields/helmets on some condition (not yet decoded).
