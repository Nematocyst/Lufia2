import sys, subprocess, shutil
sys.path.insert(0,'/home/claude/lufia2/tools')
from hd import *
from PIL import Image
S='/tmp/claude-0/-home-claude/94b3994a-61e1-50a5-81a3-e47f92eae4ae/scratchpad/'; F=S+'final/'; T=S+'s3test/'
lo=lambda a:(a>>16&0x7F)*0x8000+(a&0x7FFF)
src=bytearray(open(F+'lufia2_rir_bg3.sfc','rb').read())
for part in range(3):
    rom=bytearray(src)
    R=lo(0xDF8000)
    for k in range(16):
        rec=0x40+part*16+k
        rom[R+4*(0x30+k):R+4*(0x30+k)+4]=src[R+4*rec:R+4*rec+4]
    rom[lo(0xDFF600):lo(0xDFF600)+128]=bytes(128)       # no variants
    p=T+'t%d.sfc'%part; open(p,'wb').write(rom)
    subprocess.run(['/home/claude/lufia2/deps/asar/build/asar/bin/asar','--fix-checksum=off','/home/claude/lufia2/mods/battletest.asm',p],check=True)
    for k in range(16):
        emu=start(p,S+'field.state',0x30+k)
        for i in range(420):
            emu.ram[0x1F8A0]=0x30+k; emu.run(1)
        emu.png(T+'r%02X.png'%(0x40+part*16+k)); print('shot %02X'%(0x40+part*16+k),flush=True)
