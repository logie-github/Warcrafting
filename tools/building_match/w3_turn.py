import sys,os,glob,json
sys.path.insert(0,'/home/user/Warcrafting/tools')
import mdx_render as M
import mdx_anim as A
import numpy as np
from PIL import Image
R='/tmp/claude-0/wc3full/'
idx={}
for root in ('ReignOfChaos','FrozenThrone','Shared'):
    for p in glob.glob(R+root+'/**/*',recursive=True):
        if os.path.isfile(p): idx.setdefault(os.path.basename(p).lower(),p)
BG=(41,41,59)
HUMAN=[('Town Hall','Shared/Buildings/Human/TownHall/TownHall.mdx'),('Farm','ReignOfChaos/Buildings/Human/Farm/Farm.mdx'),('Barracks','ReignOfChaos/Buildings/Human/HumanBarracks/HumanBarracks.mdx'),
('Blacksmith','ReignOfChaos/Buildings/Human/Blacksmith/Blacksmith.mdx'),('Lumber Mill','ReignOfChaos/Buildings/Human/HumanLumberMill/HumanLumberMill.mdx'),('Workshop','ReignOfChaos/Buildings/Human/Workshop/Workshop.mdx'),
('Arcane Sanctum','ReignOfChaos/Buildings/Human/ArcaneSanctum/ArcaneSanctum.mdx'),('Altar of Kings','ReignOfChaos/Buildings/Human/AltarOfKings/AltarOfKings.mdx'),('Gryphon Aviary','Shared/Buildings/Human/GryphonAviary/GryphonAviary.mdx'),
('Scout Tower','Shared/Buildings/Human/HumanTower/HumanTower.mdx'),('Arcane Vault','FrozenThrone/buildings/Human/ArcaneVault/ArcaneVault.mdx'),('Shipyard','FrozenThrone/buildings/Human/HumanShipyard/HumanShipyard.mdx'),
('Village Barn','ReignOfChaos/Doodads/LordaeronSummer/Structures/Barn/Barn.mdx'),('Village Inn','ReignOfChaos/Doodads/LordaeronSummer/Structures/Inn/Inn.mdx'),('Windmill','ReignOfChaos/Doodads/LordaeronSummer/Structures/WindMill/WindMill.mdx')]
ORC=[('Great Hall','ReignOfChaos/Buildings/Orc/GreatHall/GreatHall.mdx'),('Barracks','ReignOfChaos/Buildings/Orc/OrcBarracks/OrcBarracks.mdx'),('War Mill','ReignOfChaos/Buildings/Orc/WarMill/WarMill.mdx'),
('Troll Burrow','Shared/Buildings/Orc/TrollBurrow/TrollBurrow.mdx'),('Altar of Storms','Shared/Buildings/Orc/AltarOfStorms/AltarofStorms.mdx'),('Spirit Lodge','Shared/Buildings/Orc/SpiritLodge/SpiritLodge.mdx'),
('Bestiary','ReignOfChaos/Buildings/Orc/Beastiary/Beastiary.mdx'),('Tauren Totem','ReignOfChaos/Buildings/Orc/TaurenTotem/TaurenTotem.mdx'),('Watch Tower','ReignOfChaos/Buildings/Orc/WatchTower/WatchTower.mdx'),('Voodoo Lounge','FrozenThrone/buildings/Orc/VoodooLounge/VoodooLounge.mdx')]
N=16;S=360
def render_set(faction,items,team):
    out={}
    for name,path in items:
        fp=R+path
        if not os.path.exists(fp):
            alt=[p for p in glob.glob(R+'**/'+os.path.basename(path),recursive=True)]
            if not alt: print('missing',path);continue
            fp=alt[0]
        data=open(fp,'rb').read()
        mm=M.parse_mdx(data)
        am=A.Model(data)
        st=am.seq('stand') or am.seq('birth')
        posed=am.pose(st[1]) if st else [g['v'] for g in am.geosets]
        keep=[]
        for gi,g in enumerate(mm['geosets']):
            if 'uv' not in g or 'idx' not in g: continue
            if all(l['filter'] in (3,4) for l in mm['materials'][g['mat']]): continue
            if st and A.geoset_visible(am,gi,st)<=0.1: continue
            v=posed[gi]
            if len(g['idx'])<=8 and (v[:,2].max()-v[:,2].min())<2.0: continue   # flat ground plates
            h=dict(g);h['v']=v.astype(np.float32);keep.append(h)
        mm['geosets']=keep
        cache={}
        def lt(gi,g,mo):
            mat=mo['materials'][g['mat']]
            for l in reversed(mat):
                if l['filter'] in (3,4): continue
                rid,pth=mo['textures'][l['tex']]
                if rid in (1,2):
                    a=np.ones((8,8,4),np.float32);a[...,0],a[...,1],a[...,2]=team;return a
                b=pth.replace('\\','/').split('/')[-1].lower() if pth else ''
                if b and b in idx:
                    if b not in cache: cache[b]=M.load_texture(idx[b])
                    return cache[b]
            return None
        d=f'/tmp/claude-0/w3b/{faction}/{name.replace(" ","_")}';os.makedirs(d,exist_ok=True)
        for k in range(N):
            im=M.render(mm,lt,size=S*2,yaw=k*360.0/N,pitch=24,bg=BG)
            im.resize((S,S),Image.LANCZOS).save(f'{d}/{k:02d}.png')
        print(faction,name,len(mm['geosets']),'geosets',flush=True)
render_set('human',HUMAN,(0.15,0.35,0.9))
render_set('orc',ORC,(0.85,0.15,0.1))
