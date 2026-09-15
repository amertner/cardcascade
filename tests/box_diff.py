#!/usr/bin/env python3
"""Boolean diff of cad/parts/box.py against a reference STEP — a DEV LOOP,
not a test. `tests/test_box.py` is what asserts.

Takes a reference key (`box_diff.py Dom246S_raw`) and prints what the build is
MISSING (in the STEP, not mine) and what is EXTRA, as lumps with volumes and
bounding boxes, largest first. The STEPs are in spec/reference/; spec/BOX.md
says what each splits; build against `Dom246S_raw`, the one with the final
fillet suppressed. It SLICES before it subtracts: two solids sharing an entire
outer envelope return an EMPTY intersection from OCCT at any fuzzy tolerance
(spec/BOX.md, "build123d cannot subtract two boxes that share an outer
envelope"), and a feature straddling a slab boundary is then two lumps.
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
 # The build TARGET: Dom246S with `Smooth box edges` suppressed, so the
 # 0.600 fillet does not pollute the diff.
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
    # A half-failed slab boolean shows the SAME lump both ways, inflating both
    # totals while leaving their difference nearly right — hence the check
    # against the plain volume gap. SIZES are indicative; POSITIONS are exact.
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
