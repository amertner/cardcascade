#!/usr/bin/env python3
"""Boolean diff of cad/parts/box.py against a reference STEP — a DEV LOOP,
not a test. `tests/test_box.py` is what asserts.

    .venv/bin/python tests/box_diff.py Compile105S Dom650S

Prints what the build is MISSING (in the STEP, not in mine) and what is EXTRA
(mine, not in the STEP), as lumps with volumes and bounding boxes, largest
first. This is the loop the Box is built in: add a feature group, re-run, watch a
lump disappear. The five reference STEPs are in spec/reference/;
spec/BOX.md says what each one splits.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from build123d import import_step
from cad import params, derive as D
from cad.parts import box

REFS = {
 "Compile105S": ("Box Compile 105S.step",         params.Primary(3,4,7,7,0,7,1,0,"Compile")),
 "Dom244S":     ("Box Dominion 244S.step",        params.Primary(4,4,21,10,0,10,1,0,"Dominion")),
 "Dom202SM":    ("Box Dominion 202S Merged.step", params.Primary(4,4,21,10,0,10,1,1,"Dominion")),
 "Dom650S":     ("Box Dominion 650S.step",        params.Primary(5,8,50,10,0,10,1,0,"Dominion")),
 "FCM72S":      ("Box FCM 72S.step",              params.Primary(3,3,6,6,0,6,1,0,"FCM")),
}

def lumps(shape, n=12):
    out = []
    try:
        sols = shape.solids()
    except Exception:
        return out
    for s in sols:
        b = s.bounding_box()
        out.append((s.volume, b))
    out.sort(key=lambda t: -t[0])
    return out[:n]

def report(key, limit=10):
    fn, p = REFS[key]
    ref = import_step(str(Path(__file__).resolve().parent.parent / "spec" / "reference" / fn)).solids()[0]
    mine = box.build(p)
    d = D.derive(p)
    print(f"=== {key}  #BoxWidth {box.box_width(p,d):.3f}  #BoxDepth {box.box_depth(p,d):.3f}")
    print(f"  mine {mine.volume:12.3f} mm3    STEP {ref.volume:12.3f} mm3"
          f"    mine/STEP {mine.volume/ref.volume*100:.1f}%")
    for label, shape in (("MISSING (in STEP, not mine)", ref - mine),
                         ("EXTRA   (mine, not in STEP)", mine - ref)):
        ls = lumps(shape)
        tot = sum(v for v, _b in ls)
        print(f"  {label}: {len(ls)} lump(s) shown, {tot:11.3f} mm3")
        for v, b in ls[:limit]:
            print(f"     {v:11.3f}  X {b.min.X:9.3f}..{b.max.X:9.3f}"
                  f"  Y {b.min.Y:8.3f}..{b.max.Y:8.3f}"
                  f"  Z {b.min.Z:8.3f}..{b.max.Z:8.3f}")

for k in sys.argv[1:] or ["Compile105S"]:
    report(k)
