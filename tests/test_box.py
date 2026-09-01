#!/usr/bin/env python3
"""Check cad/parts/box.py against the hand-exported Onshape STEPs.

    .venv/bin/python tests/test_box.py

Five references in `tmp/step/`, listed in `spec/BOX.md`. The Box is being built
group by group against a boolean diff (see that file); this asserts only what
has actually been written, and grows with it.

Proven so far: the envelope (`#BoxWidth` / `#BoxDepth` / `BoxHeight`), the
bottom slot, the rear pusher storage — which is what carries the 7.0 lock into
the box, its rim cutouts sitting at each slot's centreline +- `s` — the lowered
front, the rounded top corners, the sliders and the front pocket.
"""
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from build123d import import_step, Box, Location   # noqa: E402
from cad import params, derive as D, lock as L    # noqa: E402
from cad.parts import box                         # noqa: E402

STEP_DIR = ROOT / "spec" / "reference"
REFS = [
    ("Compile 105 Sl", "Box Compile 105S.step",
     params.Primary(3, 4, 7, 7, 0, 7, 1, 0, "Compile")),
    ("Dominion 244 Sl", "Box Dominion 244S.step",
     params.Primary(4, 4, 21, 10, 0, 10, 1, 0, "Dominion")),
    ("Dominion 202 Sl (Mat)", "Box Dominion 202S Merged.step",
     params.Primary(4, 4, 21, 10, 0, 10, 1, 1, "Dominion")),
    ("Dominion 650 Sl", "Box Dominion 650S.step",
     params.Primary(5, 8, 50, 10, 0, 10, 1, 0, "Dominion")),
    # Not a parts.csv row — scratch parameters Allan exported as an extra
    # reference. Kept because it is the smallest box and the only C2 lock.
    ("FCM 72 Sl (scratch)", "Box FCM 72S.step",
     params.Primary(3, 3, 6, 6, 0, 6, 1, 0, "FCM")),
    # The only reference with a first-riser override, so the only one that can
    # tell calFirstSliderDistance (20.4) from calSliderDistance (9.6) — the
    # same gap the Dominion 246 STEP closed for the Pusher.
    ("Dominion 246 Sl", "Box Dominion 246S.step",
     params.Primary(3, 2, 40, 12, 1, 30, 1, 0, "Dominion")),
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
    y = box.box_depth(p, d) / 2 - 0.95           # mid-wall
    bar = Box(box.box_width(p, d) + 20, 0.4, 1.0).moved(Location((0, y, z)))
    pieces = sorted((s.bounding_box().min.X, s.bounding_box().max.X)
                    for s in (solid & bar).solids())
    return [((a[1] + b[0]) / 2, round(b[0] - a[1], 3))
            for a, b in zip(pieces, pieces[1:])]


for name, fn, p in REFS:
    path = STEP_DIR / fn
    print(f"\n=== {name} ===")
    if not path.exists():
        print(f"  SKIP — {path} not present")
        continue
    ref = import_step(str(path)).solids()[0]
    d = D.derive(p)
    rb = ref.bounding_box()

    # --- the envelope ------------------------------------------------------
    # The measured box stands proud of the sketch by 2.600 in width and 6.100
    # in depth — label holders, closing bumps and the rear storage.
    check("width  = #BoxWidth + 2.600", round(rb.size.X, 3),
          round(box.box_width(p, d) + 2.600, 3), 1e-3)
    check("depth  = #BoxDepth + 6.100", round(rb.size.Y, 3),
          round(box.box_depth(p, d) + 6.100, 3), 1e-3)
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
          sorted([round(-box.box_width(p, d) / 2, 3),
                  round(box.box_width(p, d) / 2, 3)]))

    # --- the rear pusher storage, and the lock it carries ------------------
    cuts = rim_cutouts(ref, p, d)
    n = box.pusher_slot_count(p)
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
    want = [round(x, 2) for x in box.pusher_slots(p, d)]
    check("slot centrelines", got, want)
    check("pitch is #dBackSlotWidth = calPusherTotalDepth + 4.000",
          round(got[1] - got[0], 2) if n > 1 else None,
          round(d.calPusherTotalDepth + 4.0, 2) if n > 1 else None, 0.05)

    # --- the bottom slot ---------------------------------------------------
    # Subtract the STEP from the floor slab the shell starts with. What is left
    # is the bottom slot plus the engraved text (glyph slivers, all under
    # 11 mm3 even on the biggest box), so take the one real lump.
    slab = Box(box.box_width(p, d) - 2 * box.WALL,
               box.box_depth(p, d) - 2 * box.WALL,
               box.WALL).moved(Location((0, 0, box.WALL / 2)))
    lumps = [q for q in (slab - ref).solids() if q.volume > 100]
    check("the floor has exactly one hole", len(lumps), 1)
    if len(lumps) == 1:
        hb = lumps[0].bounding_box()
        want_w, want_d, want_y = box.bottom_slot(p, d)
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
    BD = box.box_depth(p, d)
    box_w = box.box_width(p, d)
    inner = box_w / 2 - box.WALL
    mine = box.build(p)          # built once; every "build:" check reuses it

    def zprofile(x, y, shape=None):
        col = Box(0.4, 0.4, d.BoxHeight + 2).moved(
            Location((x, y, d.BoxHeight / 2)))
        return sorted((round(q.bounding_box().min.Z, 3),
                       round(q.bounding_box().max.Z, 3))
                      for q in ((ref if shape is None else shape) & col).solids())

    y0, y1 = box.slot_band(p, d)
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
    rest = box.pusher_rest(p, d)
    for who, shape in (("STEP", ref), ("build", mine)):
        check(f"{who}: the pusher rest is min(25, BoxHeight - ptH - 0.5) high",
              zprofile(x_pier, y0 + 1.6, shape)[0], (0.0, round(rest, 3)))
    # The hanging holes, read off the back wall as gaps along X.
    bar = Box(box.box_width(p, d) + 20, 0.4, 0.4).moved(
        Location((0, BD / 2 - 0.95, box.hole_rows()[0][0] + 3.0)))
    pieces = sorted((q.bounding_box().min.X, q.bounding_box().max.X)
                    for q in (ref & bar).solids())
    gaps = [(round(a[1], 3), round(b[0], 3)) for a, b in zip(pieces, pieces[1:])]
    want = [(round(a, 3), round(b, 3)) for a, b in box.hanging_holes(p, d)]
    check("hanging hole count", len(gaps), len(want))
    check("hanging hole positions", gaps, want)
    check("every hanging hole is HOLE_W wide",
          sorted({round(b - a, 3) for a, b in gaps}), [round(box.HOLE_W, 3)])

    # `Divider` — WHOLE, and that is a deliberate divergence. Onshape runs the
    # hanging holes straight through the dividers; `cad/` stops them at the
    # slot band. So this is the one place the build is knowingly not the STEP,
    # and the check asserts both halves of that — every divider solid on the
    # build, and at least one pierced on the STEP, so a future change that
    # quietly re-converged would still fail here.
    whole = box.DIVIDER_W * L.BOX_SLOT_DEPTH * box.REAR_TOP
    pierced = 0
    for a, e in box.storage_dividers(p, d):
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
        bar = Box(box.box_width(p, d) + 20, 0.4, 0.4).moved(
            Location((0, -BD / 2 + box.WALL / 2, box.FRONT_TOP + 1.0)))
        ends = sorted((round(q.bounding_box().min.X, 3),
                       round(q.bounding_box().max.X, 3))
                      for q in (shape & bar).solids())
        check(f"{who}: above it only the end walls remain", ends,
              [(round(-box.box_width(p, d) / 2, 3), round(-inner, 3)),
               (round(inner, 3), round(box.box_width(p, d) / 2, 3))])
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
              sorted((round(a, 3), round(c, 3)) for a, c in box.slider_ribs(p, d)))
        check(f"{who}: every rib stands SLIDER_PROUD proud",
              sorted({round(b.max.X + inner, 3) for b in lumps}),
              [round(box.SLIDER_PROUD, 3)])
        # `Round top of slider`: 0.400 below the rim a rib has lost this much
        # off each side. Read on the backmost rib, which no other feature is
        # near on any reference.
        y0, y1 = box.slider_ribs(p, d)[0]
        cap = Box(3.0, 20.0, 1.4).moved(
            Location((-inner + 1.5, (y0 + y1) / 2, d.BoxHeight - 0.4 + 0.7)))
        b = [q.bounding_box() for q in (shape & cap).solids()
             if abs(q.bounding_box().center().Y - (y0 + y1) / 2) < 2][0]
        check(f"{who}: rib is rounded SLIDER_TOP_R across its top",
              round(b.size.Y, 3),
              round(box.SLIDER_W - 2 * arc_inset(0.4, box.SLIDER_TOP_R), 3), 2e-3)
        # `Round top box corners`: 2.000 below the rim the end wall has lost
        # this much off its front and its back. Probed inside the end wall, so
        # neither the ribs nor the side label holder is in the way.
        u = 2.0
        cap = Box(box.WALL * 0.5, BD + 40, u + 2.0).moved(
            Location((-box.box_width(p, d) / 2 + box.WALL / 2, 0,
                      d.BoxHeight - u + (u + 2.0) / 2)))
        b = [q.bounding_box() for q in (shape & cap).solids()][0]
        eaten = round(arc_inset(u, box.CORNER_R), 3)
        check(f"{who}: end wall, CORNER_R round at the top front",
              round(b.min.Y + BD / 2, 3), eaten, 2e-3)
        check(f"{who}: end wall, CORNER_R round at the top back",
              round(BD / 2 + box.REAR_DEPTH - b.max.Y, 3), eaten, 2e-3)
    # --- `Front pocket` -----------------------------------------------------
    fw, fb, pback = box.pocket_span(p, d)
    for who, shape in (("STEP", ref), ("build", mine)):
        # A section through the middle of the pocket: the two pads, then one
        # segment per divider. MatPocket shows up here as a missing divider.
        bar = Box(box_w + 20, 0.2, 0.05).moved(Location((0, (fw + fb) / 2, 30.0)))
        segs = sorted((round(q.bounding_box().min.X, 3),
                       round(q.bounding_box().max.X, 3))
                      for q in (shape & bar).solids())
        want = ([(round(-box_w / 2, 3), round(-inner + box.FRONT_PAD, 3))]
                + [(round(x - box.FRONT_DIVIDER_W, 3), round(x, 3))
                   for x in box.front_dividers(p, d)]
                + [(round(inner - box.FRONT_PAD, 3), round(box_w / 2, 3))])
        check(f"{who}: pocket section is 2 pads + {len(box.front_dividers(p, d))} dividers",
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
        holes = box.hanging_holes(p, d)
        pier = (holes[0][1] + holes[1][0]) / 2
        col = Box(0.15, BD + 40, 0.15).moved(Location((pier, 0, 40.0)))
        ys = sorted((round(q.bounding_box().min.Y, 3),
                     round(q.bounding_box().max.Y, 3))
                    for q in (shape & col).solids())
        check(f"{who}: the divider panel is FRONT_DIVIDER thick",
              [y for y in ys if abs(y[0] - fb) < 1e-6],
              [(round(fb, 3), round(pback, 3))])
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

print("\n=== #calFingerHoleOffset ===")
_p = params.Primary(4, 4, 21, 10, 0, 10, 1, 0, "Dominion")     # M4.21.10.45-Sl
check("matches the value in the feature tree",
      round(box.finger_hole_offset(_p, D.derive(_p)), 3), 162.500, 1e-3)

print("\nPASS" if not fails else "\nFAIL: " + ", ".join(fails))
sys.exit(1 if fails else 0)
