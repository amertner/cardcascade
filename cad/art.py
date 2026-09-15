"""Imported 2D artwork — the Lid's logo, and anything else drawn rather than
computed.

A DXF holds OUTLINES, not regions: which closed loop is a hole is a question
about NESTING. The artwork lives in `logos/<Game>/`, in the part's own frame;
`spec/LID.md` records where each file came from.
"""
import os
from functools import lru_cache
from pathlib import Path

from build123d import Compound, Face, Wire, export_brep, import_brep, import_dxf

LOGO_DIR = Path(__file__).resolve().parent.parent / "logos"

# How far apart two ends may be and still be one loop: a DXF's coordinates are
# text, so a curve comes back rounded. A CHAINING tolerance.
CHAIN_TOL = 0.010


def _inside_point(face):
    """A point strictly inside `face`: its centre, else a coarse grid's hit."""
    centre = face.center()
    if face.is_inside(centre):
        return centre
    bb = face.bounding_box()
    for i in range(1, 40):
        for j in range(1, 40):
            p = (bb.min.X + bb.size.X * i / 40,
                 bb.min.Y + bb.size.Y * j / 40, 0)
            if face.is_inside(p):
                return p
    raise RuntimeError("cannot find a point inside an outline")


# Filling a DXF is slow. The filled faces are cached as a B-rep named by the
# drawing's own DIGEST, so a changed drawing misses the cache by itself; a
# B-rep round-trips the faces exactly, unlike a DXF (`load`).
CACHE_DIR = Path(__file__).resolve().parent.parent / "build" / ".art"
CACHE_TAG = "v1"          # bump when the filling below changes


def _cached(path, fill):
    import hashlib
    digest = hashlib.sha256(path.read_bytes()).hexdigest()[:16]
    cache = CACHE_DIR / f"{path.parent.name}.{path.stem}.{digest}.{CACHE_TAG}.brep"
    if cache.exists():
        return tuple(import_brep(str(cache)).faces())
    faces = fill(path)
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    tmp = cache.with_suffix(f".{os.getpid()}.tmp")   # workers race: write, then rename
    export_brep(Compound(children=list(faces)), str(tmp))
    tmp.replace(cache)
    return faces


@lru_cache(maxsize=8)
def load(path):
    """The drawing in `path` (DXF) as filled faces, ready to extrude.

    A loop nested in an ODD number of others is a HOLE in the face around it;
    one nested in an even number is a face of its own. A `.brep` is a drawing
    too — OCCT's own faces, how artwork LIFTED FROM A STEP is kept exact.
    """
    if path.suffix == ".brep":
        return tuple(import_brep(str(path)).faces())
    return _cached(path, _fill_dxf)


def _fill_dxf(path):
    shapes = import_dxf(str(path))
    edges = shapes.edges()
    if not edges:
        raise ValueError(f"{path}: no geometry")
    loops = [w for w in Wire.combine(edges, tol=CHAIN_TOL) if w.is_closed]
    if not loops:
        raise ValueError(f"{path}: no closed outlines to fill")
    faces = sorted((Face(w) for w in loops), key=lambda f: -f.area)
    points = [_inside_point(f) for f in faces]
    # Depth in the nesting, counted against the LARGER faces only: they are
    # sorted, so anything containing face i comes before it.
    depth = [sum(1 for j in range(i) if faces[j].is_inside(points[i]))
             for i in range(len(faces))]
    out = []
    for i, f in enumerate(faces):
        if depth[i] % 2:
            continue                          # a hole; cut below
        holes = [faces[j] for j in range(len(faces))
                 if depth[j] == depth[i] + 1 and f.is_inside(points[j])]
        for h in holes:
            f = f - h
        out.append(f)
    return tuple(out)


def logo(game, filename="lid_logo.dxf"):
    path = LOGO_DIR / game / filename
    return load(path) if path.exists() else None


@lru_cache(maxsize=16)
def _box(game, filename):
    faces = logo(game, filename)
    if not faces:
        return None
    bb = Compound(children=list(faces)).bounding_box()
    return bb.min.X, bb.min.Y, bb.max.X, bb.max.Y


def extent(game, filename="lid_logo.dxf"):
    """(width, height) of a drawing, or None. Cached: `lid.logo_choice` asks it
    of every variant of every lid."""
    bb = _box(game, filename)
    return None if bb is None else (bb[2] - bb[0], bb[3] - bb[1])


def centre(game, filename="lid_logo.dxf"):
    """(x, y) of a drawing's bounding-box centre — what a fit scales about, so
    a mark drawn off-centre stays put."""
    bb = _box(game, filename)
    return None if bb is None else ((bb[0] + bb[2]) / 2, (bb[1] + bb[3]) / 2)
