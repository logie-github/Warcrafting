#!/usr/bin/env python3
"""Build the index-guided (option B) ground texture pack for the AC port.

Inputs
  --iso      Animal Crossing (USA) GAFE01 disc image (trimmed ISO is fine)
  --symbols  config/GAFE01_00/foresta/symbols.txt from the port
  --pal-logs one or more files of "[TEXLOG] ..." lines written by the port when
             AC_TEXPACK_LOG=1 (one run per season/date)
  --tiles    mod/ground (alliance/ and horde/ PNG tiles from fit_ground.py)
  --out      output directory (one subfolder per faction)

For every ground texture seen in the logs, each distinct runtime palette gets
its own DDS named by the port's Dolphin-style filename
  tex1_{W}x{H}_{datahash}_{tluthash}_8.dds
so seasonal palettes map to seasonal remaps. The remap keeps the original
shape (alpha) and shading, and swaps the material: greenish palette entries
become the faction grass tile, everything else the slot's own tile.
"""
import argparse, os, re, struct, collections
import xxhash
from PIL import Image

SCALE = 4
SLOT_TILE = {'earth': 'earth', 'cliff': 'cliff', 'grass': 'grass', 'rail': 'rail',
             'stone': 'stone', 'bushA': 'bush_a', 'bushB': 'bush_a', 'sand': 'sand',
             'river': 'sand', 'tunnel': 'cliff', 'station': 'stone', 'bridge1': 'rail',
             'bridge2': 'rail', 'tekkyo': 'rail', 'beach': 'sand'}


def yaz0(b):
    n = struct.unpack('>I', b[4:8])[0]
    out = bytearray(); p = 16
    while len(out) < n:
        h = b[p]; p += 1
        for i in range(8):
            if len(out) >= n:
                break
            if h & (0x80 >> i):
                out.append(b[p]); p += 1
            else:
                b1, b2 = b[p], b[p + 1]; p += 2
                d = ((b1 & 15) << 8 | b2) + 1
                l = b1 >> 4
                if l == 0:
                    l = b[p] + 18; p += 1
                else:
                    l += 2
                for _ in range(l):
                    out.append(out[-d])
    return bytes(out)


def read_rel_data(iso):
    f = open(iso, 'rb')
    f.seek(0x424); off, sz = struct.unpack('>II', f.read(8))
    f.seek(off); d = f.read(sz)
    n = struct.unpack('>I', d[8:12])[0]; st = n * 12
    def nm(o):
        return d[st + o:d.index(b'\0', st + o)].decode()
    files = {}
    for i in range(1, n):
        if d[i * 12]:
            continue
        no = struct.unpack('>I', b'\0' + d[i * 12 + 1:i * 12 + 4])[0]
        a, b = struct.unpack('>II', d[i * 12 + 4:i * 12 + 12])
        files[nm(no)] = (a, b)
    a, b = files['foresta.rel.szs']
    f.seek(a); rel = yaz0(f.read(b))
    nsec, sioff = struct.unpack('>II', rel[0xc:0x14])
    # .data is the large non-exec section holding the model data
    best = None
    for i in range(nsec):
        o, l = struct.unpack('>II', rel[sioff + i * 8:sioff + i * 8 + 8])
        if not (o & 1) and l > 0x800000:
            best = (o & ~3, l)
    return rel, best[0]


def load_blocks(iso, symbols):
    rel, base = read_rel_data(iso)
    blocks = {}
    pat = re.compile(r'(mFM_grd_[A-Za-z0-9_]*tex\w*) = \.data:0x([0-9A-F]+); // type:object size:0x([0-9A-F]+)')
    for line in open(symbols):
        m = pat.match(line)
        if m and m[1] not in blocks:
            o, s = int(m[2], 16), int(m[3], 16)
            blocks[m[1]] = rel[base + o:base + o + s]
    return blocks


