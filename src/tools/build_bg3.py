import sys, os, subprocess, time, zlib, hashlib
sys.path.insert(0,'/home/claude/lufia2/tools')
import numpy as np
from PIL import Image
import bbg_build, terrain_patch
S='/tmp/claude-0/-home-claude/94b3994a-61e1-50a5-81a3-e47f92eae4ae/scratchpad/'; R=S+'re/'; F=S+'final/'
lo=lambda a:(a>>16&0x7F)*0x8000+(a&0x7FFF)
# hill zone from the old released ROM
old=open(S+'old_bg_full.sfc','rb').read()
z=np.frombuffer(old[lo(0xF08000):lo(0xF08000)+0x8000]+old[lo(0xF18000):lo(0xF18000)+0x8000],np.uint8).reshape(256,256)
np.save(F+'hill_zone.npy',z==0x19); print('hill zone tiles',int((z==0x19).sum()),'other ids',sorted(set(z.flatten())-{0,0x19}),flush=True)
def M(n): return np.asarray(Image.open(R+n).convert('L'))>127
J=[]
def g(i,pic,mask,grad): J.append((i,R+pic,M(mask),np.load(R+grad)))
def p(i,pic): J.append((i,R+pic))
p(0x00,'00_mesa_fl3.png'); g(0x22,'22_oasis_fl3.png','22_oasis_mask.png','22_oasis_grad.npy'); g(0x23,'23_dunes_fl3m.png','23_dunes_mask.png','23_dunes_grad.npy')
g(0x04,'04_lake_rb.png','04_lake_mask.png','04_lake_grad.npy'); g(0x1A,'1A_river_rbm.png','1A_river_mask.png','1A_river_grad.npy'); g(0x1B,'1B_farm_rbm.png','1B_farm_mask.png','1B_farm_grad.npy')
p(0x06,'06_forest_rb.png'); p(0x1C,'1C_path_rb.png'); p(0x1D,'1D_stream_rb.png')
g(0x07,'07_cliff_fl2.png','07_cliff_mask.png','07_cliff_grad.npy'); g(0x20,'20_bridge_fl2.png','20_bridge_mask.png','20_bridge_grad.npy'); g(0x21,'21b_cloudsea_fl2.png','21b_cloudsea_mask.png','21b_cloudsea_grad.npy')
for i,n in ((0x19,'19_farmhouse'),(0x1E,'1E_coast'),(0x1F,'1F_woodshed')): g(i,n+'_flm.png',n+'_mask2.png',n+'_grad2.npy')
g(0x24,'24_town_fl128.png','24_town_mask.png','24_town_grad.npy')
p(0x08,'08_daos_g.png'); p(0x25,'25_balcony_k144.png'); p(0x26,'26_hall_k144.png')
g(0x03,'03_ship_fl.png','03_ship_mask.png','03_ship_grad.npy'); g(0x27,'27_shipdeck_fl.png','27_shipdeck_mask.png','27_shipdeck_grad.npy')
g(0x02,'02_terrace_fl.png','02_terrace_mask.png','02_terrace_grad.npy'); g(0x28,'28_island_fl.png','28_island_mask.png','28_island_grad.npy'); p(0x15,'15_hall_fl.png')
for n in ['01_cave','05_shrine','09_dungeon','0A_tower','0B_bridge','0C_sund','0D_river','0E_lakecave','0F_lake','10_moss','11_vine','12_lava','13_crystal','14_ruby','16_gratze','17_ahall','2A_cavelever','2B_cavetorch','2C_dungwater','2D_dungbones','2E_hallstairs','2F_library']:
    p(int(n[:2],16),n+'_fl.png')
SP='/tmp/claude-0/-home-claude/94b3994a-61e1-50a5-81a3-e47f92eae4ae/scratchpad/seasons/prep/'
PLACES=['Lake','River','Farm']; SEASONS=['Spring','Summer','Fall','Winter']; TIMES=['Day','Sunrise','Sunset','Night']
SEASONAL=[]
# Seasonal conversion settings (test build 3): floor-only palette from tile row 16 down; merge weights
# x2 for the ground (tile rows 12+) so the band below the horizon keeps its tiles.
SEASON_KW=dict(floor_row=16,row_weight=[1.0]*12+[2.0]*16)
FLOOR_ROW=16
FLOOR_RECS=set(int(x,16) for x in os.environ.get('FLOOR_RECS','').split(',') if x) if os.environ.get('FLOOR_RECS')!='all' else set(range(0x40,0x70))
for pi,pl in enumerate(PLACES):
    for si,se in enumerate(SEASONS):
        for ti,tm in enumerate(TIMES):
            rec=0x40+pi*16+si*4+ti; n='%s_%s_%s'%(pl,se,tm)
            J.append((rec,SP+n+'_fl.png',np.asarray(Image.open(SP+n+'_mask.png'))>127,np.load(SP+n+'_grad.npy'),None,dict(focus=(0,27),**SEASON_KW))); SEASONAL.append(rec)
