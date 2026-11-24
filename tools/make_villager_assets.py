#!/usr/bin/env python3
"""Bake the villager roster's Warcraft III units into villagers.bin (animated, runtime loaded).

usage: make_villager_assets.py <wc3 root> <roster_resolved.csv> <out dir>

villagers.bin (little endian):
  'WCV1', u32 nunits,
  per unit: char name[32], f32 scale, u16 nmesh, u16 nslots, u8 frames[3] (stand, walk, act), u8 pad,
    per mesh: u16 tex, u16 ngroups, per group: u8 nv, u8 nt, nv * {s16 u, v (u*1024), u8 shade}, 3*nt u8 local indices
    frames: for seq in (stand, walk, act): for frame: nslots * {s16 x, y, z}  (native units, slot order = mesh/group/vertex order)
  then roster: for faction in (alliance, horde): for looks 0..5 (normal, peppy, lazy, jock, cranky, snooty):
    u16 count, count * u16 unit index
Skins are tex1_32x32_<hash>_0.dds replacing placeholder I4 textures (index 2000 + skin).
"""
import sys, os, io, csv, glob, json, struct, hashlib
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, xxhash
from PIL import Image
from multiprocessing import Pool
import mdx_render as M, mdx_anim as A
from make_peon_mesh import chunks

LIGHT = np.array([.4, .8, .5]); LIGHT /= np.linalg.norm(LIGHT)
FR = (6, 8, 8)
SEQ = (['Stand'], ['Walk'], ['Attack', 'Attack - 1', 'Spell Attack', 'Spell', 'Stand'])
LOOKS = {'Normal': 0, 'Peppy': 1, 'Lazy': 2, 'Jock': 3, 'Cranky': 4, 'Snooty': 5}
PEASANT_SCALE = 113.64      # game units per native unit for a Peasant (92.7 native tall)
MAX_HEIGHT = 10533.0 * 1.6   # cap for tall creatures
ROOT = None; IDX = {}

def index(root):
    for r in ('ReignOfChaos', 'FrozenThrone', 'Shared'):
        for p in glob.glob(root + r + '/**/*', recursive=True):
            if os.path.isfile(p): IDX.setdefault(os.path.basename(p).lower(), p)

def bake(job):
    name, rel = job
    try:
        data = open(ROOT + rel, 'rb').read(); mm = M.parse_mdx(data); am = A.Model(data)
        st = am.seq('stand') or am.seq('walk')
        keep = []
        for gi, g in enumerate(mm['geosets']):
            if 'uv' not in g or 'idx' not in g: continue
            mats = mm['materials'][g['mat']]
            if all(l['filter'] in (3, 4) for l in mats): continue
            if st and A.geoset_visible(am, gi, st) <= 0.1: continue
            tkey = None
            for l in reversed(mats):
                if l['filter'] in (3, 4): continue
                rid, pth = mm['textures'][l['tex']]
                b = pth.replace('\\', '/').split('/')[-1].lower() if pth else ''
                if b and b in IDX: tkey = b; break
                if rid in (1, 2): tkey = 'team'; break
            if tkey is None: tkey = 'gray'
            keep.append((gi, tkey))
        if not keep: return name, None
        seqs = []
        for k, names in enumerate(SEQ):
            fr = None
            for nm in names:
                if am.seq(nm): fr = am.bake(nm, FR[k]); break
            if fr is None: fr = am.bake('Stand', FR[k]) if am.seq('Stand') else am.bake(am.sequences[0][0], FR[k])
            seqs.append(fr)
        def pack(vs):
            return np.stack([-vs[:, 1], vs[:, 2], vs[:, 0]], 1)
        # rest = stand frame 0
        rest = {gi: pack(seqs[0][0][gi]) for gi, _ in keep}
        allr = np.concatenate([rest[gi] for gi, _ in keep]); lift = allr[:, 1].min(); height = float(allr[:, 1].max() - lift)
        scale = min(PEASANT_SCALE, MAX_HEIGHT / max(height, 1.0))
        # meshes grouped by texture key
        order = []
        for gi, tk in keep:
            if tk not in [t for t, _ in order]: order.append((tk, []))
        for gi, tk in keep:
            for t, lst in order:
                if t == tk: lst.append(gi)
        body = bytearray(); slots_order = []; nmesh = 0; texkeys = []
        for tk, gis in order:
            tris = []; vmap = {}; posl = []; uvl = []; shl = []
            for gi in gis:
                g = mm['geosets'][gi]; v = rest[gi] - np.array([0, lift, 0])
                T = g['idx']
                n = np.zeros_like(v)
                fn = np.cross(v[T[:, 1]] - v[T[:, 0]], v[T[:, 2]] - v[T[:, 0]])
                for j in range(3): np.add.at(n, T[:, j], fn)
                n /= np.maximum(np.linalg.norm(n, axis=1, keepdims=True), 1e-9)
                sh = np.round(np.clip(np.maximum(n @ LIGHT, 0) * .55 + .55, 0, 1) * 255).astype(int)
                UV = np.asarray(g['uv'], np.float32)
                for t in T:
                    tri = []
                    for vi in t:
                        key = (gi, int(vi))
                        if key not in vmap: vmap[key] = len(vmap); posl.append(key); uvl.append(UV[vi]); shl.append(sh[vi])
                        tri.append(vmap[key])
                    tris.append(tuple(tri))
            if not tris: continue
            groups = chunks(tris)
            body += struct.pack('<HH', 0, len(groups)); nmesh += 1; texkeys.append(tk)
            for grp in groups:
                order_l = {}
                for t in grp:
                    for v in t: order_l.setdefault(v, len(order_l))
                body += struct.pack('<BB', len(order_l), len(grp))
                for v in order_l:
                    u, w = uvl[v]; body += struct.pack('<hhB', int(np.clip(round(u * 1024), -32768, 32767)), int(np.clip(round(w * 1024), -32768, 32767)), int(shl[v]))
                    slots_order.append(posl[v])
                for t in grp:
                    for v in t: body += struct.pack('<B', order_l[v])
        frames = bytearray()
        for k in range(3):
            for f in range(FR[k]):
                pk = {gi: pack(seqs[k][f][gi]) - np.array([0, lift, 0]) for gi, _ in keep}
                arr = np.array([pk[gi][vi] for gi, vi in slots_order])
                frames += np.round(arr).astype('<i2').tobytes()
        # textures
        texpng = {}
        for tk in set(texkeys):
            if tk == 'team': im = Image.new('RGBA', (8, 8), (150, 150, 165, 255))
            elif tk == 'gray': im = Image.new('RGBA', (8, 8), (140, 130, 120, 255))
            else: im = Image.open(IDX[tk]).convert('RGBA')
            if max(im.size) > 128: im.thumbnail((128, 128), Image.LANCZOS)
            b = io.BytesIO(); im.save(b, 'PNG'); texpng[tk] = b.getvalue()
        return name, dict(body=bytes(body), frames=bytes(frames), nmesh=nmesh, nslots=len(slots_order), scale=scale, texkeys=texkeys, texpng=texpng, height=height)
    except Exception as e:
        return name, ('ERR ' + repr(e))

