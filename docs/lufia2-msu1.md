# Lufia II — MSU-1 music (investigated + proof of concept, 2026-11-12)

## Verdict
- **Feasible and proven.** A working MSU-1 hook (`src/mods/msu1.asm`) on the user's full ROM (Restored + Iris + RETRY + backgrounds + music-off, 4 MB) passes every emulator test with captured audio (snes9x libretro, generated test tones as tracks).
- **An MSU-1 patch already exists:** by **Conn** (Zeldix thread t1833, Dec 2018, updated to 2026; versions for US/German/Spanish ROMs and the Frue/Spekkio hacks; romhacking.net hacks 4129/4132 ship MSU versions). Track packs: SourJovis arrangement (Relikk), orchestral set (JUD6MENT). Known issues in the thread: a cave theme disturbing sound channels, frog jingle missing, "expanded-ROM patches break it". Its files/track map could not be fetched from this workspace (sites not reachable) — so its hook method, free space and track numbering are unknown.
- **Conn's patch analysed (2026-11-12, user attached `luf2_msu_patch.zip` with source `luf2_msu.asm`):**
  - Track number = **song id** (`STA $2004` with the id inside LoadSong at `$80:942E`) → our default matches; packs are `luf2_msu1-<id>.pcm` + `luf2_msu1.msu`, ROM must be named `luf2_msu1.sfc`.
  - **Hard-mutes the original music** by patching the sound-driver code (`$90:C091` = `$2F`) — no fallback: missing track = silence, no MSU hardware = no music. Likely source of the thread's "cave theme disturbs sound channels" bug. Also `$80:B8CE` = `$80` (script op $4D song-position wait always passes — needed because of the hard mute).
  - No MSU presence check, no missing-track check. Fade: NMI hook `$80:863C`, −3 per frame. Stop: script op $72 hook.
  - Free space **`$81:FD10`–`$81:FFFF` = the same space Restored & Extended uses** → cannot be combined with the user's mods. Our own hook is the way.
  - Its loop table (`$81:FF00`) is now copied into ours so packs behave the same.

## How it works (msu1.asm)
- Music is centralised: `PlaySong $80:93FE` (16 callers: script op $4B, battle start `$81:8900`, scene resume `$83:B52E` after battles, title, world map…), `PrepareSongResource $80:969F` (brings the background song back after a jingle: inn `$04`, item get `$33/$36`), `FadeOutMusic $80:9692` (+ speed `SoundDriverWrite0A`; script op $70), stop = driver command 3 (`SoundDriverRequest03 $80:9528`; script op $72, `$83:83CE`, also inside LoadSong). Current background song id = `$099D` (`$FF` none); scene song `$7F:D0FD`.
- Hooks: PlaySong / PrepareSongResource start the MSU track for the song id; FadeOutMusic starts an MSU fade (−4 volume per frame, in the NMI at the INIDISP write `$80:8664`); script op $72 and `$83:83CE` also stop MSU; music.asm's ApplyMusic `$83:FFBA` replaced by an MSU-aware version (only when music.asm is present).
- **The original song keeps running on the sound chip at music volume 0** (driver command $0B, as in music-off). So sound effects, the cutscene sync that reads the song position (script op $4D, `SoundDriverRead08`) and all other driver commands behave exactly as before. Missing track (`$2000` bit 3) or song without a track → MSU stops and the original music comes back at full volume.
- Tables: TrackTable (song id → track, `$FF` = never MSU; empty slots $0C/$0E/$30/$31), LoopTable (3 loop / 1 once) = Conn's: once for 04, 06, 0C, 0E, 0F, 25, 26, 2D, 30, 31, 33–36, 3C, 3E.
- Free space: code + tables at `$D0:8000` (≈ 0x240 bytes, empty bank of the 4 MB ROM); RAM `$7F:FF80–FF83` (playing, volume, fading, SPC muted). Detection: `$2002–$2007` = "S-MSU1".
- Files: `<rom>.msu` (may be empty) + `<rom>-<n>.pcm` (44.1 kHz 16-bit stereo, "MSU1" + loop point). Hardware/emulators: FXPak/SD2SNES, MiSTer, snes9x ≥ 1.55, bsnes/higan; not Super Everdrive, ZSNES, snes9x-2010. Size ≈ 10.6 MB per minute of audio.

