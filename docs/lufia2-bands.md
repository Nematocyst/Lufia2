# Lufia II — scrolling background bands (prototype, 2026-10-31)

**PARKED by the user (2026-10-31): "looks nice", revisit in the second pass over the ROM hacks.**

Option "parallax" from the Tales of Phantasia list, reduced to what fits Lufia II: the battle
camera never moves and BG2 is taken (window panels, actors during effects), so a true second layer
gives little. Instead, horizontal **bands of the single background layer scroll on their own** —
e.g. clouds drifting over a still gradient sky.

## Status
- **Working prototype** (user's lake picture in slot 04, test ROM scratchpad `band/romF.sfc`, clip
  `band/clouds.gif`): lines 0–47 drift 1 px per 8 frames; nothing below line 48 moves; clean
  boundary line; correct through Spark (flash + shake) and the next round; all 23 original
  backgrounds pixel-identical; battle exit and field movement identical to the original.
- The band code is in `bgext.asm` but inert unless the band table has an entry (bbg_build never
  writes one yet). NOTE: bgext.asm's NMI-exit change (interrupts allowed) is active whenever the
  patch is applied — tested harmless, but remember it if anything interrupt-related shows up.

## How it works (`src/mods/bgext.asm`)
- Table `$E0:B500`, 2 bytes per graphics index: band end line (0 = none), speed (frames per pixel
  = 1 << speed). **Not yet written by bbg_build** — the prototype set it by hand
  (`rom[lo(0xE0B500) + 2*g] = (48, 3)`).
- Battle NMI hook at `$85:8E6C` (replaces `LDA $0583 / STA $2100`, 6 bytes → JSL + 2 NOP):
  BG1HOFS = `$0594` + drift for the top of the frame; HTIME 220, VTIME = band end; NMITIMEN `$B1`.
  Skipped for the desert (ripple owns BG1HOFS) and `$18`.
- IRQ vector `$00:FFEE` → `$FFA4` (was `$86C0`, a bare RTI); `$80:FFA4` JML BandIrq (free filler;
  Restored & Extended uses `$80:FFA0–FFA3`). BandIrq: ack `$4211`, BG1HOFS = `$0594` (long
  addressing, DB unknown).
- **The game never clears the interrupt-disable flag** (SEI at `$80:8000`, no CLI anywhere), so the
  NMI exit (`$80:86BA`, PLY/PLX/PLA/PLB/PLP/RTI) now jumps to NmiExit, which also clears I in the
  flags RTI restores. Harmless: nothing else in the game enables an IRQ source; field code rewrites
  NMITIMEN (`$81`) on transitions, which turns the band IRQ off after battle.
- Drift counter `$7F:FFF4` (16-bit) — **PROTOTYPE: not verified as free RAM** (battletest.asm also
  uses `$7F:FFF0/1`, test-only).

## Art rules for bands
- The band must wrap left↔right (the 32-tile map is exactly 256 px wide): no cloud may touch the
  picture's left or right edge (the prototype erased 5 such clouds).
- Nothing in the band may cross its bottom line (mountain peaks, trees): everything in the band
  moves together. Low clouds wholly below the line stay still (read as distant haze).
- A see-through gradient sky behind the band is ideal: only the cloud tiles move, the sky doesn't.

## To finish (when resumed)
- Verify a free RAM word for the counter (or derive it from a game counter).
- bbg_build support (`ID=...` option for band end + speed); converter check that nothing crosses.
- Optional: a second band (water shimmer) = a second IRQ per frame.
