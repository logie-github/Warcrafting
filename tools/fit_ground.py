#!/usr/bin/env python3
"""Fit Classic+ (kenshin_lab) terrain tiles to Animal Crossing ground slots.

usage: fit_ground.py <Classic+/terrainart dir> <out dir>

Each Classic+ tile is a blend atlas. The top-left 128x128 cell is opaque and
seamless, so it is used as the plain fill. Output: one PNG and one BC3 DDS per
AC ground slot, per faction. Final filenames (tex1_WxH_<hash>_<fmt>.dds) need
hashes of the original disc textures and are applied later by the hash step.
"""
import os, sys
from PIL import Image

# AC slot -> (WxH of original CI4 texture, alliance tile, horde tile)
SLOTS = {
    'grass':   ((32, 32), 'lordaeronsummer/lords_grass', 'barrens/barrens_grass'),
    'earth':   ((64, 64), 'lordaeronsummer/lords_dirt',  'barrens/barrens_dirt'),
    'cliff':   ((64, 64), 'lordaeronsummer/lords_rock',  'barrens/barrens_rock'),
    'sand':    ((32, 32), 'ruins/ruins_sand',            'barrens/barrens_desert'),
    'stone':   ((64, 64), 'village/village_stonepath',   'barrens/barrens_pebbles'),
    'rail':    ((64, 64), 'village/village_cobblepath',  'barrens/barrens_dirtrough'),
    'bush_a':  ((64, 64), 'village/village_grassthick',  'barrens/barrens_dirtgrass'),
}
CELL = 128

def cell(path):
    im = Image.open(path).convert('RGBA')
    c = im.crop((0, 0, CELL, CELL))
    bg = Image.new('RGBA', c.size, (0, 0, 0, 255))
    bg.alpha_composite(c)
    return bg.convert('RGB')

def main(src, out):
    for fi, faction in ((1, 'alliance'), (2, 'horde')):
        d = os.path.join(out, faction)
        os.makedirs(d, exist_ok=True)
        for slot, spec in SLOTS.items():
            t = cell(os.path.join(src, spec[fi] + '.dds'))
            t.save(os.path.join(d, slot + '.png'))
            t.convert('RGBA').save(os.path.join(d, slot + '.dds'), pixel_format='DXT5')

if __name__ == '__main__':
    main(*sys.argv[1:3])