## Test results (2026-11-12, `msu/msutest*.py`, tones: track 2 = 440 Hz, track 0 = 660 Hz)
| Test | Result |
|---|---|
| No MSU files | original music, unchanged (fallback) |
| Town (song 2) with track 2 | 100% 440 Hz, original muted |
| Menu cursor sounds over MSU | 85% of the audio during clicks = sound effects; track continues |
| Song change town → world map | track 0 (660 Hz) 100% |
| Song change to a song without a track | MSU stops, original music back (rms 3659) |
| Fade | 255 → 0 in ~64 frames, then stopped |
| MUSIC OFF / STEREO (music.asm) | OFF = silent (MSU vol 0), STEREO = MSU back, original stays muted |

### With real tracks (2026-11-12, user's pack files `luf2_msu1-2/4/24/29.pcm`; `msu/realtest*.py`, track identified by cross-correlation with the PCM)
| Test | Result |
|---|---|
| Town (song 2) | track 2, match 1.00 (original music fully silent) |
| Inn stay (script op $17 path: PlaySong 4, then PrepareSongResource $099D) | track 4 (jingle), then track 2 from the start |
| Battle start (`$83:83F5` PlaySong $18) | track 24 |
| Victory | track 29, loops at its loop point (5.7 s) |
| Back on the field after a normal encounter (`$83:848C` PlaySong $099D) | track 2 from the start (= original behaviour) |
- Scripted battles (`$7F:F8A3` = $FF, e.g. battletest.asm) do NOT restore the field song: the story script does it (op $4B). After a test battle with the battletest hook the victory song keeps playing — same in the original game.
- Demo video with sound: `msu/real/msu_demo.mp4` (town → inn → battle → victory → town), sent to the user.
- Test ROM tooling: `msu/testhooks.asm` (battletest moved to `$D0:9000`, because battletest.asm's `$83:FFBA` is music.asm's space; plus an inn trigger `$7F:FFF2`), `msu1_log.asm` (-DLOG: song request ring `$7F:FF8F/FF90`), `drvlog.asm` (sound-driver command ring).
- Still untested: real hardware, script op $72 stop, fades in cutscenes, cutscene song-position sync (op $4D) with MSU.

## Open / next steps
1. DONE: numbering + loop table matched to Conn's patch → existing packs work as-is (rename ROM to `luf2_msu1.sfc`).
2. DONE (2026-11-12): town, inn, battle, victory, return to the field with the user's real tracks.
3. Optional: resume the field track after battles instead of restarting (MSU-1 has no seek; would need the "resume" bit on hardware that supports it, or keep the field track playing at volume 0 during short jingles).
4. DELIVERED 2026-11-12: `lufia2_msu1_addon.zip` → `addon_msu1_for_restored_iris_retry_backgrounds_musicoff.bps/.ips` (549 changed bytes), applies to the music-off ROM (SHA1 E0B53677…E177, = backgrounds test ROM + music.asm); README + empty `luf2_msu1.msu`. Smoke-tested on the exact release ROM: tracks play, MUSIC OFF/STEREO, no-MSU fallback. Rebuild: asar `msu1.asm` onto the music-off ROM (no -DLOG, no test hooks). Other bases: check the hook bytes and free space first.
5. DELIVERED 2026-11-12: `lufia2_msu1_addon_bg3.zip` → `addon_msu1_for_backgrounds3_musicoff.bps/.ips` for **backgrounds test build 3** + its music-off add-on (base SHA1 70b7b3b0…a72b; result b4a43e01…0936). Bank `$D0` is used by build 3's seasonal backgrounds, so the code goes to **`$DB:FC00`** (`asar -DMSUBASE='$DBFC00' msu1.asm`); hooks identical. Free in build 3: banks `$D7–$DB` empty, tails `$D6` 14 KB, `$DE` 16 KB, `$F2` 21 KB. All tests repeated on build 3 (town, MUSIC OFF/STEREO, no-MSU fallback, inn, battle, victory, return).

