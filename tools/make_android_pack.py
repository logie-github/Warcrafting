#!/usr/bin/env python3
"""Convert the BC3 (DXT5) ground packs and the logo into uncompressed RGBA DDS files that
every Android GPU can load (no S3TC/ASTC support required), laid out as APK assets.

usage: make_android_pack.py <repo root> <assets dir>

  <assets>/mod/alliance/*.dds   ground textures, Alliance town
  <assets>/mod/horde/*.dds      ground textures, Horde town
  <assets>/mod/common/*.dds     logo and other town-independent files
  <assets>/mod/manifest.txt     file lists used by the app to extract the pack
"""
import os, struct, sys
from PIL import Image


def write_rgba_dds(path, im):
    im = im.convert('RGBA')
    w, h = im.size
    hdr = bytearray(128 + 20)
    hdr[0:4] = b'DDS '
    struct.pack_into('<7I', hdr, 4, 124, 0x1 | 0x2 | 0x4 | 0x1000, h, w, w * 4, 0, 1)
    struct.pack_into('<I', hdr, 76, 32)                      # pixel format size
    struct.pack_into('<II', hdr, 80, 0x4, 0x30315844)        # FOURCC 'DX10'
    struct.pack_into('<I', hdr, 108, 0x1000)                 # caps: texture
    struct.pack_into('<5I', hdr, 128, 28, 3, 0, 1, 0)        # DXGI_FORMAT_R8G8B8A8_UNORM, 2D
    with open(path, 'wb') as f:
        f.write(hdr); f.write(im.tobytes())


def convert_dir(src, dst):
    os.makedirs(dst, exist_ok=True)
    names = []
    for fn in sorted(os.listdir(src)):
        if fn.lower().endswith('.dds'):
            write_rgba_dds(os.path.join(dst, fn), Image.open(os.path.join(src, fn)))
            names.append(fn)
    return names


def main(root, assets):
    out = os.path.join(assets, 'mod')
    manifest = []
    for town in ('alliance', 'horde'):
        for fn in convert_dir(os.path.join(root, 'mod/pack', town), os.path.join(out, town)):
            manifest.append(f'{town}/{fn}')
    for sub in ('mod/logo', 'mod/players'):
        for fn in convert_dir(os.path.join(root, sub), os.path.join(out, 'common')):
            manifest.append(f'common/{fn}')
    mdir = os.path.join(root, 'mod/music')
    if os.path.isdir(mdir):
        os.makedirs(os.path.join(out, 'music'), exist_ok=True)
        for fn in sorted(os.listdir(mdir)):
            if fn.lower().endswith('.ogg'):
                with open(os.path.join(mdir, fn), 'rb') as a, open(os.path.join(out, 'music', fn), 'wb') as b:
                    b.write(a.read())
                manifest.append(f'music/{fn}')
    with open(os.path.join(out, 'manifest.txt'), 'w') as f:
        f.write('\n'.join(manifest) + '\n')
    print(len(manifest), 'files')


if __name__ == '__main__':
    main(*sys.argv[1:3])
