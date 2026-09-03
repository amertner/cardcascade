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

import math                                             # noqa: E402

from build123d import import_step, Plane, Box, Pos       # noqa: E402
from cad import params, derive as D, text as TX          # noqa: E402
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


def refuses(fn):
    try:
        fn()
    except ValueError:
        return True
    return False


def tri_volume(shape):
    """The TESSELLATED volume. `Solid.volume` drifts by ~1 mm3 on a body
    carrying the lettering's BSpline faces — on the hand-exported STEPs as much
    as on the source — so a comparison of two named toppers has to use this."""
    import numpy as np
    from cad.mesh3mf import triangulate
    v, t = triangulate(shape)
    v, t = np.asarray(v), np.asarray(t)
    a, b, c = v[t[:, 0]], v[t[:, 1]], v[t[:, 2]]
    return float(abs(np.einsum("ij,ij->i", a, np.cross(b, c)).sum()) / 6.0)


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
# All three rollbacks predate `Upside Down`, so they arrive in the pre-flip
# frame. That transform is itself a measurement: a 180-degree turn about X
# through (y = -depth, z = Z_BASE) puts every body on the same envelope exactly.
from build123d import Pos, Rot                            # noqa: E402
Q = params.Primary(4, 5, 15, 15, 0, 15, 1, 0, "Innovation")
dq = D.derive(Q)
dpq = T.depth(Q, dq)


def unflip(solid):
    return Pos(0, -2 * dpq, 2 * T.Z_BASE) * Rot(180, 0, 0) * solid


def load(name):
    return unflip(import_step(str(STEP_DIR / name)).solids()[0])


roll1 = load("Topper M5.15.15.62-Sl to Remove Inner Hole.step")
roll2 = load("Topper M5.15.15.62-Sl after More Dividers.step")
roll3 = load("Topper M5.15.15.62-Sl after Linear pattern 1.step")

rb1 = roll1.bounding_box()
wq = T.wedge(Q, dq)
check("the flip puts the rollback on the wedge's envelope (X)",
      round(rb1.min.X, 6), round(wq.bounding_box().min.X, 6), 1e-6)
check("... (Y)", round(rb1.min.Y, 6), round(wq.bounding_box().min.Y, 6), 1e-6)
check("... (Z)", round(rb1.min.Z, 6), round(wq.bounding_box().min.Z, 6), 1e-6)


def exact(label, mine, ref):
    """Volume AND both one-sided differences. Volume alone is not enough: the
    front-hole fillet moves 5.494 mm3 in each direction and nets to zero."""
    check(f"{label}: volume", round(mine.volume, 4), round(ref.volume, 4), 1e-4)
    check(f"{label}: face count", len(mine.faces()), len(ref.faces()))
    a, b = mine - ref, ref - mine
    check(f"{label}: nothing left over",
          round(a.volume if a else 0.0, 6), 0.0, 1e-6)
    check(f"{label}: nothing missing",
          round(b.volume if b else 0.0, 6), 0.0, 1e-6)


pocketed = wq - T.inner_hole(Q, dq)
exact("Remove Inner Hole", pocketed, roll1)
check("the pocket is inset INNER_END_INSET from each end",
      round(T.inner_hole(Q, dq).bounding_box().min.X - wq.bounding_box().min.X, 4),
      round(T.INNER_END_INSET, 4), 1e-4)
check("... and INNER_INSET * cos(theta) in Y at the rear",
      round(T.inner_hole(Q, dq).bounding_box().min.Y - rb1.min.Y, 4),
      round(T.INNER_INSET * T.slant_cos(Q, dq), 4), 1e-4)

grouped = pocketed - T.front_removal(Q, dq) + T.dividers(Q, dq)
exact("front removal + dividers", grouped, roll2)

print("\n=== `Fillet front holes`, built into the TOOL ===")
# OCCT will not put a 2.000 round on an 0.800 wall; Onshape's "allow edge
# overflow" is the permission to do it anyway, so the tool carries the round.
# The two kinds are equal and opposite, which is why `exact` above has to check
# both one-sided differences and not merely the volume.
check("the reference carries it as 16 cylinders at r2.0",
      sum(1 for f in roll2.faces()
          if "CYLINDER" in str(f.geom_type)
          and abs(f.radius - T.FRONT_FILLET) < 1e-6), 16)