## Song list (from the ROM: resources 0–62, "S2C" header + internal name; 63+ are instrument banks)
| Id (hex) | Track | Internal name | Meaning (romaji) | Plays (Conn's table) |
|---|---|---|---|---|
| 00 | 0 | FIELD | world map | loop |
| 01 | 1 | SHIRO | castle | loop |
| 02 | 2 | MACHI | town | loop |
| 03 | 3 | MURA | village | loop |
| 04 | 4 | OYASUMI | inn / rest (jingle) | once |
| 05 | 5 | TOU | tower | loop |
| 06 | 6 | OPENING 2 | opening 2 | once |
| 07 | 7 | DOROBOU | thief | loop |
| 08 | 8 | DOUKUTHU | cave | loop |
| 09 | 9 | CUCHYUTEIEN | sky garden | loop |
| 0A | 10 | DENSETU | legend | loop |
| 0B | 11 | HANA | flower | loop |
| 0C | — | DAMY | empty | once |
| 0D | 13 | OPENING.1 | opening 1 | loop |
| 0E | — | DAMY | empty | once |
| 0F | 15 | KEKKONSHIKI | wedding | once |
| 10 | 16 | PARTY | party | loop |
| 11 | 17 | WAKARE | farewell | loop |
| 12 | 18 | UMI | sea | loop |
| 13 | 19 | YAMA | mountain | loop |
| 14 | 20 | MUUS | ? | loop |
| 15 | 21 | MINATO | harbour | loop |
| 16 | 22 | MACHI HAKAI | town destroyed | loop |
| 17 | 23 | DOUKUTHU 1 | cave 1 | loop |
| 18 | 24 | BATL 1 | battle 1 | loop |
| 19 | 25 | BATL 2 | battle 2 | loop |
| 1A | 26 | HAKA | grave | loop |
| 1B | 27 | BIG BOS | boss | loop |
| 1C | 28 | LAST BATL | final battle | loop |
| 1D | 29 | KACHI | victory | loop |
| 1E | 30 | HOKORA | shrine | loop |
| 1F | 31 | KENKYUUZYO | laboratory | loop |
| 20 | 32 | KAICYU | undersea | loop |
| 21 | 33 | KAICYUCITY | undersea city | loop |
| 22 | 34 | KAZINO | casino | loop |
| 23 | 35 | 777 PLAY | slots: play | loop |
| 24 | 36 | 777 JAC GAM | slots: jackpot game | loop |
| 25 | 37 | 777 START | slots: start | once |
| 26 | 38 | GAAAAN | shock ("gaaan") | once |
| 27 | 39 | HARU | spring | loop |
| 28 | 40 | NATU | summer | loop |
| 29 | 41 | AKI | autumn | loop |
| 2A | 42 | FUYU | winter | loop |
| 2B | 43 | NAME IN | name entry | loop |
| 2C | 44 | SHINDEN | temple | loop |
| 2D | 45 | ENDING | ending | once |
| 2E | 46 | LOVE | love | loop |
| 2F | 47 | SHINDEN | temple 2 | loop |
| 30 | — | DAMY | empty | once |
| 31 | — | DAMY | empty | once |
| 32 | 50 | HIDECKA | ? | loop |
| 33 | 51 | ITEM GET1 | item get 1 | once |
| 34 | 52 | ITEM GET2 | item get 2 | once |
| 35 | 53 | ITEM GET3 | item get 3 | once |
| 36 | 54 | ITEM GET4 | item get 4 | once |
| 37 | 55 | NAZO NO HIT | mysterious person | loop |
| 38 | 56 | KOKUUTOU DA | ? | loop |
| 39 | 57 | SORA | sky | loop |
| 3A | 58 | BOSKAIWA | ? | loop |
| 3B | 59 | NAZONOFUE | mysterious flute | loop |
| 3C | 60 | MUUS CYANGE | ? | once |
| 3D | 61 | NALBIK | Narvick | loop |
| 3E | 62 | MUUS 2 | ? | once |
