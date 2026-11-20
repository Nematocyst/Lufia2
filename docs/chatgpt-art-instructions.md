# Lufia II battle backgrounds: instructions for the art pipeline

Paste this into the ChatGPT project's instructions, and add `lufia2_tile_check.py` to the project files.

## What the pictures are for
Battle backgrounds for a SNES game (Lufia II). Each picture is converted to 256×224 pixels built from
8×8 tiles, with at most **426 different tiles** per picture and 3 palettes of 15 colours. The sky becomes
a smooth colour gradient (costs no tiles). The lower ground is replaced by a repeating texture. Every
other 8×8 block of scenery costs one tile; past 426 the converter merges look-alike tiles, which shows
as flat square blocks.

## Composition rules (every picture)
- Full-height framing, about 1341×1173 (width : height ≈ 8 : 7). Same framing across a set.
- Sky in the top part, ending above about 45 % of the height. Plain sky with a few large clouds.
- Horizon scenery (hills, trees, water, buildings) in a band across the middle.
- Lower ~45 % of the picture: plain, evenly textured ground across the whole width (grass, snow, sand…),
  with no paths, puddles, footprints, flowers, light pools or objects.
- The ground just below the horizon must look like the ground further down: no strong glow, sunset
  colour or dark shading on the ground right at the horizon.
- Large, soft shapes in the distance. Avoid fine detail: thin branches, fences, small distant trees,
  villages, sparkles on water.
- Keep the art style of the reference pictures in this project (16-bit SNES pixel-art look).

## Check every picture before showing it
1. After generating a picture, save it as a PNG and run:
   `python3 lufia2_tile_check.py <picture.png>`
2. The script prints PASS, BORDERLINE or REDO, the estimated tiles, a block forecast and reasons, and
   writes `<picture>_tilemap.png` (red = costs a tile, blue = repeating ground, grey = free sky).
3. If the verdict is REDO, regenerate the picture with changes that address the printed reasons
   (usually: simpler band below the horizon, less fine detail in the distance, or a higher horizon),
   keeping the same place, season, time of day and style. Check again. Try at most 3 times.
4. Show the final picture with its verdict, its tile count and the tile map. Say so plainly if it is
   still BORDERLINE or REDO after 3 tries.

If the generated picture cannot be opened by the Python tool directly, ask me to upload it.
