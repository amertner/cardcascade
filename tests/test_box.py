#!/usr/bin/env python3
"""Check cad/parts/box.py against the hand-exported Onshape STEPs.

    .venv/bin/python tests/test_box.py

Five references in `tmp/step/`, listed in `spec/BOX.md`. The Box is being built
group by group against a boolean diff (see that file); this asserts only what
has actually been written, and grows with it.

Proven so far: the envelope (`#BoxWidth` / `#BoxDepth` / `BoxHeight`) and the
rear pusher storage's placement, which is what carries the 7.0 lock into the
box — its rim cutouts sit at each slot's centreline +- `s`.
"""
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
    inner = box.box_width(p, d) / 2 - box.WALL

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
    # A pusher rests PUSHER_REST up, not on the floor. Probe through the FIRST
    # HANGING HOLE, not the slot centreline: on an M box the centreline lands on
    # a lattice pier, where the material runs on past the rest and the profile
    # says nothing about it.
    hole0 = box.hanging_holes(p, d)[0]
    check("the pusher rest is PUSHER_REST high",
          zprofile(sum(hole0) / 2, y0 + 0.5)[0], (0.0, box.PUSHER_REST))
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

    # --- `Lower the front`, and the rim cutouts, on the BUILD as well --------
    mine = box.build(p)
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
