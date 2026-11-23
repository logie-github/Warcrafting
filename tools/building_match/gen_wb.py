import json,io,base64,os
from PIL import Image
p=json.load(open('page_data.json'))['ac'];bb=json.load(open('ac_bbox.json'))
W=json.load(open('wb_models.json'))
slots=[]
for a in p:
    slots.append({'name':a['name'],'src':a['src'],'frames':a['frames'],'bbox':bb[str(a['id'])]})
static=[(75,'Museum'),(77,'Police Box'),(79,'Dump'),(81,'Tent'),(82,'Igloo (Kamakura)'),(83,'Food Stall (Yatai)'),(84,'Fortune Stall (Mikuji)')]
def conv(i):
    v=[float(x) for x in open(f'/tmp/claude-0/sb/{i}.txt').read().split()]
    mnx,mny,mnz,mxx,mxy,mxz=v
    return {'x':[-mxz-20000,-mnz-20000],'y':[mny+3000,mxy+3000],'z':[mnx,mxx]}
def jpg(path,w=420):
    im=Image.open(path).convert('RGB');im.thumbnail((w,w*3//4));b=io.BytesIO();im.save(b,'JPEG',quality=72);return 'data:image/jpeg;base64,'+base64.b64encode(b.getvalue()).decode()
for i,name in static:
    fr=[jpg(f'/tmp/claude-0/cat/{i}/{k:02d}.ppm') for k in range(4)]
    slots.append({'name':name,'src':'static model (viewer index %d)'%i,'frames':fr,'bbox':conv(i)})
sets=json.load(open('bcat/sets.json'))
thumbs={}
path2render={}
for sn,items in sets.items():
    for rel in items: path2render[rel]=f'/tmp/claude-0/bcat/{sn}/'+rel.replace('/','__')+'.png'
for k,m in W['models'].items():
    f=path2render.get(m['path'])
    if f and os.path.exists(f):
        im=Image.open(f).convert('RGB');im.thumbnail((120,120));b=io.BytesIO();im.save(b,'JPEG',quality=70);thumbs[k]='data:image/jpeg;base64,'+base64.b64encode(b.getvalue()).decode()
D={'slots':slots,'models':W['models'],'folders':W['folders'],'thumbs':thumbs,'textures':W['textures']}
t=open('wb_template.html').read().replace('/*DATA*/null',json.dumps(D,separators=(',',':')))
open('warcrafting_worldbuilder.html','w').write(t);print(len(t)/1e6,'MB',len(slots),'slots')
