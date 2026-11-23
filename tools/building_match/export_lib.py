import sys,os,glob,json,base64,io
sys.path.insert(0,'/home/user/Warcrafting/tools')
import numpy as np
from PIL import Image
import mdx_render as M, mdx_anim as A
from multiprocessing import Pool
R='/tmp/claude-0/wc3full/'
idx={}
for root in ('ReignOfChaos','FrozenThrone','Shared'):
    for p in glob.glob(R+root+'/**/*',recursive=True):
        if os.path.isfile(p): idx.setdefault(os.path.basename(p).lower(),p)
TEAM=(150,150,165)
LIGHT=np.array([.4,.8,.5]);LIGHT/=np.linalg.norm(LIGHT)
def work(ent):
    rel=ent['path'];cap=256 if ent['cat'].startswith('Buildings') else 128
    try:
        data=open(R+rel,'rb').read();mm=M.parse_mdx(data);am=A.Model(data)
        st=am.seq('stand') or am.seq('birth');posed=am.pose(st[1]) if st else [g['v'] for g in am.geosets]
        meshes=[];texs={}
        keep=[]
        for gi,g in enumerate(mm['geosets']):
            if 'uv' not in g or 'idx' not in g: continue
            mats=mm['materials'][g['mat']]
            if all(l['filter'] in (3,4) for l in mats): continue
            if st and A.geoset_visible(am,gi,st)<=0.1: continue
            v=posed[gi]
            if len(g['idx'])<=8 and (v[:,2].max()-v[:,2].min())<2.0: continue
            tkey=None
            for l in reversed(mats):
                if l['filter'] in (3,4): continue
                rid,pth=mm['textures'][l['tex']]
                if rid in (1,2): tkey='team';break
                b=pth.replace('\\','/').split('/')[-1].lower() if pth else ''
                if b and b in idx: tkey=b;break
            if tkey is None: continue
            P=np.stack([-v[:,1],v[:,2],v[:,0]],1).astype(np.float32)
            meshes.append((P,np.asarray(g['uv'],np.float32),np.asarray(g['idx'],np.uint16).ravel(),tkey))
            h=dict(g);h['v']=v.astype(np.float32);keep.append((h,tkey))
        if not meshes: return None
        for P,UV,I,tkey in meshes:
            if tkey in texs: continue
            im=Image.new('RGBA',(8,8),TEAM+(255,)) if tkey=='team' else Image.open(idx[tkey]).convert('RGBA')
            if max(im.size)>cap: im.thumbnail((cap,cap),Image.LANCZOS)
            b=io.BytesIO();im.save(b,'PNG');texs[tkey]=b.getvalue()
        allp=np.concatenate([m[0] for m in meshes]);lo=allp.min(0);hi=allp.max(0)
        # thumbnail
        cache={}
        def lt(gi,g,mo):
            tk=keep[gi][1]
            if tk not in cache: cache[tk]=np.asarray(Image.open(io.BytesIO(texs[tk])).convert('RGBA'),np.float32)/255.0
            return cache[tk]
        mm2=dict(mm);mm2['geosets']=[k[0] for k in keep]
        thumb=M.render(mm2,lt,size=128,yaw=35,pitch=24,bg=(41,41,59))
        tb=io.BytesIO();thumb.convert('RGB').save(tb,'JPEG',quality=68)
        out=[]
        for P,UV,I,tkey in meshes:
            out.append(dict(pos=np.clip((P-lo)/np.maximum(hi-lo,1e-6)*65535,0,65535).astype(np.uint16).tobytes(),
                            uv=np.clip(np.round(UV*2048),-32768,32767).astype(np.int16).tobytes(),idx=I.tobytes(),tex=tkey))
        return dict(ent=ent,meshes=out,min=lo.tolist(),max=hi.tolist(),texs=texs,thumb=tb.getvalue())
    except Exception as e:
        return None
if __name__=='__main__':
    ents=json.load(open('/tmp/claude-0/lib/sets.json'))
    import pickle
    res=[]
    with Pool(4) as p:
        for i,r in enumerate(p.imap(work,ents,chunksize=4)):
            if r: res.append(r)
            if i%100==0: print(i,len(ents),len(res),flush=True)
    pickle.dump(res,open('/tmp/claude-0/lib/export.pkl','wb'))
    open('/tmp/claude-0/lib/export_done','w').write(str(len(res)))
    print('done',len(res))
