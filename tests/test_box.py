#!/usr/bin/env python3
"""Check cad/parts/box.py against the hand-exported Onshape STEPs.

    .venv/bin/python tests/test_box.py

Nine references in `spec/reference/`, listed in `spec/BOX.md` — six of them
distinct boxes, three of those with an unfilleted twin. The Box is being built
group by group against a boolean diff (see that file); this asserts only what
has actually been written, and grows with it.

Proven so far: the envelope (`#BoxWidth` / `#BoxDepth` / `BoxHeight`), the
bottom slot, the rear pusher storage — which is what carries the 7.0 lock into
the box, its rim cutouts sitting at each slot's centreline +- `s` — the lowered
front, the rounded top corners, the sliders, the front pocket, the thumbs and
lip, the closing bumps and both label holders.
"""
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from build123d import import_step, Box, Location   # noqa: E402
from cad import build, params, derive as D, lock as L, text as TX  # noqa: E402
import reference as REF                                        # noqa: E402
from cad.parts import box                         # noqa: E402

STEP_DIR = ROOT / "spec" / "reference"
REFS = [
    ("Compile 105 Sl", "Box Compile 105S.step",
     REF.primary(3, 4, 7, 7, 0, 7, 1, 0, "Compile")),
    ("Dominion 244 Sl", "Box Dominion 244S.step",
     REF.primary(4, 4, 21, 10, 0, 10, 1, 0, "Dominion")),
    ("Dominion 202 Sl (Mat)", "Box Dominion 202S Merged.step",
     REF.primary(4, 4, 21, 10, 0, 10, 1, 1, "Dominion")),
    ("Dominion 650 Sl", "Box Dominion 650S.step",
     REF.primary(5, 8, 50, 10, 0, 10, 1, 0, "Dominion")),
    # Not a parts.csv row — scratch parameters Allan exported as an extra
    # reference. Kept because it is the smallest box and the only C2 lock.
    ("FCM 72 Sl (scratch)", "Box FCM 72S.step",
     REF.primary(3, 3, 6, 6, 0, 6, 1, 0, "FCM")),
    # The only reference with a first-riser override, so the only one that can
    # tell calFirstSliderDistance (20.4) from calSliderDistance (9.6) — the
    # same gap the Dominion 246 STEP closed for the Pusher.
    ("Dominion 246 Sl", "Box Dominion 246S.step",
     REF.primary(3, 2, 40, 12, 1, 30, 1, 0, "Dominion")),
    # The three Allan exported once the first six showed what they could not
    # reach. Every one of the first six is SLEEVED, so half the catalogue had
    # nothing behind it.
    ("Dominion 244 Un", "Box Dominion 244U.step",
     REF.primary(4, 4, 21, 10, 0, 10, 0, 0, "Dominion")),
    # Innovation, XS and unsleeved at once — the only game with no reference,
    # the only size (HorizontalSlots 2) with none, and it is the exception that
    # takes 2 pusher slots where its size would otherwise take 3.
    ("Innovation 130 Un", "Box Innovation 130U.step",
     REF.primary(2, 5, 15, 10, 0, 10, 0, 0, "Innovation")),
    # Nine risers: the RisingSliders > 8 branch of the logo margin, the lowest
    # rise in the catalogue (9.667, clamped) and the pusher rest at its floor.
    ("Dominion 333 Sl", "Box Dominion 333S.step",
     REF.primary(3, 9, 21, 10, 0, 10, 1, 0, "Dominion")),
]
fails = []


def check(label, got, want, tol=1e-6):
    ok = abs(got - want) <= tol if isinstance(want, float) else got == want
    print(f"  {'ok  ' if ok else 'FAIL'} {label:52s} {got!r:>26} vs {want!r}")
    if not ok:
        fails.append(label)


def rim_cutouts(solid, p, d, z=102.0):
    """(centre X, width) of every gap in the box rim, left to right — the
    pusher tab cutouts.

    Probed with a thin bar through the BACK WALL only. A plain section at this
    height also catches the end walls and the label holders, which run the full
    depth, and their edges then read as rim pieces: that is what made the
    leftmost FCM cutout measure 4.15 instead of 4.50.

    The band is the back wall itself, `#BoxDepth/2 - 1.600 .. -0.300` on all
    four references — 1.300 thick, because the 3.200 pusher slot behind it eats
    0.300 of the 1.600 wall. LOCK_STANDARD.md puts the cutouts at z 99.75..105.
    """
    y = box.box_depth(d) / 2 - 0.95           # mid-wall
    bar = Box(box.box_width(d) + 20, 0.4, 1.0).moved(Location((0, y, z)))
    pieces = sorted((s.bounding_box().min.X, s.bounding_box().max.X)
                    for s in (solid & bar).solids())
    return [((a[1] + b[0]) / 2, round(b[0] - a[1], 3))
            for a, b in zip(pieces, pieces[1:])]


