import sys,glob,os
sys.path.insert(0,'/home/user/Warcrafting/tools')
import mdx_render as M
from PIL import Image,ImageDraw
R='/tmp/claude-0/trees/'
def find(p): 
    g=glob.glob(R+'**/'+p,recursive=True); return g[0] if g else None
sets=[('Lordaeron summer','lordaerontree','replaceabletextures/lordaerontree/lordaeronsummertree.dds'),
('Barrens','barrenstree','replaceabletextures/barrenstree/barrenstree.dds'),
('Ashenvale','ashentree','replaceabletextures/ashenvaletree/ashentree.dds'),
('Ruins','ruinstree','replaceabletextures/ruinstree/ruinstree.dds'),
('Northrend','northrendtree','replaceabletextures/northrendtree/northtree.dds')]
os.makedirs('/tmp/claude-0/treesheets',exist_ok=True)
S=300
for name,folder,tex in sets:
    tp=find(tex.split('/',1)[1]) if False else glob.glob(R+'**/'+tex,recursive=True)[0]
    T=M.load_texture(tp)
    W=Image.new('RGB',(5*S,2*(S+20)),(30,30,34));d=ImageDraw.Draw(W)
    for i in range(10):
        f=find(f'{folder}{i}.mdx')
        m=M.parse_mdx(open(f,'rb').read())
        im=M.render(m,lambda gi,g,mm:T,size=S)
        x,y=(i%5)*S,(i//5)*(S+20)
        W.paste(im,(x,y+20));d.text((x+4,y+4),f'{folder}{i}  ({sum(len(g["idx"]) for g in m["geosets"] if "idx" in g)} tris)',fill=(255,255,0))
    W.save(f'/tmp/claude-0/treesheets/{folder}.png');print(name,'done')
