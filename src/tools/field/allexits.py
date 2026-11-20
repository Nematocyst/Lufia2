import sys, json; sys.path.insert(0,'/home/claude/lufia2/tools')
from retro import Emu
import shots
S='/tmp/claude-0/-home-claude/a299c82d-b96b-5dd0-8703-11d363742157/scratchpad/'
ROM=sys.argv[1]; ids=[int(x,16) for x in sys.argv[2].split(',')]; out=sys.argv[3]
base=open(S+'ow/c2.state','rb').read()
res={}
e=Emu(shots.CORE,ROM); e.run(2)
for m in ids:
    e.load_state(base); e.run(2); r=e.ram
    r[0x5B4]=r[0x5AC]; r[0x5AE]=m; r[0x5B0]=2; r[0x5B1]=2; r[0x5B2]=0xF0; r[0x5B3]=2; r[0x5B5]|=0x80
    ok=False
    for _ in range(40):
        e.run(10)
        if (r[0x5AC]|r[0x5AD]<<8)==m: ok=True; break
    e.run(30)
    w=lambda a:r[a]|r[a+1]<<8; B=0xF000
    ex=[];ev=[]
    if ok:
        p=B+w(B+6); n=0
        while r[p]!=0xFF and n<64: ex.append(list(r[p:p+9])); p+=9; n+=1
        p=B+w(B+12); n=0
        while r[p]!=0xFF and n<64: ev.append(list(r[p:p+5])); p+=5; n+=1
    res['%02X'%m]={'loaded':ok,'exits':ex,'events':ev}
json.dump(res,open(out,'w'))