def placeholder(k):
    s = (k * 2654435761 + 1) & 0xFFFFFFFF; out = bytearray()
    for _ in range(0x200):
        s = (s * 1103515245 + 12345) & 0xFFFFFFFF; out.append((s >> 16) & 0xFF)
    return bytes(out)

def main(root, csvp, out):
    global ROOT
    ROOT = root.rstrip('/') + '/'; index(ROOT); os.makedirs(out, exist_ok=True)
    rows = list(csv.DictReader(open(csvp, encoding='utf-8')))
    units = {}
    for r in rows: units.setdefault(r['Resolved Unit'], r['Model Asset Path'])
    with Pool(4) as p: res = dict(p.map(bake, list(units.items())))
    bad = [k for k, v in res.items() if v is None or isinstance(v, str)]
    print('failed:', bad, [res[k] for k in bad if isinstance(res[k], str)][:3])
    names = [k for k in units if k not in bad]
    uidx = {n: i for i, n in enumerate(names)}
    skins = {}; skin_png = []
    def skin(png):
        h = hashlib.md5(png).hexdigest()
        if h not in skins: skins[h] = len(skin_png); skin_png.append(png)
        return skins[h]
    blob = bytearray(b'WCV1' + struct.pack('<I', len(names)))
    for n in names:
        d = res[n]; body = bytearray(d['body']); p = 0
        # patch texture ids into the mesh headers
        for mi in range(d['nmesh']):
            struct.pack_into('<H', body, p, 2000 + skin(d['texpng'][d['texkeys'][mi]]))
            ng = struct.unpack_from('<H', body, p + 2)[0]; p += 4
            for g in range(ng):
                nv, nt = body[p], body[p + 1]; p += 2 + nv * 5 + nt * 3
        blob += n.encode()[:31].ljust(32, b'\0') + struct.pack('<fHHBBBB', d['scale'], d['nmesh'], d['nslots'], FR[0], FR[1], FR[2], 0) + bytes(body) + d['frames']
    table = {(f, l): [] for f in (0, 1) for l in range(6)}
    for r in rows:
        if r['Resolved Unit'] in uidx:
            table[(0 if r['Faction'] == 'Alliance' else 1, LOOKS[r['Personality']])].append(uidx[r['Resolved Unit']])
    for f in (0, 1):
        for l in range(6):
            blob += struct.pack('<H', len(table[(f, l)])) + b''.join(struct.pack('<H', u) for u in table[(f, l)])
    open(os.path.join(out, 'villagers.bin'), 'wb').write(blob)
    for k, png in enumerate(skin_png):
        ph = placeholder(2000 + k); h = xxhash.xxh64(ph, seed=0).hexdigest()
        Image.open(io.BytesIO(png)).convert('RGBA').save(os.path.join(out, f'tex1_32x32_{h}_0.dds'), pixel_format='DXT5')
    print(len(names), 'units,', len(skin_png), 'skins, villagers.bin', len(blob) / 1e6, 'MB')
    json.dump({n: res[n]['height'] for n in names}, open(os.path.join(out, 'heights.json'), 'w'))

if __name__ == '__main__':
    main(*sys.argv[1:4])
