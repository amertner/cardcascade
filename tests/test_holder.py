#!/usr/bin/env python3
"""Check cad/parts/holder.py against the hand-exported Onshape STEPs.

    .venv/bin/python tests/test_holder.py

Three references in `spec/reference/`, listed in `spec/HOLDER.md`. The Holder is
being built group by group; this asserts only what has actually been written,
and grows with it.

The 246 pair is what makes this worth doing: it is ONE configuration exported
twice, as `Holder` and as `FirstHolder`, so the two differ only in what `first`
changes, and its `calSliderDistance` and `calFirstSliderDistance` differ by more
than a factor of two. Every reading below that involves a slider distance is
therefore asserted against a case that would fail if the wrong one were used.

Proven so far: the envelope (width, depth, the base), the `Top slant angle`
plane pair and its slope, the vertical datum, and `Hole for cards`.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from build123d import import_step                    # noqa: E402
from cad import params, derive as D                  # noqa: E402
from cad.parts import holder                         # noqa: E402

STEP_DIR = ROOT / "spec" / "reference"
P246 = params.Primary(3, 2, 40, 12, 1, 30, 1, 0, "Dominion")
P333 = params.Primary(3, 9, 21, 10, 0, 10, 1, 0, "Dominion")
REFS = [
    ("Dominion 246 Sl", "Holder S2.40.12-30.45-Sl.step", P246, False),
    # The same row's first riser: same box, deeper holder. calFirstSliderDistance
    # 20.400 against calSliderDistance 9.600.
    ("Dominion 246 Sl (first)", "FirstHolder S2.40.12-30.45-Sl.step", P246, True),
    # Nine risers, the catalogue's shallowest rise, and the cascade whose Box
    # and Pusher are already references.
    ("Dominion 333 Sl", "Holder S9.21.10.62-Sl.step", P333, False),
]
fails = []


def check(label, got, want, tol=1e-6):
    ok = abs(got - want) <= tol if isinstance(want, float) else got == want
    print(f"  {'ok  ' if ok else 'FAIL'} {label:54s} {got!r:>24} vs {want!r}")
    if not ok:
        fails.append(label)


def planes(shape, axis):
    """Offsets of every planar face whose normal is along `axis`."""
    out = set()
    for f in shape.faces():
        try:
            n = f.normal_at(f.center())
        except Exception:
            continue
        if abs(getattr(n, axis)) > 0.999:
            out.add(round(getattr(f.center(), axis), 3))
    return sorted(out)


def slants(shape):
    """{(slope, Z where the plane meets Y=0): total area} for the sloped faces.

    Aggregated by the PLANE, not by the face: Onshape leaves the slant split
    into several faces, and on the 246 pair no single piece is large enough to
    find by area alone. Reading the plane off the normals is also what keeps
    this honest — measuring the slope as a drop between wall tops picks up
    whichever of the two parallel planes that wall happens to reach, which is
    not the same one on every holder.
    """
    out = {}
    for f in shape.faces():
        try:
            n = f.normal_at(f.center())
        except Exception:
            continue
        if abs(n.X) < 1e-6 and 0.02 < abs(n.Z) < 0.999:
            c = f.center()
            slope = -n.Y / n.Z
            key = (round(slope, 4), round(c.Z + slope * (0.0 - c.Y), 3))
            out[key] = out.get(key, 0.0) + f.area
    return out


for name, fn, p, first in REFS:
    path = STEP_DIR / fn
    print(f"\n=== {name} ===")
    if not path.exists():
        print(f"  SKIP — {path} not present")
        continue
    ref = import_step(str(path)).solids()[0]
    d = D.derive(p)
    mine = holder.build(p, first)
    rb, mb = ref.bounding_box(), mine.bounding_box()
    sd = holder.slider_distance(d, first)

    # --- the envelope ------------------------------------------------------
    # Width is calSlotwidth * n + 9.800 and has nothing to do with the depth;
    # the two 246 holders share it and differ in everything else.
    check("width = calSlotwidth * n + 9.800", round(rb.size.X, 3),
          round(holder.holder_width(p, d), 3), 1e-3)
    check("... and the build agrees", round(mb.size.X, 3),
          round(rb.size.X, 3), 1e-3)
    # X is NOT symmetric: the origin is the first compartment's centre.
    x0, x1 = holder.x_span(p, d)
    check("X starts at -(calSlotwidth/2 + 4.900)", round(rb.min.X, 3),
          round(x0, 3), 1e-3)
    check("X ends at the last compartment + the same", round(rb.max.X, 3),
          round(x1, 3), 1e-3)

    # Depth takes the holder's OWN slider distance. 9.200 / 20.000 / 8.000.
    # Measured as the BACK FACE, not the bounding box: the rear lip's tab stands
    # proud in +Y (1.026 / 1.655 / 1.342 on the three), so the STEP's bbox is
    # wider than the body and would compare against nothing meaningful.
    check("the back face is at -(sliderDistance - 0.400)", round(rb.min.Y, 3),
          round(-holder.holder_depth(d, first), 3), 1e-3)
    check("... and the build agrees", round(mb.min.Y, 3),
          round(rb.min.Y, 3), 1e-3)
    check("the front face is Y = 0", round(mb.max.Y, 3), 0.0, 1e-3)

    # The base is (CardHeight - 1.5)/2 below the origin on every holder.
    check("base = -(CardHeight - 1.5)/2", round(rb.min.Z, 3),
          round(holder.base_z(d), 3), 1e-3)
    check("... and the build agrees", round(mb.min.Z, 3),
          round(rb.min.Z, 3), 1e-3)

    # --- `Top slant angle` --------------------------------------------------
    # Two PARALLEL planes 2.000 apart, both meeting Y = 0 at the same Z on every
    # reference whatever the slope. Asserted on the STEP and on the build.
    want = round(holder.slant_slope(d, first), 4)
    rival = round((d.calHeightIncrement - 1.0)
                  / ((d.calSliderDistance if first else d.calFirstSliderDistance)
                     - 1.2), 4)
    for who, shape in (("STEP", ref), ("build", mine)):
        found = slants(shape)
        tops = sorted({z for (s, z), a in found.items()
                       if abs(s - want) < 5e-4 and a > 20.0}, reverse=True)
        check(f"{who}: the slant slope is (HInc-1)/(sliderDistance-1.2)",
              bool(tops), True)
        if tops:
            check(f"{who}: the upper slant meets Y=0 at half the pocket",
                  tops[0], round(holder.slant_top(d), 3), 1e-3)
    # The STEP has the second plane too; the build does not build it yet.
    found = slants(ref)
    tops = sorted({z for (s, z), a in found.items()
                   if abs(s - want) < 5e-4 and a > 20.0}, reverse=True)
    check("STEP: and a second slant plane 2.000 below it",
          len(tops) >= 2 and abs((tops[0] - tops[1]) - holder.SLANT_STEP) < 1e-3,
          True)
    # The rival slider distance is a different number on the 246 pair, and the
    # same one on 333 — which is exactly why the pair had to be exported.
    if abs(rival - want) > 5e-4:
        check("the OTHER slider distance would give a different slope",
              any(abs(s - rival) < 5e-4 for (s, z) in found), False)

    # --- the vertical datum -------------------------------------------------
    # Confirmed independently by where the `Hole outline` sketch lands: inset
    # 2.000 from the pocket's bottom and calHeightIncrement + 10 from its top.
    pz0, pz1 = holder.pocket_z(d)
    check("the pocket is CardHeight - 3.5 tall", round(pz1 - pz0, 3),
          round(d.CardHeight - 3.5, 3), 1e-3)
    check("... starting 2.000 above the base",
          round(pz0 - holder.base_z(d), 3), 2.000, 1e-3)
    outline_lo, outline_hi = pz0 + 2.0, pz1 - (d.calHeightIncrement + 10.0)
    # Those two land on real faces of the STEP: the lattice's bottom rail sits
    # on the first and its top rail on the second.
    zs = planes(ref, "Z")
    for lbl, z in (("bottom", outline_lo), ("top", outline_hi - 2.0)):
        check(f"STEP has a Z-plane at the outline's {lbl}",
              any(abs(v - z) < 1e-3 for v in zs), True)

    # --- `Hole for cards` ---------------------------------------------------
    # The walls are the only material left at a lattice rail's height, so the
    # pocket is inset WALL from both faces. Four Y-planes, and the two inner
    # ones move with the holder's own depth.
    want_y = [round(v, 3) for v in
              (-holder.holder_depth(d, first),
               -holder.holder_depth(d, first) + holder.WALL,
               -holder.WALL, 0.0)]
    check("build: four Y-planes, the walls WALL thick",
          [round(abs(v), 3) if v == 0 else round(v, 3)
           for v in planes(mine, "Y")], want_y)
    for v in want_y:
        check(f"STEP has the Y-plane at {v}",
              any(abs(q - v) < 1e-3 for q in planes(ref, "Y")), True)
    # The compartment edges: DIVIDER/2 in from each slot edge, patterned at
    # calSlotwidth. Every one of them is a face of the STEP too.
    edges = []
    for x in holder.compartment_x(p, d):
        edges += [round(x - (d.calSlotwidth - holder.DIVIDER) / 2, 3),
                  round(x + (d.calSlotwidth - holder.DIVIDER) / 2, 3)]
    for v in edges:
        check(f"STEP has the compartment edge at {v}",
              any(abs(q - v) < 1e-3 for q in planes(ref, "X")), True)

print("\nPASS" if not fails else "\nFAIL: " + ", ".join(fails))
sys.exit(1 if fails else 0)
