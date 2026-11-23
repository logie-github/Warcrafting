import json
H=json.load(open('/tmp/claude-0/lib/html_lib.json'))
blocks=[];bx=bz=0
for l in open('/tmp/claude-0/town_dump.txt'):
    p=l.split()
    if p[0]=='blocks': bx,bz=int(p[1]),int(p[2])
    elif p[0]=='block': blocks.append({'x':int(p[1]),'z':int(p[2]),'kind':int(p[4])})
ab=json.load(open('/tmp/claude-0/ac_bbox.json'))
ids=[0,2,4,6,8,10,12,14,16,18,20,22,24,26,28,30,32,34,36,38,42,44]
def S(bid):
    b=ab[str(bid)];return {'w':(b['x'][1]-b['x'][0])/100,'d':(b['z'][1]-b['z'][0])/100,'h':b['y'][1]/100}
def C(slot):
    b=ab[str(ids[slot])];return {'id':slot,'cx':(b['x'][0]+b['x'][1])/200,'cz':(b['z'][0]+b['z'][1])/200}
slots={'Shop 1 (Nook’s Cranny)':S(0),'Train station - model 1':S(26),'Police Box':{'w':120,'d':120,'h':150},'Post office':S(32),'Museum':{'w':270,'d':192,'h':140},'Dump':{'w':180,'d':180,'h':60},'Town statue':S(42),'Able Sisters (tailor)':S(34),'Your house - stage 1':S(18)}
repl={'Shop':{'slots':[C(i) for i in (0,1,2,3)]},'Station':{'slots':[C(i) for i in (13,14,15)]},'Post office':{'slots':[C(16)]},'Able Sisters':{'slots':[C(17)]},'Player house':{'slots':[C(i) for i in (9,10,11,12)]}}
D={'town':{'bx':bx,'bz':bz,'blocks':blocks},'slots':slots,'repl':repl,**H}
t=open('/tmp/claude-0/tb2_template.html').read().replace('/*DATA*/null',json.dumps(D,separators=(',',':')))
import os
os.makedirs('/tmp/claude-0/builder',exist_ok=True)
open('/tmp/claude-0/builder/index.html','w').write(t);print(len(t)/1e6,'MB')
