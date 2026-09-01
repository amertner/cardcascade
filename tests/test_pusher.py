#!/usr/bin/env python3
"""Check cad/parts/pusher.py against the hand-exported Onshape STEPs.

Two references, chosen to exercise different halves of the design:

  Compile 105 Card Sleeved   S4.7.7.32-Sl   4 equal risers, C3, notch
  Dominion 246 Card Sleeved  S2.40.12-30.45-Sl  2 risers with a first-riser
                             override (30 cards), C3, notch

The Dominion one is what settles `slider_drops()`: its first riser drops
20.400 (calFirstSliderDistance) and its second 9.600 (calSliderDistance), so
the larger drop is at the leading edge.

Both carry engraved text the build places by its own rule rather than copying
(see cad/text.py), so the SOLID is compared exactly and the text is checked
against its own invariants, not against the STEP.

    .venv/bin/python tests/test_pusher.py
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from build123d import import_step, Plane, Location, Vector, Mesher
from cad import params, lock as L, text as T, derive as D
from cad.parts import pusher

UP = Path.home() / ".claude/uploads/07f2d5de-ff9b-5727-acb3-79b6a8da454a"
REFS = [
    ("Compile 105 Card Sl", UP / "63735c8a-Pusher.step",
     params.Primary(3, 4, 7, 7, 0, 7, 1, 0, "Compile", "7.0")),
    ("Dominion 246 Card Sl", UP / "332e64f9-Pusher_D.step",
     params.Primary(3, 2, 40, 12, 1, 30, 1, 0, "Dominion", "7.0")),
]
fails = []


def check(label, got, want, tol=1e-6):
    ok = abs(got - want) <= tol if isinstance(want, float) else got == want
    print(f"  {'ok  ' if ok else 'FAIL'} {label:48s} {got!r:>16} vs {want!r}")
    if not ok:
        fails.append(label)


for name, path, p in REFS:
    print(f"\n=== {name} ===")
    if not path.exists():
        print(f"  SKIP — {path} not present")
        continue
    ref = import_step(str(path)).solids()[0]
    part = pusher.build(p, text=False)
    rb, pb = ref.bounding_box(), part.bounding_box()
    # The STEPs are in assembly position and their Z origin differs between
    # parts, so align on the bounding box rather than a fixed offset.
    moved = part.moved(Location(Vector(rb.min.X - pb.min.X,
                                       rb.min.Y - pb.min.Y,
                                       rb.min.Z - pb.min.Z)))
    d = D.derive(p)
    for ax, want in (("X", d.calPusherTotalHeight), ("Y", d.calPusherTotalDepth),
                     ("Z", L.PUSHER_TOTAL)):
        check(f"bbox {ax} matches STEP", round(getattr(pb.size, ax), 6),
              round(getattr(rb.size, ax), 6))
        check(f"bbox {ax} matches derive", round(getattr(pb.size, ax), 6),
              round(float(want), 6))

    front = rb.min.Z + L.PLATE
    glyphs = sum(f.area for f in ref.faces()
                 if abs(f.center().Z - (front - pusher.ENGRAVE)) < 1e-6)
    check("volume (STEP + the volume its engraving removed)",
          round(part.volume, 3), round(ref.volume + glyphs * pusher.ENGRAVE, 3), 0.02)

    a = (moved & Plane.XY.offset(rb.min.Z + L.PLATE / 2)).faces()[0]
    r = (ref & Plane.XY.offset(rb.min.Z + L.PLATE / 2)).faces()[0]
    check("mid-plate section area", round(a.area, 4), round(r.area, 4), 1e-4)
    check("mid-plate outline vertices",
          sorted({(round(v.X, 3), round(v.Y, 3)) for v in a.vertices()}),
          sorted({(round(v.X, 3), round(v.Y, 3)) for v in r.vertices()}))

    def zf(sh, z):
        return round(sum(f.area for f in sh.faces()
                         if abs(f.center().Z - z) < 1e-6), 4)
    check("tab top area", zf(moved, rb.max.Z), zf(ref, rb.max.Z), 1e-4)

    def xf(sh, x):
        return round(sum(f.area for f in sh.faces()
                         if abs(f.center().X - x) < 1e-6
                         and abs(f.normal_at(f.center()).X) > 0.999), 4)
    xs = sorted({round(f.center().X, 3) for f in ref.faces()
                 if abs(f.normal_at(f.center()).X) > 0.999 and f.area > 1.0})
    for x in xs:
        check(f"X-normal face area at x={x}", xf(moved, x), xf(ref, x), 1e-3)

    drops = pusher.slider_drops(p, d)
    check("slider drops sum to the depth", round(sum(drops), 6),
          round(d.calPusherTotalDepth, 6))
    if p.isFirstSlidingSlotOverride:
        check("first drop is calFirstSliderDistance (leading edge)",
              round(drops[0], 4), round(d.calFirstSliderDistance, 4))

print("\n=== the text rule (an invariant check, not a reproduction) ===")
for name, path, p in REFS:
    d = D.derive(p)
    (txt, sz, x, base), (ver, sz2, x2, base2) = T.logo_lines(p, d)
    cap = sz * T._CAP_PER_EM
    check(f"{name}: version cap is half the product's",
          round(sz2 * T._CAP_PER_EM, 6), round(cap / 2, 6))
    check(f"{name}: version baseline one cap below",
          round(base - base2, 6), round(cap, 6))
    # ink spans from `base` up to -margin, so the depth it uses is -base, and
    # it must leave the same margin below.
    check(f"{name}: product ink clears the front strip",
          round(-base + T.LOGO_MARGIN * d.calSliderDistance, 4)
          <= round(d.calSliderDistance, 4), True)
    width = T._width_per_cap(txt) * cap
    check(f"{name}: product line stops short of the end chamfer",
          round(x + width, 4) <= round(d.calPusherTotalHeight - pusher.CHAMFER, 4), True)
    check(f"{name}: both lines share a left anchor",
          round(x - T._LSB_C * sz, 4), round(x2 - T._LSB_C * sz2, 4), 1e-4)

print("\n=== every pusher in parts.csv builds and exports ===")
rows = params.load_rows(Path(__file__).resolve().parent.parent / "automation/parts.csv")
seen = {}
for r in rows:
    for slv in (0, 1):
        q = params.from_row(r, slv)
        seen.setdefault((q.GameName, q.RisingSliders, q.CardsPerSlidingSlot,
                         q.FirstSlidingSlotCards if q.isFirstSlidingSlotOverride
                         else 0, slv), q)
built = 0
for k, q in sorted(seen.items()):
    dq = D.derive(q)
    part = pusher.build(q, text=True)
    b = part.bounding_box()
    assert abs(b.size.X - dq.calPusherTotalHeight) < 1e-6
    assert abs(b.size.Y - dq.calPusherTotalDepth) < 1e-6
    assert abs(b.size.Z - L.PUSHER_TOTAL) < 1e-6
    built += 1
check("pushers built", built, len(seen))
check("classes cover C1..C5",
      sorted({L.lock_class(D.derive(q).calPusherTotalDepth)[0] for q in seen.values()}),
      ["C1", "C2", "C3", "C4", "C5"])
out = Path("/tmp/pusher_smoke.3mf")
m = Mesher(); m.add_shape(pusher.build(REFS[0][2]), part_number="Pusher"); m.write(out)
check("3MF export", out.exists() and out.stat().st_size > 0, True)
out.unlink(missing_ok=True)

print(f"\n{'PASS' if not fails else 'FAIL: ' + ', '.join(fails)}")
sys.exit(1 if fails else 0)
