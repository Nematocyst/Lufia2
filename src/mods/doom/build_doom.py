"""Doom Island restoration (test build).

    python3 build_doom.py IN.sfc OUT.sfc [--free D78000]     (IN = clean or combined ROM)

1. Walls on Doom Island ($E6): the island top, the staircase and the teleporter rock (doom_walls.py).
   The map data grows by a few bytes -> moved to the free area, resource entry repointed.
2. Header: new point 06 = the teleporter pad (15,30).
3. Arrival $63 (after the Sinistrals' scene in $EB): the warp now lands on point 06 (the pad) instead
   of point 01; the arrival script just rebuilds the party and fades in (no flight into the castle,
   no warp into the dark shrine), so the player has control on the island.
6. Healing pad: stepping onto the pad's centre restores HP and MP (living members) with a short
   fade out/in; works on the clean ROM too (no extra code).
5. Shrine of Daos 1F ($E7) header: the step just inside the door (event rectangle x11-18, y41, which
   ran an empty script) now runs event 03 too, so the arrival scene plays on the first step in.
4. Shrine of Daos 1F ($E7) event 03 (just inside the door, used to say "We can't run away."):
   now jumps to the shrine's arrival scene, which plays once ("Is everyone ok?" ... Light ... Daos'
   voice; sets flag $82) and does nothing afterwards, so the party can walk back out.
"""
import sys, json
sys.path.insert(0, '/home/claude/lufia2/tools/mapview'); sys.path.insert(0, '/home/claude/lufia2/tools')
sys.path.insert(0, '/home/claude/lufia2/mods'); sys.path.insert(0, '/home/claude/lufia2/mods/doom')
import l2compress as L
from mapdata import MapData
from mapheader import MapHeader
import doom_walls

PAD = (15, 30)


def patch(rom, cpu, old, new):
    o = L.lo(cpu)
    assert bytes(rom[o:o + len(old)]) == bytes(old), 'unexpected bytes at $%06X: %s' % (cpu, rom[o:o + len(old)].hex())
    rom[o:o + len(new)] = bytes(new)


def build(rom, free):
    rom = bytearray(rom)
    if len(rom) < 0x400000:
        rom += bytes(0x400000 - len(rom))
    # 1. walls
    m = MapData(rom, 0xE6)
    for k, x, y, v in doom_walls.edits(rom):
        m.set(k, x, y, v)
    rom, n, end = m.write(rom, free)
    if end:
        free = end
    # 2. header point 06 = pad
    h = MapHeader(rom, 0xE6)
    if not any(r[0] == 6 for r in h.lists[0x0E]):
        h.lists[0x0E].append([6, PAD[0], PAD[1]])
    if not any(r[0] == 1 for r in h.lists[0x0C]):                     # event 01 = the pad's centre (step 6)
        h.lists[0x0C].append([1, PAD[0], PAD[1], PAD[0] + 1, PAD[1] + 1])
    rom, n2, end2 = h.write(rom, free)
    if end2:
        free = end2
    # 3. arrival $63 at $8E:81CE (28 bytes): put leader + party on the pad, fade in, free control
    old63 = bytes.fromhex('2e012e022e036c00f80034 00fa a3009b 5911 76 8900 3714 16e76201 00'.replace(' ', ''))
    new63 = bytes.fromhex('3d00 5911 76 00'.replace(' ', ''))   # rebuild party, fade in, wait, end
    patch(rom, 0x8E81CE, old63, new63 + bytes([0x00]) * (len(old63) - len(new63)))
    # 3b. the warp that leads here ($EB, after the Sinistrals' scene): arrive at point 06 (the pad)
    #     instead of point 01 (the start of the old flight). Op 16 = warp map, arrival script, point.
    patch(rom, 0x8E9CBF, bytes.fromhex('16e66301'), bytes.fromhex('16e66306'))
    # 4. E7 event 03 at $8E:853D -> goto L_0038 (the shrine's arrival scene; it checks flag $82 itself)
    patch(rom, 0x8E853D, bytes.fromhex('4710615794'), bytes.fromhex('1c3800') + bytes.fromhex('0000'))
    # 5. E7 events: the rectangle just inside the door (x11-18, y41) ran event 02 (an empty script);
    #    point it at event 03, so the first step into the shrine plays the arrival scene.
    h7 = MapHeader(rom, 0xE7)
    for r in h7.lists[0x0C]:
        if r == [0x02, 0x0B, 0x29, 0x12, 0x2A]:
            r[0] = 0x03
    rom, _, _ = h7.write(rom)
    # 6. Healing pad: header event 01 = the pad's centre cell; E6 script block slot 8 (events) gets
    #    [01 -> +$28]; the script sits in the bytes freed from the old arrival $63 ($8E:81D4-81E9):
    #    restore HP/MP (op $28, living members), sound + colour flash as feedback, end
    #    (a fade out/in froze the player after the event).
    #    (Iris' far op $02 was tried first: it only works for text inside a window.)
    ev_list = bytes([0x01, 0x28, 0x00, 0xFF])                         # event id 01 -> block +$28
    heal = bytes([0x28, 0x4C, 0x6F, 0x95, 0xFF, 0x00, 0x1E, 0x37, 0x20, 0x97, 0x00])  # heal, sound $6F, flash, wait, restore the map's colours, end
    patch(rom, 0x8E81D4, bytes(len(ev_list) + len(heal)), ev_list + heal)
    patch(rom, 0x8E81B0 + 8, bytes([0x1A, 0x00]), bytes([0x24, 0x00]))   # slot 8 list -> +$24
    return rom, free


if __name__ == '__main__':
    a = sys.argv[1:]
    free = int(a[a.index('--free') + 1], 16) if '--free' in a else 0xD78000
    rom0 = open(a[0], 'rb').read()
    rom, end = build(rom0, free)
    open(a[1], 'wb').write(rom)
    sys.path.insert(0, '/home/claude/lufia2/mods'); import mkpatch
    open(a[1].rsplit('.', 1)[0] + '.bps', 'wb').write(mkpatch.bps(rom0, bytes(rom)))
    print('free space used: $%06X-$%06X' % (free, end - 1))
