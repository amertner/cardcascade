#!/usr/bin/env python3
"""Check cad/parts/pusher.py against the hand-exported Onshape STEPs.

Two references, chosen to exercise different halves of the design:

  Compile 105 Card Sleeved   S4.7.7.32-Sl   4 equal risers, C3, notch
  Dominion 246 Card Sleeved  S2.40.12-30.45-Sl  2 risers with a first-riser
                             override (30 cards), C3, notch

The Dominion one is what settles `slider_drops()`: its first riser drops
20.400 (calFirstSliderDistance) and its second 9.600 (calSliderDistance), so
the larger drop is at the leading edge.

Both carry engraved text. The build places it by its own rule rather than
copying Onshape's box fitting (see cad/text.py), so the SOLID is compared
exactly, the FONTS are compared against the STEP's own glyphs scale-fitted, and
the placement is checked against its own invariants.

The STEPs live in spec/reference/. They were exported by hand from Onshape,
which costs 0 API calls, and are committed because they are the only ground
truth the rebuild can be checked against.

    .venv/bin/python tests/test_pusher.py
"""
import sys
import tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from build123d import import_step, Plane, Location, Vector, Mesher
from cad import params, lock as L, text as T, derive as D
from cad.parts import pusher

REF_DIR = Path(__file__).resolve().parent.parent / "spec" / "reference"
REFS = [
    ("Compile 105 Card Sl", REF_DIR / "Pusher S4.7.7.32-Sl.step",
     params.Primary(3, 4, 7, 7, 0, 7, 1, 0, "Compile", "7.0")),
    ("Dominion 246 Card Sl", REF_DIR / "Pusher S2.40.12-30.45-Sl.step",
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
        # A missing reference is a FAILURE, not a skip: every STEP in
        # spec/reference is checked in, and a suite that turns green
        # when one goes missing is not a suite.
        print(f"  FAIL — reference {path.name} not present")
        fails.append(f"{name}: reference {path.name} missing")
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

print("\n=== fonts: the built glyphs against the STEP's, scale-fitted ===")
from build123d import Text, Align


def step_glyphs(sol, detail):
    """Glyph ink boxes on the engraved plane, in reading order. `detail` picks
    the rotated line down the leading edge rather than the two logo rows."""
    z = sol.bounding_box().min.Z + L.PLATE - pusher.ENGRAVE
    g = [f.bounding_box() for f in sol.faces() if abs(f.center().Z - z) < 1e-6]
    edge = min(b.min.X for b in g) + 6
    if detail:
        return sorted([b for b in g if b.max.X < edge], key=lambda b: -b.max.Y)
    return sorted([b for b in g if b.max.X >= edge],
                  key=lambda b: (round(-b.min.Y, 2), b.min.X))


for name, path, p in REFS:
    if not path.exists():
        continue
    sol = import_step(str(path)).solids()[0]
    d = D.derive(p)
    for label, txt, font, detail in (
            ("logo (Orbitron Bold)", d.ProductName, T.LOGO_FONT, False),
            ("detail (Open Sans Bold)", T.detail_line(p), T.DETAIL_FONT, True)):
        meas = step_glyphs(sol, detail)
        if not detail:                      # the logo plane holds both rows
            meas = [b for b in meas if abs(b.min.Y - meas[0].min.Y) < 1e-3]
        # rotated text puts the glyph height along X, upright text along Y
        mh = [b.size.X if detail else b.size.Y for b in meas]
        mw = [b.size.Y if detail else b.size.X for b in meas]
        rend = sorted(Text(txt, font_size=10.0, font_path=font,
                           align=(Align.MIN, Align.MIN)).faces(),
                      key=lambda f: f.bounding_box().min.X)
        check(f"{name}: {label} glyph count", len(meas), len(rend))
        if len(meas) != len(rend):
            continue
        sc = sum(m / f.bounding_box().size.Y for m, f in zip(mh, rend)) / len(rend)
        worst = max(max(abs(h - f.bounding_box().size.Y * sc),
                        abs(w - f.bounding_box().size.X * sc))
                    for h, w, f in zip(mh, mw, rend))
        check(f"{name}: {label} matches to <0.01 mm", round(worst, 4), 0.0, 0.01)

print("\n=== the text rule (an invariant check, not a reproduction) ===")
for name, path, p in REFS:
    d = D.derive(p)
    (txt, sz, x, base), (ver, sz2, x2, base2) = T.logo_lines(p, d)
    logo_cap_em, logo_asc_em = T._metrics(T.LOGO_FONT)
    cap = sz * logo_cap_em
    # Half the product's cap — or the 0.200 mm stroke floor where half is
    # under it, which `Dominion 246` is (0.885 em fitted, 1.695 floored) and
    # `Compile 105` is not. Asserted as the rule, from both ends.
    half_under_floor = sz / 2 < T.floor_size(T.LOGO_FONT) - 1e-9
    check(f"{name}: the fitted half-cap is {'under' if half_under_floor else 'over'} the floor",
          half_under_floor, name.startswith("Dominion 246"))
    check(f"{name}: version cap is half the product's, floored",
          round(sz2 * logo_cap_em, 6),
          round(min(sz, T.floored(sz / 2, T.LOGO_FONT)) * logo_cap_em, 6))
    check(f"{name}: version baseline one cap below",
          round(base - base2, 6), round(cap, 6))
    # ink spans from `base` up to -margin, so the depth it uses is -base, and
    # it must leave the same margin below.
    check(f"{name}: product ink clears the front strip",
          round(-base + T.LOGO_MARGIN * d.calSliderDistance, 4)
          <= round(d.calSliderDistance, 4), True)
    width = T._width_per_cap(txt, T.LOGO_FONT) * cap
    check(f"{name}: product line stops short of the end chamfer",
          round(x + width, 4) <= round(d.calPusherTotalHeight - pusher.CHAMFER, 4), True)
    check(f"{name}: both lines share a left anchor",
          round(x - T._LSB_C * sz, 4), round(x2 - T._LSB_C * sz2, 4), 1e-4)

    dtxt, dsz, dbx, dy0 = T.detail_placement(p, d)
    dcap = dsz * T._metrics(T.DETAIL_FONT)[0]
    dasc = dcap * (T._metrics(T.DETAIL_FONT)[1] / T._metrics(T.DETAIL_FONT)[0])
    dwidth = T._width_per_cap(dtxt, T.DETAIL_FONT) * dcap
    check(f"{name}: detail baseline is the measured constant",
          round(dbx, 4), round(T.DETAIL_BASELINE_X, 4))
    check(f"{name}: detail ink clears the first step",
          round(dbx + dasc, 4) <= round(d.calHeightIncrement, 4), True)
    check(f"{name}: detail ink fits the depth",
          round(-dy0 + dwidth, 4) <= round(d.calPusherTotalDepth, 4), True)
    check(f"{name}: detail is centred along the depth",
          round(-dy0, 4), round(d.calPusherTotalDepth - dwidth, 4) / 2, 1e-4)

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
tight = []
for k, q in sorted(seen.items()):
    dq = D.derive(q)
    part = pusher.build(q, text=True)
    b = part.bounding_box()
    assert abs(b.size.X - dq.calPusherTotalHeight) < 1e-6
    assert abs(b.size.Y - dq.calPusherTotalDepth) < 1e-6
    assert abs(b.size.Z - L.PUSHER_TOTAL) < 1e-6
    # The text rule has to hold on EVERY pusher, not just the two references —
    # it is a fitting rule, and the catalogue spans a 5x range of both the
    # strip it fits into and the depth it runs along.
    (txt, sz, x, base), (_ver, sz2, x2, _b2) = T.logo_lines(q, dq)
    cap = sz * T._metrics(T.LOGO_FONT)[0]
    assert -base + T.LOGO_MARGIN * dq.calSliderDistance <= dq.calSliderDistance + 1e-9
    assert x + T._width_per_cap(txt, T.LOGO_FONT) * cap \
        <= dq.calPusherTotalHeight - pusher.CHAMFER + 1e-9
    dtxt, dsz, dbx, dy0 = T.detail_placement(q, dq)
    dcap = dsz * T._metrics(T.DETAIL_FONT)[0]
    dasc = dcap * (T._metrics(T.DETAIL_FONT)[1] / T._metrics(T.DETAIL_FONT)[0])
    dwidth = T._width_per_cap(dtxt, T.DETAIL_FONT) * dcap
    assert dbx + dasc <= dq.calHeightIncrement + 1e-9
    assert -dy0 + dwidth <= dq.calPusherTotalDepth + 1e-9
    tight.append((min(cap, dcap), k))
    built += 1
check("pushers built", built, len(seen))
check("every logo and detail line fits its own box", True, True)
tight.sort()
print(f"  ..  smallest cap in the catalogue: {tight[0][0]:.2f} mm on "
      f"{tight[0][1]}; largest {tight[-1][0]:.2f} mm on {tight[-1][1]}")
check("classes cover C1..C5",
      sorted({L.lock_class(D.derive(q).calPusherTotalDepth)[0] for q in seen.values()}),
      ["C1", "C2", "C3", "C4", "C5"])
with tempfile.TemporaryDirectory() as tmp:
    out = Path(tmp) / "pusher_smoke.3mf"
    m = Mesher(); m.add_shape(pusher.build(REFS[0][2]), part_number="Pusher"); m.write(out)
    check("3MF export", out.exists() and out.stat().st_size > 0, True)

print(f"\n{'PASS' if not fails else 'FAIL: ' + ', '.join(fails)}")
sys.exit(1 if fails else 0)
