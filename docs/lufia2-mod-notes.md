# Lufia II mod: "Restored & Extended" v0.4 (2026-10-28)

Source: mods/l2mod.asm (asar 1.90), build with mods/build_mod.sh, test with mods/test_mod.py (65816 interpreter tools/cpu65816.py runs the hooked routines from the patched ROM; 38 checks pass). Output: mods/out/lufia2_restored.bps/.ips. build_mod.sh also writes mods/out/l2mod.sym (WLA symbols), which test_mod.py reads.

## Features
- Map names: two parts.
  - Decoder fix ($80:C9EB → NameBackref): $0A back-refs resolved page-relative (src = (pos & $F000) | low12, minus $1000 if src > pos). Real decoder used src = $878000 + (word & $0FFF).
  - Banner fix (v0.2): the arrival banner (TextUpdateSceneLabel $80:C825, called at $83:B47F on normal map entry) printed the raw ROM name through the scene-text VM, which resolves $0A the same broken way. $80:C89D now loads #$E300 and $80:C8AD loads #$7E, so the banner prints the copy just decoded into $7E:E300. v0.1 lacked this, so the visible banner was still broken.
  - Verified in snes9x: banners of all 242 maps identical to the original except D2–D5 Gratze Castle B1–B4, D6/D7 Gratze Kingdom, D9 Narvick (previously no banner), EF Capsule Monsters' Cave (previously "U e MoV T Cave"). Original banners match TCRF's garbled heading. The backtick in "Monsters` Cave/Shrine" has no glyph and shows as a space, as in the original.
