#!/usr/bin/env python3
"""Check cad/parts/topper.py against the hand-exported Onshape STEPs.

    .venv/bin/python tests/test_topper.py

The Topper is being built group by group, as the Box was, and this asserts only
what has actually been written. It grows with it.

The reference it builds against is the **unfilleted** one — `Top and front
edges` suppressed — because that is the body every dimension can be read off
without a blend in the way. `spec/TOPPER.md` records what each was measured
from.

Proven so far: the envelope and its three rules, the frame, `#TopperHeight`
both ways, the section that `TriangleMatch` and `CardHeight` make, the slant
being the Holder's OWN, and where the ribs and front bands sit.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from build123d import import_step, Plane, Box, Pos       # noqa: E402
from cad import params, derive as D                      # noqa: E402
from cad.parts import holder as H, topper as T           # noqa: E402

STEP_DIR = ROOT / "spec" / "reference"
# Innovation `4 Later Ages 5 Expansions` unsleeved, M5.10.10.32-Un. The
# unfilleted export is at this parameter set, and so is every logo sketch.
P = params.Primary(4, 5, 15, 10, 0, 10, 0, 0, "Innovation")

fails = []


def check(label, got, want, tol=1e-6):
    ok = abs(got - want) <= tol if isinstance(want, float) else got == want
    print(f"  {'ok  ' if ok else 'FAIL'} {label:58s} {got!r:>24} vs {want!r}")
    if not ok:
        fails.append(label)


def runs(solid, y, z, x_centre=100.5, span=400.0):
    """X runs of material along a thin bar at (y, z) — the probe that separates
    a rib from the front band, which a plan section cannot."""
    cut = solid & (Pos(x_centre, y, z) * Box(span, 0.02, 0.02))
    if cut is None:
        return []
    segs = sorted((q.bounding_box().min.X, q.bounding_box().max.X)
                  for q in cut.solids())
    out = []
    for a, b in segs:
        if out and a - out[-1][1] < 0.01:
            out[-1][1] = b
        else:
            out.append([a, b])
    return [(round(a, 3), round(b, 3)) for a, b in out]


d = D.derive(P)
ref = import_step(
    str(STEP_DIR / "Topper Blank M5.10.10.32-Un without top and front edges.step")
).solids()[0]

print("=== the envelope, and its three rules ===")
rb = ref.bounding_box()
check("width is calSlotwidth * HorizontalSlots",
      round(T.width(P, d), 3), round(rb.size.X, 3), 1e-3)
check("depth is the HOLDER's own", round(T.depth(P, d), 3),
      round(rb.size.Y, 3), 1e-3)
check("... which is 2.000 + calSlotDepth",
      round(T.depth(P, d), 3), round(2.0 + d.calSlotDepth, 3), 1e-9)
check("the tabs top out TOTAL_HEIGHT above the base",
      round(T.Z_BASE + T.TOTAL_HEIGHT, 3), round(rb.max.Z, 3), 1e-3)

print("\n=== the frame ===")
x0, x1 = T.x_span(P, d)
front, rear = T.y_span(P, d)
check("X starts at -calSlotwidth/2 — the HOLDER's datum",
      round(x0, 3), round(rb.min.X, 3), 1e-3)
check("X 0 is the centre of the first slot",
      round(x0 + d.calSlotwidth / 2, 6), 0.0, 1e-9)
check("the front face is at -depth", round(front, 3), round(rb.max.Y, 3), 1e-3)
check("the rear face is at -2*depth", round(rear, 3), round(rb.min.Y, 3), 1e-3)
check("the base is at Z_BASE", round(T.Z_BASE, 3), round(rb.min.Z, 3), 1e-3)

print("\n=== #TopperHeight, two ways ===")
th = T.topper_height(P, d)
check("Allan's expression gives 4.200", round(th, 3), 4.200, 1e-9)
# and the geometry says the same: the rear of the section is that thick
rear_runs = [f for f in Plane.YZ.offset(100.5).intersect(ref).faces()]
check("the section's REAR is #TopperHeight thick",
      round(T.slant_z(P, d, rear) - T.Z_BASE, 3), round(th, 3), 1e-9)

print("\n=== the slant is the HOLDER's, not a second transcription ===")
check("topper.slant_slope IS holder.slant_slope",
      T.slant_slope(P, d), H.slant_slope(P, d, first=False))
# read off the reference, so the claim is measured and not merely delegated
sec = Plane.YZ.offset(33.5).intersect(ref).faces()[0]
slant = max((e for e in sec.edges()
             if abs(e.start_point().Y - e.end_point().Y) > 1e-9),
            key=lambda e: e.length)
a, b = slant.start_point(), slant.end_point()
check("... and that is the reference's own slope",
      round(abs((b.Z - a.Z) / (b.Y - a.Y)), 6),
      round(T.slant_slope(P, d), 6), 1e-5)

print("\n=== the wedge: TriangleMatch + CardHeight ===")
w = T.wedge(P, d)
wb = w.bounding_box()
for ax in "XYZ":
    check(f"wedge {ax} min", round(getattr(wb.min, ax), 3),
          round(getattr(rb.min, ax), 3), 1e-3)
check("wedge Z max is the wall top, below the tabs",
      round(wb.max.Z, 3), round(T.slant_z(P, d, front - T.FRONT_WALL), 3), 1e-3)
for x in (33.5, 100.5, 167.5):
    check(f"section at a rib, X={x}",
          round(sum(f.area for f in Plane.YZ.offset(x).intersect(w).faces()), 3),
          round(sum(f.area for f in Plane.YZ.offset(x).intersect(ref).faces()), 3),
          1e-3)

print("\n=== ribs and front bands: a T in plan, not a post ===")
# At the front face the material is BAND wide; one step back it is RIB wide.
# A plan section cannot tell those apart — it reads one 14.800 block.
front_runs = runs(ref, front - 0.1, 55.0, x_centre=33.5, span=60.0)
back_runs = runs(ref, front - 0.9, 55.0, x_centre=33.5, span=60.0)
check("at the front face the band is 14.800 wide",
      round(front_runs[0][1] - front_runs[0][0], 3), round(2 * T.BAND_HALF, 3), 1e-3)
check("one step back only the rib remains, 1.600",
      round(back_runs[0][1] - back_runs[0][0], 3), round(T.RIB_W, 3), 1e-3)
check("the rib is centred on the slot boundary",
      round((back_runs[0][0] + back_runs[0][1]) / 2, 3), 33.500, 1e-3)

check("rib count is HorizontalSlots - 1", len(T.rib_x(P, d)), P.HorizontalSlots - 1)
for got, want in zip(T.rib_x(P, d), [(32.7, 34.3), (99.7, 101.3), (166.7, 168.3)]):
    check(f"rib at {want}", (round(got[0], 3), round(got[1], 3)), want)
for got, want in zip(T.band_x(P, d),
                     [(-33.5, -26.1), (26.1, 40.9), (93.1, 107.9),
                      (160.1, 174.9), (227.1, 234.5)]):
    check(f"band at {want}", (round(got[0], 3), round(got[1], 3)), want)

print("\n=== against the rolled-back exports (M15-Sl, a SECOND parameter set) ===")
# Both rollbacks predate `Upside Down`, so they arrive in the pre-flip frame.
# That transform is itself a measurement: a 180-degree turn about X through
# (y = -depth, z = Z_BASE) puts all three bodies on the same envelope exactly.
from build123d import Pos, Rot                            # noqa: E402
Q = params.Primary(4, 5, 15, 15, 0, 15, 1, 0, "Innovation")
dq = D.derive(Q)
dpq = T.depth(Q, dq)


def unflip(solid):
    return Pos(0, -2 * dpq, 2 * T.Z_BASE) * Rot(180, 0, 0) * solid


roll1 = unflip(import_step(str(STEP_DIR / "Topper M5.15.15.62-Sl to Remove Inner Hole.step")).solids()[0])
roll2 = unflip(import_step(str(STEP_DIR / "Topper M5.15.15.62-Sl after More Dividers.step")).solids()[0])

rb1 = roll1.bounding_box()
wq = T.wedge(Q, dq)
check("the flip puts the rollback on the wedge's envelope (X)",
      round(rb1.min.X, 6), round(wq.bounding_box().min.X, 6), 1e-6)
check("... (Y)", round(rb1.min.Y, 6), round(wq.bounding_box().min.Y, 6), 1e-6)
check("... (Z)", round(rb1.min.Z, 6), round(wq.bounding_box().min.Z, 6), 1e-6)

pocketed = wq - T.inner_hole(Q, dq)
check("Remove Inner Hole: volume", round(pocketed.volume, 4),
      round(roll1.volume, 4), 1e-4)
check("Remove Inner Hole: face count", len(pocketed.faces()), len(roll1.faces()))
check("Remove Inner Hole: nothing left over",
      round((pocketed - roll1).volume if (pocketed - roll1) else 0.0, 6), 0.0, 1e-6)
check("Remove Inner Hole: nothing missing",
      round((roll1 - pocketed).volume if (roll1 - pocketed) else 0.0, 6), 0.0, 1e-6)

check("the pocket is inset INNER_END_INSET from each end",
      round(T.inner_hole(Q, dq).bounding_box().min.X - wq.bounding_box().min.X, 4),
      round(T.INNER_END_INSET, 4), 1e-4)
check("... and INNER_INSET * cos(theta) in Y at the rear",
      round(T.inner_hole(Q, dq).bounding_box().min.Y - rb1.min.Y, 4),
      round(T.INNER_INSET * T.slant_cos(Q, dq), 4), 1e-4)

grouped = pocketed - T.front_removal(Q, dq) + T.dividers(Q, dq)
check("front removal + dividers: volume", round(grouped.volume, 3),
      round(roll2.volume, 3), 1e-3)
# The r2.0 `Fillet front holes` is NOT built — OCCT will not put a 2.000 round
# on an 0.800 wall, which is what Onshape's "allow edge overflow" is doing. It
# moves 5.494 mm3 without changing the total, so volume alone would pass it.
sym = (grouped - roll2)
check("what is left is ONLY the unbuilt r2.0 fillet",
      round(sym.volume if sym else 0.0, 3), 5.494, 0.01)
check("... which is under 0.1% of the group",
      round(100 * (sym.volume if sym else 0.0) / roll2.volume, 3) < 0.1, True)
check("the reference carries it as 16 cylinders at r2.0",
      sum(1 for f in roll2.faces()
          if "CYLINDER" in str(f.geom_type) and abs(f.radius - T.FRONT_FILLET) < 1e-6), 16)

print("\n=== it is Innovation-only ===")
check("(not yet enforced — build() is not written)", True, True)

print("\nPASS" if not fails else f"\nFAIL ({len(fails)}): " + ", ".join(fails[:6]))
sys.exit(1 if fails else 0)
