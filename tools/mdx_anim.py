#!/usr/bin/env python3
"""Warcraft III MDX (v800) skeleton and animation reader with a pose baker.

Bakes a named sequence into per-frame vertex positions (skinned from the bone matrices), so the
animation can be played as a series of static poses.  Interpolation: linear (slerp for rotations);
hermite and bezier tracks are treated as linear.
"""
import struct
import numpy as np


def _quat_to_mat(q):
    x, y, z, w = q
    n = x * x + y * y + z * z + w * w
    if n < 1e-12:
        return np.eye(3)
    s = 2.0 / n
    xx, yy, zz = x * x * s, y * y * s, z * z * s
    xy, xz, yz = x * y * s, x * z * s, y * z * s
    wx, wy, wz = w * x * s, w * y * s, w * z * s
    return np.array([[1 - (yy + zz), xy - wz, xz + wy],
                     [xy + wz, 1 - (xx + zz), yz - wx],
                     [xz - wy, yz + wx, 1 - (xx + yy)]])


def _slerp(a, b, t):
    a = np.array(a, float); b = np.array(b, float)
    d = float(np.dot(a, b))
    if d < 0:
        b = -b; d = -d
    if d > 0.9995:
        r = a + t * (b - a)
    else:
        th = np.arccos(min(1.0, d)); s = np.sin(th)
        r = (np.sin((1 - t) * th) * a + np.sin(t * th) * b) / s
    n = np.linalg.norm(r)
    return r / n if n else np.array([0, 0, 0, 1.0])


class Track:
    def __init__(self, kind, interp, gseq, keys):
        self.kind, self.interp, self.gseq, self.keys = kind, interp, gseq, keys   # keys: [(time, value)]

    def sample(self, t, default):
        if not self.keys:
            return default
        ks = self.keys
        if t <= ks[0][0]:
            return ks[0][1]
        if t >= ks[-1][0]:
            return ks[-1][1]
        for i in range(len(ks) - 1):
            t0, v0 = ks[i]; t1, v1 = ks[i + 1]
            if t0 <= t <= t1:
                f = 0.0 if t1 == t0 else (t - t0) / (t1 - t0)
                if self.interp == 0:
                    return v0
                if self.kind == 'rot':
                    return _slerp(v0, v1, f)
                return np.array(v0) + f * (np.array(v1) - np.array(v0))
        return ks[-1][1]

    def has_range(self, t0, t1):
        return any(t0 <= k[0] <= t1 for k in self.keys)


class Node:
    pass


