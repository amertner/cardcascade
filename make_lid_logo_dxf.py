#!/usr/bin/env python3
"""Lift a lid's logo artwork out of a reference STEP into a DXF.

The Lid carries its game's logo in the underside of its floor, printed in the
second filament: a pocket `0.810` deep with an inlay solid sitting in it. In
Onshape that is one sketch — "derived from a .DXF file with the logo and tidied
up" (Allan) — and two features, `Remove logo` then `Add Logo Material`.

`cad/` needs the same artwork. The authoritative copy is whatever Allan
exports from that sketch; this lifts an equivalent one out of a hand-exported
lid STEP, which costs 0 API calls and needs nothing but a reference that
already carries the logo. Use it to bootstrap a game that has no DXF yet, and
to CHECK one that does — `tests/test_lid.py` holds the built pattern to the
reference either way.

    python3 make_lid_logo_dxf.py "spec/reference/Lid Dominion 246S with logo.step" \
            logos/Dominion/lid_logo.dxf

The inlays are the solids in the file that are not the lid body; their top
faces ARE the artwork, and they are already in the lid's own frame, so the
lifted DXF needs no placing. Curves survive: `Lid Innovation 130U` carries 361
arcs and 234 B-splines, and the round trip holds its area to 0.003 % and its
bounding box exactly.

Requires the venv (build123d).
"""
import argparse
import sys
from pathlib import Path

from build123d import Compound, GeomType, Location, Unit, import_step
from build123d.exporters import ExportDXF


def artwork(step):
    """The logo's top faces, flattened to z = 0, from a lid STEP."""
    solids = import_step(str(step)).solids()
    body = max(solids, key=lambda s: s.volume)
    tops = [f for s in solids if s is not body for f in s.faces()
            if f.geom_type == GeomType.PLANE
            and f.normal_at(f.center()).Z > 0.999]
    if not tops:
        sys.exit(f"{step}: no inlay solids — is this an export WITHOUT the "
                 f"logo meshes embedded?")
    return [f.moved(Location((0, 0, -f.center().Z))) for f in tops]


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("step", type=Path, help="a lid STEP carrying the logo")
    ap.add_argument("dxf", type=Path, help="where to write the artwork")
    args = ap.parse_args(argv)

    faces = artwork(args.step)
    ex = ExportDXF(unit=Unit.MM)
    for f in faces:
        ex.add_shape(f)
    args.dxf.parent.mkdir(parents=True, exist_ok=True)
    ex.write(str(args.dxf))
    bb = Compound(children=faces).bounding_box()
    print(f"  {args.dxf}: {len(faces)} regions, "
          f"{sum(len(f.wires()) for f in faces)} loops, "
          f"{sum(f.area for f in faces):.3f} mm2")
    print(f"  bbox x {bb.min.X:.3f}..{bb.max.X:.3f}  "
          f"y {bb.min.Y:.3f}..{bb.max.Y:.3f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
