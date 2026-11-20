# Regenerate only the floors (prep/<n>_fl.png) with the seamless-floor settings; masks and gradients stay.
import sys, glob, re
sys.path.insert(0,'/home/claude/lufia2/tools')
from PIL import Image
import bbg_floor
for f in sorted(glob.glob('in/*.png')):
    s,p,t=re.match(r'in/(Spring|Summer|Fall|Winter)(Farm|Lake|River)(Day|Night|Sunrise|Sunset)',f).groups()
    n='%s_%s_%s'%(p,s,t)
    im=Image.open(f).convert('RGB'); w,h=im.size
    fit=im.resize((256,round(h*256/w)),Image.BOX).crop((0,0,256,224))
    img,fl,info=bbg_floor.rebuild_floor(fit,sample=(150,205,32,224),patch=(128,32),min_row=96,patch_rows=(130,210),
                                        drop_below=168,seamless=True,margin=2,fade=4,anchor=160,low=(128,400))
    img.save('prep/'+n+'_fl.png'); print(n,round(info['replaced'],2),flush=True)
