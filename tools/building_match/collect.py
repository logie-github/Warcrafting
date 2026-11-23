import glob,os,json,collections
R='/tmp/claude-0/wc3full/'
names=collections.OrderedDict()
def add(cat,pat):
    for root in ('ReignOfChaos','FrozenThrone','Shared'):
        for p in sorted(glob.glob(R+root+'/'+pat,recursive=True)):
            low=p.lower()
            if not low.endswith('.mdx') or low.endswith('_portrait.mdx'): continue
            b=os.path.basename(p)[:-4]
            if any(x in b.lower() for x in ('ruin','destroyed','rubble','_dead','construction','death','portrait')): continue
            key=b.lower()
            if key in names: continue
            names[key]=dict(name=b,cat=cat,path=p[len(R):])
for k in ('Human','Orc','Other','NightElf','Undead','Naga','Demon'):
    add(f'Buildings / {k}',f'[Bb]uildings/{k}/**/*.mdx')
cats=set()
for root in ('ReignOfChaos','FrozenThrone'):
    for d in os.listdir(R+root+'/Doodads'):
        for s in os.listdir(R+root+'/Doodads/'+d):
            if 'Cliff' in s or 'Portraits' in s or 'GlowingRunes' in s: continue
            cats.add((d,s))
for d,s in sorted(cats):
    add(f'Props / {d} / {s}',f'Doodads/{d}/{s}/**/*.mdx')
json.dump(list(names.values()),open('sets.json','w'))
print(len(names))
