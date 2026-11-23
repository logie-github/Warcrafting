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
             'river': 'sand', 'tunnel': 'brick', 'station': 'brick', 'bridge1': 'stone',
             'bridge2': 'wood', 'tekkyo': 'wood', 'beach': 'sand'}
WATER_SLOTS = ('river', 'beach')
WOOD_SLOTS = ('bridge2', 'tekkyo')


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


def make_seamless(img):
    """Cross-fade a tile with a half-shifted copy of itself so opposite edges match."""
    import numpy as np
    a = np.asarray(img.convert('RGB'), dtype=float)
    n_y, n_x = a.shape[:2]
    wy = np.sin(np.linspace(0, np.pi, n_y)) ** 2
    wx = np.sin(np.linspace(0, np.pi, n_x)) ** 2
    w2 = (wy[:, None] * wx[None, :])[:, :, None]
    shifted = np.roll(np.roll(a, n_y // 2, axis=0), n_x // 2, axis=1)
    out = a * w2 + shifted * (1 - w2)
    return Image.fromarray(np.clip(out, 0, 255).astype('uint8'))


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


def remap(orig, tile, grass, slot, wood=None, snow=None, ref=None):
    """Material swap guided by the original palette colors, per ground slot.

    water (river/beach): blue entries stay blue
    green entries: faction grass (except on the grass slot itself)
    station: everything else becomes brick
    bridges/tekkyo: everything else becomes wood
    rail: orange/brown/cream entries (the ties) become wood, the rest gravel
    """
    px = orig.load(); tp = tile.load(); gp = grass.load()
    wp = wood.load() if wood is not None else None
    sp = snow.load() if snow is not None else None
    refp = ref.load() if ref is not None else None
    res = Image.new('RGBA', orig.size); rp = res.load()
    for y in range(orig.size[1]):
        for x in range(orig.size[0]):
            c = px[x, y]
            if sp is not None and is_snow(c) and (refp is None or is_green(refp[x, y])):
                rp[x, y] = snow_px(sp, x, y, c)
                continue
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
            if refp is not None:
                base = shift_color(base, c, refp[x, y])
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


def remap_rail(idx, pal, tile, grass, wood, snow=None, refpal=None):
    """Rail slot: steel rails and bolts keep their detail, ties become wood,
    gravel becomes the stone tile, green becomes grass. Output at SCALE x."""
    h = len(idx); w = len(idx[0])
    cls = rail_masks(idx, pal)
    res = Image.new('RGBA', (w * SCALE, h * SCALE)); rp = res.load()
    tp = tile.load(); gp = grass.load(); wp = wood.load()
    sp = snow.load() if snow is not None else None
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
                    if sp is not None and k != 'm' and is_snow(c) and (
                            refpal is None or is_green(refpal[idx[y][x]])):
                        rp[X, Y] = snow_px(sp, X, Y, c); continue
                    if k == 'm':
                        v = 40 + 190 * L ** 1.3
                        rp[X, Y] = (int(v * 0.96), int(v * 1.0), min(255, int(v * 1.08)), 255); continue
                    base = {'g': gp, 'w': wp}.get(k, tp)[X, Y]
                    if refpal is not None:
                        base = shift_color(base, c, refpal[idx[y][x]])
                    f = 0.55 + 0.9 * L
                    rp[X, Y] = (min(255, int(base[0] * f)), min(255, int(base[1] * f)),
                                min(255, int(base[2] * f)), c[3])
    return res


def is_snow(c):
    hh, ss, vv = hsv(c)
    return c[3] > 0 and ss < 0.3 and vv > 0.85


def is_green(c):
    return c[3] > 0 and c[1] > c[0] * 1.12 and c[1] > c[2] * 1.12


def snow_px(snow, x, y, c):
    """Snow material tinted by the original colour so AC's blue-white pattern shows."""
    s_ = snow[x, y]
    return tuple(min(255, int(s_[i] * (0.42 + 0.58 * c[i] / 255.0))) for i in range(3)) + (255,)


def shift_color(base, c, cr):
    """Season recolour: where the season palette entry `c` clearly differs in hue from
    the summer reference `cr`, take on the palette's hue (and part of its saturation)
    while keeping the material's own brightness variation."""
    import colorsys
    h1, s1, v1 = hsv(c); h0, s0, v0 = hsv(cr)
    if min(s1, s0) < 0.12:
        return base
    d = abs(((h1 - h0 + 180.0) % 360.0) - 180.0)
    w = min(1.0, max(0.0, (d - 15.0) / 45.0))
    if w <= 0:
        return base
    bh, bs, bv = colorsys.rgb_to_hsv(base[0] / 255.0, base[1] / 255.0, base[2] / 255.0)
    nh = h1 / 360.0
    ns = bs * (1 - 0.5 * w) + s1 * 0.5 * w
    r, g, b = colorsys.hsv_to_rgb(nh, ns, bv)
    r0, g0, b0 = colorsys.hsv_to_rgb(bh, bs, bv)
    return (int((r0 + (r - r0) * w) * 255), int((g0 + (g - g0) * w) * 255), int((b0 + (b - b0) * w) * 255))


def remap_steel(orig):
    """Iron girders: keep every pixel of the original structure as steel, shaded by its luminance."""
    px = orig.load()
    res = Image.new('RGBA', orig.size); rp = res.load()
    lums = [0.3 * c[0] + 0.59 * c[1] + 0.11 * c[2] for c in orig.getdata() if c[3] > 0]
    lo, hi = min(lums), max(lums)
    for y in range(orig.size[1]):
        for x in range(orig.size[0]):
            c = px[x, y]
            if c[3] == 0:
                rp[x, y] = c; continue
            L = min(1.0, max(0.0, (0.3 * c[0] + 0.59 * c[1] + 0.11 * c[2] - lo) / max(1.0, hi - lo)))
            v = 45 + 190 * L ** 1.2
            rp[x, y] = (int(v * 0.95), int(v * 0.99), min(255, int(v * 1.08)), c[3])
    return res


def tonal_ramp(tile_img, lo_pct, hi_pct, steps=32):
    """Colors of the tile sorted by luminance, averaged into `steps` bins between two percentiles."""
    import numpy as np
    arr = np.asarray(tile_img.convert('RGB'), dtype=float).reshape(-1, 3)
    lum = arr @ np.array([0.3, 0.59, 0.11])
    order = np.argsort(lum)
    n = len(order)
    lo, hi = int(n * lo_pct / 100.0), int(n * hi_pct / 100.0)
    sel = order[lo:hi]
    bins = np.array_split(sel, steps)
    return [tuple(int(v) for v in arr[b].mean(axis=0)) for b in bins]


def remap_ramp(orig, tile_img, slot, snow=None):
    """Keep the original structure (planks, rings, bricks); take colors from the
    Warcraft material's tonal ramp and its fine grain.
    bridges: whole ramp.  station: brick faces use the upper ramp, mortar the dark end."""
    from PIL import ImageFilter
    px = orig.load()
    blur = tile_img.filter(ImageFilter.GaussianBlur(2 if slot in ('station', 'tunnel') else 6)).load()
    tp = tile_img.load()
    sp = snow.load() if snow is not None else None
    full = tonal_ramp(tile_img, 3, 97)
    light = tonal_ramp(tile_img, 35, 97)
    dark = [tuple(int(v * 0.4) for v in c) for c in tonal_ramp(tile_img, 1, 10)]
    lums = [0.3 * c[0] + 0.59 * c[1] + 0.11 * c[2] for row in range(orig.size[1])
            for c in (px[x, row] for x in range(orig.size[0])) if c[3] > 0]
    lo, hi = min(lums), max(lums)
    res = Image.new('RGBA', orig.size); rp = res.load()
    for y in range(orig.size[1]):
        for x in range(orig.size[0]):
            c = px[x, y]
            if c[3] == 0:
                rp[x, y] = c; continue
            hh, ss, vv = hsv(c)
            if sp is not None and is_snow(c):
                rp[x, y] = snow_px(sp, x, y, c); continue
            if ss < 0.2 and vv > 0.9:          # white highlights stay
                rp[x, y] = c; continue
            L = (0.3 * c[0] + 0.59 * c[1] + 0.11 * c[2] - lo) / max(1.0, hi - lo)
            L = min(1.0, max(0.0, L))
            if slot in ('station', 'tunnel'):
                cream = 30 <= hh <= 60 and vv > 0.75 and ss < 0.5
                ramp = dark if cream else light
            else:
                ramp = full
            base = ramp[min(len(ramp) - 1, int(L * (len(ramp) - 1) + 0.5))]
            g = tp[x, y]; b = blur[x, y]
            grain = [(g[i] - b[i]) * (0.5 if slot in ('station', 'tunnel') else 0.8) for i in range(3)]
            rp[x, y] = tuple(min(255, max(0, int(base[i] + grain[i]))) for i in range(3)) + (c[3],)
    return res


# slot -> (width, height, palette source)
#   palette source: ('arr', symbol)  season-indexed table (12 entries, index = season palette)
#                   ('fix', symbol)  one fixed palette
SLOT_INFO = {
    'earth':   (64, 64, ('arr', 'mFM_earth_pal')),
    'grass':   (32, 32, ('arr', 'mFM_earth_pal')),
    'stone':   (64, 64, ('arr', 'mFM_earth_pal')),
    'cliff':   (64, 64, ('arr', 'mFM_cliff_pal')),
    'river':   (64, 32, ('arr', 'mFM_cliff_pal')),
    'bushA':   (64, 64, ('arr', 'mFM_bush_pal')),
    'bushB':   (64, 32, ('arr', 'mFM_bush_pal')),
    'rail':    (64, 64, ('arr', 'mFM_rail_pal')),
    'sand':    (64, 32, ('arr', 'mFM_beach_pal')),
    'beach':   (64, 32, ('arr', 'mFM_beach_pal')),
    'bridge1': (128, 32, ('fix', 'mFM_grd_s_bridge1_pal')),
    'bridge2': (128, 32, ('fix', 'mFM_grd_s_bridge2_pal')),
    'station': (128, 32, ('fix', 'mFM_grd_s_station1_pal')),
    'tunnel':  (64, 64, ('fix', 'mFM_grd_s_station1_pal')),
    'tekkyo':  (128, 32, ('fix', 'mFM_grd_s_bridge1_pal')),
}


def load_palettes(iso, symbols):
    rel, base = read_rel_data(iso)
    want = {v[2][1] for v in SLOT_INFO.values()}
    out = {}
    pat = re.compile(r'(\w+) = \.data:0x([0-9A-F]+); // type:object size:0x([0-9A-F]+)')
    for line in open(symbols):
        m = pat.match(line)
        if m and m[1] in want and m[1] not in out:
            o, sz = int(m[2], 16), int(m[3], 16)
            raw = rel[base + o:base + o + sz]
            out[m[1]] = [raw[i * 32:(i + 1) * 32].hex() for i in range(sz // 32)]
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--iso', required=True)
    ap.add_argument('--symbols', required=True)
    ap.add_argument('--tiles', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--slots', nargs='*', help='only these slots (default: all)')
    a = ap.parse_args()

    blocks = load_blocks(a.iso, a.symbols)
    pals = load_palettes(a.iso, a.symbols)
    # unique data blocks: hash -> (slot, set of seasons 's'/'w')
    uniq = {}
    for n, b in blocks.items():
        m = re.match(r'mFM_grd_([sw])_(\w+?)(?:_\d)?_tex$', n)
        if not m or m[2] not in SLOT_INFO:
            continue
        if a.slots and m[2] not in a.slots:
            continue
        w, h, _src = SLOT_INFO[m[2]]
        if len(b) != w * h // 2:
            continue
        key = xxhash.xxh64(b, seed=0).hexdigest()
        e = uniq.setdefault(key, [m[2], set(), b])
        e[1].add(m[1])

    count = collections.Counter()
    for faction in ('alliance', 'horde'):
        od = os.path.join(a.out, faction); os.makedirs(od, exist_ok=True)
        tiles = {}
        def tile(slot, w, h, rotate=False):
            k = (slot, w, h, rotate)
            if k not in tiles:
                base = Image.open(os.path.join(a.tiles, faction, slot + '.png')).convert('RGB')
                if slot in ('wood', 'brick', 'sand'):
                    base = make_seamless(base)
                if rotate:
                    base = base.rotate(90, expand=True)
                side = max(min(w, h), max(w, h) // 2)
                base = base.resize((side, side), Image.LANCZOS)
                canvas = Image.new('RGB', (w, h))
                for ty in range(0, h, side):
                    for tx in range(0, w, side):
                        canvas.paste(base, (tx, ty))
                tiles[k] = canvas
            return tiles[k]
        for key, (slot, seasons, data) in sorted(uniq.items()):
            w, h, (kind, sym) = SLOT_INFO[slot]
            table = pals[sym]
            if kind == 'fix':
                combos = [(table[0], False)]
            else:
                combos = []
                for ssn in sorted(seasons):
                    idxs = range(0, 9) if ssn == 's' else range(9, 12)
                    for i in idxs:
                        combos.append((table[i], ssn == 'w'))
            done = set()
            for palhex, winter in combos:
                th = tlut_hash(data, palhex)
                if th in done:
                    continue
                done.add(th)
                pal = pal_from_hex(palhex)
                refhex = table[1] if kind == 'arr' else palhex
                refpal = pal_from_hex(refhex)
                W, H = w * SCALE, h * SCALE
                snow = tile('snow', W, H) if winter else None
                if slot == 'rail':
                    out = remap_rail(decode_idx(data, w, h), pal, tile('rail', W, H),
                                     tile('grass', W, H), tile('wood', W, H), snow, refpal)
                elif slot == 'tekkyo':
                    out = remap_steel(decode_ci4(data, w, h, pal).resize((W, H), Image.NEAREST))
                elif slot in WOOD_SLOTS or slot in ('station', 'tunnel'):
                    orig = decode_ci4(data, w, h, pal).resize((W, H), Image.NEAREST)
                    out = remap_ramp(orig, tile(SLOT_TILE[slot], W, H, slot in WOOD_SLOTS), slot, snow)
                else:
                    orig = decode_ci4(data, w, h, pal).resize((W, H), Image.NEAREST)
                    ref = decode_ci4(data, w, h, refpal).resize((W, H), Image.NEAREST)
                    out = remap(orig, tile(SLOT_TILE[slot], W, H), tile('grass', W, H), slot,
                                tile('wood', W, H), snow, ref)
                out.save(os.path.join(od, f'tex1_{w}x{h}_{key}_{th:016x}_8.dds'), pixel_format='DXT5')
                count[faction] += 1
    print(dict(count), 'files from', len(uniq), 'unique ground blocks')


if __name__ == '__main__':
    main()