for name, fn, p in REFS:
    path = STEP_DIR / fn
    print(f"\n=== {name} ===")
    if not path.exists():
        # A missing reference is a FAILURE, not a skip: every STEP in
        # spec/reference is checked in, and a suite that turns green
        # when one goes missing is not a suite.
        print(f"  FAIL — reference {path.name} not present")
        fails.append(f"{name}: reference {path.name} missing")
        continue
    ref = import_step(str(path)).solids()[0]
    d = D.derive(p)
    rb = ref.bounding_box()

    # --- the envelope ------------------------------------------------------
    # The measured box stands proud of the sketch by 2.600 in width and 6.100
    # in depth — label holders, closing bumps and the rear storage.
    check("width  = #BoxWidth + 2.600", round(rb.size.X, 3),
          round(box.box_width(d) + 2.600, 3), 1e-3)
    check("depth  = #BoxDepth + 6.100", round(rb.size.Y, 3),
          round(box.box_depth(d) + 6.100, 3), 1e-3)
    check("height = BoxHeight", round(rb.size.Z, 3), round(d.BoxHeight, 3), 1e-3)
    # The sketch box is centred on the origin: its outer walls are the two
    # largest X-normal planar faces, and they sit at exactly +-#BoxWidth/2.
    walls = {}
    for f in ref.faces():
        try:
            n = f.normal_at(f.center())
        except Exception:
            continue
        if abs(n.X) > 0.999:
            walls[round(f.center().X, 3)] = walls.get(round(f.center().X, 3), 0) + f.area
    left = min(walls, key=lambda k: (k > 0, -walls[k] if k < 0 else 0))
    biggest = sorted(walls, key=lambda k: -walls[k])[:2]
    check("outer walls at +-#BoxWidth/2", sorted(round(x, 3) for x in biggest),
          sorted([round(-box.box_width(d) / 2, 3),
                  round(box.box_width(d) / 2, 3)]))

    # --- the rear pusher storage, and the lock it carries ------------------
    cuts = rim_cutouts(ref, p, d)
    n = box.pusher_slot_count(d)
    check("rim cutouts = 2 per pusher slot", len(cuts), 2 * n)
    if len(cuts) != 2 * n:
        continue
    cls, sv = L.lock_class(d.calPusherTotalDepth)
    check("every cutout is BOX_CUTOUT_W wide",
          sorted({round(w, 2) for _c, w in cuts}), [round(L.BOX_CUTOUT_W, 2)])
    for k in range(n):
        lo, hi = cuts[2 * k][0], cuts[2 * k + 1][0]
        check(f"slot {k}: cutout pair is 2s apart ({cls})",
              round(hi - lo, 2), round(2 * sv, 2), 0.05)
    got = [round((cuts[2 * k][0] + cuts[2 * k + 1][0]) / 2, 2) for k in range(n)]
    want = [round(x, 2) for x in box.pusher_slots(d)]
    check("slot centrelines", got, want)
    check("pitch is #dBackSlotWidth = calPusherTotalDepth + 4.000",
          round(got[1] - got[0], 2) if n > 1 else None,
          round(d.calPusherTotalDepth + 4.0, 2) if n > 1 else None, 0.05)

    # --- the bottom slot ---------------------------------------------------
    # Subtract the STEP from the floor slab the shell starts with. What is left
    # is the bottom slot plus the engraved text (glyph slivers, all under
    # 11 mm3 even on the biggest box), so take the one real lump.
    slab = Box(box.box_width(d) - 2 * box.WALL,
               box.box_depth(d) - 2 * box.WALL,
               box.WALL).moved(Location((0, 0, box.WALL / 2)))
    lumps = [q for q in (slab - ref).solids() if q.volume > 100]
    check("the floor has exactly one hole", len(lumps), 1)
    if len(lumps) == 1:
        hb = lumps[0].bounding_box()
        want_w, want_d, want_y = box.bottom_slot(d)
        check("bottom slot width", round(hb.size.X, 3), round(want_w, 3), 1e-3)
        check("bottom slot depth", round(hb.size.Y, 3), round(want_d, 3), 1e-3)
        check("bottom slot centre Y", round(hb.center().Y, 3), round(want_y, 3), 1e-3)
        check("bottom slot goes clean through the floor",
              round(hb.size.Z, 3), round(box.WALL, 3), 1e-3)
        # A plain prism: the removed volume IS its bounding box, so there is no
        # chamfer, draft or second pocket hiding inside it.
        check("bottom slot is a plain rectangular prism",
              round(lumps[0].volume, 3),
              round(hb.size.X * hb.size.Y * hb.size.Z, 3), 1e-3)

    # --- the rear storage ---------------------------------------------------
    BD = box.box_depth(d)
    box_w = box.box_width(d)
    inner = box_w / 2 - box.WALL
    mine = box.build(D.derive(p))  # built once; every "build:" check reuses it

    def zprofile(x, y, shape=None):
        col = Box(0.4, 0.4, d.BoxHeight + 2).moved(
            Location((x, y, d.BoxHeight / 2)))
        return sorted((round(q.bounding_box().min.Z, 3),
                       round(q.bounding_box().max.Z, 3))
                      for q in ((ref if shape is None else shape) & col).solids())

    y0, y1 = box.slot_band(d)
    check("slot band starts SLOT_BITE inside the sketch box",
          round(y0, 3), round(BD / 2 - box.SLOT_BITE, 3), 1e-3)
    check("slot band is LOCK_STANDARD's box slot depth",
          round(y1 - y0, 3), round(L.BOX_SLOT_DEPTH, 3), 1e-3)
    # The outer back wall is capped at REAR_TOP; only the end walls carry on.
    check("outer back wall is capped at REAR_TOP",
          zprofile(0.0, BD / 2 + box.REAR_DEPTH - box.WALL / 2),
          [(0.0, box.REAR_TOP)])
    # A pusher rests part way up, not on the floor. Probe the strip of
    # cavity floor BEFORE the first hanging hole — HOLE_INSET wide, so always
    # inside the first cavity and never pierced. Through a hole instead, the
    # profile reads (0, 3.000) because the first hole ROW starts at 3.000, which
    # is the reading that put a 3.000 rest in this file for two stages; on the
    # slot centreline it can land on a divider and read (0, 85.000).
    x_pier = -box_w / 2 + box.WALL + box.HOLE_INSET / 2
    rest = box.pusher_rest(d)
    for who, shape in (("STEP", ref), ("build", mine)):
        check(f"{who}: the pusher rest is min(25, BoxHeight - ptH - 0.5) high",
              zprofile(x_pier, y0 + 1.6, shape)[0], (0.0, round(rest, 3)))
    # The hanging holes, read off the back wall as gaps along X.
    bar = Box(box.box_width(d) + 20, 0.4, 0.4).moved(
        Location((0, BD / 2 - 0.95, box.hole_rows()[0][0] + 3.0)))
    pieces = sorted((q.bounding_box().min.X, q.bounding_box().max.X)
                    for q in (ref & bar).solids())
    gaps = [(round(a[1], 3), round(b[0], 3)) for a, b in zip(pieces, pieces[1:])]
    want = [(round(a, 3), round(b, 3)) for a, b in box.hanging_holes(d)]
    check("hanging hole count", len(gaps), len(want))
    check("hanging hole positions", gaps, want)
    check("every hanging hole is HOLE_W wide",
          sorted({round(b - a, 3) for a, b in gaps}), [round(box.HOLE_W, 3)])
    # The build cuts `hole_openings`, which is `hanging_holes` unless an edge
    # lands on a divider face (HOLE_CLEAR). None of the nine references is one
    # of the three boxes where it does, so here the two must be the same and
    # the build's own back wall must read exactly as the STEP's.
    check("no reference hole is clipped by a divider face",
          box.hole_openings(d) == box.hanging_holes(d), True)
    mpieces = sorted((q.bounding_box().min.X, q.bounding_box().max.X)
                     for q in (mine & bar).solids())
    mgaps = [(round(a[1], 3), round(b[0], 3))
             for a, b in zip(mpieces, mpieces[1:])]
    check("build: hanging hole positions", mgaps, want)

    # `Divider` — WHOLE, and that is a deliberate divergence. Onshape runs the
    # hanging holes straight through the dividers; `cad/` stops them at the
    # slot band. So this is the one place the build is knowingly not the STEP,
    # and the check asserts both halves of that — every divider solid on the
    # build, and at least one pierced on the STEP, so a future change that
    # quietly re-converged would still fail here.
    whole = box.DIVIDER_W * L.BOX_SLOT_DEPTH * box.REAR_TOP
    pierced = 0
    for a, e in box.storage_dividers(d):
        cell = Box(e - a, y1 - y0, box.REAR_TOP).moved(
            Location(((a + e) / 2, (y0 + y1) / 2, box.REAR_TOP / 2)))
        check(f"build: the divider at x={a:.1f} is whole",
              round((mine & cell).volume, 3), round(whole, 3), 1e-3)
        if (ref & cell).volume < whole - 1e-3:
            pierced += 1
    check("the STEP pierces dividers, which is what this diverges from",
          pierced > 0, True)

    # --- `Lower the front`, and the rim cutouts, on the BUILD as well --------
    for who, shape in (("STEP", ref), ("build", mine)):
        check(f"{who}: front wall stops at FRONT_TOP",
              zprofile(0.0, -BD / 2 + box.WALL / 2, shape),
              [(0.0, box.FRONT_TOP)])
        bar = Box(box.box_width(d) + 20, 0.4, 0.4).moved(
            Location((0, -BD / 2 + box.WALL / 2, box.FRONT_TOP + 1.0)))
        ends = sorted((round(q.bounding_box().min.X, 3),
                       round(q.bounding_box().max.X, 3))
                      for q in (shape & bar).solids())
        check(f"{who}: above it only the end walls remain", ends,
              [(round(-box.box_width(d) / 2, 3), round(-inner, 3)),
               (round(inner, 3), round(box.box_width(d) / 2, 3))])
    # --- `Round top box corners` and `Sliders` ------------------------------
    # Both probes take everything ABOVE a plane, so the lump's section is read
    # at exactly that height with no slab thickness to correct for.
    def arc_inset(u, r):
        """How far a radius-`r` round has eaten in, `u` below the top."""
        return r - math.sqrt(max(0.0, 2 * r * u - u * u))

    for who, shape in (("STEP", ref), ("build", mine)):
        # The ribs. The bar runs along Y from the back of the front pocket's
        # divider to just short of the inner back wall, so neither the front
        # pocket's side padding (not built yet) nor the back panel is in it.
        y_lo = -BD / 2 + box.WALL + d.calFrontPocketDepth + box.FRONT_DIVIDER + 0.05
        y_hi = BD / 2 - box.WALL - 0.05
        # 8.000 wide so it cannot clip a rib, and starting 0.05 clear of the
        # inner wall so the ribs stay separate lumps instead of fusing into one
        # slice of wall.
        bar = Box(7.95, y_hi - y_lo, 0.4).moved(
            Location((-inner + 4.025, (y_lo + y_hi) / 2, 50.0)))
        lumps = sorted((q.bounding_box() for q in (shape & bar).solids()),
                       key=lambda b: b.min.Y)
        check(f"{who}: slider ribs",
              [(round(b.min.Y, 3), round(b.max.Y, 3)) for b in lumps],
              sorted((round(a, 3), round(c, 3)) for a, c in box.slider_ribs(d)))
        check(f"{who}: every rib stands SLIDER_PROUD proud",
              sorted({round(b.max.X + inner, 3) for b in lumps}),
              [round(box.SLIDER_PROUD, 3)])
        # `Round top of slider`: 0.400 below the rim a rib has lost this much
        # off each side. Read on the backmost rib, which no other feature is
        # near on any reference.
        rib_y0, rib_y1 = box.slider_ribs(d)[0]
        cap = Box(3.0, 20.0, 1.4).moved(
            Location((-inner + 1.5, (rib_y0 + rib_y1) / 2,
                      d.BoxHeight - 0.4 + 0.7)))
        b = [q.bounding_box() for q in (shape & cap).solids()
             if abs(q.bounding_box().center().Y
                    - (rib_y0 + rib_y1) / 2) < 2][0]
        check(f"{who}: rib is rounded SLIDER_TOP_R across its top",
              round(b.size.Y, 3),
              round(box.SLIDER_W - 2 * arc_inset(0.4, box.SLIDER_TOP_R), 3), 2e-3)
        # `Round top box corners`: 2.000 below the rim the end wall has lost
        # this much off its front and its back. Probed inside the end wall, so
        # neither the ribs nor the side label holder is in the way.
        u = 2.0
        cap = Box(box.WALL * 0.5, BD + 40, u + 2.0).moved(
            Location((-box.box_width(d) / 2 + box.WALL / 2, 0,
                      d.BoxHeight - u + (u + 2.0) / 2)))
        b = [q.bounding_box() for q in (shape & cap).solids()][0]
        eaten = round(arc_inset(u, box.CORNER_R), 3)
        check(f"{who}: end wall, CORNER_R round at the top front",
              round(b.min.Y + BD / 2, 3), eaten, 2e-3)
        check(f"{who}: end wall, CORNER_R round at the top back",
              round(BD / 2 + box.REAR_DEPTH - b.max.Y, 3), eaten, 2e-3)
    # --- `Front pocket` -----------------------------------------------------
    fw, fb, pback = box.pocket_span(d)
    for who, shape in (("STEP", ref), ("build", mine)):
        # A section through the middle of the pocket: the two pads, then one
        # segment per divider. MatPocket shows up here as a missing divider.
        bar = Box(box_w + 20, 0.2, 0.05).moved(Location((0, (fw + fb) / 2, 30.0)))
        segs = sorted((round(q.bounding_box().min.X, 3),
                       round(q.bounding_box().max.X, 3))
                      for q in (shape & bar).solids())
        want = ([(round(-box_w / 2, 3), round(-inner + box.FRONT_PAD, 3))]
                + [(round(x - box.FRONT_DIVIDER_W, 3), round(x, 3))
                   for x in box.front_dividers(d)]
                + [(round(inner - box.FRONT_PAD, 3), round(box_w / 2, 3))])
        check(f"{who}: pocket section is 2 pads + {len(box.front_dividers(d))} dividers",
              segs, want)
        # `Angled cutout`: the front face of the pad, read as the frontmost
        # material above a plane. The x window keeps the end walls out of it.
        def pad_front(z):
            cap = Box(2.0, BD + 40, d.BoxHeight + 20 - z).moved(
                Location((-inner + 2.9, 0, (z + d.BoxHeight + 20) / 2)))
            return round(min(q.bounding_box().min.Y
                             for q in (shape & cap).solids()), 3)
        for z in (box.FRONT_TOP, 76.0, 84.0):
            frac = (z - box.FRONT_TOP) / (box.POCKET_CUT_TOP - box.FRONT_TOP)
            check(f"{who}: angled cutout at z={z}",
                  pad_front(z), round(fw + frac * (pback - fw), 3), 2e-3)
        # The divider panel, read where the lattice leaves a pier.
        holes = box.hanging_holes(d)
        pier = (holes[0][1] + holes[1][0]) / 2
        col = Box(0.15, BD + 40, 0.15).moved(Location((pier, 0, 40.0)))
        ys = sorted((round(q.bounding_box().min.Y, 3),
                     round(q.bounding_box().max.Y, 3))
                    for q in (shape & col).solids())
        check(f"{who}: the divider panel is FRONT_DIVIDER thick",
              [y for y in ys if abs(y[0] - fb) < 1e-6],
              [(round(fb, 3), round(pback, 3))])
        # `Thumb` — one finger hole per horizontal slot, through the panel.
        # Read as gaps in a section of everything above z=80: a column between
        # two holes is widest where the holes are narrowest, so the reading is
        # the section at exactly z=80 and nowhere else.
        def thumbs(y_at, z_at=80.0):
            cap = Box(box_w + 20, 0.02, 300).moved(
                Location((0, y_at - 0.01, z_at + 150)))
            pcs = sorted((q.bounding_box().min.X, q.bounding_box().max.X)
                         for q in (shape & cap).solids())
            return [((a[1] + b[0]) / 2, b[0] - a[1])
                    for a, b in zip(pcs, pcs[1:])]

        got = thumbs(fb + 0.5)
        check(f"{who}: one thumb per horizontal slot", len(got), p.HorizontalSlots)
        check(f"{who}: thumb centres",
              [round(c, 3) for c, _w in got],
              [round(x, 3) for x in box.thumb_centres(d)])
        # A cylinder of THUMB_R about z = THUMB_Z: the implied radius from the
        # chord at z=80 is the radius itself, so it reads straight off.
        check(f"{who}: thumb is THUMB_R at THUMB_Z",
              sorted({round(math.sqrt((w / 2) ** 2 + (box.THUMB_Z - 80.0) ** 2), 3)
                      for _c, w in got}), [round(box.THUMB_R, 3)])
        # `Fillet thumb hole`, THUMB_FILLET into both faces. Probed at one
        # depth inside the arc and one past its tangency.
        for depth in (0.12, 0.42):
            f = box.THUMB_FILLET
            grew = f - math.sqrt(max(0.0, 2 * f * depth - depth * depth)) if depth < f else 0.0
            check(f"{who}: thumb fillet {depth} below the panel face",
                  sorted({round(math.sqrt((w / 2) ** 2 + (box.THUMB_Z - 80.0) ** 2), 3)
                          for _c, w in thumbs(fb + depth)}),
                  [round(box.THUMB_R + grew, 3)], 2e-3)
        # `Lip` — two per thumb. Read off its lower ramp face, the one face
        # that carries the angle, the anchor, the depth and the length at once.
        c0 = box.thumb_centres(d)[0]
        ramp = []
        for face in shape.faces():
            fc = face.center()
            if not (c0 - 27 < fc.X < c0 - 13.5 and pback - 0.6 < fc.Y < pback + 4
                    and 84.5 < fc.Z < 90.5) or face.area < 15:
                continue
            try:
                n = face.normal_at(fc)
            except Exception:
                continue
            if abs(n.Y) < 0.4 or n.Z >= 0:
                continue
            ramp.append((face, n))
        check(f"{who}: the left lip has one ramp face", len(ramp), 1)
        if ramp:
            face, n = ramp[0]
            bb = face.bounding_box()
            check(f"{who}: lip angle is the holder's diagonal cutout",
                  round(abs(n.Z / n.Y), 5), round(box.lip_slope(d), 5), 1e-4)
            check(f"{who}: lip leaves the panel at LIP_Z",
                  round(bb.min.Z, 3), round(box.LIP_Z, 3), 1e-3)
            check(f"{who}: lip runs LIP_DEPTH",
                  round((bb.size.Y ** 2 + bb.size.Z ** 2) ** 0.5, 3),
                  round(box.LIP_DEPTH, 3), 2e-3)
            check(f"{who}: lip base is LipLength + 2*LipChamfer",
                  round(bb.size.X, 3),
                  round(box.LIP_LENGTH + 2 * box.LIP_CHAMFER, 3), 1e-3)
            check(f"{who}: lip centre is LIP_OFFSET from the thumb",
                  round(c0 - bb.center().X, 3), round(box.LIP_OFFSET, 3), 1e-3)
        # ... and carries the back wall's lattice exactly.
        bar = Box(box_w + 20, 0.2, 0.05).moved(
            Location((0, (fb + pback) / 2, box.hole_rows()[0][0] + 3.0)))
        pieces = sorted((q.bounding_box().min.X, q.bounding_box().max.X)
                        for q in (shape & bar).solids())
        check(f"{who}: the panel's slits are the back's hanging holes",
              [(round(a[1], 3), round(b[0], 3))
               for a, b in zip(pieces, pieces[1:])],
              [(round(a, 3), round(b, 3)) for a, b in holes])
    # The rim cutouts, built and measured the same way.
    got = rim_cutouts(mine, p, d)
    check("the BUILD's rim cutouts match the STEP's",
          [(round(c, 2), round(w, 2)) for c, w in got],
          [(round(c, 2), round(w, 2)) for c, w in cuts])
    # Through a rim cutout the back wall stops at RIM_CUTOUT_Z instead of
    # reaching the rim. Assert only the TOP: whether the profile below it is one
    # interval or several depends on whether the cutout centre happens to land
    # on a hanging hole or a pier, which varies by box.
    for who, shape in (("STEP", ref), ("build", mine)):
        check(f"{who}: the back wall stops at RIM_CUTOUT_Z in a cutout",
              zprofile(got[0][0], BD / 2 - 0.95, shape)[-1][1],
              box.RIM_CUTOUT_Z, 1e-3)
        check(f"{who}: and reaches the rim beside one",
              zprofile(got[0][0] + L.BOX_CUTOUT_W, BD / 2 - 0.95, shape)[-1][1],
              round(d.BoxHeight, 3), 1e-3)

    # `Thumb Cutout in back` and `Closing mechanism`, on both shapes.
    slot_lo, slot_hi = box.slot_band(d)      # y0/y1 are a rib's by now
    for who, shape in (("STEP", ref), ("build", mine)):
        # The rear thumb, read as the gap in the OUTER back wall at z = 80.
        for depth, radius in ((0.02, box.REAR_THUMB_FILLET
                               - math.sqrt(2 * box.REAR_THUMB_FILLET * 0.02 - 0.0004)),
                              (0.80, 0.0)):
            bar = Box(box_w + 20, 0.02, 0.05).moved(
                Location((0, slot_hi + depth - 0.01, 80.0)))
            pcs = sorted((q.bounding_box().min.X, q.bounding_box().max.X)
                         for q in (shape & bar).solids())
            gaps = [((a[1] + b[0]) / 2, b[0] - a[1])
                    for a, b in zip(pcs, pcs[1:])]
            check(f"{who}: one rear thumb, {depth} into the outer back wall",
                  len(gaps), 1)
            if gaps:
                c, w = gaps[0]
                check(f"{who}: rear thumb centre at {depth}",
                      round(c, 3), round(box.rear_thumb_x(d), 3), 1e-3)
                # The chord at z=80 gives the radius back directly, since the
                # hole is centred on REAR_TOP.
                check(f"{who}: rear thumb radius at {depth}",
                      round(math.sqrt((w / 2) ** 2 + (box.REAR_TOP - 80.0) ** 2), 2),
                      round(d.ThumbCutoutRadius if hasattr(d, "ThumbCutoutRadius")
                            else 12.0, 2) + round(radius, 2), 0.02)
        # ... and it leaves the 1.300 inner back wall alone, which is what says
        # it cuts the outer wall only.
        bar = Box(box_w + 20, 0.2, 0.05).moved(Location((0, BD / 2 - 0.95, 80.0)))
        check(f"{who}: the rear thumb does not touch the inner back wall",
              len((shape & bar).solids()), 1)
        # The closing bumps, one per end wall.
        for sign, lbl in ((-1, "-X"), (1, "+X")):
            # Entirely clear of the wall: include any of it and the biggest
            # solid is a slice of wall running the full depth and height.
            # Starts 0.050 clear of the wall — include any of it and the
            # biggest solid is a slice of wall running the full depth and
            # height — and reaches past the pad so it clips nothing.
            wide = box.BUMP_DEPTH + 0.5
            cell = Box(wide, BD + 30, 30).moved(
                Location((sign * (box_w / 2 + 0.05 + wide / 2), 0,
                          (box.BUMP_Z0 + box.BUMP_Z1) / 2)))
            pad = sorted((shape & cell).solids(), key=lambda q: -q.volume)[0]
            bb = pad.bounding_box()
            check(f"{who}: {lbl} closing bump stands BUMP_DEPTH proud",
                  round(bb.max.X if sign > 0 else -bb.min.X, 3),
                  round(box_w / 2 + box.BUMP_DEPTH, 3), 1e-3)
            check(f"{who}: {lbl} closing bump Y",
                  (round(bb.min.Y, 3), round(bb.max.Y, 3)),
                  (round(box.BUMP_Y0, 3), round(box.BUMP_Y1, 3)))
            check(f"{who}: {lbl} closing bump Z",
                  (round(bb.min.Z, 3), round(bb.max.Z, 3)),
                  (round(box.BUMP_Z0, 3), round(box.BUMP_Z1, 3)))

    # `Front Label Holder` and `Side Label Holder`.
    check("build: envelope matches the STEP's now the holders are on",
          (round(mine.bounding_box().size.X, 3),
           round(mine.bounding_box().size.Y, 3)),
          (round(rb.size.X, 3), round(rb.size.Y, 3)))
    for who, shape in (("STEP", ref), ("build", mine)):
        # Each holder's outer face carries its length, its height and — through
        # its area — the opening cut out of it, all in one measurement.
        front = [f for f in shape.faces()
                 if abs(f.center().Y + BD / 2 + box.LABEL_PROUD) < 1e-6
                 and f.area > 50]
        side = [f for f in shape.faces()
                if abs(f.center().X + box_w / 2 + box.LABEL_PROUD) < 1e-6
                and f.area > 50]
        check(f"{who}: one front and one side label holder",
              (len(front), len(side)), (1, 1))
        if front and side:
            fb, sb = front[0].bounding_box(), side[0].bounding_box()
            check(f"{who}: front holder is its label less two chamfers",
                  round(fb.size.X, 3),
                  round(box.front_label_len(d) - 2 * box.LABEL_CHAMFER, 3), 1e-3)
            check(f"{who}: side holder is calSideLabelWidth + 0.600",
                  round(sb.size.Y, 3), round(d.calSideLabelWidth + 0.6, 3), 1e-3)
            check(f"{who}: side holder is centred on SIDE_LABEL_Y",
                  round(sb.center().Y, 3), round(box.SIDE_LABEL_Y, 3), 1e-3)
            for lbl, bb in (("front", fb), ("side", sb)):
                check(f"{who}: {lbl} holder z",
                      (round(bb.min.Z, 3), round(bb.max.Z, 3)),
                      (round(box.LABEL_Z0 + box.LABEL_CHAMFER, 3),
                       round(box.LABEL_Z1, 3)))
        # The fastener: the lens of two FASTENER_R cylinders, clipped by the
        # stadium that rounds its ends. Both expectations come from those
        # constants, not from a measured literal — the probe cell is CENTRED on
        # its point, so the reading is at the edge nearest the ridge's middle,
        # and a literal silently bakes that offset in.
        # ... at the thirds of the WIDE holder. The narrow one is checked
        # separately below, because there the build and the STEP differ.
        R, cx = box.FASTENER_R, box.fastener_centres(d)[-1]
        if len(box.fastener_centres(d)) < 2:
            continue
        thin = 0.02
        for z in (64.6, 65.0):
            col = Box(0.1, 4.0, thin).moved(
                Location((cx, -BD / 2 - 1.0, z + thin / 2)))
            near = min(z + thin, box.LABEL_Z1 + box.FASTENER_TALL / 2)
            want = (R ** 2 - (box.LABEL_Z1 + box.FASTENER_TALL - near) ** 2) ** 0.5
            check(f"{who}: fastener proud at z={z}",
                  [round(-BD / 2 - q.bounding_box().min.Y, 3)
                   for q in (shape & col).solids()], [round(want, 3)])
        off = 4.667                      # into the rounded end
        col = Box(thin, 4.0, 0.1).moved(Location((cx - off, -BD / 2 - 1.0, 65.0)))
        past = (off - thin / 2) - (box.FASTENER_LEN / 2 - R)
        check(f"{who}: fastener taper at its rounded end",
              [round(-BD / 2 - q.bounding_box().min.Y, 3)
               for q in (shape & col).solids()],
              [round((R ** 2 - past ** 2) ** 0.5, 3)])

    # --- `Model name` and the `Logo` group ---------------------------------
    y_front, y_back = box.card_area(d)
    span = y_back - y_front
    sf_edge = box_w / 2 - box.WALL - box.side_floor(d)

    def engraved(shape, sign):
        """Every glyph cut into one side floor, as bounding boxes."""
        lo, hi = sorted((sign * (box_w / 2 - box.WALL), sign * sf_edge))
        slab = Box(hi - lo, BD - 2 * box.WALL, box.ENGRAVE).moved(
            Location(((lo + hi) / 2, 0, box.WALL - box.ENGRAVE / 2)))
        return [q.bounding_box() for q in (slab - shape).solids()]

    # Where the engraving sits, compared LIKE FOR LIKE. Reconstructing each
    # line from the glyph boxes and holding it to the sketch rules is doable
    # but brittle — a line is identified by its baseline, and which glyph
    # reaches furthest depends on whether the string has an ascender, which
    # varies by box. The band each side floor's engraving occupies says the
    # same thing and cannot be fooled by a stray dot.
    band = {}
    for who, shape in (("STEP", ref), ("build", mine)):
        for sign, lbl in ((-1, "-X"), (1, "+X")):
            gs = engraved(shape, sign)
            check(f"{who}: {lbl} side floor is engraved", len(gs) > 10, True)
            if not gs:
                continue
            check(f"{who}: {lbl} engraving is ENGRAVE deep into the floor top",
                  (round(min(g.min.Z for g in gs), 3),
                   round(max(g.max.Z for g in gs), 3)),
                  (round(box.WALL - box.ENGRAVE, 3), round(box.WALL, 3)))
            # The block starts TEXT_INSET in from the side floor's inner edge
            # and runs outward; on -X it reads down in Y, on +X up.
            near = (max(g.max.X for g in gs) if sign < 0
                    else min(g.min.X for g in gs))
            start = (max(g.max.Y for g in gs) if sign < 0
                     else min(g.min.Y for g in gs))
            band[(who, lbl)] = (round(abs(near) - abs(sf_edge), 2),
                                round(start, 2))
            check(f"{who}: {lbl} engraving starts about TEXT_INSET in",
                  abs(abs(near) - abs(sf_edge) - box.TEXT_INSET) < 0.6, True)
    for lbl in ("-X", "+X"):
        if ("STEP", lbl) in band and ("build", lbl) in band:
            # Component by component: `check` only tolerances FLOATS, so a
            # tuple is compared exactly and 0.01 of rounding fails it.
            for i, what in enumerate(("inset", "start")):
                check(f"build: {lbl} engraving {what} matches the STEP's",
                      band[("build", lbl)][i], band[("STEP", lbl)][i], 0.3)
    # A single CENTRED fastener on the NARROW front holder is a DELIBERATE
    # DIVERGENCE (Allan). `Box Innovation 130U` has none at all, and a label
    # with nothing gripping its top edge is what that fixes. Asserted from both
    # ends: one on the build, none on the STEP.
    if len(box.fastener_centres(d)) == 1:
        for who, shape, want in (("STEP", ref, 0), ("build", mine, 1)):
            # 10.5 wide about the centre — clear of the frame's posts, which
            # stand at |x| >= 28.800 on the narrow holder.
            cell = Box(10.5, 1.8, 2.2).moved(Location((0, -BD / 2 - 0.95, 65.0)))
            found = (shape & cell)
            check(f"{who}: the narrow holder has {want} centred fastener",
                  len(found.solids()) if found else 0, want)
    # --- `Smooth box edges` ------------------------------------------------
    # Every rounded corner is probed the same way: a CUBE_ centred on where the
    # sharp edge WOULD be, positioned from the constants and not from either
    # solid. At a right convex corner a quarter of it is material while the
    # corner is sharp; a SMOOTH_R round takes all of it, because the far corner
    # of that quarter is sqrt(2) * (0.600 - 0.120) = 0.679 from the fillet
    # cylinder's centre and the cylinder is only 0.600. So "rounded" is exactly
    # zero and "sharp" is about 0.0035 mm3 — no tolerance to tune.
    CUBE_ = 0.24
    x_out = box_w / 2                      # `inner` is already box_w/2 - WALL
    y_front, y_back = -BD / 2, BD / 2 + box.REAR_DEPTH
    c = box.CORNER_R * (1 - 2 ** -0.5)          # an arc midpoint's inset, 1.347

    def corner_stock(shape, x, y, z):
        cell = Box(CUBE_, CUBE_, CUBE_).moved(Location((x, y, z)))
        got = shape & cell
        return round(got.volume, 5) if got else 0.0

    for sx in (-1, +1):
        side = "+X" if sx > 0 else "-X"
        for lbl, x, y, z in (
                # The end wall's vertical corners on its INNER face: front from
                # FRONT_TOP up, back from REAR_TOP up, both stopping where the
                # corner round starts. Their outer twins were already rounded.
                (f"{side} inner back corner", sx * inner, y_back, 92.0),
                # `Round top box corners` leaves one arc on each face of each
                # end wall. Rounding all four closes the perimeter chain.
                (f"{side} outer back arc", sx * x_out, y_back - c, d.BoxHeight - c),
                (f"{side} inner back arc", sx * inner, y_back - c, d.BoxHeight - c),
                (f"{side} outer front arc", sx * x_out, y_front + c, d.BoxHeight - c)):
            for who, shape in (("STEP", ref), ("build", mine)):
                check(f"{who}: {lbl} is rounded",
                      corner_stock(shape, x, y, z), 0.0, 1e-9)

    # Two things Onshape rounds on the end walls' INNER face and OCCT will not,
    # both recorded in cad/parts/box.py sharp_edges: the rim, in every segment
    # the ribs break it into, and the front vertical corner with the arc above
    # it. Each is asserted from BOTH ends — rounded on the STEP, sharp on the
    # build — so a future kernel that manages them fails here rather than
    # passing quietly.
    twin = STEP_DIR / fn.replace(".step", " without final fillet.step")
    if twin.exists():
        raw = import_step(str(twin)).solids()[0]
        # Locations from the UNFILLETED reference, on the +X wall only: the
        # segments as Onshape cut them, before its own fillet consumed them.
        segs = sorted((e for e in raw.edges()
                       if abs(e.tangent_at(0.5).Z) < 1e-6
                       and abs(e.tangent_at(0.5).Y) > 1 - 1e-6
                       and abs((e @ 0.5).Z - d.BoxHeight) < 1e-3
                       and abs((e @ 0.5).X - inner) < 1e-3
                       and e.length > 0.5),
                      key=lambda e: (e @ 0.5).Y)
        check("the ribs break the inner rim into segments", len(segs) >= 3, True)
        spots = [(f"{lbl} inner rim segment", (s_ @ 0.5).X, (s_ @ 0.5).Y,
                  (s_ @ 0.5).Z)
                 for lbl, s_ in (("front-most", segs[0]), ("rear-most", segs[-1]))]
        spots.append(("inner front corner", inner, y_front, 85.0))
        spots.append(("inner front arc", inner, y_front + c, d.BoxHeight - c))
        for lbl, x, y, z in spots:
            check(f"STEP: Onshape rounds the {lbl}",
                  corner_stock(ref, x, y, z), 0.0, 1e-9)
            check(f"build: ... and OCCT leaves it sharp",
                  corner_stock(mine, x, y, z) > 1e-4, True)

    # The version line is a DELIBERATE DIVERGENCE: Allan's sketch still reads
    # "Rev <version>" and the build says calVersion, as the Lid does. Told
    # apart by the line's ink-length-to-cap ratio, which is a property of the
    # string and the face alone — the same measurement that identified the
    # font. Asserted BOTH ways, so a future re-export that converged would fail.
    for who, shape, txt in (("STEP", ref, f"Rev {p.Version}"),
                            ("build", mine, d.calVersion)):
        gs = engraved(shape, 1)
        # A line shares its BASELINE, which on +X is the glyphs' max X — the
        # caps grow inward. Grouping by min X instead picks out one glyph.
        outer = [g for g in gs if g.max.X > max(q.max.X for q in gs) - 0.05]
        if not outer:
            continue
        span = max(g.max.Y for g in outer) - min(g.min.Y for g in outer)
        tall = max(g.size.X for g in outer)
        check(f"{who}: the version line reads {txt!r}",
              round(span / tall, 2),
              round(TX.ink(txt)[0] / TX.ink(txt)[1], 2), 0.05)