def pal_from_hex(hexs):
    out = []
    for i in range(0, len(hexs), 4):
        v = int(hexs[i:i + 4], 16)
        if v & 0x8000:
            out.append(((v >> 10 & 31) * 255 // 31, (v >> 5 & 31) * 255 // 31, (v & 31) * 255 // 31, 255))
        else:
            out.append(((v >> 8 & 15) * 17, (v >> 4 & 15) * 17, (v & 15) * 17, ((v >> 12) & 7) * 255 // 7))
    return out


def tlut_hash(data, hexs):
    idx = [x for b in data for x in (b >> 4, b & 15)]
    lo, hi = min(idx), max(idx)
    raw = bytes.fromhex(hexs)
    return xxhash.xxh64(raw[lo * 2:(hi + 1) * 2], seed=0).intdigest()


def decode_ci4(b, w, h, pal):
    im = Image.new('RGBA', (w, h)); px = im.load(); i = 0
    for by in range(0, h, 8):
        for bx in range(0, w, 8):
            for y in range(8):
                for x in range(0, 8, 2):
                    v = b[i]; i += 1
                    px[bx + x, by + y] = pal[v >> 4]; px[bx + x + 1, by + y] = pal[v & 15]
    return im


def remap(orig, tile, grass, is_grass_slot):
    px = orig.load(); tp = tile.load(); gp = grass.load()
    res = Image.new('RGBA', orig.size); rp = res.load()
    for y in range(orig.size[1]):
        for x in range(orig.size[0]):
            c = px[x, y]
            L = (0.3 * c[0] + 0.59 * c[1] + 0.11 * c[2]) / 255.0
            green = c[1] > c[0] * 1.12 and c[1] > c[2] * 1.12
            blue = c[2] > c[0] * 1.15 and c[2] > c[1] * 1.05
            if blue:
                # water stays water: keep the original blue (shaded below)
                rp[x, y] = c
                continue
            base = gp[x, y] if (green and not is_grass_slot) else tp[x, y]
            f = 0.55 + 0.9 * L
            rp[x, y] = (min(255, int(base[0] * f)), min(255, int(base[1] * f)),
                        min(255, int(base[2] * f)), c[3])
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--iso', required=True)
    ap.add_argument('--symbols', required=True)
    ap.add_argument('--pal-logs', nargs='+', required=True)
    ap.add_argument('--tiles', required=True)
    ap.add_argument('--out', required=True)
    a = ap.parse_args()

    blocks = load_blocks(a.iso, a.symbols)
    byhash = collections.defaultdict(list)
    for n, b in blocks.items():
        byhash[xxhash.xxh64(b, seed=0).hexdigest()].append(n)

    seen = {}  # (hash, palhex) -> (w, h)
    pat = re.compile(r'\[TEXLOG\] (\d+)x(\d+) fmt=8 hash=([0-9a-f]+) size=\d+ tlut=\d+ pal=([0-9a-f]+)')
    for path in a.pal_logs:
        for line in open(path):
            m = pat.match(line)
            if m and m[3] in byhash:
                seen[(m[3], m[4])] = (int(m[1]), int(m[2]))

    count = collections.Counter()
    for faction in ('alliance', 'horde'):
        od = os.path.join(a.out, faction); os.makedirs(od, exist_ok=True)
        tiles = {}
        def tile(slot, w, h):
            k = (slot, w, h)
            if k not in tiles:
                tiles[k] = Image.open(os.path.join(a.tiles, faction, slot + '.png')).convert('RGB').resize((w, h), Image.LANCZOS)
            return tiles[k]
        for (h, palhex), (w, hh) in seen.items():
            name = byhash[h][0]
            m = re.match(r'mFM_grd_[sw]_(\w+?)(?:_\d)?_tex', name)
            slot = m[1] if m else None
            if slot not in SLOT_TILE:
                continue
            data = blocks[name]
            orig = decode_ci4(data, w, hh, pal_from_hex(palhex)).resize((w * SCALE, hh * SCALE), Image.NEAREST)
            out = remap(orig, tile(SLOT_TILE[slot], w * SCALE, hh * SCALE),
                        tile('grass', w * SCALE, hh * SCALE), slot == 'grass')
            th = tlut_hash(data, palhex)
            fn = f'tex1_{w}x{hh}_{h}_{th:016x}_8.dds'
            out.save(os.path.join(od, fn), pixel_format='DXT5')
            count[faction] += 1
        # Blocks never seen at runtime (winter set, _2/_3 variants, sand, ...):
        # reuse the palette and size of a seen block of the same slot and emit a
        # wildcard-palette file (tex1_WxH_<datahash>_$_8.dds).
        ref = {}
        for (h, palhex), (w, hh) in seen.items():
            m = re.match(r'mFM_grd_[sw]_(\w+?)(?:_\d)?_tex', byhash[h][0])
            if m:
                ref.setdefault(m[1], (palhex, w, hh))
        done_hash = {h for (h, _p) in seen}
        for h, names in byhash.items():
            if h in done_hash:
                continue
            m = re.match(r'mFM_grd_[sw]_(\w+?)(?:_\d)?_tex', names[0])
            slot = m[1] if m else None
            if slot not in SLOT_TILE or slot not in ref:
                continue
            palhex, w, hh = ref[slot]
            if len(blocks[names[0]]) != w * hh // 2:
                continue
            data = blocks[names[0]]
            orig = decode_ci4(data, w, hh, pal_from_hex(palhex)).resize((w * SCALE, hh * SCALE), Image.NEAREST)
            out = remap(orig, tile(SLOT_TILE[slot], w * SCALE, hh * SCALE),
                        tile('grass', w * SCALE, hh * SCALE), slot == 'grass')
            out.save(os.path.join(od, f'tex1_{w}x{hh}_{h}_$_8.dds'), pixel_format='DXT5')
            count[faction + '_wildcard'] += 1
    print(dict(count), 'files;', len(seen), 'texture+palette combinations seen')


if __name__ == '__main__':
    main()
