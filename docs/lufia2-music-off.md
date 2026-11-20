# Lufia II — CONFIG: music off (2026-10-31)

## CONFIG: music off (BUILT 2026-10-31, `src/mods/music.asm`)
- MUSIC option now STEREO / MONO / OFF (`$0B54` = 0/1/2, saved with the game). LEFT/RIGHT cycle it (LEFT on MUSIC was a vanilla bug: 3-entry table at `$82:BF52`, row 3 read past it).
- Mute = driver music volume (`SetMusicVolume $80:9601`, driver mode `$0B`): 0 = silent, `$FF` = driver default (audio A/B identical). Volume ramps (fades) rather than cutting.
- Verified in snes9x with audio capture: music silent at 0, menu SFX full strength; mute survives map changes and new songs (`PlaySong`), so it is applied only on new game (`$82:9AD4`), save load (`$82:EAEE`) and option change. Save → reset → load keeps OFF. Title screen still plays music (no save loaded yet).
- Hooks: `$82:BF4C` JMP LeftHook, `$82:BFAD` JSR MusicNext, `$82:A0BB/A0BF` option string → `$83:FFDA`. Free space used: `$82:FFB7–FFFF`, `$83:FFBA–FFFF` (noisy-$AA filler; no overlap with Restored/Iris/RETRY/backgrounds).
- Free-space note: the ROM's spare space is "noisy $AA" (random bit flips), not clean $AA/$FF. Remaining known gaps: `$86:FF79–FFEF` (between Iris and RETRY). `$80:9B80–9C0E` ($FF) is NOT free (empty sound-resource entries point there).
- asar gotcha: `bra $XXXX` with a number is taken as the raw offset; branch to a label instead.
- Test helpers: `exp/hook.asm` (field frame hook at `$83:900C`: poke `$7F:FFF0` = volume, `$7F:FFF3` = song) and `retro.py` audio capture (`emu.audio`, `emu.rms()`, `emu.wav()`); newer snes9x cores need `retro_set_controller_port_device(0,1)` (added) and the file screen needs ~30-frame gaps between presses.
- Delivered: add-on BPS/IPS for the Restored+Iris+RETRY+backgrounds test ROM (rebuilt exactly by applying `lufia2_restored_iris_retry_backgrounds.bps` to the clean ROM; base SHA1 4D3FB9D1306AC85B5D2A59C9343AC04F01DB1911, result E0B5367752EAC914CD9D012FED0F1B230B3DE177). All emulator tests repeated on that ROM.