print("\n=== #calFingerHoleOffset ===")
_p = REF.primary(4, 4, 21, 10, 0, 10, 1, 0, "Dominion")     # M4.21.10.45-Sl
check("matches the value in the feature tree",
      round(box.finger_hole_offset(D.derive(_p)), 3), 162.500, 1e-3)


print("\n=== the RisingSliders > 8 branch ===")
# `#RisingSliders <= 8 ? 2.5 mm : 2.5mm + (#RisingSliders-8)*#calSliderDistance`
# on the `Card Cascade` sketch. No reference reaches it — Dominion's `333 Card`
# at `S9.21.10` is the only catalogue row that does — so it is checked by its
# effect: past eight risers the extra term is exactly the depth those risers add
# to the card area, so the logo block stops growing.
_lens = []
for _r in (8, 9, 10, 12):
    _p = REF.primary(3, _r, 21, 10, 0, 10, 1, 0, "Dominion")
    _d = D.derive(_p)
    _yf, _yb = box.card_area(_d)
    _lens.append(round(_yb - _yf - box.LOGO_FRONT_INSET - box.logo_margin(_d), 3))
check("the logo block is frozen past eight risers", len(set(_lens)), 1)
check("... at the length it had at eight", _lens[0], 64.000, 1e-3)
_p = REF.primary(3, 7, 21, 10, 0, 10, 1, 0, "Dominion")
check("and below eight the margin is the plain 2.500",
      round(box.logo_margin(D.derive(_p)), 3), round(box.LOGO_FRONT_INSET, 3), 1e-9)


