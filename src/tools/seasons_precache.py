import sys, os, glob, pickle, hashlib as _h
sys.path.insert(0,'/home/claude/lufia2/tools')
import numpy as np, warnings
from PIL import Image
import bbg_convert as B, bbg_gradient as G
from multiprocessing import Pool
F='/tmp/claude-0/-home-claude/94b3994a-61e1-50a5-81a3-e47f92eae4ae/scratchpad/final/'; CD=F+'cache/'
P='/tmp/claude-0/-home-claude/94b3994a-61e1-50a5-81a3-e47f92eae4ae/scratchpad/seasons/prep/'
def _key(img,kw):
    h=_h.md5(np.asarray(img.convert('RGB')).tobytes())
    for k in sorted(kw):
        v=kw[k]; h.update(k.encode()); h.update(np.asarray(v).tobytes() if v is not None else b'N')
    return CD+h.hexdigest()+'.pkl'
def job(n):
    warnings.filterwarnings('ignore')
    img=Image.open(P+n+'_fl.png'); m=np.asarray(Image.open(P+n+'_mask.png'))>127
    grad=G.fit(img,m,smooth=4); np.save(P+n+'_grad.npy',grad)
    end=G.sky_end(m)
    kw=dict(npal=3,mask=m,max_tiles=426,backdrop=G.quantized(grad,end),outliers=3,smooth=0.3)
    f=_key(img,kw)
    if not os.path.exists(f):
        r=B.convert_n(img,**kw); pickle.dump(r,open(f,'wb')); return n,r[4]
    return n,'cached'
if __name__=='__main__':
    names=sorted(os.path.basename(f)[:-7] for f in glob.glob(P+'*_fl.png'))
    with Pool(2) as p:
        for r in p.imap_unordered(job,names): print(*r,flush=True)