check("... and so does the source", sum(
    1 for f in grouped.faces()
    if "CYLINDER" in str(f.geom_type)
    and abs(f.radius - T.FRONT_FILLET) < 1e-6), 16)
check("each is a quarter cylinder through the front wall",
      round(4 * (1 - math.pi / 4) * T.FRONT_FILLET ** 2 * T.FRONT_WALL / 4, 4),
      0.6867, 1e-4)

print("\n=== the holder tabs and the lip rooms ===")
tabbed = grouped + T.holder_tabs(Q, dq) - T.lip_rooms(Q, dq)
exact("Tab-to-attach .. Linear pattern 1", tabbed, roll3)
check("two tabs, not one per slot", len(T.holder_tabs(Q, dq).solids()), 2)
check("the tabs top out at TOTAL_HEIGHT",
      round(T.holder_tabs(Q, dq).bounding_box().max.Z - T.Z_BASE, 3),
      round(T.TOTAL_HEIGHT, 3), 1e-3)
check("... which is FLOOR + a 44 mm blind extrude",
      round(T.FLOOR + T.TAB_RISE, 3), 45.200, 1e-9)
check("2 lip rooms a slot, HorizontalSlots over",
      len(T.lip_room_x(Q, dq)), 2 * Q.HorizontalSlots)
check("the reference carries 16 cylinders at r1.4",
      sum(1 for f in roll3.faces()
          if "CYLINDER" in str(f.geom_type)
          and abs(f.radius - T.LIP_FILLET) < 1e-6), 16)

print("\n=== the lip room IS the holder's lip base, with no clearance ===")
# the notch on the +x side of the FIRST slot; lip_room_x is sorted, so
# index 0 is that slot's other one, at negative x.
lo, hi = T.lip_room_x(Q, dq)[1]
xs = [x for x, _y in H.lip_plan(Q, dq, first=False)]
check("the notch runs |x| min(lip_plan) .. max(lip_plan)",
      (round(lo, 4), round(hi, 4)), (round(min(xs), 4), round(max(xs), 4)))
check("... which is LIP_LEN + 2 * LIP_CHAMFER wide",
      round(hi - lo, 4), round(H.LIP_LEN + 2 * H.LIP_CHAMFER, 4), 1e-9)
check("... starting LIP_GAP - LIP_CHAMFER past the scallop's filleted edge",
      round(lo, 4),
      round(H.FINGER_R + H.FINGER_FILLET + H.LIP_GAP - H.LIP_CHAMFER, 4), 1e-9)
check("the notch floor is LIP_ROOM_RISE above the topper's floor",
      round(T.LIP_ROOM_RISE, 3), 2.000, 1e-9)

print("\n=== `Top and front edges`, the last feature of the blank ===")
for tag, pp in (("M10-Un", P), ("M15-Sl", Q)):
    dd = D.derive(pp)
    body = T.build(pp, dd)
    cyl = [f for f in body.faces()
           if "CYLINDER" in str(f.geom_type) and abs(f.radius - T.EDGE_ROUND) < 1e-6]
    check(f"{tag}: eight r0.800 cylinders and no more", len(cyl), 8)
    check(f"{tag}: no tori — one chain, not four fillets",
          sum(1 for f in body.faces() if "TORUS" in str(f.geom_type)), 0)
    x0, x1 = T.x_span(pp, dd)
    fr, re_ = T.y_span(pp, dd)
    r = T.EDGE_ROUND
    longest = max(cyl, key=lambda f: f.area)
    check(f"{tag}: the bottom perimeter runs width - 2r",
          round(longest.bounding_box().size.X, 3),
          round(T.width(pp, dd) - 2 * r, 3), 1e-3)
    # the tell: the REAR vertical fillet is trimmed by the SLANT, not by the
    # rear's own top, so its cylinder reaches slant_z at rear + r.
    rear_v = [f for f in cyl if abs(f.bounding_box().min.Y - re_) < 1e-6
              and f.bounding_box().size.Z > 1.0]
    check(f"{tag}: two rear vertical fillets", len(rear_v), 2)
    check(f"{tag}: ... trimmed by the slant at rear + r",
          round(rear_v[0].bounding_box().max.Z, 3),
          round(T.slant_z(pp, dd, re_ + r), 3), 1e-3)