ids=[j[0] for j in J]; assert len(ids)==len(set(ids)); print(len(J),'pictures',flush=True)
for j in J: assert os.path.exists(j[1]),j[1]
CD=F+'cache/'

import pickle, hashlib as _h, bbg_convert as B, bbg_gradient as G
from multiprocessing import Pool
CD=F+'cache/'; os.makedirs(CD,exist_ok=True)
_orig=B.convert_n
def _key(img,kw):
    h=_h.md5(np.asarray(img.convert('RGB')).tobytes())
    for k in sorted(kw):
        v=kw[k]; h.update(k.encode()); h.update(np.asarray(v).tobytes() if v is not None else b'N')
    return CD+h.hexdigest()+'.pkl'
def cached(img,**kw):
    f=_key(img,kw)
    if os.path.exists(f): return pickle.load(open(f,'rb'))
    r=_orig(img,**kw); pickle.dump(r,open(f,'wb')); return r
B.convert_n=cached
def _pre(job):
    import warnings; warnings.filterwarnings('ignore')
    mask=job[2] if len(job)>2 else None; grad=job[3] if len(job)>3 else None
    end=G.sky_end(mask) if mask is not None else None
    cached(Image.open(job[1]),npal=3,mask=mask,max_tiles=426,backdrop=None if grad is None else G.quantized(grad,end),outliers=3,smooth=0.3,**(job[5] if len(job)>5 else {}))
    return job[0]
if __name__=='__main__':
    with Pool(2) as P:
        for i in P.imap_unordered(_pre,J): print('converted %02X'%i,flush=True)
t=time.time()
rep=bbg_build.build(S+'base_rir.sfc',F+'s1.sfc',J,3,426,dict(outliers=3,smooth=0.3),keep_orig_pals=False)
for r in rep: print(r,flush=True)
print('bbg_build %.0f s'%(time.time()-t),flush=True)
subprocess.run(['/home/claude/lufia2/deps/asar/build/asar/bin/asar','--fix-checksum=off','/home/claude/lufia2/mods/bgext.asm',F+'s1.sfc'],check=True)
print(terrain_patch.build(F+'s1.sfc',F+'s2.sfc',{},[(F+'hill_zone.npy',0x19)]),flush=True)
V={0x00:[0x22,0x23],0x01:[0x2A,0x2B],0x02:[0x28,0x15],0x03:[0x27],0x04:[0x1A,0x1B]+SEASONAL,0x06:[0x1C,0x1D],0x07:[0x20,0x21],0x08:[0x25,0x26],0x09:[0x2C,0x2D],0x15:[0x02,0x28],0x17:[0x2E,0x2F],0x19:[0x1E,0x1F]}
import shutil; shutil.copy(F+'s2.sfc',F+'s3.sfc')
subprocess.run(['/home/claude/lufia2/deps/asar/build/asar/bin/asar','--fix-checksum=off','/home/claude/lufia2/mods/variants2.asm',F+'s3.sfc'],check=True)
rom=bytearray(open(F+'s3.sfc','rb').read())
vt=bytearray(128)
for i,alts in V.items():
    assert 0<len(alts)<255 and all(a!=0x18 for a in alts)
    vt[2*i:2*i+2]=len(vt).to_bytes(2,'little'); vt+=bytes([len(alts)])+b''.join(a.to_bytes(2,'little') for a in alts)
q=lo(0xDFF600); assert not any(rom[q:q+len(vt)]) and len(vt)<=0xA00
rom[q:q+len(vt)]=vt; open(F+'s3.sfc','wb').write(rom); print('variant table',len(vt),'bytes',flush=True)
rom=bytearray(open(F+'s3.sfc','rb').read()); q=lo(0x88BE40)
assert rom[q:q+5]==bytes.fromhex('4b19740453'),rom[q:q+5].hex()
rom[q+3]=0x24
rom[0x7FDC:0x7FE0]=bytes([0xFF,0xFF,0,0]); s=sum(rom)&0xFFFF
rom[0x7FDE:0x7FE0]=s.to_bytes(2,'little'); rom[0x7FDC:0x7FDE]=(s^0xFFFF).to_bytes(2,'little')
open(F+'lufia2_rir_bg3.sfc','wb').write(rom)
print('final CRC %08X SHA1 %s'%(zlib.crc32(rom),hashlib.sha1(rom).hexdigest()),'total %.0f s'%(time.time()-t),flush=True)
