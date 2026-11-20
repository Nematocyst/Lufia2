# Lufia II battle backgrounds (PC version) — art instructions for ChatGPT (2026-11-14)

Paste the block below into the ChatGPT project's instructions. Replaces `chatgpt-art-instructions.md`
(SNES version, tile limits) for PC-version art; the tile-check script is not needed for the PC.
Advice given to the user: keep generating at full size (ChatGPT can't make a clean 256×224 pixel
grid); Claude downscales to 256×224 and converts with `src/tools/hicolour.py`. Guides:
`docs/bg_layout_guide_pc.png`, overlay `docs/bg_overlay_pc_256x224.png` (workspace; sent to the user).

```
# Lufia II battle backgrounds (PC version) — art instructions

## What the pictures are for
Battle backgrounds for Lufia II (16-bit SNES RPG), shown in a PC version of the game at
256×224 pixels, in full colour. There are no tile or palette limits: the picture is used as
painted. Monsters, the party and menu windows are drawn on top of it.

## Size and framing
- Generate at full size, landscape, framed 8:7 (about 1340×1172). Keep the same framing
  across a set. I shrink it to 256×224 myself, so don't try to draw tiny pixels.
- Extend the scenery naturally to the left and right edges (a wider version may be
  cropped later), with nothing important touching the edges.

## Layout (top to bottom, as a share of the height)
- 0–27 %   Sky and horizon: always visible. Paint freely: gradients, clouds, sunsets,
           distant mountains, full detail.
- 27–46 %  Monster zone: monsters stand with their feet at about 43–46 % of the height.
           Mid-tones and moderate contrast so monsters stay easy to see. No tall objects
           in the middle third that would hide behind or fight with monsters.
- 46–59 %  Foreground: always visible; the party walks here. Ground can be detailed,
           but keep it calm.
- 59–100 % Lower ground: mostly covered by menu windows. Continue the same ground
           calmly to the bottom.

## Style
- 16-bit SNES pixel-art look, like the reference pictures in this project: crisp edges,
  limited shading steps, no photo textures, no painterly blur, no film grain.
- Lighting from above or the side; readable shapes at small size.

## Avoid
- Characters, monsters, animals, people or text in the picture.
- Busy or high-contrast detail behind the monster zone (people must see the monsters).
- Large pure-white or pure-black areas (spell flashes tint the whole picture; mid-tones
  show it best). Avoid bright glowing spots in the lower ground: they shine through the
  menu windows.
- A visible frame, vignette, border or UI.
- Strong perspective lines that point at the bottom corners, or a floor tilted toward
  the viewer: the ground should read as a flat stage seen from slightly above.
- Paths, pools or objects placed exactly where the party stands (left-middle, around
  50–70 % of the height).

## Delivery
Give the picture as a PNG. Say which battle location it is for.
```
