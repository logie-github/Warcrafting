import sys,os,glob,json,base64,io
sys.path.insert(0,'/home/user/Warcrafting/tools')
import numpy as np
from PIL import Image
import mdx_render as M, mdx_anim as A
R='/tmp/claude-0/wc3full/'
idx={}
for root in ('ReignOfChaos','FrozenThrone','Shared'):
    for p in glob.glob(R+root+'/**/*',recursive=True):
        if os.path.isfile(p): idx.setdefault(os.path.basename(p).lower(),p)
sets=json.load(open('/tmp/claude-0/bcat/sets.json'))
TEAM={'Alliance':(40,90,230),'Horde':(220,40,25),'Neutral':(150,150,160)}
tex_table=[];tex_index={}
def b64(a): return base64.b64encode(a.tobytes()).decode()
def tex_id(key,im):
    if key in tex_index: return tex_index[key]
    im=im.convert('RGBA')
    if max(im.size)>256: im.thumbnail((256,256),Image.LANCZOS)
    buf=io.BytesIO()
    if np.asarray(im)[...,3].min()<250: im.save(buf,'PNG',optimize=True);mime='image/png'
    else: im.convert('RGB').save(buf,'JPEG',quality=70);mime='image/jpeg'
    tex_table.append('data:%s;base64,%s'%(mime,base64.b64encode(buf.getvalue()).decode()));tex_index[key]=len(tex_table)-1;return tex_index[key]
def category(setname,rel):
    parts=rel.split('/')
    low=[x.lower() for x in parts]
    if 'doodads' in low:
        d=parts[low.index('doodads')+1]
        return f'{setname} / Doodad structures / {d}'
    if 'buildings' in low:
        d=parts[low.index('buildings')+1]
        return f'{setname} / {d} buildings'
    return f'{setname} / Other'
models={};folders={}
for setname,items in sets.items():
    for rel in items:
        try:
            data=open(R+rel,'rb').read();mm=M.parse_mdx(data);am=A.Model(data)
            st=am.seq('stand') or am.seq('birth');posed=am.pose(st[1]) if st else [g['v'] for g in am.geosets]
            meshes=[]
            for gi,g in enumerate(mm['geosets']):
                if 'uv' not in g or 'idx' not in g: continue
                mats=mm['materials'][g['mat']]
                if all(l['filter'] in (3,4) for l in mats): continue
                if st and A.geoset_visible(am,gi,st)<=0.1: continue
                v=posed[gi]
                if len(g['idx'])<=8 and (v[:,2].max()-v[:,2].min())<2.0: continue
                tid=None
                for l in reversed(mats):
                    if l['filter'] in (3,4): continue
                    rid,pth=mm['textures'][l['tex']]
                    if rid in (1,2):
                        tid=tex_id('team_'+setname,Image.new('RGBA',(8,8),TEAM[setname]+(255,)));break
                    b=pth.replace('\\','/').split('/')[-1].lower() if pth else ''
                    if b and b in idx:
                        tid=tex_id(b,Image.open(idx[b]));break
                if tid is None: continue
                P=np.stack([-v[:,1],v[:,2],v[:,0]],1).astype(np.float32)
                meshes.append((P,np.asarray(g['uv'],np.float32),np.asarray(g['idx'],np.uint16).ravel(),tid))
            if not meshes: continue
            allp=np.concatenate([m[0] for m in meshes]);lo=allp.min(0);hi=allp.max(0)
            out=[]
            for P,UV,I,tid in meshes:
                out.append(dict(pos=b64(np.clip((P-lo)/np.maximum(hi-lo,1e-6)*65535,0,65535).astype(np.uint16)),
                                uv=b64(np.clip(np.round(UV*2048),-32768,32767).astype(np.int16)),idx=b64(I),tex=tid))
            name=os.path.basename(rel)[:-4]
            key=name if name not in models else f'{name} ({setname})'
            models[key]=dict(path=rel,meshes=out,min=lo.tolist(),max=hi.tolist())
            folders.setdefault(category(setname,rel),[]).append(key)
        except Exception as e: print('skip',rel,e)
print(len(models),'models',len(tex_table),'textures')
json.dump(dict(models=models,folders=folders,textures=tex_table),open('/tmp/claude-0/wb_models.json','w'),separators=(',',':'))
print(os.path.getsize('/tmp/claude-0/wb_models.json')/1e6,'MB')
for k,v in sorted(folders.items()): print(k,len(v))