class Model:
    def __init__(self, data):
        assert data[:4] == b'MDLX'
        pos = 4
        ch = {}
        while pos + 8 <= len(data):
            tag = data[pos:pos + 4]; size = struct.unpack('<I', data[pos + 4:pos + 8])[0]
            ch.setdefault(tag, []).append(data[pos + 8:pos + 8 + size]); pos += 8 + size
        self.sequences = []
        for t in ch.get(b'SEQS', []):
            for i in range(len(t) // 132):
                nm = t[i * 132:i * 132 + 80].split(b'\0')[0].decode('latin1')
                st, en = struct.unpack('<II', t[i * 132 + 80:i * 132 + 88])
                self.sequences.append((nm, st, en))
        self.global_seqs = [struct.unpack('<I', t[i * 4:i * 4 + 4])[0] for t in ch.get(b'GLBS', []) for i in range(len(t) // 4)]
        self.pivots = []
        for t in ch.get(b'PIVT', []):
            for i in range(len(t) // 12):
                self.pivots.append(np.array(struct.unpack('<3f', t[i * 12:i * 12 + 12])))
        self.nodes = {}
        for tag in (b'BONE', b'HELP'):
            for t in ch.get(tag, []):
                p = 0
                while p < len(t):
                    inc = struct.unpack('<I', t[p:p + 4])[0]
                    self._node(t[p:p + inc], tag == b'BONE')
                    p += inc + (8 if tag == b'BONE' else 0)
        self.geosets = []
        for t in ch.get(b'GEOS', []):
            p = 0
            while p < len(t):
                inc = struct.unpack('<I', t[p:p + 4])[0]
                self.geosets.append(self._geoset(t[p + 4:p + inc]))
                p += inc
        self.geoanim = {}
        for t in ch.get(b'GEOA', []):
            p = 0
            while p < len(t):
                inc = struct.unpack('<I', t[p:p + 4])[0]
                b = t[p:p + inc]
                alpha = struct.unpack('<f', b[4:8])[0]
                gid = struct.unpack("<I", b[24:28])[0]
                keys = []
                q = 28
                if b[q:q + 4] == b'KGAO':
                    cnt, interp, gseq = struct.unpack('<IIi', b[q + 4:q + 16]); q += 16
                    for _ in range(cnt):
                        tm = struct.unpack('<i', b[q:q + 4])[0]; v = struct.unpack('<f', b[q + 4:q + 8])[0]; q += 8
                        if interp > 1: q += 8
                        keys.append((tm, v))
                self.geoanim[gid] = (alpha, keys)
                p += inc
        self.order = sorted(self.nodes)

    def _node(self, b, is_bone):
        n = Node()
        n.name = b[4:84].split(b'\0')[0].decode('latin1')
        n.id, n.parent, n.flags = struct.unpack('<III', b[84:96])
        n.parent = -1 if n.parent == 0xFFFFFFFF else n.parent
        n.tracks = {}
        q = 96
        while q + 4 <= len(b) and b[q:q + 4] in (b'KGTR', b'KGRT', b'KGSC'):
            tag = b[q:q + 4]; cnt, interp, gseq = struct.unpack('<IIi', b[q + 4:q + 16]); q += 16
            kind = {b'KGTR': 'trans', b'KGRT': 'rot', b'KGSC': 'scale'}[tag]
            nv = 4 if kind == 'rot' else 3
            keys = []
            for _ in range(cnt):
                tm = struct.unpack('<i', b[q:q + 4])[0]; q += 4
                val = struct.unpack('<%df' % nv, b[q:q + 4 * nv]); q += 4 * nv
                if interp > 1:
                    q += 8 * nv
                keys.append((tm, np.array(val)))
            n.tracks[kind] = Track(kind, interp, gseq, keys)
        self.nodes[n.id] = n

    def _geoset(self, g):
        q = 0; geo = {}
        while q + 8 <= len(g):
            tag = g[q:q + 4]; q += 4
            n = struct.unpack('<I', g[q:q + 4])[0]
            if tag == b'VRTX':
                geo['v'] = np.frombuffer(g, '<f4', n * 3, q + 4).reshape(n, 3).astype(np.float64); q += 4 + n * 12
            elif tag == b'NRMS':
                q += 4 + n * 12
            elif tag == b'PTYP':
                q += 4 + n * 4
            elif tag == b'PCNT':
                q += 4 + n * 4
            elif tag == b'PVTX':
                geo['idx'] = np.frombuffer(g, '<u2', n, q + 4).astype(np.int64).reshape(-1, 3); q += 4 + n * 2
            elif tag == b'GNDX':
                geo['gndx'] = np.frombuffer(g, 'u1', n, q + 4).astype(np.int64); q += 4 + n
            elif tag == b'MTGC':
                geo['mtgc'] = np.frombuffer(g, '<u4', n, q + 4).astype(np.int64); q += 4 + n * 4
            elif tag == b'MATS':
                geo['mats'] = np.frombuffer(g, '<u4', n, q + 4).astype(np.int64); q += 4 + n * 4
            else:
                q -= 4
                break
        geo['mat'] = struct.unpack('<I', g[q:q + 4])[0]; q += 12 + 28
        nanim = struct.unpack('<I', g[q:q + 4])[0]; q += 4 + nanim * 28
        if g[q:q + 4] == b'UVAS':
            q += 8
            if g[q:q + 4] == b'UVBS':
                n = struct.unpack('<I', g[q + 4:q + 8])[0]
                geo['uv'] = np.frombuffer(g, '<f4', n * 2, q + 8).reshape(n, 2)
        return geo

    # ---- posing ----
    def seq(self, name):
        for s in self.sequences:
            if s[0].strip().lower() == name.lower():
                return s
        for s in self.sequences:
            if s[0].strip().lower().startswith(name.lower()):
                return s
        return None

    def node_world(self, t):
        """World matrices (4x4) for every node at sequence time t (ms)."""
        mats = {}
        def local(n):
            piv = self.pivots[n.id] if n.id < len(self.pivots) else np.zeros(3)
            tr = n.tracks.get('trans').sample(t, np.zeros(3)) if 'trans' in n.tracks and n.tracks['trans'].gseq < 0 else np.zeros(3)
            ro = n.tracks.get('rot').sample(t, np.array([0, 0, 0, 1.0])) if 'rot' in n.tracks and n.tracks['rot'].gseq < 0 else np.array([0, 0, 0, 1.0])
            sc = n.tracks.get('scale').sample(t, np.ones(3)) if 'scale' in n.tracks and n.tracks['scale'].gseq < 0 else np.ones(3)
            M = np.eye(4)
            RS = _quat_to_mat(ro) @ np.diag(sc)
            M[:3, :3] = RS
            M[:3, 3] = piv + tr - RS @ piv
            return M
        def world(i):
            if i in mats:
                return mats[i]
            n = self.nodes[i]
            L = local(n)
            mats[i] = world(n.parent) @ L if n.parent >= 0 and n.parent in self.nodes else L
            return mats[i]
        for i in self.nodes:
            world(i)
        return mats

    def pose(self, t):
        """Skinned vertices per geoset at time t."""
        W = self.node_world(t)
        out = []
        for g in self.geosets:
            v = g['v']; res = np.zeros_like(v)
            mtgc = g.get('mtgc'); mats = g.get('mats'); gndx = g.get('gndx')
            if mtgc is None or mats is None or gndx is None:
                out.append(v.copy()); continue
            starts = np.concatenate([[0], np.cumsum(mtgc)[:-1]])
            vh = np.concatenate([v, np.ones((len(v), 1))], 1)
            groups = {}
            for gi in range(len(mtgc)):
                bones = mats[starts[gi]:starts[gi] + mtgc[gi]]
                M = np.zeros((4, 4))
                cnt = 0
                for b in bones:
                    if int(b) in W:
                        M += W[int(b)]; cnt += 1
                groups[gi] = (M / cnt) if cnt else np.eye(4)
            for i in range(len(v)):
                M = groups[int(gndx[i])]
                res[i] = (M @ vh[i])[:3]
            out.append(res)
        return out

    def bake(self, seq_name, frames):
        s = self.seq(seq_name)
        if s is None:
            return None
        _, st, en = s
        times = [st + (en - st) * k / float(frames) for k in range(frames)]
        return [self.pose(t) for t in times]


def geoset_visible(model, gi, seq):
    """Geoset alpha for a sequence (name, start, end): keys are only used when some fall inside the
    sequence interval, otherwise the static alpha applies (the Warcraft III rule)."""
    if gi not in model.geoanim:
        return 1.0
    alpha, keys = model.geoanim[gi]
    _, st, en = seq
    inside = [(t, v) for t, v in keys if st <= t <= en]
    if not inside:
        return alpha
    t = (st + en) / 2.0
    if t <= inside[0][0]:
        return inside[0][1]
    for i in range(len(inside) - 1):
        if inside[i][0] <= t <= inside[i + 1][0]:
            return inside[i][1]
    return inside[-1][1]
