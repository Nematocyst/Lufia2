import sys
sys.path.insert(0,'/home/claude/lufia2/tools')
from retro import Emu
import shots
S='/tmp/claude-0/-home-claude/a299c82d-b96b-5dd0-8703-11d363742157/scratchpad/iris/'
ROM='/home/claude/lufia2/mods/out/lufia2_iris.sfc'
def w16(r,a): return r[a]|r[a+1]<<8
def s16(r,a,v): r[a]=v&0xFF; r[a+1]=v>>8
def emu_from(state, rom=ROM):
    emu=Emu(shots.CORE,rom); emu.run(2)
    emu.load_state(open(state,'rb').read()); emu.run(2); return emu
def party(r):
    out=[]
    for c in range(7):
        b=0xBAD+c*0xBE
        out.append(dict(lv=r[b+0xE],hp=(w16(r,b+0x11),w16(r,b+0x25)),mp=(w16(r,b+0x13),w16(r,b+0x27)),
            atp=w16(r,b+0x29),dfp=w16(r,b+0x2B),stats=[w16(r,b+0x2D+2*i) for i in range(5)],
            eq=[hex(w16(r,b+0x66+2*s)) for s in range(6)]))
    return out
import ctypes as C
def sram(emu):
    L=emu.lib; p=L.retro_get_memory_data(0); n=L.retro_get_memory_size(0)
    return (C.c_uint8*n).from_address(p)
