import sys; sys.path.insert(0,'/home/claude/lufia2/tools')
from retro import Emu
import shots
from PIL import Image
S='/tmp/claude-0/-home-claude/a299c82d-b96b-5dd0-8703-11d363742157/scratchpad/survey/'
ROM,st,out=sys.argv[1:4]; plan=sys.argv[4:]   # e.g. UP:10 DOWN:40 (steps of 6 frames)
e=Emu(shots.CORE,ROM); e.run(2); e.load_state(open(S+st+'.state','rb').read()); e.run(2); r=e.ram
w16=lambda a:r[a]|r[a+1]<<8
def cam():
    x,y=w16(0x5A4),w16(0x5A6); return x-65536*(x>32767), y-65536*(y>32767)
canvas={}; m0=w16(0x5AC)
for p in plan:
    d,n=p.split(':')
    for _ in range(int(n)):
        sv=e.save_state(); r[0x57C]=0xFF; e.held={'B',d}; e.run(4); e.held=set(); e.run(10)
        if w16(0x5AC)!=m0 or r[0x5B5]&0x80: e.load_state(sv); break
        canvas[cam()]=e.image()
xs=[k[0] for k in canvas]; ys=[k[1] for k in canvas]; x0,y0=min(xs),min(ys)
big=Image.new('RGB',(max(xs)-x0+256,max(ys)-y0+224))
for (x,y),im in sorted(canvas.items(),key=lambda kv:(kv[0][1],kv[0][0])): big.paste(im,(x-x0,y-y0))
big.save(S+out+'.png'); print(out,big.size)