print("\n=== build(): the whole blank ===")
mine = T.build(P, d)
exact("unfilleted M10-Un, before the last fillet",
      T.wedge(P, d) - T.inner_hole(P, d) - T.front_removal(P, d)
      + T.dividers(P, d) + T.holder_tabs(P, d) - T.lip_rooms(P, d), ref)
# The strongest check available: the FILLETED Unseen export at this exact
# parameter set. Its lettering is a removal, so it may hold LESS than the blank
# — but it must hold nothing the blank does not.
unseen = max(import_step(str(STEP_DIR / "Topper Unseen M5.10.10.32-Un.step")).solids(),
             key=lambda s: s.volume)
left = unseen - mine
check("the filleted Unseen body has nothing the blank lacks",
      round(left.volume if left else 0.0, 6), 0.0, 1e-6)
over = mine - unseen
check("... and what the blank has spare is only the engraving",
      round(over.volume if over else 0.0, 3), 19.300, 0.01)
check("the blank is a single solid", len(mine.solids()), 1)

print("\n=== `Expansion Name`: where the mark and the name go ===")
# Every filleted STEP: all five expansions at M15-Sl, plus two more Unseens at
# other parameter sets so no rule below rests on one configuration. A STEP's
# engraving differences out of the blank exactly, so all of this is measured.
M15SL = params.Primary(4, 5, 15, 15, 0, 15, 1, 0, "Innovation")
NAMED = [
    ("Unseen M10-Un", "Topper Unseen M5.10.10.32-Un.step",
     params.Primary(4, 5, 15, 10, 0, 10, 0, 0, "Innovation"), "Unseen"),
    ("Unseen M15-Un", "Topper Unseen M5.15.15.45-Un.step",
     params.Primary(4, 5, 15, 15, 0, 15, 0, 0, "Innovation"), "Unseen"),
    ("Artifacts M15-Sl", "Topper Artifacts M5.15.15.62-Sl.step", M15SL, "Artifacts"),
    ("Cities M15-Sl", "Topper Cities M5.15.15.62-Sl.step", M15SL, "Cities"),
    ("Echoes M15-Sl", "Topper Echoes M5.15.15.62-Sl.step", M15SL, "Echoes"),
    ("Figures M15-Sl", "Topper Figures M5.15.15.62-Sl.step", M15SL, "Figures"),
    ("Unseen M15-Sl", "Topper Unseen M5.15.15.62-Sl.step", M15SL, "Unseen"),
]


def split(sols, pp, dd):
    """(mark solids, letter solids) of a filleted STEP's inlays.

    Split on the PEN, not on a letter count: `Artifacts` and `Figures` carry a
    dotted `i` whose tittle is its own solid, so counting glyphs undercounts.
    """
    body = max(sols, key=lambda q: q.volume)
    ins = sorted((q for q in sols if q is not body),
                 key=lambda q: q.bounding_box().min.X)
    pen = T.text_origin_x(pp, dd)
    return ([q for q in ins if q.bounding_box().max.X < pen],
            [q for q in ins if q.bounding_box().max.X >= pen])


