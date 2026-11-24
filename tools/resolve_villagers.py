import csv,glob,os,json,collections,re
R='/tmp/claude-0/wc3full/'
idx={}
for root in ('ReignOfChaos','FrozenThrone','Shared'):
    for p in glob.glob(R+root+'/Units/**/*.mdx',recursive=True):
        b=os.path.basename(p)[:-4]
        if b.lower().endswith('_portrait') or 'portrait' in b.lower() or b.lower().endswith('cin'): continue
        idx.setdefault(b.lower(),p[len(R):])
def M(*names):
    out=[]
    for n in names:
        if n.lower() in idx: out.append(n)
        else: print('missing model name',n)
    return out
# pools: list of (keywords, models) in priority order; last entry (None,..) = default cycle
POOL={
'Human':[(('footman','captain','marshal','watchman','shieldbearer','militia','banner'),M('Footman','Militia')),(('knight','outrider','stablemaster'),M('Knight')),(('rifleman','archer','crossbow','scout'),M('Rifleman')),(('priest','cleric','medic','inquisitor'),M('Priest')),(('sorceress','conjurer'),M('Sorceress')),(('archmage','apprentice','mage'),M('HumanMage')),(('paladin',),M('Uther')),(('peasant','farmer','merchant','herbalist','cartographer'),M('Peasant','VillagerMan','VillagerWoman')),(None,M('VillagerMan','VillagerWoman','Peasant','Footman','VillagerMan1'))],
'Dwarf':[(('rifleman','thunderer','mountaineer'),M('Rifleman')),(('mortar','artillerist','siege','demolition','steam'),M('MortarTeam')),(('mountain king','shieldguard'),M('HeroMountainKing')),(('gryphon',),M('GryphonRider')),(None,M('Muradin','HeroMountainKing'))],
'Gnome':[(None,M('Peasant','Militia'))],
'Night Elf':[(('archer','scout','tracker','ranger'),M('Archer')),(('huntress','sentinel'),M('Huntress')),(('priestess','moon','sage'),M('HeroMoonPriestess')),(('warden',),M('HeroWarden','Maiev')),(('druid','herbalist','dryad'),M('Dryad')),(None,M('Archer','Huntress','ElfVillagerWoman','Shandris','Maiev'))],
'High Elf':[(('archer','ranger','scout'),M('HighElfArcher')),(None,M('HighElfPeasant','HighElfArcher','HumanMage'))],
'Blood Elf':[(('peasant','farmer','merchant'),M('BloodElfPeasant')),(('thief','spell','rogue'),M('BloodElfSpellThief')),(('lieutenant','captain','knight'),M('BloodElfLieutenant')),(None,M('BloodElfPeasant','BloodElfSpellThief','BloodElfLieutenant','Kael'))],
'Draenei':[(('mage','shaman','priest','vindicator'),M('DranaiMage','DranaiWhite')),(None,M('Dranai','DranaiMage','DranaiWhite','DranaiAkama'))],
'Worgen':[(None,M('WhiteWolf','TimberWolf','DireWolf'))],
'Dark Iron Dwarf':[(None,M('Muradin','HeroMountainKing'))],
'Kul Tiran':[(None,M('Proudmoore','Militia','Knight','Footman'))],
'Mechagnome':[(None,M('HeroTinkerRobot'))],
'Furbolg':[(('shaman','elder'),M('FurbolgShaman','FurbolgElder')),(('tracker',),M('FurbolgTracker')),(None,M('Furbolg','FurbolgPanda','PolarFurbolg'))],
'Harpy':[(('witch','queen'),M('HarpyWitch','HarpyQueen')),(None,M('Harpy'))],
'Makrura':[(None,M('Lobstrokkred','Lobstrokkblue','Lobstrokkgreen'))],
'Orc':[(('peon','herbalist','blacksmith','armorer','quartermaster'),M('Peon')),(('shaman','spirit','earth','storm','totem'),M('Shaman')),(('warlock',),M('OrcWarlock')),(('blademaster','berserker','firebrand'),M('HeroBladeMaster')),(('far seer','farseer'),M('HeroFarseer')),(('wolfrider','outrider','raider'),M('Wolfrider')),(('hunter','axethrower','scout','skirmisher'),M('HeadHunter','Grunt')),(('beast','handler','tamer'),M('Beastmaster')),(None,M('Grunt','Peon','Shaman'))],
'Troll':[(('witch','doctor','medicine','hexer','oracle','venom','spirit','fire dancer'),M('WitchDoctor','ForestTrollShadowPriest')),(('batrider',),M('BatTroll')),(('shadow hunter',),M('HeroShadowHunter')),(('trapper','ambusher','stalker','tracker','scalper'),M('ForestTrollTrapper','DarkTrollTrapper')),(None,M('HeadHunter','ForestTroll','IceTroll','DarkTroll'))],
'Zandalari Troll':[(None,M('DarkTroll','DarkTrollTrapper','DarkTrollShadowPriest'))],
'Tauren':[(('chieftain',),M('HeroTaurenChieftain')),(('spirit','walker','shaman','sunwalker'),M('SpiritWalker')),(None,M('Tauren','SpiritWalker'))],
'Forsaken':[(('acolyte','priest','cultist'),M('Acolyte')),(('necromancer','plague','mage'),M('Necromancer')),(('ghoul',),M('Ghoul')),(('banshee','ranger','dark'),M('Banshee','BansheeRanger')),(('abomination','butcher'),M('Abomination')),(None,M('Acolyte','Ghoul','Skeleton','Necromancer','Zombie'))],
'Goblin':[(('sapper','mine','demolition'),M('GoblinSapper')),(('alchem','chemist','potion'),M('HEROGoblinALCHEMIST')),(None,M('HeroTinker','GoblinSapper','HEROGoblinALCHEMIST'))],
'Ogre':[(('magi','mage','shaman'),M('OgreMagi')),(('lord','chief','king'),M('OgreLord')),(None,M('Ogre','OgreOneHeaded','OgreLord'))],
'Moknathal':[(None,M('Rexxar'))],
'Hozen':[(None,M('Sasquatch','Wendigo'))],
'Vulpera':[(None,M('Raccoon','Rat'))],
'Murloc':[(('warrior','tidewarrior'),M('MurlocWarrior')),(('flesh','eater'),M('MurlocFleshEater')),(('night','crawler'),M('MurlocNightCrawler')),(None,M('Murloc','MurlocWarrior','MurlocMutant'))],
'Naga':[(('siren',),M('NagaSiren')),(('summoner','tide','witch'),M('NagaSummoner')),(('guard','royal'),M('NagaRoyalGuard')),(None,M('NagaMyrmidon','NagaSiren','NagaSummoner','NagaRoyalGuard'))],
'Gnoll':[(('archer',),M('GnollArcher')),(('warden',),M('GnollWarden')),(('overseer',),M('GnollOverSeer')),(None,M('Gnoll','GnollArcher'))],
'Centaur':[(('archer',),M('CentaurArcher')),(('khan','chief'),M('CentaurKhan')),(None,M('Centaur','CentaurArcher'))],
'Kobold':[(('geomancer',),M('KoboldGeomancer')),(None,M('Kobold'))],
}
f='/root/.claude/uploads/16791841-fdf9-5928-8378-eba12022b2ed/aaf3e223-warcraft_animal_crossing_436_full_roster.csv'
rows=list(csv.DictReader(open(f,encoding='utf-8-sig')))
cyc=collections.Counter()
for r in rows:
    race=r['Race'];name=r['Model'].lower();pool=POOL[race]
    sel=None;why=''
    for kw,ms in pool:
        if kw and ms and any(k in name for k in kw): sel=ms[cyc[(race,kw)]%len(ms)];cyc[(race,kw)]+=1;why='role';break
    if sel is None:
        ms=pool[-1][1];sel=ms[cyc[(race,None)]%len(ms)];cyc[(race,None)]+=1;why='race'
    r['Model Asset Path']=idx[sel.lower()];r['Resolved Unit']=sel
    exact={'Human','Orc','Night Elf','Undead'}
    r['Unit Source Status']=('W3 unit, matched by role' if why=='role' else 'W3 unit, matched by race')+('' if race in ('Human','Orc','Night Elf','Forsaken','Troll','Tauren','Ogre','Goblin','Murloc','Naga','Gnoll','Centaur','Kobold','Furbolg','Harpy','Makrura','Dwarf','High Elf','Blood Elf','Draenei','Moknathal') else ' (approximate: no Warcraft III equivalent)')
out='/tmp/claude-0/vil/roster_resolved.csv'
cols=list(rows[0].keys())
if 'Resolved Unit' not in cols: cols.insert(cols.index('Model Asset Path')+1,'Resolved Unit')
w=csv.DictWriter(open(out,'w',newline='',encoding='utf-8'),fieldnames=cols);w.writeheader();w.writerows(rows)
u=collections.OrderedDict()
for r in rows: u.setdefault(r['Resolved Unit'],[]).append(r['Race'])
print(len(u),'distinct W3 units used for',len(rows),'villagers')
print({k:len(v) for k,v in list(u.items())[:80]})
json.dump(u,open('/tmp/claude-0/vil/units_used.json','w'))
json.dump({k:idx[k.lower()] for k in u},open('/tmp/claude-0/vil/unit_paths.json','w'))
