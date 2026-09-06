#!/usr/bin/env python3
"""Boolean diff of cad/parts/box.py against a reference STEP — a DEV LOOP,
not a test. `tests/test_box.py` is what asserts.

    .venv/bin/python tests/box_diff.py Dom246S_raw

Prints what the build is MISSING (in the STEP, not in mine) and what is EXTRA
(mine, not in the STEP), as lumps with volumes and bounding boxes, largest
first. Add a feature group, re-run, watch a lump disappear.

The five reference STEPs are in spec/reference/; spec/BOX.md says what each one
splits. Build against `Dom246S_raw`, which has the final fillet suppressed.

## Why this slices before it subtracts

Once the rear storage landed, `mine` and the STEP shared their ENTIRE outer
envelope — same walls, same 105.000 height, same 4.500 of added depth — and
OCCT's boolean then returns an EMPTY intersection for two solids that plainly
overlap. Both shapes pass BRepCheck_Analyzer, each intersects a large box
correctly, and a fuzzy tolerance from 1e-7 to 1e-3 changes nothing; `ref - mine`
comes back as `ref` and `ref & mine` as zero volume.

Slicing both shapes into slabs first and diffing slab by slab works, and the
totals reconcile with the plain volume difference. So that is what this does. A
feature straddling a slab boundary is reported as two lumps — the cost of the
workaround, and the reason SLABS is kept low.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from build123d import Box, Location, import_step
from cad import params, derive as D
import reference as REF                                        # noqa: E402
from cad.parts import box

SLABS = 8
REFS = {
 "Compile105S": ("Box Compile 105S.step",         REF.primary(3,4,7,7,0,7,1,0,"Compile")),
 "Dom244S":     ("Box Dominion 244S.step",        REF.primary(4,4,21,10,0,10,1,0,"Dominion")),
 "Dom202SM":    ("Box Dominion 202S Merged.step", REF.primary(4,4,21,10,0,10,1,1,"Dominion")),
 "Dom650S":     ("Box Dominion 650S.step",        REF.primary(5,8,50,10,0,10,1,0,"Dominion")),
 "FCM72S":      ("Box FCM 72S.step",              REF.primary(3,3,6,6,0,6,1,0,"FCM")),
 # The build TARGET: same box as Dom246S with `Smooth box edges` suppressed, so
 # the diff is not polluted by the 0.600 fillet.
 "Dom246S_raw": ("Box Dominion 246S without final fillet.step",
                 REF.primary(3,2,40,12,1,30,1,0,"Dominion")),
 "Dom246S":     ("Box Dominion 246S.step",        REF.primary(3,2,40,12,1,30,1,0,"Dominion")),
}


def sliced_diff(a, b, slabs=SLABS):
    """[(volume, bounding box)] of `a - b`, computed slab by slab. See above."""
    bb = a.bounding_box()
    lo, hi = bb.min.X - 1, bb.max.X + 1
    span = max(bb.size.Y, bb.size.Z) * 4
    out, failed = [], 0
    for i in range(slabs):
        x0 = lo + (hi - lo) * i / slabs
        x1 = lo + (hi - lo) * (i + 1) / slabs
        cell = Box(x1 - x0, span, span).moved(Location(((x0 + x1) / 2, 0, 0)))
        pa, pb = a & cell, b & cell
        if pa is None:
            continue
        rest = pa if pb is None else pa - pb
        if rest is None:
            failed += 1
            continue
        for s in rest.solids():
            out.append((s.volume, s.bounding_box()))
    out.sort(key=lambda t: -t[0])
    return out, failed


def report(key, limit=25, slabs=SLABS):
    fn, p = REFS[key]
    ref = import_step(str(Path(__file__).resolve().parent.parent
                          / "spec" / "reference" / fn)).solids()[0]
    mine = box.build(D.derive(p))
    d = D.derive(p)
    print(f"=== {key}  #BoxWidth {box.box_width(p,d):.3f}  "
          f"#BoxDepth {box.box_depth(p,d):.3f}")
    print(f"  mine {mine.volume:12.3f} mm3    STEP {ref.volume:12.3f} mm3"
          f"    mine/STEP {mine.volume/ref.volume*100:.1f}%")
    totals = {}
    for label, a, b in (("MISSING (in STEP, not mine)", ref, mine),
                        ("EXTRA   (mine, not in STEP)", mine, ref)):
        lumps, failed = sliced_diff(a, b, slabs)
        totals[label] = sum(v for v, _ in lumps)
        note = f", {failed} slab(s) failed" if failed else ""
        print(f"  {label}: {totals[label]:11.3f} mm3 in "
              f"{len(lumps)} lump(s){note}")
        for v, bb in lumps[:limit]:
            print(f"     {v:11.3f}  X {bb.min.X:9.3f}..{bb.max.X:9.3f}"
                  f"  Y {bb.min.Y:8.3f}..{bb.max.Y:8.3f}"
                  f"  Z {bb.min.Z:8.3f}..{bb.max.Z:8.3f}")
    # A slab whose boolean half-failed shows the SAME lump in both directions,
    # which inflates both totals while leaving their difference nearly right.
    # Check them against the plain volume gap, which needs no boolean at all.
    # Individual lump SIZES are indicative, not exact; their positions are what
    # this tool is for.
    got = totals["MISSING (in STEP, not mine)"] - totals["EXTRA   (mine, not in STEP)"]
    want = ref.volume - mine.volume
    if abs(got - want) > max(1.0, 0.002 * abs(want)):
        print(f"  ** the two totals differ by {got:.3f} where the volumes differ "
              f"by {want:.3f} — a slab boolean failed; re-run with --slabs N")
    else:
        print(f"  (totals reconcile: {got:.3f} vs a {want:.3f} volume gap)")


args = sys.argv[1:]
slabs = SLABS
if "--slabs" in args:
    i = args.index("--slabs")
    slabs = int(args[i + 1])
    del args[i:i + 2]
for k in args or ["Dom246S_raw"]:
    report(k, slabs=slabs)
