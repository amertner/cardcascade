#!/usr/bin/env python3
"""Lift a lid's logo artwork out of a reference export into a DXF.

The Lid carries its game's logo in the underside of its floor, printed in the
second filament: a pocket `0.810` deep with an inlay solid sitting in it. In
Onshape that is one sketch — "derived from a .DXF file with the logo and tidied
up" (Allan) — and two features, `Remove logo` then `Add Logo Material`.

`cad/` needs the same artwork. The authoritative copy is whatever Allan
exports from that sketch; this lifts an equivalent one out of a reference that
already carries the logo, which costs 0 API calls. Use it to bootstrap a game
that has no DXF yet, and to CHECK one that does — `tests/test_lid.py` holds the
built pattern to the reference either way.

Two sources, in order of fidelity:

    # a hand-exported STEP: true curves, exact
    python3 make_lid_logo_dxf.py "spec/reference/Lid Dominion 246S with logo.step" \
            logos/Dominion/lid_logo.dxf

    # a cached component 3MF: polylines, and every game already has one
    python3 make_lid_logo_dxf.py "individual/Compile/Lid S5.7.7.20-Un.3mf" \
            logos/Compile/lid_logo.dxf

The inlays are the solids in the file that are not the lid body; their top
faces ARE the artwork, and they are already in the lid's own frame, so the
lifted DXF needs no placing.

A STEP keeps the curves: `Lid Innovation 130U` carries 361 arcs and 234
B-splines, and the round trip holds its area to 0.003 % and its bounding box
exactly. A 3MF has been meshed, so its outlines come back as polylines at
Onshape's own export tolerance — on the same Innovation mark that is 2773
segments over 31 regions and 685.614 mm2 against the STEP's 685.790, an area
error of 0.026 % and about 90 segments a region. Small enough not to matter in
a 0.810-deep inlay, but a STEP is still better where one exists: prefer it, and
record in `spec/LID.md` which source each file came from.

Requires the venv (build123d).
"""
import argparse
import math
import sys
import zipfile
from collections import defaultdict
from pathlib import Path

from build123d import (Compound, GeomType, Location, Polyline, Unit, Wire,
                       import_step)
from build123d.exporters import ExportDXF

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cad import art, mesh3mf                               # noqa: E402

# How far two vertices may be apart and still be the same one when the loops
# are chained. A 3MF's vertices are welded by the writer, so the ends of two
# boundary edges either share an index or do not — this only guards a file
# welded on a coarser key than `mesh3mf` uses.
WELD = 1e-6


def _from_step(path):
    """The logo's top faces, flattened to z = 0, from a lid STEP."""
    solids = import_step(str(path)).solids()
    body = max(solids, key=lambda s: s.volume)
    tops = [f for s in solids if s is not body for f in s.faces()
            if f.geom_type == GeomType.PLANE
            and f.normal_at(f.center()).Z > 0.999]
    if not tops:
        sys.exit(f"{path}: no inlay solids — is this an export WITHOUT the "
                 f"logo meshes embedded?")
    return [f.moved(Location((0, 0, -f.center().Z))) for f in tops]


def _volume(verts, tris):
    """Six times the signed tetrahedron sum — only its magnitude is used, to
    tell the lid body from the inlays without assuming an order or a name."""
    total = 0.0
    for a, b, c in tris:
        (ax, ay, az), (bx, by, bz), (cx, cy, cz) = verts[a], verts[b], verts[c]
        total += (ax * (by * cz - bz * cy) - ay * (bx * cz - bz * cx)
                  + az * (bx * cy - by * cx))
    return abs(total) / 6


