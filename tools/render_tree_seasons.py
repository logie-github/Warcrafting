import sys,glob,os,colorsys
sys.path.insert(0,'/home/user/Warcrafting/tools')
import mdx_render as M
import numpy as np
from PIL import Image,ImageDraw
R='/tmp/claude-0/trees/'
def f1(p): return glob.glob(R+'**/'+p,recursive=True)[0]
def tex(p): return M.load_texture(f1(p))
def rgb2hsv(rgb):
    r,g,b=rgb[...,0],rgb[...,1],rgb[...,2]
    mx=rgb.max(-1);mn=rgb.min(-1);d=mx-mn
    h=np.zeros_like(mx)
    m=d>1e-6
    rc=np.where(m&(mx==r),((g-b)/np.where(m,d,1))%6,0)
    gc=np.where(m&(mx==g)&(mx!=r),(b-r)/np.where(m,d,1)+2,0)
    bc=np.where(m&(mx==b)&(mx!=r)&(mx!=g),(r-g)/np.where(m,d,1)+4,0)
    h=(rc+gc+bc)/6.0
    s=np.where(mx>1e-6,d/np.where(mx>1e-6,mx,1),0)
    return np.stack([h%1.0,s,mx],-1)
def hsv2rgb(hsv):
    h,s,v=hsv[...,0],hsv[...,1],hsv[...,2]
    i=np.floor(h*6).astype(int)%6;f=h*6-np.floor(h*6)
    p=v*(1-s);q=v*(1-f*s);t=v*(1-(1-f)*s)
    r=np.choose(i,[v,q,p,p,t,v]);g=np.choose(i,[t,v,v,q,p,p]);b=np.choose(i,[p,p,t,v,v,q])
    return np.stack([r,g,b],-1)
def hueshift(t,mapfn):
    out=t.copy();hsv=rgb2hsv(np.clip(t[...,:3],0,1));out[...,:3]=hsv2rgb(mapfn(hsv));return out
barrens=tex('replaceabletextures/barrenstree/barrenstree.dds')
def leafmask(shape):
    H,W=shape[:2]; yy,xx=np.mgrid[0:H,0:W]
    sx=W/1024.0; sy=H/512.0
    return ((xx>=668*sx)&(yy<310*sy))|((yy>=310*sy)&(xx>=323*sx))
def to_green(hsv):
    h=hsv[...,0].copy();s=hsv[...,1];leaf=LM&(s>0.3)
    h[leaf]=0.22+((h[leaf]+0.0)%0.30)*0.2; hsv[...,0]=h; return hsv
def to_autumn(hsv):
    h=hsv[...,0].copy();s=hsv[...,1];leaf=LM&(s>0.3)&(h>0.06)&(h<0.30)
    h[leaf]=0.02+h[leaf]*0.35; hsv[...,0]=h; return hsv
def to_spring(hsv):
    h=hsv[...,0].copy();s=hsv[...,1].copy();leaf=LM&(s>0.3)
    h[leaf]=0.18+((h[leaf])%0.30)*0.25; s[leaf]=s[leaf]*0.85; hsv[...,0]=h; hsv[...,1]=s; return hsv
LM=leafmask(barrens.shape)
towns={
 'Alliance':[('Spring','lordaerontree','replaceabletextures/lordaerontree/lordaeronsummertree.dds',None),
             ('Summer','lordaerontree','replaceabletextures/lordaerontree/lordaeronsummertree.dds',None),
             ('Autumn','lordaerontree','replaceabletextures/lordaerontree/lordaeronfalltree.dds',None),
             ('Winter','northrendtree','replaceabletextures/northrendtree/northtree.dds',None)],
 'Horde':[('Spring','barrenstree',None,to_spring),('Summer','barrenstree',None,to_green),('Autumn','barrenstree',None,to_autumn),
          ('Winter','northrendtree','replaceabletextures/northrendtree/northtree.dds',None)]}
variants={'Spring':[0,3,6,8,9],'Summer':[1,2,4,5,7],'Autumn':[2,5,7,8,1],'Winter':[0,2,4,6,8]}
S=260
os.makedirs('/tmp/claude-0/seasonsheets',exist_ok=True)
for town,rows in towns.items():
    W=Image.new('RGB',(5*S,len(rows)*(S+18)),(30,30,34));d=ImageDraw.Draw(W)
    for r,(season,folder,tp,fn) in enumerate(rows):
        T=tex(tp) if tp else (hueshift(barrens,fn) if fn else barrens)
        for c,v in enumerate(variants[season]):
            m=M.parse_mdx(open(f1(f'{folder}{v}.mdx'),'rb').read())
            im=M.render(m,lambda gi,g,mm:T,size=S)
            W.paste(im,(c*S,r*(S+18)+18));d.text((c*S+4,r*(S+18)+3),f'{town} {season} - {folder}{v}',fill=(255,255,0))
    W.save(f'/tmp/claude-0/seasonsheets/{town}.png');print(town)
