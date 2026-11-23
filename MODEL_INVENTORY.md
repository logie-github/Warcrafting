# Warcrafting data inventory

Generated from the repo scripts and the extracted data. Source key:
- **Original WC3** = the original Warcraft III game data you supplied as zips, extracted to `ReignOfChaos/`, `FrozenThrone/`, `Shared/` (MDX models, BLP textures).
- **Classic+ (kenshin_lab_v1.0)** = the community 'Classic+' pack from the Google Drive link you gave ('Warcraft 3 Classic HD'). It is NOT original game data.
- **Wago** = Wago tools, used only for music.

## 1. Characters (baked into `acgc/pc/src/pc_wc3_meshes.c`, script `tools/make_wc3_meshes.py`)

| # | Role | Source | MDX | Notes |
|---|---|---|---|---|
| 0 | Player: Peasant | Original WC3 | ReignOfChaos/Units/Human/Peasant/peasant.mdx | geosets 2-5 dropped, tool components removed |
| 1 | Player: Peon | Original WC3 | ReignOfChaos/Units/Orc/Peon/peon.mdx | geosets 2-4 dropped |
| 2 | Player: Sorceress (Reign of Chaos) | Original WC3 | ReignOfChaos/Units/Human/Sorceress/Sorceress.mdx | geoset 2 dropped |
| 3 | Player: Dark Ranger | Original WC3 | FrozenThrone/Units/Creeps/BansheeRanger/BansheeRanger.mdx | geosets 2-6 dropped; walk animation reported broken |
| 4 | Thrall (replaces Tom Nook, Horde) | Original WC3 | ReignOfChaos/Units/Orc/Thrall/Thrall.mdx | |
| 5 | Grom Hellscream (replaces Rover, Horde) | Original WC3 | ReignOfChaos/Units/Orc/Hellscream/Hellscream.mdx | train-seat animation not done |

Animations baked from MDX sequences: Stand, Walk, Attack/Spell (action). Height target 7900*4/3 game units (2x the previous 2/3 size).

## 2. Alliance buildings (baked into `acgc/pc/src/pc_wc3_buildings.c`, script `tools/make_building_meshes.py`)

| Slot | Replaces | Model | MDX (Original WC3) |
|---|---|---|---|
| 1 | Nook's Cranny | Town Hall | Shared/Buildings/Human/TownHall/TownHall.mdx |
| 2 | Nook 'n' Go | Blacksmith | ReignOfChaos/Buildings/Human/Blacksmith/Blacksmith.mdx |
| 3 | Nookway | Arcane Sanctum | ReignOfChaos/Buildings/Human/ArcaneSanctum/ArcaneSanctum.mdx |
| 4 | Nookington's | Arcane Sanctum | ReignOfChaos/Buildings/Human/ArcaneSanctum/ArcaneSanctum.mdx |
| 5 | House A | Farm | ReignOfChaos/Buildings/Human/Farm/Farm.mdx |
| 6 | House B | Farm | ReignOfChaos/Buildings/Human/Farm/Farm.mdx |
| 7 | House C | Farm | ReignOfChaos/Buildings/Human/Farm/Farm.mdx |
| 8 | House D | Farm | ReignOfChaos/Buildings/Human/Farm/Farm.mdx |
| 9 | House E | Farm | ReignOfChaos/Buildings/Human/Farm/Farm.mdx |
| 10 | My Home 1 | Farm | ReignOfChaos/Buildings/Human/Farm/Farm.mdx |
| 11 | My Home 2 | Village Inn | ReignOfChaos/Doodads/LordaeronSummer/Structures/Inn/Inn.mdx |
| 12 | My Home 3 | Village Barn | ReignOfChaos/Doodads/LordaeronSummer/Structures/Barn/Barn.mdx |
| 13 | My Home 4 | Shipyard | FrozenThrone/buildings/Human/HumanShipyard/HumanShipyard.mdx |
| 14 | Station 1 | Gryphon Aviary | Shared/Buildings/Human/GryphonAviary/GryphonAviary.mdx |
| 15 | Station 2 | Gryphon Aviary | Shared/Buildings/Human/GryphonAviary/GryphonAviary.mdx |
| 16 | Station 3 | Arcane Sanctum | ReignOfChaos/Buildings/Human/ArcaneSanctum/ArcaneSanctum.mdx |
| 17 | Post Office | Windmill | ReignOfChaos/Doodads/LordaeronSummer/Structures/WindMill/WindMill.mdx |
| 18 | Able Sisters | Workshop | ReignOfChaos/Buildings/Human/Workshop/Workshop.mdx |
| 19 | Crazy Redd's | Arcane Vault | FrozenThrone/buildings/Human/ArcaneVault/ArcaneVault.mdx |
| 20 | Fortune Teller | Arcane Sanctum | ReignOfChaos/Buildings/Human/ArcaneSanctum/ArcaneSanctum.mdx |
| 21 | Statue | Altar of Kings | ReignOfChaos/Buildings/Human/AltarOfKings/AltarOfKings.mdx |
| 22 | Lighthouse | Scout Tower | Shared/Buildings/Human/HumanTower/HumanTower.mdx |

Candidate pool in the positioner (all Original WC3): the 15 Human buildings plus Lordaeron town buildings:

