"""Imported 2D artwork — the Lid's logo, and anything else drawn rather than
computed.

A DXF holds outlines, not regions: the counters of an `o` and the gaps in a
logo arrive as separate closed loops, and which of them is a hole is a
question about nesting. `labelmaker.load_art` answers it the same way for the
printed labels; this is that rule for `cad/`, without dragging in
`labelmaker`'s 67 KB of label machinery.

The artwork lives in `logos/<Game>/` and is already in the part's own frame —
`spec/LID.md` records where each file came from.
"""
from functools import lru_cache
from pathlib import Path

from build123d import Compound, Face, Wire, import_brep, import_dxf

LOGO_DIR = Path(__file__).resolve().parent.parent / "logos"

# How far apart two ends may be and still be one loop. A DXF's coordinates are
# text, so a curve exported from CAD comes back rounded: build123d's own
# exporter needs 0.010 here, where a file of closed polylines needs nothing at
# all. It is a CHAINING tolerance, not a geometric one — the loops it builds
# hold their area to 0.003 % and their bounding box exactly.
CHAIN_TOL = 0.010


def _inside_point(face):
    """A point strictly inside `face` — its centre when the shape is convex
    enough, else the first hit of a coarse grid. Same trick as
    `labelmaker.load_art`: a logo's outline is rarely convex."""
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


@lru_cache(maxsize=8)
def load(path):
    """The drawing in `path` (DXF) as filled faces, ready to extrude.

    A loop nested in an odd number of others is a HOLE in the face around it,
    and one nested in an even number is a face of its own — an island inside a
    hole, which the Innovation logo's `o` counters need.

    A `.brep` is a drawing too — the faces themselves, as OCCT wrote them,
    which is how artwork LIFTED FROM A STEP is kept exact: a DXF re-fits a
    spline hole on the way back and the `o`'s counter came out 0.65 % small,
    where the B-rep round-trips to the last digit (`spec/LID.md`, "the
    corrected export"). Its faces are complete, holes included, so the loop
    nesting below is skipped.

    Cached: one file serves every lid of its game.
    """
    if path.suffix == ".brep":
        return tuple(import_brep(str(path)).faces())
    shapes = import_dxf(str(path))
    edges = shapes.edges()
    if not edges:
        raise ValueError(f"{path}: no geometry")
    loops = [w for w in Wire.combine(edges, tol=CHAIN_TOL) if w.is_closed]
    if not loops:
        raise ValueError(f"{path}: no closed outlines to fill")
    faces = sorted((Face(w) for w in loops), key=lambda f: -f.area)
    points = [_inside_point(f) for f in faces]
    # Depth in the nesting, counted against the LARGER faces only — they are
    # sorted, so anything that contains face i comes before it.
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
    """A game's lid artwork, or None where the game has none on file."""
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
    """(width, height) of a drawing, or None where there is no such file.

    Cached, because `lid.logo_choice` asks it of every variant of every lid
    just to decide which one fits — that question needs the size and not the
    geometry.
    """
    bb = _box(game, filename)
    return None if bb is None else (bb[2] - bb[0], bb[3] - bb[1])


def centre(game, filename="lid_logo.dxf"):
    """(x, y) of a drawing's bounding-box centre — what a fit scales about, so
    that a mark drawn off-centre stays where it was drawn."""
    bb = _box(game, filename)
    return None if bb is None else ((bb[0] + bb[2]) / 2, (bb[1] + bb[3]) / 2)
