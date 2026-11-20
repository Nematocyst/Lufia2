"""Warp to a map in the emulator and dump WRAM, VRAM, a screenshot (for the map renderer)."""
import sys, json; sys.path.insert(0,'/home/claude/lufia2/tools')
from retro import Emu
import shots, ctypes as C
S='/tmp/claude-0/-home-claude/a299c82d-b96b-5dd0-8703-11d363742157/scratchpad/'
def vram(e):
    L=e.lib; p=L.retro_get_memory_data(3); n=L.retro_get_memory_size(3)
    return bytes((C.c_uint8*n).from_address(p)) if p else b''
def load(rom, m, X, Y, par=0xF0, frames=200, e=None):
    if e is None:
        e=Emu(shots.CORE,rom); e.run(2)
    e.load_state(open(S+'ow/c2.state','rb').read()); e.run(2); r=e.ram
    r[0x5B4]=r[0x5AC]; r[0x5AE]=m; r[0x5B0]=X; r[0x5B1]=Y; r[0x5B2]=par; r[0x5B3]=2; r[0x5B5]|=0x80
    e.run(frames)
    return e
if __name__=='__main__':
    rom=sys.argv[1]; m,X,Y=[int(x,16) for x in sys.argv[2:5]]
    e=load(rom,m,X,Y)
    v=vram(e); print('map',hex(e.ram[0x5AC]),'vram',len(v))
    open('m%02X.wram'%m,'wb').write(bytes(e.ram)); open('m%02X.vram'%m,'wb').write(v); e.png('m%02X.png'%m,1)
