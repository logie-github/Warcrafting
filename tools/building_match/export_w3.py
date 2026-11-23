import sys,os,glob,json,base64,io,struct
sys.path.insert(0,'/home/user/Warcrafting/tools')
import numpy as np
from PIL import Image
import mdx_render as M, mdx_anim as A
R='/tmp/claude-0/wc3full/'
idx={}
for root in ('ReignOfChaos','FrozenThrone','Shared'):
    for p in glob.glob(R+root+'/**/*',recursive=True):
        if os.path.isfile(p): idx.setdefault(os.path.basename(p).lower(),p)
exec(open('/tmp/claude-0/w3_turn.py').read().split("N=16")[0].split("BG=(41,41,59)")[1])   # HUMAN / ORC lists
TEAM={'human':(40,90,230),'orc':(220,40,25)}
def b64(a): return base64.b64encode(a.tobytes()).decode()
def export(fac,items):
    tex_table=[];tex_index={}
    def tex_id(key,img):
        if key in tex_index: return tex_index[key]
        im=img.convert('RGBA')
        if max(im.size)>512: im.thumbnail((512,512),Image.LANCZOS)
        buf=io.BytesIO();
        has_alpha=np.asarray(im)[...,3].min()<250
        if has_alpha: im.save(buf,'PNG',optimize=True);mime='image/png'
        else: im.convert('RGB').save(buf,'JPEG',quality=82);mime='image/jpeg'
        tex_table.append('data:%s;base64,%s'%(mime,base64.b64encode(buf.getvalue()).decode()));tex_index[key]=len(tex_table)-1;return tex_index[key]
    models={}
    for name,path in items:
        fp=R+path
        if not os.path.exists(fp):
            alt=glob.glob(R+'**/'+os.path.basename(path),recursive=True)
            if not alt: print('missing',path);continue
            fp=alt[0]
        data=open(fp,'rb').read();mm=M.parse_mdx(data);am=A.Model(data)
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
                    tid=tex_id('team_'+fac,Image.new('RGBA',(8,8),TEAM[fac]+(255,)));break
                b=pth.replace('\\','/').split('/')[-1].lower() if pth else ''
                if b and b in idx:
                    tid=tex_id(b,Image.open(idx[b]) if idx[b].lower().endswith(('.png','.jpg')) else _blp(idx[b]));break
            if tid is None: continue
            P=np.stack([-v[:,1],v[:,2],v[:,0]],1).astype(np.float32)   # Y up, front +Z
            meshes.append(dict(pos=b64(P),uv=b64(np.asarray(g['uv'],np.float32)),idx=b64(np.asarray(g['idx'],np.uint16).ravel()),n=len(P),ni=int(len(g['idx'])*3),tex=tid))
        allp=np.concatenate([np.frombuffer(base64.b64decode(m['pos']),np.float32).reshape(-1,3) for m in meshes])
        models[name]=dict(path=path,meshes=meshes,min=allp.min(0).tolist(),max=allp.max(0).tolist())
        print(fac,name,len(meshes),'meshes',[round(x) for x in allp.min(0)],[round(x) for x in allp.max(0)],flush=True)
    return models,tex_table
def _blp(p):
    return M_load(p)
def M_load(p):
    return Image.open(p)
hm,ht=export('human',HUMAN)
json.dump(dict(models=hm,textures=ht),open('/tmp/claude-0/w3_human_3d.json','w'))
print(len(ht),'textures')
