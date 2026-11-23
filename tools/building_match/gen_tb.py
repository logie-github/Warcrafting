import json,re
W=json.load(open('wb_models.json'))
thumbs=json.loads(open('warcrafting_worldbuilder.html').read().split('const D = ')[1].split(';\n// D.slots')[0])['thumbs']
blocks=[];bx=bz=0
for l in open('town_dump.txt'):
    p=l.split()
    if p[0]=='blocks': bx,bz=int(p[1]),int(p[2])
    elif p[0]=='block': blocks.append({'x':int(p[1]),'z':int(p[2]),'kind':int(p[4])})
ab=json.load(open('ac_bbox.json'))
import json as j
pages=j.load(open('page_data.json'))['ac']
slots={}
for a in pages:
    b=ab[str(a['id'])];slots[a['name'].replace(' (shop stage 1)',' (Nook’s Cranny)') if False else a['name']]={'w':(b['x'][1]-b['x'][0])/100,'d':(b['z'][1]-b['z'][0])/100,'h':b['y'][1]/100}
# key names used by the page
def S(name,src): 
    b=ab[str(src)];return {'w':(b['x'][1]-b['x'][0])/100,'d':(b['z'][1]-b['z'][0])/100,'h':b['y'][1]/100}
names={'Shop 1 (Nook’s Cranny)':0,'Train station - model 1':26,'Police Box':None,'Post office':32,'Museum':None,'Dump':None,'Town statue':42,'Able Sisters (tailor)':34,'Your house - stage 1':18}
S2={}
for k,v in names.items():
    if v is not None: S2[k]=S(k,v)
S2['Police Box']={'w':120,'d':120,'h':150};S2['Museum']={'w':250,'d':200,'h':140};S2['Dump']={'w':180,'d':180,'h':60}
D={'town':{'bx':bx,'bz':bz,'blocks':blocks},'slots':S2,'models':W['models'],'folders':W['folders'],'thumbs':thumbs,'textures':W['textures']}
t=open('tb_template.html').read().replace('/*DATA*/null',json.dumps(D,separators=(',',':')))
open('warcrafting_townbuilder.html','w').write(t);print(len(t)/1e6,'MB',bx,bz,len(blocks))
