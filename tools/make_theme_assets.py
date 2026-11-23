#!/usr/bin/env python3
"""Warcraft III launcher theme assets from the original game UI files.

usage: make_theme_assets.py <wc3 root> <res/drawable-nodpi dir>
  wc3_bg_alliance.jpg   Lordaeron campaign loading screen (UI/Glues/Loading/Backgrounds/Campaigns/Lordaeron-*)
  wc3_bg_horde.jpg      Barrens campaign loading screen
  wc3_crest_human.png   Human symbol, alpha from luminance
  wc3_crest_orc.png     Orc symbol
  wc3_stone.png         Orc options-menu button stone texture
"""
import sys, os
from PIL import Image, ImageChops

def comp(ui, name):
    t = [Image.open(f'{ui}Glues/Loading/Backgrounds/Campaigns/{name}-{p}.blp').convert('RGB') for p in ('TopLeft', 'TopRight', 'BotLeft', 'BotRight')]
    w, h = t[0].size
    im = Image.new('RGB', (w * 2, h * 2))
    for img, pos in zip(t, ((0, 0), (w, 0), (0, h), (w, h))): im.paste(img, pos)
    return im.crop((0, 0, w * 2, int(h * 1.5)))

def crest(path):
    im = Image.open(path).convert('RGB')
    a = ImageChops.lighter(ImageChops.lighter(im.getchannel('R'), im.getchannel('G')), im.getchannel('B')).point(lambda v: min(255, int(v * 3.0)))
    out = im.convert('RGBA'); out.putalpha(a)
    return out

def main(root, out):
    ui = root.rstrip('/') + '/ReignOfChaos/UI/'
    os.makedirs(out, exist_ok=True)
    comp(ui, 'Lordaeron').save(os.path.join(out, 'wc3_bg_alliance.jpg'), quality=86)
    comp(ui, 'Barrens').save(os.path.join(out, 'wc3_bg_horde.jpg'), quality=86)
    crest(ui + 'Glues/Loading/Backgrounds/Campaigns/HumanSymbol.blp').save(os.path.join(out, 'wc3_crest_human.png'), optimize=True)
    crest(ui + 'Glues/Loading/Backgrounds/Campaigns/OrcSymbol.blp').save(os.path.join(out, 'wc3_crest_orc.png'), optimize=True)
    Image.open(ui + 'Widgets/EscMenu/Orc/orc-options-button-background.blp').convert('RGB').save(os.path.join(out, 'wc3_stone.png'), optimize=True)

if __name__ == '__main__':
    main(*sys.argv[1:3])