# --- isLabelHoldersOnBox = 0: the branch no catalogue row can reach ----------
# `Box Innovation S5.15.15.62-Sl without label holders.step` (2026-09-04) is
# that row's box exported with the flag off. The build takes a Derived with
# the flag flipped and must match its envelope exactly — the label holders
# are the whole of the 2.600 width and 6.100 depth the box otherwise adds —
# and differ from it only where every box does: the storage dividers stay
# whole where Onshape's holes sever them, and the floor text is floored and
# says CC. Asserted from both ends.
print("\n=== isLabelHoldersOnBox = 0 ===")
nl_path = STEP_DIR / "Box Innovation S5.15.15.62-Sl without label holders.step"
if not nl_path.exists():
    fails.append("no-label-holders reference missing")
    print(f"  FAIL — reference {nl_path.name} not present")
else:
    nl_ref = import_step(str(nl_path)).solids()[0]
    nl_p = next(REF.from_row(r, 1) for r in params.load_rows(ROOT / "automation" / "parts.csv")
                if D.derive(REF.from_row(r, 1)).calModelName.startswith("S5.15.15"))
    nl_d = D.derive(nl_p)
    check("the catalogue row has the flag ON", nl_d.isLabelHoldersOnBox, 1)
    # The OPTION: parts.csv's `Label holders` column becomes
    # `Primary.LabelHolders`, and derive folds it into the flag. Off by the
    # column, off in the Derived, and named apart on disk.
    nl_row = next(r for r in params.load_rows(ROOT / "automation" / "parts.csv")
                  if D.derive(REF.from_row(r, 1)).calModelName.startswith("S5.15.15"))
    nl_p0 = REF.from_row({**nl_row, "Label holders": "FALSE"}, 1)
    check("`Label holders` FALSE reaches the Primary", nl_p0.LabelHolders, 0)
    nl_d0 = D.derive(nl_p0)
    check("... and turns the flag off", nl_d0.isLabelHoldersOnBox, 0)
    check("... and names the box apart", build.box_file(nl_d0),
          build.box_file(nl_d).replace(".3mf", " no label holders.3mf"))
    check("a blank column leaves them on", REF.from_row(nl_row, 1).LabelHolders, 1)
    nl_mine = box.build(D.derive(nl_p0))
    rb, mb = nl_ref.bounding_box(), nl_mine.bounding_box()
    for ax in "XYZ":
        check(f"no holders: {ax} min", round(getattr(mb.min, ax), 3), round(getattr(rb.min, ax), 3), 1e-3)
        check(f"no holders: {ax} max", round(getattr(mb.max, ax), 3), round(getattr(rb.max, ax), 3), 1e-3)
    # Without the holders the box is #BoxWidth plus a closing bump each end
    # by #BoxDepth plus the rear block; the side holder then stands 0.600
    # further out than the bump it covers and the front holder adds 1.600.
    check("no holders: the envelope is #BoxWidth + 2 bumps by #BoxDepth + rear block",
          (round(mb.size.X, 3), round(mb.size.Y, 3)),
          (round(box.box_width(nl_d) + 2 * box.BUMP_DEPTH, 3),
           round(box.box_depth(nl_d) + box.REAR_DEPTH, 3)))
    with_holders = box.build(nl_d).bounding_box()
    check("... and the holders add 0.600 and 1.600 to that",
          (round(with_holders.size.X - mb.size.X, 3), round(with_holders.size.Y - mb.size.Y, 3)),
          (0.6, 1.6))
    # The two differ where every box does, and it is read by RAY rather than
    # by a boolean between two 1700-face solids (which OCCT cannot clean here):
    # down each storage divider's centre in the slot band the build is one span
    # of material — the dividers stay whole — where Onshape's hanging holes
    # sever the STEP's; and the volumes agree to within what those pieces and
    # the floored, `CC` floor text account for.
    sys.path.insert(0, str(ROOT / "tests"))
    import probe
    import numpy as _np
    from cad import mesh3mf as _m3
    def _mesh(shape):
        v, t = _m3.triangulate(shape)
        return _np.array(v), _np.array(t)
    RV, RT = _mesh(nl_ref)
    MV, MT = _mesh(nl_mine)
    y0, _y1 = box.slot_band(nl_d)
    y_div = y0 + 1.0 + probe.EPS
    severed = 0
    for a, e in box.storage_dividers(nl_d):
        xm = (a + e) / 2 + probe.EPS
        check(f"no holders: build divider at x={xm:.2f} is whole",
              len(probe.spans(MV, MT, 2, xm, y_div)), 1)
        severed += len(probe.spans(RV, RT, 2, xm, y_div)) > 1
    # Which dividers a hole crosses depends on the layout: on this box the
    # first is cut clean through at every row and the second only nicked at
    # its edge, so it is at least one, not every one.
    check("no holders: Onshape's holes sever at least one STEP divider", severed >= 1, True)
    check("no holders: volumes agree to 0.3%",
          round(100 * abs(nl_mine.volume / nl_ref.volume - 1), 3) < 0.3, True)

