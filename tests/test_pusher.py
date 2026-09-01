#!/usr/bin/env python3
"""Check cad/parts/pusher.py against the hand-exported Onshape STEP.

The reference is Compile 105 Card Sleeved (S4.7.7.32-Sl), the parameter set in
spec/PUSHER.md. It carries three engraved text lines that the build does not
yet cut (one is in an unidentified font), so volume is compared against the
STEP plus the volume those engravings removed, measured off the STEP itself.

    .venv/bin/python tests/test_pusher.py [path/to/Pusher.step]
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from build123d import import_step, Plane, Location
from cad import params, lock as L
from cad.parts import pusher

REF = sys.argv[1] if len(sys.argv) > 1 else str(
    Path.home() / ".claude/uploads/07f2d5de-ff9b-5727-acb3-79b6a8da454a/63735c8a-Pusher.step")
fails = []


def check(label, got, want, tol=1e-6):
    ok = abs(got - want) <= tol if isinstance(want, float) else got == want
    print(f"  {'ok  ' if ok else 'FAIL'} {label:50s} {got!r:>18} vs {want!r}")
    if not ok:
        fails.append(label)


ref = import_step(REF).solids()[0]
p = params.Primary(HorizontalSlots=3, RisingSliders=4, FrontPocketCardCapacity=7,
                   CardsPerSlidingSlot=7, isFirstSlidingSlotOverride=0,
                   FirstSlidingSlotCards=7, isSleeved=1, MatPocket=0,
                   GameName="Compile", Version="7.0")
part = pusher.build(p, text=False)
moved = part.moved(Location(pusher.STEP_OFFSET))

print("\nbounding box")
b, rb = part.bounding_box(), ref.bounding_box()
for ax in "XYZ":
    check(f"size {ax}", round(getattr(b.size, ax), 6),
          round(getattr(rb.size, ax), 6), 1e-6)

print("\nvolume (STEP + the volume its engraving removed)")
glyphs = sum(f.area for f in ref.faces() if abs(f.center().Z + 15.4) < 1e-6)
want = ref.volume + glyphs * pusher.ENGRAVE
check("engraved glyph area (mm^2)", round(glyphs, 3), 144.964, 0.001)
check("volume (mm^3)", round(part.volume, 3), round(want, 3), 0.02)

print("\nmid-plate outline (z = -16.5 in STEP coordinates)")
a = (moved & Plane.XY.offset(-16.5)).faces()[0]
r = (ref & Plane.XY.offset(-16.5)).faces()[0]
check("section area", round(a.area, 4), round(r.area, 4), 1e-4)
check("vertex count", len(a.vertices()), len(r.vertices()))
va = sorted({(round(v.X, 3), round(v.Y, 3)) for v in a.vertices()})
vr = sorted({(round(v.X, 3), round(v.Y, 3)) for v in r.vertices()})
check("vertex positions", va, [(round(x, 3), round(y, 3)) for x, y in vr])

print("\nlock features")
def zface(shape, z, tol=1e-6):
    return [f for f in shape.faces() if abs(f.center().Z - z) < tol]
check("tab top area (2 x 3.80 x 5.00)",
      round(sum(f.area for f in zface(moved, -13.5)), 4),
      round(sum(f.area for f in zface(ref, -13.5)), 4), 1e-4)
def ycentres(shape, area_each):
    return sorted(round(f.center().Y, 4) for f in shape.faces()
                  if abs(f.area - area_each) < 1e-3
                  and abs(f.normal_at(f.center()).Y) > 0.999)
check("tab flank Y positions", ycentres(moved, 7.5), ycentres(ref, 7.5))
check("notch flank Y positions", ycentres(moved, 15.6), ycentres(ref, 15.6))
name, s = L.lock_class(32.0)
check("lock class for D=32.00", name, "C3")
check("tab offset s", s, 8.5)

print("\nriser fillets (face area proves the radius: (PLATE - 2r) x length)")
def xface(shape, x):
    return round(sum(f.area for f in shape.faces()
                     if abs(f.center().X - x) < 1e-6
                     and abs(f.normal_at(f.center()).X) > 0.999), 4)
for x in (21.0, 39.0, 57.0, 75.0):
    check(f"riser face area at x={x}", xface(moved, x), xface(ref, x), 1e-3)
check("leading edge face area (no fillet)", xface(moved, 3.0), xface(ref, 3.0), 1e-3)
check("notch end face area", xface(moved, 8.2), xface(ref, 8.2), 1e-3)

print("\nengraved text (the two Orbitron lines; the third is not cut)")
textd = pusher.build(p, text=True).moved(Location(pusher.STEP_OFFSET))
def inks(sh, only_cut=False):
    g = [f.bounding_box() for f in sh.faces() if abs(f.center().Z + 15.4) < 1e-6]
    if only_cut:
        g = [b for b in g if b.min.X > 15]          # drop the un-cut third line
    return sorted(g, key=lambda b: (round(-b.min.Y, 2), b.min.X))
gb, gr = inks(textd), inks(ref, only_cut=True)
check("glyph count", len(gb), len(gr))
worst = max(max(abs(a.min.X - b.min.X), abs(a.min.Y - b.min.Y))
            for a, b in zip(gb, gr))
check("worst glyph placement error (mm)", round(worst, 4), 0.0, 0.005)
check("engrave depth leaves the third line uncut (mm^3)",
      round(textd.volume - ref.volume, 2),
      round((sum(f.area for f in ref.faces() if abs(f.center().Z + 15.4) < 1e-6)
             - sum(f.area for f in textd.faces() if abs(f.center().Z + 15.4) < 1e-6))
            * pusher.ENGRAVE, 2), 0.05)

print("\n3MF export")
from build123d import Mesher
out = Path("/tmp/pusher_smoke.3mf")
m = Mesher(); m.add_shape(textd, part_number="Pusher"); m.write(out)
check("wrote a 3MF", out.exists() and out.stat().st_size > 0, True)
out.unlink(missing_ok=True)

print(f"\n{'PASS' if not fails else 'FAIL: ' + ', '.join(fails)}")
sys.exit(1 if fails else 0)