def _loops(verts, tris):
    """The outlines of the top of one meshed inlay, as lists of points.

    The top is flat, so its triangles are the ones whose three vertices all sit
    at the object's maximum z. Each of those is wound counter-clockwise seen
    from +Z, so every directed edge has the region on its LEFT; an edge whose
    reverse is also present is interior, and one that stands alone is on the
    outline. Chaining those gives one loop per region and one more per counter
    — the `o`s of a wordmark come back as their own loops, which is what
    `cad.art` then reads as holes.

    Two loops can MEET at a vertex — a tessellation pinch, and the FCM mark has
    several. So the walk is the standard face traversal rather than "follow the
    only other edge": arriving along u->v it leaves along the first edge
    clockwise from v->u, which keeps the region on the left and so keeps the
    two loops apart. Chained by nearest-neighbour instead, one FCM inlay came
    back as a single 1592-point figure of eight that no plane could be fitted
    to.
    """
    zmax = max(v[2] for v in verts)
    top = [t for t in tris if all(abs(verts[i][2] - zmax) < WELD for i in t)]
    seen = set()
    for a, b, c in top:
        for e in ((a, b), (b, c), (c, a)):
            seen.add(e)
    out_edges = defaultdict(list)
    for a, b in seen:
        if (b, a) not in seen:
            out_edges[a].append(b)

    def angle(a, b):
        return math.atan2(verts[b][1] - verts[a][1], verts[b][0] - verts[a][0])

    def step(u, v):
        """The edge out of `v` that continues the loop arrived at along u->v."""
        cand = out_edges[v]
        if len(cand) == 1:
            return cand[0]
        back = angle(v, u)
        # first edge clockwise from v->u, i.e. the largest turn the other way
        return max((w for w in cand if w != u), key=lambda w:
                   (angle(v, w) - back) % (2 * math.pi), default=u)

    walked, out = set(), []
    for start in list(out_edges):
        for first in out_edges[start]:
            if (start, first) in walked:
                continue
            loop, u, v = [start], start, first
            walked.add((start, first))
            while v != start:
                loop.append(v)
                w = step(u, v)
                walked.add((v, w))
                u, v = v, w
            if len(loop) >= 3:
                out.append([(verts[i][0], verts[i][1], 0.0) for i in loop])
    return out


def _from_3mf(path):
    """The logo's outlines, as closed wires at z = 0, from a cached lid 3MF."""
    objs = mesh3mf.read(path)
    if len(objs) < 2:
        sys.exit(f"{path}: one object only — this lid carries no logo")
    body = max(range(len(objs)), key=lambda i: _volume(objs[i][1], objs[i][2]))
    wires = []
    for i, (_name, verts, tris) in enumerate(objs):
        if i == body:
            continue
        for loop in _loops(verts, tris):
            wires.append(Wire(Polyline(*loop, close=True).edges()))
    if not wires:
        sys.exit(f"{path}: no inlay outlines found")
    return wires


def artwork(src):
    """The logo's outlines at z = 0, from a STEP, a 3MF, or another DXF."""
    src = Path(src)
    if src.suffix.lower() == ".3mf":
        return _from_3mf(src)
    if src.suffix.lower() == ".dxf":
        return list(art.load(src))
    if not zipfile.is_zipfile(src):
        return _from_step(src)
    sys.exit(f"{src}: a zip that is not a .3mf — expected a STEP, 3MF or DXF")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("src", type=Path,
                    help="a lid STEP or 3MF carrying the logo, or a DXF")
    ap.add_argument("dxf", type=Path, help="where to write the artwork")
    ap.add_argument("--above", type=float, metavar="Y",
                    help="keep only the parts of the mark that sit above Y — "
                         "how the plain Innovation logo is cut from the "
                         "Ultimate one (spec/LID.md)")
    ap.add_argument("--recentre", action="store_true",
                    help="with --above, put what is kept back on the FULL "
                         "mark's own centre in Y, so it still sits centred on "
                         "the lid")
    args = ap.parse_args(argv)

    shapes = artwork(args.src)
    if args.above is not None:
        was = Compound(children=list(shapes)).bounding_box()
        shapes = [s for s in shapes if s.bounding_box().min.Y > args.above]
        if not shapes:
            sys.exit(f"--above {args.above}: nothing left of the mark")
        if args.recentre:
            now = Compound(children=list(shapes)).bounding_box()
            dy = (was.min.Y + was.max.Y) / 2 - (now.min.Y + now.max.Y) / 2
            shapes = [s.moved(Location((0, dy, 0))) for s in shapes]
    ex = ExportDXF(unit=Unit.MM)
    for s in shapes:
        ex.add_shape(s)
    args.dxf.parent.mkdir(parents=True, exist_ok=True)
    ex.write(str(args.dxf))
    bb = Compound(children=list(shapes)).bounding_box()
    kind = "regions" if args.src.suffix.lower() != ".3mf" else "loops"
    print(f"  {args.dxf}: {len(shapes)} {kind}")
    print(f"  bbox x {bb.min.X:.3f}..{bb.max.X:.3f} ({bb.size.X:.3f})  "
          f"y {bb.min.Y:.3f}..{bb.max.Y:.3f} ({bb.size.Y:.3f})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
