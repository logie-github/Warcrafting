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
# stem from apple: top triangles
v=ap['v'];z=v[:,2];zt=z.min()+0.62*(z.max()-z.min())
def texel(u,vv):
    h,w=atlas.shape[:2];return atlas[int((vv%1)*h)%h,int((u%1)*w)%w]
def greenish(t):
    uv=ap['uv'][t].mean(0);c=texel(uv[0],uv[1]);return c[1]>c[0]*0.95 and c[1]>0.15
tris=np.array([t for t in ap['idx'] if all(z[i]>zt*0.6 for i in t) and greenish(t)])
print('stem tris',len(tris))
used=np.unique(tris.ravel());remap={int(i):k for k,i in enumerate(used)}
stem={'v':v[used].copy(),'n':ap['n'][used].copy(),'uv':ap['uv'][used].copy(),'idx':np.vectorize(remap.get)(tris),'mat':0}
def body(dx):
    g={k:(vv.copy() if hasattr(vv,'copy') else vv) for k,vv in orr.items()}
    g['v']=g['v']*0.42; g['v'][:,0]+=dx; return g
def mkstem(dx,lean):
    """Apple stem as modelled (4 triangle sprig), unstretched, upright, uniformly scaled onto the cherry top."""
    g={k:(vv.copy() if hasattr(vv,'copy') else vv) for k,vv in stem.items()}
    p=g['v']; base=p[:,2].min(); cx=p[:,:2].mean(0)
    p[:,:2]-=cx; p[:,2]-=base
    p*=0.75
    p[:,2]+=0.16; p[:,0]+=dx
    g['v']=p; return g
dx=0.13
cher={'textures':[],'materials':[],'geosets':[body(-dx),body(dx),mkstem(-dx,0.55),mkstem(dx,-0.55)]}
tex=lambda gi,g,m: cherry_tex if gi<2 else atlas
S=320
W=Image.new('RGB',(3*S,S+20),(30,30,34));d=ImageDraw.Draw(W)
for i,(pitch,yaw) in enumerate([(20,35),(15,80),(25,-30)]):
    W.paste(M.render(cher,tex,size=S,pitch=pitch,yaw=yaw),(i*S,20));d.text((i*S+4,4),'Cherries (orange body recoloured, apple stems)',fill=(255,255,0))
W.save('/tmp/claude-0/fruit/cherry.png')
