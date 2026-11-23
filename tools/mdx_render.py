#!/usr/bin/env python3
"""Minimal Warcraft III MDX (version 800) reader and software renderer for static previews.

Reads geosets (vertices, normals, UVs, triangles), materials and textures. No animation:
meshes are drawn in their bind pose. Renders with a z-buffer, alpha test and simple lighting.
"""
import struct
import numpy as np
from PIL import Image


def parse_mdx(data):
    assert data[:4] == b'MDLX', 'not an MDX file'
    pos = 4
    chunks = {}
    while pos + 8 <= len(data):
        tag = data[pos:pos + 4]; size = struct.unpack('<I', data[pos + 4:pos + 8])[0]
        chunks.setdefault(tag, []).append(data[pos + 8:pos + 8 + size])
        pos += 8 + size
    model = {'textures': [], 'materials': [], 'geosets': []}
    for t in chunks.get(b'TEXS', []):
        for i in range(len(t) // 268):
            rid = struct.unpack('<I', t[i * 268:i * 268 + 4])[0]
            path = t[i * 268 + 4:i * 268 + 264].split(b'\0')[0].decode('latin1')
            model['textures'].append((rid, path))
    for t in chunks.get(b'MTLS', []):
        p = 0
        while p < len(t):
            inc = struct.unpack('<I', t[p:p + 4])[0]
            m = t[p:p + inc]
            q = 12
            layers = []
            if m[q:q + 4] == b'LAYS':
                n = struct.unpack('<I', m[q + 4:q + 8])[0]; q += 8
                for _ in range(n):
                    li = struct.unpack('<I', m[q:q + 4])[0]
                    filt, shade, tex = struct.unpack('<III', m[q + 4:q + 16])
                    layers.append({'filter': filt, 'shade': shade, 'tex': tex})
                    q += li
            model['materials'].append(layers)
            p += inc
    for t in chunks.get(b'GEOS', []):
        p = 0
        while p < len(t):
            inc = struct.unpack('<I', t[p:p + 4])[0]
            g = t[p + 4:p + inc]
            q = 0
            geo = {}
            while q + 8 <= len(g):
                tag = g[q:q + 4]; q += 4
                if tag == b'VRTX':
                    n = struct.unpack('<I', g[q:q + 4])[0]
                    geo['v'] = np.frombuffer(g, '<f4', n * 3, q + 4).reshape(n, 3); q += 4 + n * 12
                elif tag == b'NRMS':
                    n = struct.unpack('<I', g[q:q + 4])[0]
                    geo['n'] = np.frombuffer(g, '<f4', n * 3, q + 4).reshape(n, 3); q += 4 + n * 12
                elif tag == b'PTYP':
                    n = struct.unpack('<I', g[q:q + 4])[0]; q += 4 + n * 4
                elif tag == b'PCNT':
                    n = struct.unpack('<I', g[q:q + 4])[0]; q += 4 + n * 4
                elif tag == b'PVTX':
                    n = struct.unpack('<I', g[q:q + 4])[0]
                    geo['idx'] = np.frombuffer(g, '<u2', n, q + 4).astype(np.int64).reshape(-1, 3); q += 4 + n * 2
                elif tag == b'GNDX':
                    n = struct.unpack('<I', g[q:q + 4])[0]; q += 4 + n
                elif tag == b'MTGC':
                    n = struct.unpack('<I', g[q:q + 4])[0]; q += 4 + n * 4
                elif tag == b'MATS':
                    n = struct.unpack('<I', g[q:q + 4])[0]; q += 4 + n * 4
                else:
                    # tail: material id, selection group, flags, bounds, anims, then UVAS/UVBS
                    q -= 4
                    break
            # remaining header: matId, selGroup, selFlags (3 uints) + radius/min/max + nAnims + anims
            matid = struct.unpack('<I', g[q:q + 4])[0]
            geo['mat'] = matid
            q += 12 + 28
            nanim = struct.unpack('<I', g[q:q + 4])[0]; q += 4 + nanim * 28
            if g[q:q + 4] == b'UVAS':
                nuv = struct.unpack('<I', g[q + 4:q + 8])[0]; q += 8
                if g[q:q + 4] == b'UVBS':
                    n = struct.unpack('<I', g[q + 4:q + 8])[0]
                    geo['uv'] = np.frombuffer(g, '<f4', n * 2, q + 8).reshape(n, 2)
            model['geosets'].append(geo)
            p += inc
    return model


def load_texture(path):
    im = Image.open(path).convert('RGBA')
    return np.asarray(im, dtype=np.float32) / 255.0


def render(model, tex_for_geo, size=512, yaw=35.0, pitch=28.0, bg=(46, 46, 52), light=(-0.4, -0.5, 0.8)):
    """tex_for_geo(index, geo, model) -> RGBA float array or None. Z is up."""
    verts = np.concatenate([g['v'] for g in model['geosets'] if 'v' in g])
    lo, hi = verts.min(0), verts.max(0)
    ctr = (lo + hi) / 2; rad = np.linalg.norm(hi - lo) / 2
    ya, pa = np.radians(yaw), np.radians(pitch)
    Rz = np.array([[np.cos(ya), -np.sin(ya), 0], [np.sin(ya), np.cos(ya), 0], [0, 0, 1]])
    Rx = np.array([[1, 0, 0], [0, np.cos(pa), -np.sin(pa)], [0, np.sin(pa), np.cos(pa)]])
    R = Rx @ Rz.T
    L = np.array(light, dtype=float); L /= np.linalg.norm(L)
    img = np.zeros((size, size, 3), dtype=np.float32); img[:] = np.array(bg, dtype=np.float32) / 255.0
    zbuf = np.full((size, size), 1e9, dtype=np.float32)
    scale = size * 0.46 / rad
    for gi, g in enumerate(model['geosets']):
        if 'v' not in g or 'idx' not in g or 'uv' not in g:
            continue
        tex = tex_for_geo(gi, g, model)
        if tex is None:
            continue
        th, tw = tex.shape[:2]
        P = (g['v'] - ctr) @ R.T
        N = (g['n'] @ R.T) if 'n' in g else None
        Nl = g['n'] @ np.eye(3) if 'n' in g else None
        sx = P[:, 0] * scale + size / 2
        sy = -P[:, 2] * scale + size / 2   # view up = model Z after rotation
        # after Rx @ Rz: x right, y depth(away), z up
        depth = P[:, 1]
        for tri in g['idx']:
            a, b, c = tri
            xs = np.array([sx[a], sx[b], sx[c]]); ys = np.array([sy[a], sy[b], sy[c]])
            x0, x1 = int(max(0, np.floor(xs.min()))), int(min(size - 1, np.ceil(xs.max())))
            y0, y1 = int(max(0, np.floor(ys.min()))), int(min(size - 1, np.ceil(ys.max())))
            if x1 < x0 or y1 < y0:
                continue
            d = (ys[1] - ys[2]) * (xs[0] - xs[2]) + (xs[2] - xs[1]) * (ys[0] - ys[2])
            if abs(d) < 1e-9:
                continue
            gx, gy = np.meshgrid(np.arange(x0, x1 + 1) + 0.5, np.arange(y0, y1 + 1) + 0.5)
            w0 = ((ys[1] - ys[2]) * (gx - xs[2]) + (xs[2] - xs[1]) * (gy - ys[2])) / d
            w1 = ((ys[2] - ys[0]) * (gx - xs[2]) + (xs[0] - xs[2]) * (gy - ys[2])) / d
            w2 = 1 - w0 - w1
            m = (w0 >= 0) & (w1 >= 0) & (w2 >= 0)
            if not m.any():
                continue
            z = w0 * depth[a] + w1 * depth[b] + w2 * depth[c]
            u = w0 * g['uv'][a, 0] + w1 * g['uv'][b, 0] + w2 * g['uv'][c, 0]
            v = w0 * g['uv'][a, 1] + w1 * g['uv'][b, 1] + w2 * g['uv'][c, 1]
            ui = (np.mod(u, 1.0) * tw).astype(int) % tw
            vi = (np.mod(v, 1.0) * th).astype(int) % th
            texel = tex[vi, ui]
            m &= texel[..., 3] > 0.5
            zb = zbuf[y0:y1 + 1, x0:x1 + 1]
            m &= z < zb
            if not m.any():
                continue
            nrm = (w0[..., None] * N[a] + w1[..., None] * N[b] + w2[..., None] * N[c]) if N is not None else None
            if nrm is not None:
                nl = np.linalg.norm(nrm, axis=-1, keepdims=True); nrm = nrm / np.maximum(nl, 1e-6)
                # light is defined in view space: x right, y away, z up
                lam = np.abs(nrm @ L)
                shade = 0.55 + 0.6 * lam
            else:
                shade = 1.0
            col = texel[..., :3] * (shade[..., None] if nrm is not None else 1.0)
            sub = img[y0:y1 + 1, x0:x1 + 1]
            sub[m] = np.clip(col[m], 0, 1)
            zb[m] = z[m]
    return Image.fromarray((np.clip(img, 0, 1) * 255).astype('uint8'))
