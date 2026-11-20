"""HDMA usage logger for battles (test ROM with battletest.asm)."""
from bt import *
REG = {0x0D:'BG1HOFS',0x0E:'BG1VOFS',0x0F:'BG2HOFS',0x10:'BG2VOFS',0x11:'BG3HOFS',0x12:'BG3VOFS',
       0x21:'CGADD',0x22:'CGDATA',0x26:'WH0',0x27:'WH1',0x28:'WH2',0x29:'WH3',0x2C:'TM',0x2D:'TS',
       0x30:'CGWSEL',0x31:'CGADSUB',0x32:'COLDATA',0x00:'INIDISP',0x05:'BGMODE',0x18:'VMDATAL',0x2E:'TMW',0x2F:'TSW'}
def chans(r):
    out = {}
    m = r[0xD9]
    for c in range(8):
        if m >> c & 1:
            b = r[0x1AEF + 5*c:0x1AEF + 5*c + 5]
            out[c] = '%s mode %02X src %02X:%04X' % (REG.get(b[1], '$21%02X' % b[1]), b[0], b[4], b[2] | b[3] << 8)
    return out
def start(rom, state, bg, group=1):
    emu = Emu(CORE, rom); emu.run(2)
    emu.load_state(open(state, 'rb').read()); r = emu.ram
    emu.run(30); r[0x1F8A0] = bg; r[0x1FFF1] = group; r[0x1FFF0] = 1
    return emu
