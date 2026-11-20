"""Generate collector.asm: new dialogue for Gruberik's treasure hunter (talk $58) and the
Iris Treasure collector (talk $59).

The scripts are reassembled into their original space $8A:F026-$8A:F422. New text is stored
as "far text" (script op $02, added by iris.asm) in bank $80's free space, so its length is not
limited by the old scripts' size; strings used more than once are stored once. Unchanged vanilla
lines stay compressed in place.

    python3 gruberik_dialogue.py   -> collector.asm (scripts) + collector_far.asm (far strings)
"""
import sys
sys.path.insert(0, '/home/claude/lufia2/tools')
import rom
from scriptasm import Asm

d = rom.load()
o = rom.to_off
BASE = 0x8AEB1C                       # map $69 script block
START, END = 0x8AF026, 0x8AF423       # talk $58 .. up to talk $5A's script (exclusive)
SET_FLAG = 0xDC                       # set by iris.asm while a party member wears the full set

NAMES = ['Sword', 'Shield', 'Helmet', 'Armor', 'Ring', 'Jewel', 'Staff', 'Pot', 'Tiara']

a = Asm(BASE, START)

# ---------------------------------------------------------------- treasure hunter (talk $58)
a.label('HUNTER')
a.window("I may not look it, but I'm\na treasure hunter. I've\nbeen as low as  B25 but\n"
         "found no Iris Treasures.")                  # vanilla line
a.op(0x01)                                            # wait_button
a.op(0x14, 0x10, 0x0E, 0x00); a.target(0x30, 'HUNTER_SOME'); a.op(0xFF)   # gallery empty?
a.far_window("I've heard the Iris\nTreasures can be worn,\nbut only by girls!")
a.op(0x01)
a.far_window("The legends say they grow\nstronger as you do... And\nif you wear them all, they\n"
             "become even more powerful!")
a.op(0x00)
a.label('HUNTER_SOME')
a.far_window("So the legends were\ntrue! Keep going, there\nare more down there.")
a.op(0x00)

# ---------------------------------------------------------------- collector (talk $59)
a.label('COLLECTOR')
for k, nm in enumerate(NAMES):
    a.label('P%d' % k)
    nxt = 'P%d' % (k + 1) if k < 8 else 'BOSS'
    a.op(0x14, 0x01, 0xC8 + k, 0x40, 0xD2 + k); a.target(0x20, nxt); a.op(0xFF)  # skip unless new
    a.far_window("I see you found the\nIris ", ('text', nm),
                 "! That's\nwonderful! Let me make\na copy for my gallery.")
    a.op(0x01)
    a.op(0x33, k + 1, 0x59)                           # walk to the display
    a.op(0x37, 0x1E)
    a.op(0x2D, 0x5C + k)                              # show the piece
    a.op(0xA3, 0x5C + k, 0x9D)
    a.op(0x38, 0x01)
    a.op(0x33, 0x0B, 0x59)                            # walk back
    a.op(0x1A, 0xD2 + k)                              # displayed
    a.op(0x1E, 0x0E, 0x01)                            # gallery count += 1
    a.goto('POT' if nm == 'Pot' else 'WEAR')

a.label('WEAR')
a.far_window("Go ahead, try putting\nit on, young one.")
a.op(0x01)
a.far_window("You look really\npowerful!")
a.op(0x00)

a.label('POT')
a.far_window("Hmm... I don't think\nyou can wear that.")
a.op(0x01)
a.far_window("Keep it with you,\nthough. They say the\nset isn't complete\nwithout it.")
a.op(0x00)

# cave boss: vanilla text and actions
a.label('BOSS')
a.op(0x14, 0x01, 0xD1, 0x40, 0xDB); a.target(0x20, 'TAIL'); a.op(0xFF)
a.window("You defeated the boss\nin the Ancient Cave!\nThat's wonderful! Let\nme display it right away!")
BOSS_OPS = bytes([0x01, 0x33, 0x0A, 0x59, 0x37, 0x1E, 0x2D, 0x65, 0xA3, 0x65, 0x9D, 0x38, 0x01,
                  0x33, 0x0B, 0x59, 0x1A, 0xDB, 0x1E, 0x0E, 0x01, 0x00])
assert d[o(0x8AF371):o(0x8AF387)] == BOSS_OPS
a.op(*BOSS_OPS)

a.label('TAIL')
a.op(0x14, 0x10, 0x0E, 0x0A); a.target(0x20, 'ALL'); a.op(0xFF)       # all 10 displayed
a.op(0x14, 0x12, 0x0E, 0x01); a.target(0x20, 'SOME'); a.op(0xFF)      # at least one
a.window("All the Iris Treasures\nare to be displayed here,\nbut, sad to say, there\nare none here yet.")
a.op(0x00)
a.label('SOME')
a.window("I'd like this place to\nbe full of Iris Treasures.")
a.op(0x00)
a.label('ALL')
a.window("You brought back all\nthe Iris Treasures!? You\nmust be the best treasure\n"
         "hunter in the world!")
a.op(0x01)
a.op(0x6A, SET_FLAG); a.target(None, 'DONE')        # goto_if_not_flag: nobody wears the set
a.far_window("You look magnificent!\nI bet you'd be more than\na match for any evil\ngods now!")
a.label('DONE')
a.op(0x00)

# ---------------------------------------------------------------- output
data = a.assemble(max_len=END - START)

# talk table entries for ids $58 / $59
hdr = o(BASE)
assert d[hdr:hdr + 2] == b'PH'
talk = BASE + (d[hdr + 6] | d[hdr + 7] << 8)
p = o(talk)
patch = {}
while d[p] != 0xFF:
    key, w = d[p], d[p + 1] | d[p + 2] << 8
    if key == 0x58:
        assert w == 0x050A; patch[rom.to_cpu(p + 1)] = a.labels['HUNTER'] - BASE
    if key == 0x59:
        assert w == 0x0548; patch[rom.to_cpu(p + 1)] = a.labels['COLLECTOR'] - BASE
    p += 3
assert len(patch) == 2


def dbs(f, blob):
    for i in range(0, len(blob), 16):
        f.write('    db ' + ','.join('$%02X' % b for b in blob[i:i + 16]) + '\n')


with open('/home/claude/lufia2/mods/collector.asm', 'w') as f:
    far_total = sum(len(k) for k in a.far_strings)
    f.write('; generated by gruberik_dialogue.py - do not edit\n')
    f.write('; scripts: %d of %d bytes; far text: %d bytes in collector_far.asm\n' % (len(data), END - START, far_total))
    for adr, w in sorted(patch.items()):
        f.write('org $%06X : dw $%04X\n' % (adr, w))
    f.write('org $%06X\n' % START)
    pos = 0
    for off, lab in a.far_refs:
        dbs(f, data[pos:off]); f.write('    dl %s\n' % lab); pos = off + 3
    dbs(f, data[pos:])
    f.write('    fillbyte $00 : fill %d\n' % (END - START - len(data)))   # zero the rest of the old scripts
with open('/home/claude/lufia2/mods/collector_far.asm', 'w') as f:
    f.write('; generated by gruberik_dialogue.py - far-text strings (plain ASCII, $00-terminated)\n')
    for enc, lab in a.far_strings.items():
        f.write('%s:\n' % lab); dbs(f, enc)
print('scripts %d / %d bytes, far text %d bytes' % (len(data), END - START, far_total))
