import os,json,glob,base64,io
from PIL import Image,ImageEnhance
import numpy as np
BG=np.array([40,40,60])
W_,H_=320,240
def frames_for(paths,bright):
    ims=[Image.open(p).convert('RGB') for p in paths]
    # union bbox of non-background pixels
    box=None
    for im in ims:
        a=np.asarray(im).astype(int)
        m=(np.abs(a-BG).sum(-1)>24)
        ys,xs=np.where(m)
        if len(xs)==0: continue
        b=(xs.min(),ys.min(),xs.max(),ys.max())
        box=b if box is None else (min(box[0],b[0]),min(box[1],b[1]),max(box[2],b[2]),max(box[3],b[3]))
    if box is None: box=(0,0,ims[0].width-1,ims[0].height-1)
    x0,y0,x1,y1=box;w=x1-x0+1;h=y1-y0+1
    sc=min((W_-24)/w,(H_-24)/h)
    out=[]
    for im in ims:
        c=im.crop((x0,y0,x1+1,y1+1)).resize((max(1,int(w*sc)),max(1,int(h*sc))),Image.LANCZOS)
        if bright!=1.0:
            a0=np.asarray(c).astype(float)
            mask=(np.abs(a0-BG).sum(-1)>24)[...,None]
            a1=np.clip(a0*bright,0,255)
            c=Image.fromarray(np.where(mask,a1,a0).astype('uint8'))
        canvas=Image.new('RGB',(W_,H_),tuple(int(v) for v in BG))
        canvas.paste(c,((W_-c.width)//2,(H_-c.height)//2))
        buf=io.BytesIO();canvas.save(buf,'JPEG',quality=74);out.append('data:image/jpeg;base64,'+base64.b64encode(buf.getvalue()).decode())
    return out
AC_NAMES={0:"Nook's Cranny (shop stage 1)",2:"Nook 'n' Go (shop stage 2)",4:"Nookway (shop stage 3)",6:"Nookington's (shop stage 4)",
 8:"Villager house A",10:"Villager house B",12:"Villager house C",14:"Villager house D",16:"Villager house E",
 18:"Your house - stage 1",20:"Your house - stage 2",22:"Your house - stage 3",24:"Your house - stage 4",
 26:"Train station - model 1",28:"Train station - model 2",30:"Train station - model 3",32:"Post office",34:"Able Sisters (tailor)",36:"Crazy Redd's tent",38:"Katrina's fortune teller tent",42:"Town statue",44:"Lighthouse"}
AC_SRC={0:'Shop 1',2:'Shop 2',4:'Shop 3',6:'Shop 4',8:'House 1',10:'House 2',12:'House 3',14:'House 4',16:'House 5',18:'My Home 1',20:'My Home 2',22:'My Home 3',24:'My Home 4',26:'Station 1',28:'Station 2',30:'Station 3',32:'Post Office',34:'Tailor',36:"Redd's Shop",38:'Fortune Teller',42:'Statue',44:'Lighthouse'}
ac=[]
for i in sorted(AC_NAMES):
    fs=sorted(glob.glob(f'/tmp/claude-0/acb/{i}/*.ppm'))
    ac.append(dict(id=i,name=AC_NAMES[i],src='viewer model '+AC_SRC[i],frames=frames_for(fs,1.7)))
PATHS={'Town Hall':'Buildings/Human/TownHall','Farm':'Buildings/Human/Farm','Barracks':'Buildings/Human/HumanBarracks','Blacksmith':'Buildings/Human/Blacksmith','Lumber Mill':'Buildings/Human/HumanLumberMill','Workshop':'Buildings/Human/Workshop','Arcane Sanctum':'Buildings/Human/ArcaneSanctum','Altar of Kings':'Buildings/Human/AltarOfKings','Gryphon Aviary':'Buildings/Human/GryphonAviary','Scout Tower':'Buildings/Human/HumanTower','Arcane Vault':'Buildings/Human/ArcaneVault','Shipyard':'Buildings/Human/HumanShipyard','Village Barn':'Doodads/LordaeronSummer/Structures/Barn','Village Inn':'Doodads/LordaeronSummer/Structures/Inn','Windmill':'Doodads/LordaeronSummer/Structures/WindMill'}
ORCP={'Great Hall':'Buildings/Orc/GreatHall','Barracks':'Buildings/Orc/OrcBarracks','War Mill':'Buildings/Orc/WarMill','Troll Burrow':'Buildings/Orc/TrollBurrow','Altar of Storms':'Buildings/Orc/AltarOfStorms','Spirit Lodge':'Buildings/Orc/SpiritLodge','Bestiary':'Buildings/Orc/Beastiary','Tauren Totem':'Buildings/Orc/TaurenTotem','Watch Tower':'Buildings/Orc/WatchTower','Voodoo Lounge':'Buildings/Orc/VoodooLounge'}
w3={'human':[],'orc':[]}
for fac,paths in (('human',PATHS),('orc',ORCP)):
    for d in sorted(glob.glob(f'/tmp/claude-0/w3b/{fac}/*')):
        name=os.path.basename(d).replace('_',' ')
        fs=sorted(glob.glob(d+'/*.png'))
        w3[fac].append(dict(name=name,src='Warcraft III '+('Human' if fac=='human' else 'Orc')+': '+paths.get(name,name),frames=frames_for(fs,1.0)))
print(len(ac),len(w3['human']),len(w3['orc']))
json.dump(dict(ac=ac,w3=w3),open('/tmp/claude-0/page_data.json','w'))
