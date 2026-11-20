# Lufia II — Seasons and time of day (lead)

Added 2026-11-01 — feasibility notes only, nothing built. Pairs with the battle-background variants (`variants_patch.py`) and the background toolkit (`bgext.asm`).

Idea (user): a time-of-day and seasons system, used first by the battle-background variants (twilight, night, sunrise versions), with other uses to follow.

### Clock: already there, already saved
- Play-time counter ticks in the NMI (`$80:866A`): `$0B50` frames (0–59), `$0B4F` seconds, `$0B4E` minutes, `$0B4D` hours. Saved with every file (the file screen shows it), so a clock derived from it needs **no new save data** and survives save/load and resets. Frames bit 7 set = clock paused (`BMI` at `$80:866D`).
- Derive the time instead of storing it: total minutes T = hours×60 + minutes. Example scale: 1 real minute = 1 in-game hour → a day lasts 24 real minutes; phase = T mod 24 → sunrise / day / twilight / night slots. Season = (T / (24 × days per season)) mod 4. A few instructions, callable from anywhere.
- Things that want to *move* the clock (sleeping at an inn → morning) need a stored offset: 1–2 bytes in the save. Candidate: spare bytes of the saved item-storage block next to the Iris NG+ bytes (`$7F:F17C–F17F` used by Iris); confirm what else is free. Without an offset, inns can't change the time.

### Battle backgrounds (first use)
- The variant picker (`variants_patch.py`, hook `$81:B9C8`, table `$E0:F400`, 8 bytes per id) already reads `$0B4F/$0B50` for randomness. Extend the table to per-time-slot lists (e.g. id → {sunrise, day, twilight, night} each with its own variants), so e.g. grassland at night picks a night picture.
- Only outdoor backgrounds get time versions (grass, forest, hills, mountains, desert, sea…); caves/towers/indoors keep one look. The table naturally handles that (no entry = no change).
- Cheaper alternative / complement to new art: a **palette tint at load time** — the bgext hook (`$81:BAB9`, copies the background palettes into rows 2–4) can scale the colours toward blue/dark (night), orange (twilight/sunrise), white-ish (winter haze). Every outdoor background gets a time look for free; hand-drawn variants (stars, moon, sunset sky) only where wanted. Palette tint is safer than colour math in battle, because effect scripts use the colour-math registers and the gradient skies (`bgext.asm`) already use COLDATA via HDMA channel 6. With gradient skies, the tint must also be applied to the per-line gradient colour table (HDMA ch0 → colour 0), or the sky stays in daylight.

### Field (world map, towns)
- The game already has coloured screen fades through colour math: script ops `$94`/`$96` (`ScriptOp9x_ColdataFadePreset` → `sub_80AF77`: CGADSUB `$93`/`$D3` = subtract fixed colour on BG1/BG2/backdrop, COLDATA fade from source to target over n steps), op `$97` restores the map's own setting. Each map's own colour-math setup is in its header copy at `$7F:0001–0005` (TM, TS, CGWSEL, CGADSUB, COLDATA), applied by `FieldSetSceneDisplay $80:F2F3` on map load.
- So a night/twilight tint on the world map and town exteriors = a fixed-colour subtract (blue-ish night, orange evening), applied after `FieldSetSceneDisplay` for maps on an "outdoor" list. Risk: maps whose header already uses colour math (transparency, fog) would conflict — need a list of which maps set `$7F:0003/0004`.
- Alternative per map: tinted palettes (like battle) — more work, no conflicts.
- Seasons on the world map: recoloured world-map palette per season (greens → autumn orange, winter white) = palette swap only; matching battle variants (snowy grassland, autumn forest) through the same variant table.

### Other uses that fall out of it (ideas)
- Expose the time as **event flags** (e.g. flag "night", flags per season) updated by the clock code, so the existing script ops (`15`/`6A` goto if flag set/clear, condition lists) can test it: shops closed at night, NPCs with night lines, night-only events. Needs a few unused event flags (Iris uses `$DC`, Restored `$DD`/`$DE`; find more).
- Night/season monsters: the world-map encounter lookup (`$86:9D0B`, region × `$97:C493`) could switch to alternate region tables at night or in winter.
- Music: `PlaySong $80:93FE` hook could pick night versions of field songs (if there are suitable songs).
- Visual feedback: a small clock/season indicator on the file screen or menu (the menu already shows TIME).

### Open questions for the user
- Real-time scale (how long a day and a season last), or tied to something else (steps, story chapters, inns)?
- Should inns/sleeping advance to morning (needs a saved offset)?
- Which time slots (sunrise, day, twilight, night — 4?) and seasons (4?), and indoor exclusion.

### Next steps
1. Mock-up previews: a battle background with load-time palette tints (sunrise/twilight/night) and the world map with a colour-math night tint, in the emulator, as GIFs/pictures.
2. List maps that already use colour math; find free event flags and save bytes.
3. Design the extended variant table (id × time slot × season).

