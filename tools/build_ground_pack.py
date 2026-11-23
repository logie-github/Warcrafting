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
             'river': 'sand', 'tunnel': 'cliff', 'station': 'brick', 'bridge1': 'wood',
             'bridge2': 'wood', 'tekkyo': 'wood', 'beach': 'sand'}
WATER_SLOTS = ('river', 'beach')
WOOD_SLOTS = ('bridge1', 'bridge2', 'tekkyo')


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


def decode_idx(b, w, h):
    g = [[0] * w for _ in range(h)]; i = 0
    for by in range(0, h, 8):
        for bx in range(0, w, 8):
            for y in range(8):
                for x in range(0, 8, 2):
                    v = b[i]; i += 1
                    g[by + y][bx + x] = v >> 4; g[by + y][bx + x + 1] = v & 15
    return g


def decode_ci4(b, w, h, pal):
    im = Image.new('RGBA', (w, h)); px = im.load(); i = 0
    for by in range(0, h, 8):
        for bx in range(0, w, 8):
            for y in range(8):
                for x in range(0, 8, 2):
                    v = b[i]; i += 1
                    px[bx + x, by + y] = pal[v >> 4]; px[bx + x + 1, by + y] = pal[v & 15]
    return im


def hsv(c):
    import colorsys
    h, s_, v = colorsys.rgb_to_hsv(c[0] / 255.0, c[1] / 255.0, c[2] / 255.0)
    return h * 360.0, s_, v


def remap(orig, tile, grass, slot, wood=None):
    """Material swap guided by the original palette colors, per ground slot.

    water (river/beach): blue entries stay blue
    green entries: faction grass (except on the grass slot itself)
    station: everything else becomes brick
    bridges/tekkyo: everything else becomes wood
    rail: orange/brown/cream entries (the ties) become wood, the rest gravel
    """
    px = orig.load(); tp = tile.load(); gp = grass.load()
    wp = wood.load() if wood is not None else None
    res = Image.new('RGBA', orig.size); rp = res.load()
    for y in range(orig.size[1]):
        for x in range(orig.size[0]):
            c = px[x, y]
            L = (0.3 * c[0] + 0.59 * c[1] + 0.11 * c[2]) / 255.0
            hh, ss, vv = hsv(c)
            green = c[1] > c[0] * 1.12 and c[1] > c[2] * 1.12
            blue = 190 <= hh <= 260 and ss > 0.3
            if slot in WATER_SLOTS and blue:
                rp[x, y] = c
                continue
            if green and slot != 'grass':
                base = gp[x, y]
            elif slot == 'rail' and wp is not None and (
                    (10 <= hh <= 50 and ss > 0.2) or (30 <= hh <= 60 and vv > 0.8)):
                base = wp[x, y]
            else:
                base = tp[x, y]
            f = 0.55 + 0.9 * L
            rp[x, y] = (min(255, int(base[0] * f)), min(255, int(base[1] * f)),
                        min(255, int(base[2] * f)), c[3])
    return res


def rail_masks(idx, pal):
    """Return per-pixel class grid for a rail texture: g,w,m(etal),s(tone),t(ransparent)."""
    h = len(idx); w = len(idx[0])
    def kind(i):
        c = pal[i]
        if c[3] == 0:
            return 't'
        hh, ss, vv = hsv(c)
        if c[1] > c[0] * 1.12 and c[1] > c[2] * 1.12:
            return 'g'
        if (10 <= hh <= 50 and ss > 0.2) or (30 <= hh <= 60 and vv > 0.8) or hh >= 330 or hh < 10:
            return 'w'
        return 's'
    k = [[kind(idx[y][x]) for x in range(w)] for y in range(h)]
    out = [row[:] for row in k]
    # rails: rows that are (almost) a single purple index across the whole width
    for y in range(h):
        cnt = collections.Counter(idx[y])
        top, n = cnt.most_common(1)[0]
        if n >= 0.9 * w and k[y][0] == 's':
            out[y] = ['m' if c == 's' else c for c in k[y]]
    # bolts: purple pixels inside a tie: wood on both sides (left/right) and
    # wood or rail above and below, all within 6 px
    def hit(y, x, dy, dx):
        for _ in range(6):
            y += dy; x += dx
            if not (0 <= y < h and 0 <= x < w):
                return None
            if out[y][x] != 's':
                return out[y][x]
        return None
    bolts = []
    for y in range(h):
        for x in range(w):
            if out[y][x] != 's':
                continue
            if (hit(y, x, 0, 1) == 'w' and hit(y, x, 0, -1) == 'w'
                    and hit(y, x, 1, 0) in ('w', 'm') and hit(y, x, -1, 0) in ('w', 'm')):
                bolts.append((y, x))
    for y, x in bolts:
        out[y][x] = 'm'
    return out