for tag, fn, pp, word in NAMED:
    dd = D.derive(pp)
    sols = import_step(str(STEP_DIR / fn)).solids()
    m_sol, t_sol = split(sols, pp, dd)
    ins = m_sol + t_sol
    boxes = [q.bounding_box() for q in ins]
    mark = [q.bounding_box() for q in m_sol]
    text = [q.bounding_box() for q in t_sol]

    # Two different things, and they differ by 0.010: the POCKET runs from the
    # underside up by ENGRAVE, and the STEP's separate inlay solids are the
    # same height but sit 0.010 lower, so they stand proud of the face and
    # leave 0.010 clear at the pocket's top — as the Lid's logo inlays do.
    pocket = T.build(pp, dd) - max(sols, key=lambda q: q.volume)
    pz = pocket.bounding_box()
    check(f"{tag}: the pocket starts at the underside",
          round(pz.min.Z, 3), round(T.Z_BASE, 3), 1e-3)
    check(f"{tag}: ... and is ENGRAVE deep",
          round(pz.size.Z, 3), round(T.ENGRAVE, 3), 1e-3)
    check(f"{tag}: the inlays are ENGRAVE tall too",
          round(max(b.max.Z for b in boxes) - min(b.min.Z for b in boxes), 3),
          round(T.ENGRAVE, 3), 1e-3)
    check(f"{tag}: ... and stand 0.010 proud of the face",
          round(T.Z_BASE - min(b.min.Z for b in boxes), 3), 0.010, 1e-3)
    # the mark's box: its width and its TOP edge, which every expansion fills
    mx0, my0, mx1, my1 = T.mark_box(pp, dd)
    check(f"{tag}: the mark box is calLogoSidelength wide",
          round(mx1 - mx0, 4), round(dd.calLogoSidelength, 4), 1e-9)
    # The BOX is the mark's own element — Unseen's shield, Cities' star — and
    # the largest solid is that element on both. Unseen's five rays are drawn
    # OUTSIDE it, and symmetrically: the group is 1.2644 * L wide and shares
    # the box's centre, which is the 1.2644 spec/TOPPER.md records.
    big = max(m_sol, key=lambda q: q.volume).bounding_box()
    # unrounded: mark_box lands on exact halves of a thousandth here, and
    # rounding the two sides separately splits them by a whole 0.001.
    check(f"{tag}: the mark's left edge is L/2 + MARK_GAP past the flat face",
          big.min.X, mx0, 1e-4)
    check(f"{tag}: ... and its right edge closes the box", big.max.X, mx1, 1e-4)
    check(f"{tag}: ... and sits on its top edge",
          round(big.min.Y, 3), round(my0, 3), 1e-3)
    grp = (min(b.min.X for b in mark), max(b.max.X for b in mark))
    check(f"{tag}: the whole mark group is centred on the box",
          (grp[0] + grp[1]) / 2, (mx0 + mx1) / 2, 1e-4)
    check(f"{tag}: the mark box is centred in the DEPTH",
          round((my0 + my1) / 2, 6),
          round(sum(T.y_span(pp, dd)) / 2, 6), 1e-9)

    # the lettering: baseline, band, and the pen
    base = T.baseline_y(pp, dd)
    # A flat-bottomed letter sits ON the baseline; a round one overshoots it.
    # So the LEAST-descending letter's bottom IS the baseline, exactly — `n`
    # in Unseen, `t` and `i` in Cities.
    a, lsb, lo, _hi = TX.metrics(word, T.FONT)
    size = T.font_size(pp, dd)
    # By LETTER, not by solid: a dotted `i` is two solids and its tittle never
    # comes near the baseline, so a per-solid minimum reads the dot instead.
    glyphs = []
    for b in text:
        if glyphs and b.min.X < glyphs[-1][0] + 0.05:
            glyphs[-1] = (glyphs[-1][0], max(glyphs[-1][1], b.max.Y))
        else:
            glyphs.append((b.max.X, b.max.Y))
    check(f"{tag}: a flat letter sits exactly on 2*LogoEdgeDist in",
          round(min(g[1] for g in glyphs), 3), round(base, 3), 1e-3)
    check(f"{tag}: and the round ones overshoot it by the font's own yMin",
          round(max(b.max.Y for b in text) - base, 4), round(-lo * size, 4),
          0.008 * size)
    check(f"{tag}: the pen starts at 1.5L + 3 past the flat face",
          round(min(b.min.X for b in text) - lsb * size, 3),
          round(T.text_origin_x(pp, dd), 3), 0.01)

    # and the whole word, rendered and placed the way build() will place it
    sk = T.name_sketch(pp, dd, word)
    placed = (Pos(T.text_origin_x(pp, dd), base, 0)
              * sk.mirror(Plane.XZ))
    pb = placed.bounding_box()
    tb = (min(b.min.X for b in text), max(b.max.X for b in text),
          min(b.min.Y for b in text), max(b.max.Y for b in text))
    # A tolerance PROPORTIONAL to the em, not an absolute one: the vendored
    # Noto Serif Bold is not byte-identical to Onshape's — `s` measures
    # 3.6/1000 em wider there — so the word's ink drifts by a fixed fraction of
    # the size. Measured 0.0055 em on all three sizes, which is what says the
    # difference is in the font's metrics and not in the placement. 0.008 em is
    # that with headroom. spec/TOPPER.md, "The vendored Noto Serif Bold".
    ftol = 0.008 * size
    check(f"{tag}: the name's ink left", round(pb.min.X, 3), round(tb[0], 3), ftol)
    check(f"{tag}: the name's ink right", round(pb.max.X, 3), round(tb[1], 3), ftol)
    check(f"{tag}: the name's ink top", round(pb.min.Y, 3), round(tb[2], 3), ftol)
    check(f"{tag}: the name's ink bottom", round(pb.max.Y, 3), round(tb[3], 3), ftol)
    check(f"{tag}: ... and the drift is a constant fraction of the em",
          round(abs(pb.size.X - (tb[1] - tb[0])) / size, 4) <= 0.0060, True)
    check(f"{tag}: ... and it is under 0.3% of the word",
          round(100 * abs(pb.size.X - (tb[1] - tb[0])) / (tb[1] - tb[0]), 3) < 0.3,
          True)

