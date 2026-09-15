#!/usr/bin/env python3
"""Check cad/parts/token_holder.py against the two hand-exported Onshape STEPs.

    .venv/bin/python tests/test_token_holder.py

Both are Dominion `324 Card` sleeved, `M6.21.10.62-Sl`, FULL and HALF, which
differ in one number. `spec/TOKENHOLDER.md` is the record.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

from build123d import import_step, Plane, Box, Location   # noqa: E402
from cad import params, derive as D, text as TX      # noqa: E402
import reference as REF                                        # noqa: E402
from cad.parts import token_holder as TH             # noqa: E402

STEP_DIR = ROOT / "spec" / "reference"
# Dominion `324 Card` sleeved; the STEP engraves `CC 7.0 M21.Sl`.
P = REF.primary(4, 6, 21, 10, 0, 10, 1, 0, "Dominion")
REFS = [("FULL", False, "TokenHolder M6.21.10.62-Sl.step"),
        ("HALF", True, "HalfTokenHolder M6.21.10.62-Sl.step")]

fails = []


def check(label, got, want, tol=1e-6):
    ok = abs(got - want) <= tol if isinstance(want, float) else got == want
    print(f"  {'ok  ' if ok else 'FAIL'} {label:56s} {got!r:>22} vs {want!r}")
    if not ok:
        fails.append(label)


def section_area(solid, z):
    return sum(f.area for f in Plane.XY.offset(z).intersect(solid).faces())


d = D.derive(P)
built = {half: TH.build(D.derive(P), half) for _, half, _ in REFS}
refs = {half: import_step(str(STEP_DIR / fn)).solids()[0]
        for _, half, fn in REFS}

print("=== the derived slot, and what the sketch says ===")
check("calTokenHolderSlotWidth", round(d.calTokenHolderSlotWidth, 3), 64.400, 1e-3)
check("... less 0.500 is the sketch's 63.9", round(d.calTokenHolderSlotWidth - 0.5, 3),
      63.900, 1e-3)
check("2.600 + calFrontPocketDepth/2 is the sketch's 8.9",
      round(TH.HALF_BASE + d.calFrontPocketDepth / 2, 3), 8.900, 1e-3)
check("calTokenHolderModel", d.calTokenHolderModel, "M21.Sl")
check("the engraved line", TH.text_line(d), "CC 7.0 M21.Sl")

print("\n=== the envelope ===")
for name, half, _ in REFS:
    b, r = built[half].bounding_box(), refs[half].bounding_box()
    for ax in "XYZ":
        check(f"{name}: {ax} min", round(getattr(b.min, ax), 6),
              round(getattr(r.min, ax), 6), 1e-6)
        check(f"{name}: {ax} max", round(getattr(b.max, ax), 6),
              round(getattr(r.max, ax), 6), 1e-6)

print("\n=== FULL and HALF differ in the depth and in NOTHING else ===")
# The same 231 faces and 644 edges on both (spec/TOKENHOLDER.md).
check("the references have the same face count",
      len(refs[False].faces()), len(refs[True].faces()))
check("the references have the same edge count",
      len(refs[False].edges()), len(refs[True].edges()))
check("and so does the build", len(built[False].faces()),
      len(built[True].faces()))
check("FULL depth is calFrontPocketDepth - 2*CLEARANCE",
      round(TH.depth(d, False), 3), 11.800, 1e-3)
check("HALF depth is 2.600 + half of it, less the same",
      round(TH.depth(d, True), 3), 8.100, 1e-3)

print("\n=== volume ===")
# The only divergence: the grip's round into the rim's (spec/TOKENHOLDER.md).
for name, half, _ in REFS:
    v, rv = built[half].volume, refs[half].volume
    check(f"{name}: within 0.002% of the reference",
          round(100 * abs(v / rv - 1), 4), 0.0, 0.002)

print("\n=== the shell, section by section ===")
for name, half, _ in REFS:
    for z in (1.5, 40.0, 64.5, 65.1, 74.0, 75.05, 76.0, 80.0, 82.4):
        check(f"{name}: section area at Z {z}",
              round(section_area(built[half], z), 3),
              round(section_area(refs[half], z), 3), 1e-3)

print("\n=== the token divider ===")
for name, half, _ in REFS:
    cy0, cy1 = TH.cavity(d, half)[2:]
    below = section_area(built[half], 60.0)
    above = section_area(built[half], 70.0)
    check(f"{name}: the divider is 2.000 x the cavity depth",
          round(below - above, 3), round(TH.DIVIDER_W * (cy1 - cy0), 3), 1e-3)
    check(f"{name}: centred on the part", round(TH.divider_x(d), 3),
          round(TH.CLEARANCE + TH.width(d) / 2, 3), 1e-3)
check("its bead tops out 10.000 below the rim",
      round(TH.height() - TH.DIVIDER_DROP, 3), 65.000, 1e-3)

print("\n=== the grip ===")
# The radius is read off the reference by two sections, not assumed.
za, zb = 76.0, 80.0
wa, wb = (Plane.XY.offset(z).intersect(refs[False]).faces()[0].bounding_box().size.X / 2
          for z in (za, zb))
z0 = (za + zb) / 2 - (wa ** 2 - wb ** 2) / (2 * (zb - za))
check("the grip's circle is centred on the rim", round(z0, 3),
      round(TH.height(), 3), 1e-3)
check("... with radius GRIP_R", round((wa ** 2 + (za - z0) ** 2) ** 0.5, 3),
      round(TH.GRIP_R, 3), 1e-3)
check("so the part is 82.500 tall on every parameter set",
      round(TH.height() + TH.GRIP_R, 3), 82.500, 1e-3)

print("\n=== the engraved underside ===")
# The bottom face LESS the engraving: the one place the fonts differ.
for name, half, _ in REFS:
    check(f"{name}: the engraved floor, to 0.05 mm2",
          round(section_area(built[half], 0.1), 3),
          round(section_area(refs[half], 0.1), 3), 0.05)

print("\n=== the branding ===")
em = TH.text_size(d, False)
# The em is the reference's own reading, 5.7000 +-0.0014; derived TRAIL 5.6992.
check("em size", round(em, 4), 5.7000, 1e-3)
cut = TH.branding(d, False)
b = cut.bounding_box()
check("ink X min", round(b.min.X, 3), 10.719, 6e-3)
check("ink X max", round(b.max.X, 3), 53.065, 6e-3)
check("ink Y min", round(b.min.Y, 3), -8.642, 6e-3)
check("ink Y max (the BASELINE — the glyphs run -Y)",
      round(b.max.Y, 3), -4.248, 6e-3)
check("engraved depth", round(b.max.Z - b.min.Z, 3), round(TH.ENGRAVE, 3), 1e-6)
check("the text box's origin is TEXT_INSET from the left edge",
      round(b.min.X - TX.metrics(TH.text_line(d))[1] * em - TH.CLEARANCE, 3),
      round(TH.TEXT_INSET, 3), 5e-3)
check("the cap band is centred on the part's depth",
      round(b.max.Y - TX.CAP * em / 2, 3),
      round(-TH.CLEARANCE - TH.depth(d, False) / 2, 3), 5e-3)

print("\n=== two more HALF references, 2026-09-04 ===")
# Two more hand-exported HALF references, one ending `n` not `l`, one Onshape
# CLIPS (spec/TOKENHOLDER.md).
MORE = [("HALF Un", "HalfTokenHolder M6.21.10.45-Un.step",
         REF.primary(4, 6, 21, 10, 0, 10, 0, 0, "Dominion"), False),
        ("HALF merged Sl", "HalfTokenHolder M4.21.10.45-M-Sl.step",
         REF.primary(4, 4, 21, 10, 0, 10, 1, 1, "Dominion"), True)]
for name, fn, q, clipped in MORE:
    dq = D.derive(q)
    ref = import_step(str(STEP_DIR / fn)).solids()[0]
    mine = TH.build(D.derive(q), True)
    b, r = mine.bounding_box(), ref.bounding_box()
    for ax in "XYZ":
        check(f"{name}: {ax} min", round(getattr(b.min, ax), 6),
              round(getattr(r.min, ax), 6), 1e-6)
        check(f"{name}: {ax} max", round(getattr(b.max, ax), 6),
              round(getattr(r.max, ax), 6), 1e-6)
    check(f"{name}: depth is the HALF's", round(b.max.Y - b.min.Y, 3),
          round(TH.depth(dq, True), 3), 1e-3)
    for z in (1.5, 40.0, 64.5, 74.0, 80.0):
        check(f"{name}: section area at Z {z}",
              round(section_area(mine, z), 3), round(section_area(ref, z), 3), 1e-3)
    def ink_y(shape):
        """Y extent of the underside engraving — the voids just above z = 0."""
        bb = shape.bounding_box()
        # the part's footprint in Y, so a glyph on a face stays its own void
        slab = Box(bb.size.X - 2 * TH.CLEARANCE, bb.size.Y, TH.ENGRAVE - 0.02).moved(
            Location(((bb.min.X + bb.max.X) / 2, (bb.min.Y + bb.max.Y) / 2, TH.ENGRAVE / 2)))
        lumps = [q for q in (slab - shape).solids()
                 if q.volume > 0.01 and q.bounding_box().min.Y >= bb.min.Y - 1e-3
                 and q.bounding_box().max.Y <= bb.max.Y + 1e-3]
        return (min(q.bounding_box().min.Y for q in lumps),
                max(q.bounding_box().max.Y for q in lumps))
    if not clipped:
        check(f"{name}: within 0.002% of the reference",
              round(100 * abs(mine.volume / ref.volume - 1), 4), 0.0, 0.002)
        # 0.1 where the sleeved pair holds 0.05: two more glyphs, fitted apart.
        check(f"{name}: the engraved floor, to 0.1 mm2",
              round(section_area(mine, 0.1), 3), round(section_area(ref, 0.1), 3), 0.1)
    else:
        # Onshape fits the text box on width alone, ours on the depth too.
        ry0, ry1 = ink_y(ref)
        my0, my1 = ink_y(mine)
        check(f"{name}: Onshape's ink reaches the part's back face",
              round(ry0, 3), round(r.min.Y, 3), 1e-3)
        check(f"{name}: ... and its front face", round(ry1, 3), round(r.max.Y, 3), 1e-3)
        check(f"{name}: ours stops short of both",
              my0 > r.min.Y + 1e-3 and my1 < r.max.Y - 1e-3, True)
        check(f"{name}: ... and is heavier by under 0.1%",
              0.0 < 100 * (mine.volume / ref.volume - 1) < 0.1, True)

print("\n=== it is Dominion-only, and says so ===")
try:
    TH.build(D.derive(REF.primary(4, 6, 21, 10, 0, 10, 1, 0, "Innovation")))
    check("a non-Dominion Primary is refused", False, True)
except ValueError:
    check("a non-Dominion Primary is refused", True, True)

print("\nPASS" if not fails else "\nFAIL: " + ", ".join(fails))
sys.exit(1 if fails else 0)
