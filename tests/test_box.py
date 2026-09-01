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

print("\nPASS" if not fails else "\nFAIL: " + ", ".join(fails))
sys.exit(1 if fails else 0)
