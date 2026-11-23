import sys
sys.path.insert(0,'/home/user/Warcrafting/tools'); sys.path.insert(0,'/tmp/claude-0')
import mdx_render as M
import numpy as np
from PIL import Image,ImageDraw
exec(open('/tmp/claude-0/render_seasons.py').read().split("def leafmask")[0].split("barrens=tex")[0].split("R='/tmp/claude-0/trees/'")[0])
src=open('/tmp/claude-0/render_seasons.py').read()
a=src.index('def rgb2hsv');b=src.index('barrens=tex');exec(src[a:b].replace('def hueshift','def _hs'))
F='/tmp/claude-0/fruit/'
ap=M.parse_m2(open(F+'199724.m2','rb').read(),open(F+'505647.bin','rb').read())['geosets'][0]
orr=M.parse_m2(open(F+'199730.m2','rb').read(),open(F+'505644.bin','rb').read())['geosets'][0]
atlas=np.asarray(Image.open(F+'199733.blp').convert('RGBA'),dtype=np.float32)/255.0
hsv=rgb2hsv(np.clip(atlas[...,:3],0,1))
o=(hsv[...,0]>0.04)&(hsv[...,0]<0.16)&(hsv[...,1]>0.35)      # orange pixels
hsv[...,0]=np.where(o,0.995,hsv[...,0]); hsv[...,1]=np.where(o,np.minimum(1,hsv[...,1]*1.15),hsv[...,1]); hsv[...,2]=np.where(o,hsv[...,2]*0.62,hsv[...,2])
cherry_tex=atlas.copy();cherry_tex[...,:3]=hsv2rgb(hsv)
# stem from the peach model: brown stick + leaf (triangles above the body)
PC=M.parse_m2(open(F+'5242776.m2','rb').read(),open(F+'5243001.bin','rb').read())['geosets'][0]
ptex=np.asarray(Image.open(F+'5242995.blp').convert('RGBA'),dtype=np.float32)/255.0
ph,pw=ptex.shape[:2]
pv=PC['v']
def ptexel(t):
    uv=PC['uv'][t].mean(0);return ptex[int((uv[1]%1)*ph)%ph,int((uv[0]%1)*pw)%pw]
def is_stem(t):
    c=ptexel(t)
    if pv[t,2].mean()<1.15: return False
    green=c[1]>c[0]*1.05 and c[1]>0.2
    brown=c[0]<0.5 and c[0]>c[2]*1.3 and 0.1<c[1]<c[0]*0.9
    return green or brown
tris=np.array([t for t in PC['idx'] if is_stem(t)])
print('peach stem tris',len(tris))
used=np.unique(tris.ravel());remap={int(i):k for k,i in enumerate(used)}
stem={'v':pv[used].copy(),'n':PC['n'][used].copy(),'uv':PC['uv'][used].copy(),'idx':np.vectorize(remap.get)(tris),'mat':0}
def body(dx):
    g={k:(vv.copy() if hasattr(vv,'copy') else vv) for k,vv in orr.items()}
    g['v']=g['v']*0.42; g['v'][:,0]+=dx; return g
def mkstem(dx,lean):
    g={k:(vv.copy() if hasattr(vv,'copy') else vv) for k,vv in stem.items()}
    p=g['v']; base=p[:,2].min(); cx=p[:,:2].mean(0)
    p[:,:2]-=cx; p[:,2]-=base
    p[:,:2]*=0.2; p[:,2]*=0.36
    p[:,2]+=0.15; p[:,0]+=dx+lean*(p[:,2]-0.15)
    g['v']=p; return g
dx=0.13
cher={'textures':[],'materials':[],'geosets':[body(-dx),body(dx),mkstem(-dx,0.5),mkstem(dx,-0.5)]}
tex=lambda gi,g,m: cherry_tex if gi<2 else ptex
S=320
W=Image.new('RGB',(3*S,S+20),(30,30,34));d=ImageDraw.Draw(W)
for i,(pitch,yaw) in enumerate([(20,35),(15,80),(25,-30)]):
    W.paste(M.render(cher,tex,size=S,pitch=pitch,yaw=yaw),(i*S,20));d.text((i*S+4,4),'Cherries (orange body recoloured, peach stems)',fill=(255,255,0))
W.save('/tmp/claude-0/fruit/cherry.png')
