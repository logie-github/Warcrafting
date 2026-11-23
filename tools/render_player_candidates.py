import sys,os,glob
sys.path.insert(0,'/home/user/Warcrafting/tools')
import mdx_render as M
import numpy as np
from PIL import Image,ImageDraw
R='/tmp/claude-0/wc3full/'
idx={}
for root in ('ReignOfChaos','FrozenThrone','Shared'):
    for p in glob.glob(R+root+'/**/*',recursive=True):
        if os.path.isfile(p): idx.setdefault(os.path.basename(p).lower(),p)
cache={}
def tex(path):
    b=path.replace('\\','/').split('/')[-1].lower()
    if b not in cache: cache[b]=M.load_texture(idx[b])
    return cache[b]
def comps(g):
    n=len(g['v']);par=list(range(n))
    def f(x):
        while par[x]!=x: par[x]=par[par[x]];x=par[x]
        return x
    key={}
    for i,p in enumerate(np.round(g['v'],2)):
        k=tuple(p)
        if k in key: par[f(i)]=f(key[k])
        else: key[k]=i
    for a,b,c in g['idx']: par[f(a)]=f(b);par[f(b)]=f(c)
    lab={};out=[]
    for t in g['idx']:
        r=f(t[0]);lab.setdefault(r,len(lab));out.append(lab[r])
    return np.array(out)
def subset(g,drop_comps):
    lab=comps(g);keep=np.array([l not in drop_comps for l in lab])
    h=dict(g);h['idx']=g['idx'][keep];return h
# model path, whole geosets dropped, {geoset: components dropped}
SPEC=[('Peasant','ReignOfChaos/Units/Human/Peasant/peasant.mdx',{2,3,4,5},{0:{4,7}}),
      ('Peon','ReignOfChaos/Units/Orc/Peon/peon.mdx',{2,3,4},{0:{0,5}}),
      ('Sorceress','ReignOfChaos/Units/Human/Sorceress/Sorceress.mdx',{2},{}),
      ('Dark Ranger','FrozenThrone/Units/Creeps/BansheeRanger/BansheeRanger.mdx',{2,3,4,5,6},{0:{5,6,8,10,11}})]
def build(fn,dropg,dropc):
    m=M.parse_mdx(open(R+fn,'rb').read());gs=[]
    for gi,g in enumerate(m['geosets']):
        if gi in dropg: continue
        gs.append(subset(g,dropc[gi]) if gi in dropc else g)
    m['geosets']=gs;return m
def loader(gi,g,m):
    mat=m['materials'][g['mat']];l=[l for l in mat if m['textures'][l['tex']][0]==0][-1]
    return tex(m['textures'][l['tex']][1])
if __name__=='__main__':
    S=330
    W=Image.new('RGB',(4*S,4*(S+18)),(30,30,34));d=ImageDraw.Draw(W)
    for r,(n,fn,dg,dc) in enumerate(SPEC):
        m=build(fn,dg,dc)
        for c,yaw in enumerate((0,60,150,240)):
            big=M.render(m,loader,size=S*2,yaw=yaw,pitch=10)
            W.paste(big.resize((S,S),Image.LANCZOS),(c*S,r*(S+18)+18));d.text((c*S+4,r*(S+18)+3),f'{n} ({yaw} deg)',fill=(255,255,0))
    W.save('/tmp/claude-0/four_nohands.png');print('ok')