## Budget (discussed 2026-11-01; user worried 4 slots × 4 seasons = 16× the art)
- Measured: original-style background ≈ 8 KB (197 KB for 25 in `$E1–$EF`); remade with the toolkit (426 tiles, 3 palettes, gradient) ≈ 13 KB (first 8 KB tiles compressed + 170 extra tiles raw 5.4 KB + tilemap + gradient).
- **Recolour variant** = same graphics + tilemap, new palette (64 + 32 B) + new gradient (~0.7 KB) ≈ 1 KB: background records already split tilemap / graphics / palette indexes, so a night record points at the day picture's graphics.
- Free in the 4 MB ROM: ~1.2 MB. ~14 outdoor pictures: 4 slots recoloured = 56 ≈ 0.2 MB; 4×4 recoloured = 224 ≈ 0.4 MB; 4×4 redrawn ≈ 2.9 MB (needs 6–8 MB, possible without a chip); recoloured times + redrawn winter ≈ 0.9 MB.
- Background record table: 64 ids (`$E0:F100`, `$18` black), ~half used → enlarge for more than ~30 variants (variants_patch masks ids with `AND #$3F`).
- Proposal to the user: times of day all recoloured; seasons mostly recoloured (autumn colour swap), only winter redrawn (snow); optional hand-drawn night skies later. 

## Decisions
- 2026-11-01 (Q3): **4 time slots — sunrise, day, sunset, night** (door left open for extra variants later); **4 seasons**. Plan as proposed: times recoloured, seasons mostly recoloured, winter redrawn.
- 2026-11-01 (Q1, part): **day/night in real time** (play-time clock). **Seasons follow the story**: 4 story beats (event flags) give one full cycle; after the 4th beat the player gets a **field-only spell that changes the season** (like Reset: not usable in battle), so they choose from then on.
  - Implications: the chosen season must be saved → 1 save byte (2 bits; can share a byte with the inn offset). Season = story-flag table until the spell is learned, then the saved choice.
  - New spell: spell records `$95:FA5B` (40, bank full — relocate or reuse one), kind $48/$08 = field spell, learner mask, MP; field effect through the menu effect kind (`$0A62`, Reset = $24) → needs a new handler: either cycle to the next season on each cast (simplest) or open a 4-way choice (menu work). How it is obtained: shop spell list, NPC or event after beat 4.
  - To pick: the 4 story beats (event flags) and which season each starts.
- 2026-11-02: spell **cycles** to the next season on each cast. **Story beats = party members joining**: game starts in **Spring**; **Summer** when Guy joins (user: either first meeting at Tanbel or when his sister is rescued and he joins for good — to pick); **Fall** when Selan joins; **Winter** when Dekar joins. After that a quest or an NPC gives the spell (to decide).
  - Implementation note: use the story event flags set by each join (monotonic), not the current roster (members leave/return). Flags to identify in the scripts (scriptdec output, party/story flags per TCRF notes).
- 2026-11-02: Summer starts **when Guy joins Maxim to go rescue his sister**. **A full day = 2 real hours.** **Inns jump to morning** (needs the saved clock offset; shares the season byte area). **Slot split (final): sunrise 20 min, day 40, sunset 20, night 40** (real minutes per 2-hour day; = 4 / 8 / 4 / 8 in-game hours, e.g. sunrise 4–8, day 8–16, sunset 16–20, night 20–4). **Inn: wake up at the start of sunrise.**
- All design questions answered (2026-11-02).

## Season spell quest (user's design, 2026-11-02)
1. After winter (Dekar joined), a **blue chest in one of the next dungeons** holds a new scenario item (stone tablet or scroll; name TBD).
2. When the party meets **Lexis**, he notices the item and says a colleague of his could make sense of it.
3. "A few days" later, returning to **Lexis' home**: a lady NPC is there — his colleague (name TBD). She takes the item and asks for a week.
4. After "a week", on entering the next town **Lexis says he received a letter** from her.
5. Back at Lexis' home: the item holds **ancient magic older than the Sinistrals**; she tried to cast it and couldn't. She **teaches the spell** and asks them to cast it; afterwards she explains it **speeds up the current season** (= moves to the next season, cycling).
6. **Only Maxim and Selan learn it** (special spiritual energy) → learner mask Maxim $01 + Selan $02.
- Pieces needed: 1 new key/scenario item (spare ids Key30 `$1CA` or PURIFIA `$1CD`, or after the item-table expansion), a blue chest (placement + Ancient-Cave-style blue table? no — normal dungeon chest), Lexis dialogue branch (checks the item in the bag), new NPC sprite/actor in Lexis' home (conditional on quest stage), letter trigger on town entry, spell record (field spell, cycle effect), quest-stage flags (a few unused event flags), and day counting.
- Timing (decided 2026-11-06): **count inn nights** — each inn sleep = one day passing ("a few days" = a few nights, "a week" = 7 nights). Needs a small saved night counter (quest only).
- Names (2026-11-06): scroll = **Hymn of Zurvan**; colleague = **Stela Glynn**; spell = **SeasShift**, **0 MP**.
  - Length check: item names are 12 characters (`$9E:C7E8 + 12·id`) → "Hymn of Zurvan" (14) needs a short form in the item list (e.g. "Zurvan Hymn"), full name in dialogue. Spell names are 8 characters (spell record bytes 0–7) → "SeasShift" (9) is one too long.
  - **Final (2026-11-07): spell name "SeasShft"; item-list name "Zurvan Hymn"** (dialogue keeps the full "Hymn of Zurvan").

- Old open list: Q1 rest — day length and slot split (e.g. sunrise 5–7, day 7–17, sunset 17–19, night 19–5); Q2 inn → morning (save offset); spell details (cycle vs choice, name, who learns it, MP).