print("\n=== the marks: derived from calLogoSidelength, not traced ===")
for tag, fn, pp, word in NAMED:
    dd = D.derive(pp)
    sols = import_step(str(STEP_DIR / fn)).solids()
    ref, _t = split(sols, pp, dd)
    # The STEP's inlays are ENGRAVE tall and sit 0.010 proud, so area is volume
    # over their own height and not over anything assumed.
    h = (max(q.bounding_box().max.Z for q in ref)
         - min(q.bounding_box().min.Z for q in ref))
    area = sum(q.volume for q in ref) / h
    mine = T.MARKS[word](dd.calLogoSidelength)
    check(f"{tag}: the mark's AREA, to five decimals",
          round(mine.area, 5), round(area, 5), 1e-3)
    check(f"{tag}: ... as the same number of pieces", len(mine.faces()), len(ref))
    check(f"{tag}: ... and the same width", round(mine.bounding_box().size.X, 4),
          round(max(q.bounding_box().max.X for q in ref)
                - min(q.bounding_box().min.X for q in ref), 4), 1e-4)
    check(f"{tag}: ... centred on the box",
          round(mine.bounding_box().center().X, 6), 0.0, 1e-6)

print("\n=== and each is a RULE, not an outline ===")
Lq = D.derive(M15SL).calLogoSidelength
check("Echoes is L**2 / 2 exactly",
      round(T.MARKS["Echoes"](Lq).area, 6), round(Lq * Lq / 2, 6), 1e-6)
fig = T.MARKS["Figures"](Lq)
check("Figures is an ANNULUS — one face, two wires",
      (len(fig.faces()), len(fig.faces()[0].wires())), (1, 2))
check("... outer L/2, inner L/2 - L/5",
      round(fig.area, 6),
      round(math.pi * ((Lq / 2) ** 2 - (Lq / 2 - Lq / 5) ** 2), 6), 1e-6)
check("Artifacts' two triangles OVERLAP, so the union is one face",
      len(T.MARKS["Artifacts"](Lq).faces()), 1)
check("Cities is 8 triangles, and they fuse to ONE face",
      len(T.MARKS["Cities"](Lq).faces()), 1)
