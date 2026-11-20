import sys; sys.path.insert(0,'/home/claude/lufia2/tools')
from retro import Emu
import shots
from PIL import Image
S='/tmp/claude-0/-home-claude/a299c82d-b96b-5dd0-8703-11d363742157/scratchpad/survey/'
ROM=sys.argv[1]; val=int(sys.argv[2],16); plan=sys.argv[3:]
e=Emu(shots.CORE,ROM); e.run(2); e.load_state(open(S+'e6x.state','rb').read()); e.run(2); r=e.ram
W,H=r[0x10008],r[0x10009]; n=W*H; base=0x10000+0xC0E
print('W',W,'H',H)
cnt=0
for i in range(n):
    if r[base+2*i]==0 and r[base+2*i+1]==0: r[0x4000+i]|=val; cnt+=1
print('blocked cells',cnt)
ims=[]
for p in plan:
    d,k=p.split(':'); e.held={d}; e.run(int(k)); e.held=set(); e.run(20)
    ims.append(e.image()); print(p,'pos',r[0x6BA],r[0x6E2])
o=Image.new('RGB',(len(ims)*260,224),'white')
for i,im in enumerate(ims): o.paste(im,(i*260,0))
o.save(S+'collide4000_%02x.png'%val)
