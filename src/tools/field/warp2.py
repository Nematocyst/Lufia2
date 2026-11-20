import sys; sys.path.insert(0,'/home/claude/lufia2/tools')
from retro import Emu
import shots
from PIL import Image
S='/tmp/claude-0/-home-claude/a299c82d-b96b-5dd0-8703-11d363742157/scratchpad/'
ROM=sys.argv[1]; m,X,Y,par=[int(x,16) for x in sys.argv[2:6]]; out=sys.argv[6]
frames=int(sys.argv[7]) if len(sys.argv)>7 else 240
e=Emu(shots.CORE,ROM); e.run(2); e.load_state(open(S+'ow/c2.state','rb').read()); e.run(2); r=e.ram
r[0x5B4]=r[0x5AC]; r[0x5AE]=m; r[0x5B0]=X; r[0x5B1]=Y; r[0x5B2]=par; r[0x5B3]=2; r[0x5B5]|=0x80
ims=[]
for k in range(4): e.run(frames//4); ims.append(e.image())
print('map',hex(r[0x5AC]|r[0x5AD]<<8),'pos',r[0x6BA],r[0x6E2])
o=Image.new('RGB',(4*260,224),'white')
for i,im in enumerate(ims): o.paste(im,(i*260,0))
o.save(S+'survey/'+out+'.png'); open(S+'survey/'+out+'.state','wb').write(e.save_state())
