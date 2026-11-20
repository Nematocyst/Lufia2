import sys
from emu_iris import *
emu=Emu(shots.CORE, sys.argv[3] if len(sys.argv)>3 else ROM); emu.run(2)
s=sram(emu); d=open(S+sys.argv[1],'rb').read()
for i in range(len(d)): s[i]=d[i]
emu.lib.retro_reset(); emu.run(700)
emu.press('START',hold=3,gap=60)       # title -> file screen (cursor on last file)
emu.press('A',hold=3,gap=40)            # file -> "start from this file?"
emu.press('A',hold=3,gap=200)           # YES
emu.run(200)
print('map',hex(w16(emu.ram,0x5AC)))
emu.png(S+sys.argv[2]+'.png',scale=2); open(S+sys.argv[2]+'.state','wb').write(emu.save_state())
