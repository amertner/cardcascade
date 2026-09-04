"""Ray-casting a cached mesh — the corpus tests' one shared instrument.

Lifted from `tests/test_lid_corpus.py`, whose docstring records the two
lessons this carries: a vertex scan misses a face wherever the tessellation
splits one, so the mesh is PROBED with rays; and a ray must **never aim at a
feature's exact centre** — a rectangular face is two triangles, and a ray
down their shared diagonal is counted once per triangle, which cancels and
the face vanishes. Every probe is offset by `EPS`, an amount no dimension in
the catalogue is a multiple of.
"""
import numpy as np

EPS = 0.013


def load(path, biggest=True):
    """(vertices, triangles) of a component 3MF's body — the biggest object,
    since a lid 3MF carries its inlays as separate objects."""
    from cad import mesh3mf
    meshes = mesh3mf.read(path)
    _n, verts, tris = (max(meshes, key=lambda m: len(m[2])) if biggest
                       else meshes[0])
    return np.array(verts), np.array(tris)


def spans(V, T, axis, u, v, tol=1e-6):
    """[(lo, hi)] of material along `axis` on the ray through the other two
    coordinates, in cyclic order — (y, z) for X, (z, x) for Y, (x, y) for Z."""
    i, j, k = axis, (axis + 1) % 3, (axis + 2) % 3
    A, B, C = V[T[:, 0]], V[T[:, 1]], V[T[:, 2]]
    a = np.column_stack([A[:, j], A[:, k]])
    b = np.column_stack([B[:, j], B[:, k]])
    c = np.column_stack([C[:, j], C[:, k]])
    p = np.array([u, v])

    def cross(m, n):        # numpy 2.0 deprecates cross() on 2-vectors
        return m[:, 0] * n[:, 1] - m[:, 1] * n[:, 0]

    d1, d2, d3 = (cross(b - a, p - a), cross(c - b, p - b), cross(a - c, p - c))
    area = cross(b - a, c - a)
    inside = (((d1 >= 0) & (d2 >= 0) & (d3 >= 0))
              | ((d1 <= 0) & (d2 <= 0) & (d3 <= 0))) & (np.abs(area) > 1e-12)
    idx = np.where(inside)[0]
    w1, w2 = d2[idx] / area[idx], d3[idx] / area[idx]
    t = np.sort(w1 * A[idx, i] + w2 * B[idx, i] + (1 - w1 - w2) * C[idx, i])
    merged = []
    for x in t:                       # a ray grazing a shared edge crosses twice
        if merged and abs(x - merged[-1]) < tol:
            merged.pop()
        else:
            merged.append(float(x))
    return list(zip(merged[0::2], merged[1::2]))


def gaps(spans_):
    """The spaces BETWEEN spans — an opening in a wall reads as a gap."""
    return [(a[1], b[0]) for a, b in zip(spans_, spans_[1:])]


def near(got, want, tol=1e-3):
    return (len(got) == len(want)
            and all(abs(a - c) < tol and abs(b - e) < tol
                    for (a, b), (c, e) in zip(got, want)))


def box(V):
    """[xmin, xmax, ymin, ymax, zmin, zmax]."""
    return [float(V[:, 0].min()), float(V[:, 0].max()),
            float(V[:, 1].min()), float(V[:, 1].max()),
            float(V[:, 2].min()), float(V[:, 2].max())]
