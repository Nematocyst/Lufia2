import sys, json, os, numpy as np, multiprocessing as mp
sys.path.insert(0,'/home/claude/lufia2/tools/mapview'); sys.path.insert(0,'.')
from PIL import Image
J=json.load(open('../survey/all_exits.json'))
dest={}
for src,v in J.items():
    for e in v.get('exits',[]):
        dm=e[8]
        if dm!=0xFF and dm not in dest: dest[dm]=(e[6],e[7])
def job(m):
    import dump, render as R
    try:
        X,Y=dest.get(m,(10,10))
        e=dump.load('/home/claude/lufia2/rom/orig.smc',m,X,Y)
        w=bytes(e.ram); v=dump.vram(e); shot=np.array(e.image().convert('RGB')).astype(int)
        if (w[0x5AC])!=m: return (m,'notloaded',w[0x5AC])
        F=R.Field(w,v,0x8000)
        if not F.layers: return (m,'nolayers')
        imgs=[F.render(k) for k in range(len(F.layers))]
        H=max(i[0].shape[0] for i in imgs); W=max(i[0].shape[1] for i in imgs)
        img=np.zeros((H,W,3),np.uint8)
        for a,ma in imgs:          # first layer at the bottom
            pass
        a,ma=imgs[0]; img[:a.shape[0],:a.shape[1]]=a
        for b,mb in imgs[1:]:
            sub=img[:b.shape[0],:b.shape[1]]; sub[mb]=b[mb]
        Image.fromarray(img).save('maps/map_%02X.png'%m)
        sx=R.w16(w,0x594); sy=R.w16(w,0x596)+1
        crop=img[sy:sy+224,sx:sx+256].astype(int)
        d=float(np.abs(crop-shot).mean()) if crop.shape==shot.shape else -1
        open('maps/map_%02X.wram'%m,'wb').write(w); open('maps/map_%02X.vram'%m,'wb').write(v)
        e.png('maps/shot_%02X.png'%m,1)
        return (m,'ok',[l[1:] for l in F.layers],round(d,1))
    except Exception as ex:
        return (m,'error',str(ex)[:80])
if __name__=='__main__':
    os.makedirs('maps',exist_ok=True)
    ids=[int(k,16) for k in J]
    with mp.Pool(8) as p: res=p.map(job,sorted(ids))
    json.dump(res,open('maps/batch.json','w'))
    for r in res: print(r)
