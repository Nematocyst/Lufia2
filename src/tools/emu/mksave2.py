import sys
sys.path.insert(0,'/home/claude/lufia2/tools')
from emu_iris import *
from cpu65816 import CPU
mp=int(sys.argv[1],16); out=sys.argv[2]
rom=open(ROM,'rb').read()
emu=emu_from(S+'tia_full.state')
cpu=CPU(rom); cpu.wram[:]=bytes(emu.ram)[:0x20000]; cpu.sram[:]=bytes(sram(emu))
cpu.wram[0x05AC]=mp
for kv in sys.argv[3:]:
    a,v=kv.split('='); cpu.wram[int(a,16)]=int(v,16)
cpu.call(0x8090C9, a=2, m=1, xf=0, db=0x80, d=0, max_steps=5000000)
s=cpu.sram; s[0]=(s[0]&0xF0)|0x02
open(S+out,'wb').write(bytes(s))