- Town Hall: `Shared/Buildings/Human/TownHall/TownHall.mdx`
- Farm: `ReignOfChaos/Buildings/Human/Farm/Farm.mdx`
- Barracks: `ReignOfChaos/Buildings/Human/HumanBarracks/HumanBarracks.mdx`
- Blacksmith: `ReignOfChaos/Buildings/Human/Blacksmith/Blacksmith.mdx`
- Lumber Mill: `ReignOfChaos/Buildings/Human/HumanLumberMill/HumanLumberMill.mdx`
- Workshop: `ReignOfChaos/Buildings/Human/Workshop/Workshop.mdx`
- Arcane Sanctum: `ReignOfChaos/Buildings/Human/ArcaneSanctum/ArcaneSanctum.mdx`
- Altar of Kings: `ReignOfChaos/Buildings/Human/AltarOfKings/AltarOfKings.mdx`
- Gryphon Aviary: `Shared/Buildings/Human/GryphonAviary/GryphonAviary.mdx`
- Scout Tower: `Shared/Buildings/Human/HumanTower/HumanTower.mdx`
- Arcane Vault: `FrozenThrone/buildings/Human/ArcaneVault/ArcaneVault.mdx`
- Shipyard: `FrozenThrone/buildings/Human/HumanShipyard/HumanShipyard.mdx`
- Village Barn: `ReignOfChaos/Doodads/LordaeronSummer/Structures/Barn/Barn.mdx`
- Village Inn: `ReignOfChaos/Doodads/LordaeronSummer/Structures/Inn/Inn.mdx`
- Windmill: `ReignOfChaos/Doodads/LordaeronSummer/Structures/WindMill/WindMill.mdx`
- Town Small0_0: `ReignOfChaos/Buildings/Other/CityBuildingSmall0_0/CityBuildingSmall0_0.mdx`
- Town Small0_1: `ReignOfChaos/Buildings/Other/CityBuildingSmall0_1/CityBuildingSmall0_1.mdx`
- Town Small0_2: `ReignOfChaos/Buildings/Other/CityBuildingSmall0_2/CityBuildingSmall0_2.mdx`
- Town Small45_0: `ReignOfChaos/Buildings/Other/CityBuildingSmall45_0/CityBuildingSmall45_0.mdx`
- Town Small45_1: `ReignOfChaos/Buildings/Other/CityBuildingSmall45_1/CityBuildingSmall45_1.mdx`
- Town Small45_2: `ReignOfChaos/Buildings/Other/CityBuildingSmall45_2/CityBuildingSmall45_2.mdx`
- Town Small90_0: `ReignOfChaos/Buildings/Other/CityBuildingSmall90_0/CityBuildingSmall90_0.mdx`
- Town Small90_1: `ReignOfChaos/Buildings/Other/CityBuildingSmall90_1/CityBuildingSmall90_1.mdx`
- Town Small90_2: `ReignOfChaos/Buildings/Other/CityBuildingSmall90_2/CityBuildingSmall90_2.mdx`
- Town Small135_0: `ReignOfChaos/Buildings/Other/CityBuildingSmall135_0/CityBuildingSmall135_0.mdx`
- Town Small135_1: `ReignOfChaos/Buildings/Other/CityBuildingSmall135_1/CityBuildingSmall135_1.mdx`
- Town Small135_2: `ReignOfChaos/Buildings/Other/CityBuildingSmall135_2/CityBuildingSmall135_2.mdx`
- Town Large_0: `ReignOfChaos/Buildings/Other/CityBuildingLarge_0/CityBuildingLarge_0.mdx`
- Town Large_45: `ReignOfChaos/Buildings/Other/CityBuildingLarge_45/CityBuildingLarge_45.mdx`
- Town Large_90: `ReignOfChaos/Buildings/Other/CityBuildingLarge_90/CityBuildingLarge_90.mdx`
- Town Large_135: `ReignOfChaos/Buildings/Other/CityBuildingLarge_135/CityBuildingLarge_135.mdx`
- Cathedral: `ReignOfChaos/Doodads/Cityscape/Structures/Cathedral/Cathedral.mdx`
- Tavern: `FrozenThrone/buildings/Other/Tavern/Tavern.mdx`
- GrainWarehouse: `ReignOfChaos/Buildings/Other/GrainWarehouse/GrainWarehouse.mdx`

## 3. Not original game data (to review)

- **Ground textures** (`mod/ground`, `mod/pack`): fitted from Classic+ terrain tiles (`kenshin_lab_v1.0/Classic+/terrainart`); snow is a recolor of the grass.
- **Trees** (render sheets only, not wired into the game): Classic+ models `kenshin_lab_v1.0/Classic+/doodads/terrain/{lordaerontree,barrenstree,northrendtree,ashentree,ruinstree}*.mdx` with Classic+ DDS textures. These are NOT original WC3 models.
- **Cherries/fruit** (render only): built from Classic+ tree textures (`199733.blp`, `5242995.blp`).
- **Music** (`mod/music`, Horde town): Orgrimmar tracks from Wago: orgrimmar-intro, orgrimmar01-moment, orgrimmar01-zone, orgrimmar02-moment, orgrimmar02-zone.
- **Title logo and app icon**: supplied by you.

## 4. Animal Crossing models still in use

Every villager, the town props (bridge, flag, mailbox, lotus, train, boat, event props, gacha/sewing machines), the Museum, Police Box, Dump, Tent, Igloo, Food Stall, Fortune Stall, Shrine, and all interiors remain the original Animal Crossing models, as do the building clocks/windows/signs.