def remap_rail(idx, pal, tile, grass, wood):
    """Rail slot: steel rails and bolts keep their detail, ties become wood,
    gravel becomes the stone tile, green becomes grass. Output at SCALE x."""
    h = len(idx); w = len(idx[0])
    cls = rail_masks(idx, pal)
    res = Image.new('RGBA', (w * SCALE, h * SCALE)); rp = res.load()
    tp = tile.load(); gp = grass.load(); wp = wood.load()
    for y in range(h):
        for x in range(w):
            c = pal[idx[y][x]]
            L = (0.3 * c[0] + 0.59 * c[1] + 0.11 * c[2]) / 255.0
            k = cls[y][x]
            for dy in range(SCALE):
                for dx in range(SCALE):
                    X, Y = x * SCALE + dx, y * SCALE + dy
                    if k == 't':
                        rp[X, Y] = (0, 0, 0, 0); continue
                    if k == 'm':
                        v = 40 + 190 * L ** 1.3
                        rp[X, Y] = (int(v * 0.96), int(v * 1.0), min(255, int(v * 1.08)), 255); continue
                    base = {'g': gp, 'w': wp}.get(k, tp)[X, Y]
                    f = 0.55 + 0.9 * L
                    rp[X, Y] = (min(255, int(base[0] * f)), min(255, int(base[1] * f)),
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
        def tile(slot, w, h, rotate=False):
            k = (slot, w, h, rotate)
            if k not in tiles:
                base = Image.open(os.path.join(a.tiles, faction, slot + '.png')).convert('RGB')
                if rotate:
                    base = base.rotate(90, expand=True)
                side = min(w, h)
                base = base.resize((side, side), Image.LANCZOS)
                canvas = Image.new('RGB', (w, h))
                for ty in range(0, h, side):
                    for tx in range(0, w, side):
                        canvas.paste(base, (tx, ty))
                tiles[k] = canvas
            return tiles[k]
        for (h, palhex), (w, hh) in seen.items():
            name = byhash[h][0]
            m = re.match(r'mFM_grd_[sw]_(\w+?)(?:_\d)?_tex', name)
            slot = m[1] if m else None
            if slot not in SLOT_TILE:
                continue
            data = blocks[name]
            if slot == 'rail':
                out = remap_rail(decode_idx(data, w, hh), pal_from_hex(palhex),
                                 tile('rail', w * SCALE, hh * SCALE),
                                 tile('grass', w * SCALE, hh * SCALE),
                                 tile('wood', w * SCALE, hh * SCALE))
            else:
                orig = decode_ci4(data, w, hh, pal_from_hex(palhex)).resize((w * SCALE, hh * SCALE), Image.NEAREST)
                out = remap(orig, tile(SLOT_TILE[slot], w * SCALE, hh * SCALE, slot in WOOD_SLOTS),
                            tile('grass', w * SCALE, hh * SCALE), slot,
                            tile('wood', w * SCALE, hh * SCALE))
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
            if slot == 'rail':
                out = remap_rail(decode_idx(data, w, hh), pal_from_hex(palhex),
                                 tile('rail', w * SCALE, hh * SCALE),
                                 tile('grass', w * SCALE, hh * SCALE),
                                 tile('wood', w * SCALE, hh * SCALE))
            else:
                orig = decode_ci4(data, w, hh, pal_from_hex(palhex)).resize((w * SCALE, hh * SCALE), Image.NEAREST)
                out = remap(orig, tile(SLOT_TILE[slot], w * SCALE, hh * SCALE, slot in WOOD_SLOTS),
                            tile('grass', w * SCALE, hh * SCALE), slot,
                            tile('wood', w * SCALE, hh * SCALE))
            out.save(os.path.join(od, f'tex1_{w}x{hh}_{h}_$_8.dds'), pixel_format='DXT5')
            count[faction + '_wildcard'] += 1
    print(dict(count), 'files;', len(seen), 'texture+palette combinations seen')


if __name__ == '__main__':
    main()
