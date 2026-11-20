import sys, glob, re, os
sys.path.insert(0,'/home/claude/lufia2/tools')
import numpy as np
from PIL import Image
from scipy import ndimage
import bbg_floor
OUT='prep/'; os.makedirs(OUT,exist_ok=True)
def sky(f, hmax=100, tol=30):
    a=np.asarray(f).astype(float)
    sm=ndimage.uniform_filter(a,(3,3,1))
    gm=np.abs(np.diff(sm,axis=0,prepend=sm[:1])).sum(2)+np.abs(np.diff(sm,axis=1,prepend=sm[:,:1])).sum(2)
    cand=gm<18; cand[hmax:]=False
    lab,_=ndimage.label(cand); cand=np.isin(lab,[l for l in np.unique(lab[0]) if l])
    ref=np.zeros((hmax,3)); ok=np.zeros(hmax,bool)
    for y in range(hmax):
        px=a[y][cand[y]]
        if len(px)>=16: ref[y]=np.median(px,0); ok[y]=True
    ys=np.where(ok)[0]
    if len(ys)==0: return np.zeros(a.shape[:2],bool)
    for c in range(3): ref[:,c]=np.interp(np.arange(hmax),ys,ref[ys,c])
    m=np.zeros(a.shape[:2],bool)
    d=np.sqrt(((a[:hmax]-ref[:,None,:])**2).sum(2)); m[:hmax]=d<tol
    m[:hmax]&=np.arange(hmax)[:,None]<=ys.max()
    lab,_=ndimage.label(m); m=np.isin(lab,[l for l in np.unique(lab[0]) if l])
    o=ndimage.binary_opening(m,np.ones((3,3))); lab,_=ndimage.label(o)
    k=np.isin(lab,[l for l in np.unique(lab[0]) if l])
    return m & ndimage.binary_dilation(k)
fs=sorted(glob.glob('in/*.png'))
for f in fs:
    s,p,t=re.match(r'in/(Spring|Summer|Fall|Winter)(Farm|Lake|River)(Day|Night|Sunrise|Sunset)',f).groups()
    n='%s_%s_%s'%(p,s,t)
    im=Image.open(f).convert('RGB'); w,h=im.size
    fit=im.resize((256,round(h*256/w)),Image.BOX).crop((0,0,256,224))
    m=sky(fit)
    img,fl,info=bbg_floor.rebuild_floor(fit,sample=(150,205,32,224),patch=(128,32),min_row=96,patch_rows=(130,210),drop_below=168,seamless=True,margin=2,fade=4,anchor=160,low=(128,400))
    img.save(OUT+n+'_fl.png'); Image.fromarray((m*255).astype(np.uint8)).save(OUT+n+'_mask.png')
    print(n, 'sky px',int(m.sum()),'end',int(np.where(m.any(1))[0].max()) if m.any() else -1,'floor',round(info['replaced'],2),flush=True)