- Region 17: region table copied to $81:FE83 (+ record 17 = formations 147,163,138,156,157 weights 100,100,80,60,40); $86:9D22/9D3E/9D59 repointed.
- Ancient Cave bosses: CavePick hook at $83:9A42 (table CaveBosses: floor min, max, 1-in-N, formation): King Hidora $C0 B55–66 1/24, Kraken formation 165 B60–75 1/24, Gades $DE $C1 B85–98 1/32. Virtual formations ≥$C0 via FormationRead hook at $81:83A9 (fixed lists $FF,$01,...). Field sprite hook FormationSprite at $83:9A4A and $80:AB86 ($C0 → 191 Hidora, $C1 → $7A Gades' story sprite since v0.4).
- IP skills: BattleIpAction hook at $81:AB50 — effect record ids ≥$F0 read from NewIpEffects (bank $84). IP 5 "Test" → Black thunder, IP 167 "Double slash" → Cold stream, IP 13 "Dragon fury" → Golden mist. IP records at $84:FD50, descriptions at $97:B0A1 (table $97:8000 index $230+IP).
- Items: Key26–29 records ($96:F979, 64 bytes) → Sword jewel (IP 1 Repeat attack), Spirit jewel (IP 5, INT+20), White eye (IP 167, AGL+20), Golden rock (IP 13); Key30 → PURIFIA record.
- Drops: DropHook at $81:FB1A (ExtraDrops table), rolled before the enemy's own tags: Unicorn → Uni jewel, Deadly Sword → Sword jewel, Dark Spirit/Leech → Spirit jewel, White Dragon → White eye, Gold Gorem → Golden rock.
- Capsule fixes (v0.3), details in claude/lufia2-capsules.md:
  - Winged Horse record $97:E2D7: +$0F 30→26 (innate Air attack), +$14 26→30 (learnable slot 3 Electro bolt), so the menu matches its AI.
  - Darbi courage: "set L2, K" words at $97:E73D/E7C0/E847/E8DB = 9/20/30/36 (were 17/35/50/60). Flee when % HP lost ≥ GUT×25/K.
  - Firebird loop ($97:EE70 = $0044) deliberately left as is (user choice).
  - Wind/earth: shared routine table $96:FADD; routines 22 and 27–32 are unused by every script in the ROM. New code at $96:FD4A: WeakFlyerWind (table entry 4 repointed; old routine 4 + "and attr,1 → ×2") and ResistThunderWeakEarth (entry 27). Seven regular thunder-resistant enemies' `call routine 7` operands → 27: Wind Genie $96:8BCE, Salamander $96:9039, Bolt Fish $96:9FB2, Specter $96:A845, High Hidora $96:B605, Silver Dragon $96:BA16, Tengu $96:C061. Bosses (Tarantula, Pierre, Tank, Idura ×3, Erim, Daos, Egg Dragon, Gades) keep routine 7.
  - Shared routine encoding: 0C var val (set), 16 and, 06/07 if_eq/if_ne var val jump (jumps relative to the routine start), 0F mul, 10 div, 43 return; var byte $80 = L0, value word $8000|n = global Gn; G39 = attack attribute, G42 = damage. mods/weakness_routines.py runs a routine in the VM for tests.
- Cave Gades (v0.4):
  - Sprite: $7A (story Gades). It has one pose per direction (header "33 01"; Maxim is "51 01", monster sprites like Archfiend "0B 02" have a 2-frame idle bob), so there is no walking or idle animation.
    - Large cave objects ($7F:E216 = 3, from sprite header & 3) never move in the cave, vanilla included (Archfiend sprite on the same floor stays put too).
  - Gate: CavePick skips the Gades row unless event flag $DD is set. Map $3D (Gordovan West Tower 6F) win branch L_024D: $89:EC05 `wait_frames 10` → `set_flag $DD`. After `op_53 $0B` (scene battle), flag $FF = lost, so goto_if_not_flag $FF = won.
    - Saves past Gordovan from older versions lack $DD.
  - Speech:
    - Hook $83:B96F (FieldProbeActorContact, `LDA $05B6 / BIT #1 / BNE`) → CaveContact ($81). On a cave floor ($05B6 bit 0) it checks the touched object's formation ($7F:F966 + actor id − $50). For a Gades not yet spoken ($DE clear) it sets $DE and turns him toward the leader ($0692/$066A). It then starts a scene script the way FieldTryActorInteraction + FieldPrepareEventControl do:
      - $09AB/$09AC = actor; $0622 bit 0 on him and on the leader; text_state $099B = $80;
      - $1259/$1255/$1256/$7FD0FF = 0, $7FD0C1 = $FF;
      - $09B7/$09B9 = GadesSpeech ($97:C493).
    - The return slot $1252/$1254 = $8E:A1E2 (map $F0's `end`), so ScriptOp00_End returns to the cave's script bank and ends there. The script has no dictionary words, which also use that slot.
    - It returns SEC (contact handled). The next frame's contact check finds $DE set and starts the battle normally.
    - CavePick clears $DE when it places a Gades.
  - New script op $11 xx (was BRK; table $80:CA36 → stub $80:FFA0 → ScriptOp11 $84:FDC7): window at actor xx via window_ex's tail $80:BC33. xx = $FF uses $7FF8A4 + $50 (the met monster). A character id falls back to ids 1–6 on screen (FieldSelectActorById, state bit 2 clear), then 0.
    - On cave floors only the leader is an actor ($0926 / rebuild_party does not add followers there), so Selan's line shows over Maxim.
  - snes9x test: a test ROM with CaveBosses row 1 = (1, 99, 1, $C1), a save made in map $F0 with $0799 = $20, then the right door. Verified: the sprite, facing, the 4 windows, battle start, direct battle when $DE is already set, and the loss → cave entrance.
- Package lufia2-restored-v0.4.zip also contains the combined v0.4 + Iris BPS. The two patches overlap only in the header checksum.

## Free space map (verified unused)
- $81:FD10–$81:FFFF and $84:FD41–$84:FFFF, $85:FEFA–, $86:FDBC–: $AA-style filler, no code or tables ($81:FD00–FD03 holds stray bytes "20 04 FD 6B", left alone). The Iris patch uses $84:FE00–, $85:FEC0–, $86:FC10–, $80:FC20–FF9F.
- $97:B0A1–$97:B125: zero padding after the last action-description string (terminator at $97:B0A0; table at $97:B126 follows).
- $97:C493–$97:C53C: the original region table (17×10 bytes), read only by $86:9D22/3E/59, which v0.1 repointed. v0.4 uses $97:C493–C522 for Gades' speech.
- $80:FFA0–FFAF: filler before the header; v0.4 uses FFA0–FFA3.
- Bank $81 free space is used up by v0.4 (ends at $81:FFFE); $84:FDFA–FDFF left.
- $96:FD4A–$96:FD97: shared battle routines 27–32 (unused); v0.3 uses $96:FD4A–FD96. Routine 22 ($96:FCF2, 22 bytes) is also unused.
- NOT free: $97:EF1D zero run (unused tail of the 256-entry shop pointer table $97:EE9F), $87:AED6 $FF run (after a 4-byte record table at $87:AE4E of unknown use).

## Emulator harness (2026-10-27)
- snes9x libretro core built from GitHub in the scratchpad; tools/retro.py = ctypes frontend (input, WRAM access, save states, PNG frames); tools/shots.py and tools/mapshot.py.
- Debug mode for test ROMs only: PAR 8380C7D4 = byte $D4 at $83:80C7 (low byte of JSL FieldRunMenu target). Then Controller 2 Select + Controller 1 X toggles debug ($7E057C = $FF); Start+X opens EV FLAGS; Select opens the debug Load/Save menu (RIGHT for the SAVE column).
- Reaching any map cleanly: in the debug save menu, set $05AC (field_map_id) to the target map just before saving, reset, load the save from the title. The game then loads into that map with a proper script context.
- Forced warps: write $05AE map, $05B3 = 0, $05B5 |= $88. With $05B3 bit 0 set the game runs an "arrive" script record instead of TextUpdateSceneLabel (garbage balloon). Arrival position ignored (top-left).
- Fade-in after a forced warp with arrive flag: $0582 = 0, $0581 = $81.
- mapshot.py stitches a full map by sweeping with debug walk-through-walls (B held, one axis at a time, 4 px/frame), masking 16 px screen edges and the party sprite, and using the camera value from before each frame ($05A4/$05A6, signed). Small maps hide rooms the party is not in.

## Gratze maps (corrected 2026-10-27)
- $D6 Gratze Kingdom = the castle grounds/exterior: courtyard, side buildings, moat, drawbridge (48×44 tiles). Entry script places ~20 actors (soldiers $18/$19, commander $66, $67 after flag $61). Event 1 "This is..." starts the capture scene → warp $D5 jail. Exits: drawbridge → world map (201,33); side doors (13,15)/(35,15) → $D7.
- $D7 Gratze Kingdom = two small side-door rooms (window, statue, door), 18×16 tiles. Left room exit → $D2 Gratze Castle B1 (9,36); right room exit → map $90 Dankirk North Cave B5 (69,31), probably a placeholder. No events.
- No map exists behind the main castle door.
- Overworld entrance 73 at (216,35) → $D6 (24,35) but is walled in by mountains; the story arrives via Gratze Sth. Submarine Cave ($D1).
- Open question for the user: how and when the grounds ($D6) should be revisitable after the story (would need a flag gate on the capture event and a route in).

## Optional patch: RETRY from the start (retry.asm, v1.0, 2026-10-28)
- Title menu mode count $1559 = SRAM $70:0000 bits 2–3 (TitleLoadSaveSelectionBits $82:E998): 0 START, 1 +RETRY (normal game cleared, set at $8E:B30C), 2 +GIFT (RETRY game cleared). Table $82:EFAF has window sizes for 0–2 only.
- Patch: $82:E998 `LDA $700000` → `JSL $86:FFF0`, which returns the byte with bit 2 set when bits 2–3 are 0. SRAM is never written.
- RETRY itself: $0B51 = 1, EXP and gold ×4 at $81:DA06 (capped); kept in the save. The Iris NG+ carry-over skips an empty last slot.
- Free space note: $80:FFAA–FFAD is a JML $808000 vector stub (COP/BRK/ABORT/IRQ point at $FFAA), so $80:FFA0–FFA9 is the only filler there. Bank $86 tail $86:FF79–FFFF is free with Iris; retry uses $86:FFF0–FFFA.
- Tests: test_retry.py (all 256 headers, IPS over mod+Iris). snes9x: fresh SRAM shows START RETRY; RETRY → name entry → Elcid with $0B51 = 1.
