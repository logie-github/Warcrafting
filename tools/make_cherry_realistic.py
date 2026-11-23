import sys
sys.path.insert(0,'/home/user/Warcrafting/tools')
import mdx_render as M
import numpy as np
from PIL import Image,ImageDraw
F='/tmp/claude-0/fruit/'
rng=np.random.default_rng(3)
def cherry_texture(n=256):
    y,x=np.mgrid[0:n,0:n]/n
    base=np.array([0.50,0.02,0.05])
    lat=y                                   # 0 = top pole, 1 = bottom
    shade=1.15-0.55*lat
    noise=rng.normal(0,0.02,(n,n))
    col=base[None,None,:]*shade[...,None]+noise[...,None]*0.5
    # soft broad highlight toward the lit side (u~0.3, v~0.35) and a small sharp one
    for (cu,cv,r,k,c) in [(0.30,0.36,0.16,0.75,(1.0,0.75,0.75)),(0.30,0.36,0.045,1.0,(1.0,1.0,1.0))]:
        d=np.sqrt(((x-cu+0.5)%1-0.5)**2*0.5+(y-cv)**2)
        g=np.exp(-(d/r)**2)*k
        col=col*(1-g[...,None])+np.array(c)[None,None,:]*g[...,None]
    # darker rim near bottom and a deeper red at the stem dimple
    dim=np.exp(-(y/0.07)**2)[...,None]; col=col*(1-0.5*dim)
    out=np.concatenate([np.clip(col,0,1),np.ones((n,n,1))],-1).astype(np.float32)
    return out
def flat(c):
    t=np.ones((8,8,4),np.float32);t[...,0],t[...,1],t[...,2]=c;return t
def sphere(cx,r=0.1,nu=40,nv=28):
    V=[];N=[];UV=[];I=[]
    for j in range(nv+1):
        th=np.pi*j/nv; 
        for i in range(nu+1):
            ph=2*np.pi*i/nu
            p=np.array([np.sin(th)*np.cos(ph),np.sin(th)*np.sin(ph),np.cos(th)])
            q=p.copy()
            q[2]*=0.93
            # dimple at the top pole and slight heart pinch
            dim=np.exp(-(th/0.28)**2)*0.22
            q[2]-=dim; q[0]*=1.0+0.03*np.cos(ph)
            V.append(q*r+np.array([cx,0,r*0.93])); N.append(p); UV.append([i/nu,j/nv])
    for j in range(nv):
        for i in range(nu):
            a=j*(nu+1)+i;b=a+1;c=a+nu+1;d=c+1
            I+= [[a,c,b],[b,c,d]]
    return {'v':np.array(V,np.float32),'n':np.array(N,np.float32),'uv':np.array(UV,np.float32),'idx':np.array(I),'mat':0}
def tube(p0,p1,p2,r0=0.0065,r1=0.005,ns=18,nr=8):
    t=np.linspace(0,1,ns)[:,None]
    pts=(1-t)**2*p0+2*(1-t)*t*p1+t**2*p2
    tang=np.gradient(pts,axis=0);tang/=np.linalg.norm(tang,axis=1,keepdims=True)
    V=[];N=[];UV=[];I=[]
    for k in range(ns):
        a=np.cross(tang[k],[0,1,0]);a/=np.linalg.norm(a);b=np.cross(tang[k],a)
        r=r0+(r1-r0)*k/(ns-1)
        for m in range(nr+1):
            ang=2*np.pi*m/nr;d=np.cos(ang)*a+np.sin(ang)*b
            V.append(pts[k]+d*r);N.append(d);UV.append([m/nr,k/(ns-1)])
    for k in range(ns-1):
        for m in range(nr):
            a=k*(nr+1)+m;b=a+1;c=a+nr+1;d=c+1;I+=[[a,c,b],[b,c,d]]
    return {'v':np.array(V,np.float32),'n':np.array(N,np.float32),'uv':np.array(UV,np.float32),'idx':np.array(I),'mat':0}
# peach leaf (green triangles above the body)
PC=M.parse_m2(open(F+'5242776.m2','rb').read(),open(F+'5243001.bin','rb').read())['geosets'][0]
ptex=np.asarray(Image.open(F+'5242995.blp').convert('RGBA'),dtype=np.float32)/255.0
ph,pw=ptex.shape[:2];pv=PC['v']
def tex_at(t):
    uv=PC['uv'][t].mean(0);return ptex[int((uv[1]%1)*ph)%ph,int((uv[0]%1)*pw)%pw]
def is_leaf(t):
    c=tex_at(t);return pv[t,2].mean()>1.15 and c[1]>c[0]*1.05 and c[1]>0.2
lt=np.array([t for t in PC['idx'] if is_leaf(t)])
used=np.unique(lt.ravel());rm={int(i):k for k,i in enumerate(used)}
leaf={'v':pv[used].copy(),'n':PC['n'][used].copy(),'uv':PC['uv'][used].copy(),'idx':np.vectorize(rm.get)(lt),'mat':0}
p=leaf['v'];c=p.mean(0);p-=c;p*=0.13
# orient so leaf points outward/up, place near the joint
def place(g,off,rotz=0.0):
    g=dict(g);g['v']=g['v'].copy()
    R=np.array([[np.cos(rotz),-np.sin(rotz),0],[np.sin(rotz),np.cos(rotz),0],[0,0,1]])
    g['v']=g['v']@R.T+off;return g
dx=0.115;top=0.205;joint=np.array([0.0,0.0,0.46])
bodyL=sphere(-dx);bodyR=sphere(dx)
stemL=tube(np.array([-dx,0,top]),np.array([-dx*0.9,0,0.36]),joint)
stemR=tube(np.array([dx,0,top]),np.array([dx*0.9,0,0.36]),joint)
leafg=place(leaf,joint+np.array([0.03,0.0,0.015]),0.5)
model={'textures':[],'materials':[],'geosets':[bodyL,bodyR,stemL,stemR,leafg]}
ctex=cherry_texture();stex=flat((0.36,0.25,0.12))
tx=lambda gi,g,m:(ctex if gi<2 else (stex if gi<4 else ptex))
S=420
W=Image.new('RGB',(3*S,S+22),(30,30,34));d=ImageDraw.Draw(W)
for i,(pitch,yaw) in enumerate([(14,20),(8,70),(20,-35)]):
    big=M.render(model,tx,size=S*2,pitch=pitch,yaw=yaw)
    W.paste(big.resize((S,S),Image.LANCZOS),(i*S,22));d.text((i*S+4,5),'Cherries',fill=(255,255,0))
W.save('/tmp/claude-0/fruit/cherry_real.png')
