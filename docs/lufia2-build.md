# Lufia II — combined edition build (layered, with overlap checks) — 2026-11-12

Decided with the user (2026-11-12): consolidate the patches into ONE build from the clean ROM.
RETRY is optional (the user only wanted it to avoid testing from zero) → two outputs per build.
Music-off and MSU-1 are always included (harmless when unused). Working name "combined edition",
versioned by date (user may name it later).

## Recipe — `src/tools/build_combined.py CLEAN OUT [--no-retry] [--report file]`
Workspace layout it expects (`/root/lufia2`): `combined/build_combined.py`, `combined/layers/*.lay`,
`src/mods/{retry,music,msu1}.asm`, asar at `ext/asar/build/asar/bin/asar` (or `$ASAR`).

| # | Layer | Kind | Source | Bytes | Where |
|---|---|---|---|---|---|
| 1 | restored_iris | data | `layers/restored_iris.lay` (6 KB) | 4,936 | Restored v0.4 + Iris v1.1 (see lufia2-mod-notes.md / iris.asm) |
| 2 | retry (optional) | asm | `retry.asm` | 15 | `$82:E998`, `$86:FFF0–FFFA` |
| 3 | backgrounds3 | data | `layers/backgrounds3.lay` (2 MB) | 1,062,906 | build 3 (4 MB expansion) |
| 4 | musicoff | asm | `music.asm` | 134 | `$82:9AD5`, `$82:A0BC`, `$82:BF4C`, `$82:BFAD`, `$82:EAEF`, `$82:FFB7–FFE2`, `$83:FFBA–FFF9` |
| 5 | msu1 | asm | `msu1.asm -DMSUBASE=$DBFC00` | 545 | hooks `$80:8664`, `$80:93FE`, `$80:9692`, `$80:969F`, `$80:B8B2`, `$83:83CF`, `$83:FFBA` (takes over music-off's ApplyMusic, declared), code `$DB:FC00–FE24` |
- Each layer's changed bytes are recorded; a layer touching bytes an earlier layer changed stops the build (except the header checksum, recomputed at the end with asar's mirrored-remainder rule, and the ALLOWED takeovers). Zero bytes in new expansion space count as free.
- Verified: with RETRY = SHA1 **b4a43e01…0936** = backgrounds test build 3 + music-off add-on + MSU-1 add-on (byte-identical). Without RETRY = **5f294537…00b5**; title menu START only, saves load, MSU town track plays.
- Delivered: `lufia2_combined_2026-11-12.zip` (two BPS from clean ROM + empty `luf2_msu1.msu` + README).

## Regression check — `src/tools/regress.py` (2026-11-14)
Catches a new build breaking something that used to work. Works on any ROM (clean, a mod, the
combined edition); compares a new build with the last good one.
- `regress.py snapshot ROM DIR [--maps …|all] [--battles …|all|none]` — records: header checksum,
  static checks for every map (map data, header, event block decode, ROM-only render hash), a new
  game booted to the field, a screenshot after warping to each of the 240 maps (party on an exit's
  landing spot), and a screenshot ~6 s into a battle forced to each background id. Battles use a
  test hook written into a **copy** of the ROM (padded to 4 MB if smaller, hook in free space at the
  end of a high bank, `$83:900C` redirected); the ROM itself is untouched. ~1.5 min for 240 maps +
  24 backgrounds. For the combined build use `--battles all` (ids 00–2F, covers the added ids).
- `regress.py compare OLD NEW [--report r.md]` — lists problems (map no longer loads, battle no
  longer starts, new decode/render errors, boot fails, bad checksum), screens that changed by more
  than 0.5 % of pixels (side-by-side images in `NEW/diff/`), and maps whose ROM data render changed.
- `regress.py check ROM OLD [--report r.md]` — snapshot into `OLD.new` + compare; exit code 1 on
  problems.
- Validated 2026-11-14: clean ROM twice → 0 differences (deterministic); Restored+Iris+RETRY →
  0 problems, 0 changed screens; the new-maps test ROM (scriptspace + mapext + 2 new maps) → 0
  changed screens (confirms those tools leave existing maps alone); a deliberately edited map →
  caught (map 06 changed 100 %, flagged as not loading). Test ROMs show "header checksum wrong"
  (they are not checksum-fixed) — expected.
- Not covered: dialogue/text, menus, audio, save/load of real files, late-game states (the run uses
  a fresh new game). The combined edition itself could not be run here (its background layer comes
  from the user's art build, not stored in the project) — first run needs the user's ROM or the
  layer files: snapshot the delivered 2026-11-12 build as the baseline, then `check` each new one.

## Where the data layers come from
- `restored_iris.lay`: Restored+Iris+RETRY ROM recovered from `addon_backgrounds3_for_restored_iris_retry.bps` (in the user's `lufia2_backgrounds3_test3.zip`) with `src/tools/recover_rir.py` (bytes the patch copies through + clean bytes elsewhere + header checksum; verified by the patch's source CRC32 4C8ED673, SHA1 5e9fc716…3c07), minus the 15 RETRY bytes.
- `backgrounds3.lay`: diff recovered RIR → build 3 (clean + `lufia2_restored_iris_retry_backgrounds3.bps`).
- Both are regenerable from the user's patches; binaries are not stored in the project. To rebuild Restored/Iris from source instead, restore l2mod.asm/iris.asm + their generators (gruberik_dialogue.py needs tools/rom.py, scriptasm.py, scriptdec.py) and check the result equals restored_iris.lay.
- **Next background build:** replace layer 3 with a new data layer made from that build (diff against the recovered RIR), or add the background build tools as an asm/py layer; then rebuild both outputs.

## Free-space map (combined ROM, 2026-11-12) — claim space here before using it
Taken (owner):
- Bank $80: `$80:FC20–FEDC` Iris, `$80:FFA0–FFA3` Restored, `$80:FFA4–FFA7` + `$80:FFEE` backgrounds (vectors), `$80:FFAA–FFAD` vector stub (game).
- `$81:FD10–FFFE` Restored (full). `$82:FFB7–FFE2` music-off. `$83:FFBA–FFF9` music-off (+ MSU hook at FFBA). `$84:FD50–FDFF` Restored, `$84:FE00–` Iris. `$85:FEC0–` Iris. `$86:FC10–FF78` Iris, `$86:FFF0–FFFA` RETRY.
- `$D0`–`$D6:C8D7`, `$DC`–`$DE:BFBE`, `$DF`, `$E0`–`$F4` (with interior zero gaps = table slots, do not use), `$F5`–`$FF`: backgrounds build 3 (data, tables, gradients, extra tiles, seasonal pictures).
- `$DB:FC00–FE24`: MSU-1.
Free:
- **`$D7:8000`–`$DA:FFFF` (128 KB, four whole banks)**, `$DB:8000–FBFF` (31 KB), `$D6:C8D8–FFFF` (14 KB), `$DE:BFBF–FFFF` (16 KB, end of a backgrounds bank — may be wanted by the next background build).
- Original banks: only `$84:FFD4–FFFF` (44 B) and `$85:FFD2–FFFF` (46 B) of filler left; `$86:FF79–FFEF` (between Iris and RETRY). `$97:B0A1+` and `$96` slots are used (Restored/Iris).
- Test-only tools must not use music-off's `$83:FFBA` (battletest.asm does — use `msu_testhooks.asm`'s copy in a free bank instead; `regress.py` finds its own space).
- ROM is 4 MB; 6–8 MB possible later (needs ExLoROM/header change) when the free banks run out.
