# Lufia II — new abilities groundwork: who plays which animation, relocated script bank (2026-11-12)

Follows `lufia2-effects.md` (VM, opcodes, Bolide draft). Test ROMs only; nothing delivered to the user yet.
Tools: `src/tools/effect_reloc.py` (new), `src/tools/effect_users.py` (new), `src/tools/effectdec.py`
(now takes `--bank`), `src/tools/effectasm.py`, `src/anim/bolide.txt` (labels renamed B_IP / B_MONSTER).

## 1. Who plays which effect id (naming table)
`effect_users.py` scans every enemy turn/reaction script (+ shared routines), capsule actions and item
scripts for battle-VM op `$5A n` (play effect n; RAN-RAN uses `$3D`), with the nearest announce (op `$1E`,
message table `$85:F2D7`, 1-based) and element (op `$21/$22`). Merged with spells (k → k+$12), IP records
(byte 2) and fixed ids → `build/effect_names.txt` (game data, regenerate). Highlights:
- **Weapon swings, verified in the emulator** (logger hook on BattlePlayEffect): effect = item word 13 − 1.
  Swords/knives 0, rods/staves 2, bows 4, spears 6, whips 8, pliers/stun gun/hammers 10, axes 12,
  unarmed 14 (`$0E`, fixed). Changing a sword's word 13 to 9 made it play the whip swing (8).
  Many physical IPs have animation byte 0 (Repeat attack, Bomb attack, Dragon rush…) = probably "the
  wielder's weapon swing" (not traced further).
- Monster normal hits: 224 (`$E0`) and the 22x family (224 Dive/Scolding/Sleep javelin, 226 Ninja/
  Samurai/Guillotine, 228 Evil lance/Galactic lancer, 230 Scissors, 232 Ax attack/Total destruction).
  220 (`$DC`) = number pop-ups after every hit.
- Monster-only animations: 128 Groundshock/Earthquake/Mega quake, 129 Doomcry (Venge Ghost), 130 Plasma
  blaster, 131 Drowsy (Fire Dragon), 132 Piercer (Tank), 133 Twister/Whirlpool/Sandstorm/Diamond dust,
  134 Raio beam/Cinder blast, 135 Golden mist, 136–137 Black thunder/Dark aura/Gloomsplash, 138 Gloomy/
  Dark force, 140 Machine-gun attack, 144 Dark fry (Erim, Daos), 145 Raging wave/Torrent/Tidal wave,
  150 Terror wave (Daos), 151 Destructo-wave (Gades), 152 Devastation wave (Erim), 153 Chaos wave (Amon),
  54 Phoenix blast (Red Dragon). Many monster moves reuse spell animations (Flash 18, Bolt 19, Fireball 22,
  Gale 27, Drowsy 32, Dread 34, Absorb 36, Confuse 39).
- Still unnamed (53 ids): odd ids 1–17 (19-byte scripts like the weapon swings: probably a second
  swing/variant), 16, 64–70, 97, 106–114, 146, 148, 149, 223/225–233 odd (225+ share one 1-byte stub),
  241, 255, 266–280 (ids 256+ are read through `$95:8200` by `$81:9F47`, spawned by index, not played).

## 2. Relocating the animation scripts (works, pixel-identical)
`python3 effect_reloc.py IN.sfc OUT.sfc --bank D1 [--add ID=file.txt:LABEL ...]`
- Copies bank `$95` verbatim to a free bank (every script pointer is 16-bit, so same offsets = valid) and
  patches 3 places: `$81:899A` `LDA.l $958000,X` (table), `$81:89A4` `LDA #$95` (script bank `$C5`),
  `$81:9F47` `LDA.l $958200,X` (ids 256+).
- **Do NOT repoint** `LDA #$95 / PHA / PLB` at `$81:96C7`, `$81:97D8`, `$81:A5BE`, `$81:A5D6`, `$81:A5EE`:
  they set the data bank only to reach I/O registers (`$2181` WMADD, `$4202` multiplier). Banks `$C0+`
  have no I/O → wrong palettes (caught by the frame comparison: pink sword slash, Tia's colours).
- Spell/IP records, their names and the pop-up table stay in `$95` and are read from there, so the copy's
  `$F1EF–$FFFF` (3,601 bytes) is free for new scripts; the copy's data region `$E793–$F08A` must stay.
- Test: all 121 distinct animations, each forced onto every attack in a scripted battle (bbg/battle.state,
  900 frames, frame hash every 3 frames), original vs relocated: **0 differing frames** (`fx2/all.py`).

## 3. A new animation at a new id (works)
- Bolide assembled into the copy at `$D1:F1EF` (221 bytes, uses the original routines L_9204 and
  L_A01D by label) and assigned to the unused ids **55 (IP version) and 56 (monster version)**.
- Played through a real game path: swords' item word 13 set to 56 → Maxim's attack plays effect 55 →
  comet, red flash, explosions on the target (`fx2/bolide_newid.gif`). 3,380 bytes left in the free area.
- So a new ability needs: script in the relocated bank, an unused id (130 left below 256), and a caller
  (IP record byte 2, monster `$5A n`, or an item's word 13 for a weapon swing).

## Next (when the user wants abilities built)
- Decide the bank (the combined build's free map: `$D7:8000–$DA:FFFF`, `$DB:8000–FBFF` in `lufia2-build.md`;
  check before using `$D1`, which was free on the 4 MB backgrounds test ROM).
- If more than ~3.3 KB of new scripts is needed: free the copy's unused orphan scripts (28) or add per-effect
  bank support (small engine patch: a parallel bank table read next to `$81:899A`).
- Monster side (Copper Dragon Bolide), IP record, item (Copper rock) per `lufia2-effects.md`.