# --- HOLE_CLEAR: the three boxes whose hole edge lands on a divider face -----
# Asserted from both ends, as every divergence is: on these three, and only
# these three, exactly ONE hole — the one whose -X edge is the first
# divider's -X face — is HOLE_CLEAR narrower than the sketch's.
print("\n=== HOLE_CLEAR ===")
clipped = {}
for row in params.load_rows(ROOT / "automation" / "parts.csv"):
    for sleeved in (0, 1):
        q = REF.from_row(row, sleeved)
        e = D.derive(q)
        a, b = box.hanging_holes(e), box.hole_openings(e)
        if a != b:
            clipped[e.calModelName] = [
                (round(x, 3), round(y, 3), round(u, 3), round(v, 3))
                for (x, y), (u, v) in zip(a, b) if (x, y) != (u, v)]
check("the boxes with a clipped hole, and the hole", clipped, {
    "XS5.15.10.45.Sl": [(-26.05, -16.05, -25.85, -16.05)],
    "S5.10.10.45.Sl": [(-60.55, -50.55, -60.35, -50.55)],
    "M5.10.10.45.Sl": [(-95.05, -85.05, -94.85, -85.05)]})

print("\nPASS" if not fails else "\nFAIL: " + ", ".join(fails))
sys.exit(1 if fails else 0)