check("Unseen is a shield and five rays", len(T.MARKS["Unseen"](Lq).faces()), 6)
check("the Unseen shield's upper arc follows from L/2 and L/7, not a radius",
      round(((Lq / 2) ** 2 + (Lq / 7) ** 2) / (2 * Lq / 7), 4), 8.0810, 1e-3)
check("every expansion has a mark", sorted(T.MARKS), sorted(T.EXPANSIONS[1:]))

print("\n=== build(<expansion>): the whole named topper ===")
for tag, fn, pp, word in NAMED:
    dd = D.derive(pp)
    blank_b = T.build(pp, dd)
    named = T.build(pp, dd, word)
    ref = max(import_step(str(STEP_DIR / fn)).solids(), key=lambda s: s.volume)
    # `Solid.volume` is not the metric here: OCCT's GProp over-reports a body
    # with this many small BSpline faces, on the reference as much as on the
    # source. What the engraving actually removes is exact.
    mine_cut = blank_b - named
    ref_cut = blank_b - ref
    check(f"{tag}: the engraving comes out in the same number of pieces",
          len(mine_cut.solids()), len(ref_cut.solids()))
    check(f"{tag}: what it removes, within 0.2%",
          round(100 * abs(mine_cut.volume - ref_cut.volume) / ref_cut.volume, 3) < 0.2,
          True)
    check(f"{tag}: tessellated volume within 0.005% of the reference",
          round(100 * abs(tri_volume(named) - tri_volume(ref))
                / tri_volume(ref), 4) < 0.005, True)
    check(f"{tag}: still one solid", len(named.solids()), 1)

check("build() refuses a name that is not an expansion",
      refuses(lambda: T.build(P, d, "Nonesuch")), True)

print("\n=== `Figures`' descender, which the doubled margin is FOR ===")
# Allan doubled the bottom margin so the font's lower-case `g` does not run off
# the face. It is load-bearing on exactly one of the six, so it is the one that
# has to be checked on every row rather than on the reference at hand — and
# with Onshape's `g`, which descends 0.00459 em DEEPER than the vendored one.
# That figure is measured: `Figures`' ink is 0.455% taller than the vendored
# font predicts, where the other four agree to 0.013%, and the `g` is the only
# glyph they do not share.
_a, _l, g_lo, _hi = TX.metrics("Figures", T.FONT)
ONSHAPE_G = g_lo - 0.00459
worst = None
for row in params.load_rows(ROOT / "automation" / "parts.csv"):
    for sleeved in (0, 1):
        pp = params.from_row(row, sleeved)
        if pp.GameName != "Innovation":
            continue
        dd = D.derive(pp)
        _x, _rear_f, front_f = T.face_datum(pp, dd)
        clear = front_f - (T.baseline_y(pp, dd) - ONSHAPE_G * T.font_size(pp, dd))
        worst = clear if worst is None else min(worst, clear)
check("the g clears the face on every row, Onshape's deeper g included",
      round(worst, 3) > 0.0, True)
check("... with 0.212 to spare at the tightest", round(worst, 3), 0.212, 1e-3)
# and the rule it depends on: the bottom margin is TWICE the top
pp = params.Primary(4, 5, 15, 15, 0, 15, 1, 0, "Innovation")
dd = D.derive(pp)
_x, rear_f, front_f = T.face_datum(pp, dd)
led = T.logo_edge_dist(pp, dd)
check("the bottom margin is 2 * LogoEdgeDist and the top is 1 *",
      round(front_f - T.baseline_y(pp, dd), 4), round(2 * led, 4), 1e-9)
check("... which is what makes the band depth - 2r - 3 * LogoEdgeDist",
      round(T.cap_band(pp, dd), 4),
      round(T.depth(pp, dd) - 2 * T.EDGE_ROUND - 3 * led, 4), 1e-9)

print("\n=== it is Innovation-only ===")
check("build() refuses a non-Innovation game",
      refuses(lambda: T.build(params.Primary(4, 5, 15, 10, 0, 10, 0, 0,
                                             "Dominion"))), True)

print("\nPASS" if not fails else f"\nFAIL ({len(fails)}): " + ", ".join(fails[:6]))
sys.exit(1 if fails else 0)
