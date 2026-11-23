import sys,glob,os
sys.path.insert(0,'/home/user/Warcrafting/tools')
import mdx_render as M
import numpy as np
from PIL import Image,ImageDraw
U='/tmp/claude-0/units/'
def find(base):
    g=[p for p in glob.glob(U+'**/*',recursive=True) if os.path.basename(p).lower()==base.lower()]
    return g[0] if g else None
def tex_loader(model,team=(0.15,0.35,0.9)):
    cache={}
    def f(gi,g,m):
        mat=m['materials'][g['mat']] if g['mat']<len(m['materials']) else []
        if not mat: return None
        if all(l['filter'] in (3,4) for l in mat): return None
        for l in reversed(mat):
            if l['filter'] in (3,4): continue
            rid,path=m['textures'][l['tex']]
            if rid in (1,2): continue
            base=path.replace('\\','/').split('/')[-1] if path else ''
            if not base or base.lower()=='gutz.blp': continue
            p=find(base)
            if not p: continue
            if p not in cache: cache[p]=M.load_texture(p)
            return cache[p]
        for l in mat:
            if m['textures'][l['tex']][0] in (1,2) and l['filter'] not in (3,4):
                a=np.ones((8,8,4),np.float32);a[...,0],a[...,1],a[...,2]=team;return a
        return None
    return f
models=[('Peasant','Peasant.mdx',(0.2,0.4,0.95)),('Peon','peon.mdx',(0.85,0.15,0.1)),('Sorceress','Sorceress_v1.mdx',(0.2,0.4,0.95)),('Dark Ranger','BansheeRanger.mdx',(0.5,0.1,0.7))]
S=360
W=Image.new('RGB',(4*S,2*(S+20)),(30,30,34));d=ImageDraw.Draw(W)
for i,(n,fn,team) in enumerate(models):
    m=M.parse_mdx(open(find(fn),'rb').read())
    ld=tex_loader(m,team)
    keep=[]
    for gi,g in enumerate(m['geosets']):
        mat=m['materials'][g['mat']] if g['mat']<len(m['materials']) else []
        paths=' '.join(m['textures'][l['tex']][1].lower() for l in mat)
        if 'resours' in paths: continue
        if ld(gi,g,m) is None: continue
        keep.append(g)
    m['geosets']=keep
    for r,yaw in enumerate((30,200)):
        big=M.render(m,tex_loader(m,team),size=S*2,yaw=yaw,pitch=12)
        W.paste(big.resize((S,S),Image.LANCZOS),(i*S,r*(S+20)+20));d.text((i*S+4,r*(S+20)+4),f'{n} ({"front" if r==0 else "back"})',fill=(255,255,0))
W.save('/tmp/claude-0/units_preview.png');print('ok')
