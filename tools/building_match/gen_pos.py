import json
p=json.load(open('page_data.json'))['ac']; bb=json.load(open('ac_bbox.json')); w=json.load(open('w3_human_3d.json'))
C=[["Town Hall"],["Blacksmith","Lumber Mill","Barracks","Workshop"],["Arcane Sanctum","Blacksmith","Barracks","Workshop","Lumber Mill"],["Arcane Sanctum","Workshop","Shipyard"]]+[["Farm"]]*6+[["Village Inn"],["Village Barn"],["Shipyard"],["Arcane Sanctum","Shipyard","Gryphon Aviary"],["Gryphon Aviary","Shipyard"],["Arcane Sanctum"],["Windmill","Arcane Sanctum"],["Workshop"],["Arcane Vault"],["Arcane Sanctum"],["Altar of Kings"],["Scout Tower"]]
assert len(C)==22
t=json.load(open('w3_town_3d.json'))
TOWN=list(t['models'])
off=len(w['textures'])
for m in t['models'].values():
    for me in m['meshes']: me['tex']+=off
w['textures']=w['textures']+t['textures']; w['models'].update(t['models'])
C=[c+TOWN for c in C]
ac=[]
for a,c in zip(p,C):
    b=bb[str(a['id'])]
    if 'x' not in b: b={'x':[b['min'][0],b['max'][0]],'y':[b['min'][1],b['max'][1]],'z':[b['min'][2],b['max'][2]]}
    ac.append({'name':a['name'],'src':a['src'],'frames':a['frames'],'bbox':b,'cands':c})
used={n for c in C for n in c}
D={'ac':ac,'models':{n:w['models'][n] for n in used},'textures':w['textures']}
t=open('positioner_template.html').read().replace('/*DATA*/null',json.dumps(D,separators=(',',':')))
open('warcrafting_positioner.html','w').write(t);print(len(t))
