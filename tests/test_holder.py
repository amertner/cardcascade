#!/usr/bin/env python3
"""Check cad/parts/holder.py against the hand-exported Onshape STEPs.

    .venv/bin/python tests/test_holder.py

Ten references in `spec/reference/`, listed in `spec/HOLDER.md` and all
asserted against, covering every slot width, compartment count, game, sleeving
and slider distance. The 246 pair is ONE configuration exported twice, whose
two slider distances differ by a factor of two, so a reading that uses one
fails on the wrong one. Every feature is asserted, the bottom text where it
reproduces Onshape and where it does not. The 3MFs: test_holder_corpus.py.
"""
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

from build123d import import_step, Box, Location, GeomType   # noqa: E402
from cad import params, derive as D, text as TX      # noqa: E402
import reference as REF                                        # noqa: E402
from cad.parts import holder, box                    # noqa: E402

STEP_DIR = ROOT / "spec" / "reference"
_ROWS = list(params.load_rows(ROOT / "automation" / "parts.csv"))


def row_params(short_name, sleeved):
    """The Primary for a parts.csv row: Compile rows leave `Front capacity`
    blank, so read the CSV rather than transcribe nine positional ints."""
    for row in _ROWS:
        if row.get("Short name") == short_name:
            return REF.from_row(row, sleeved)
    raise KeyError(short_name)


P246 = REF.primary(3, 2, 40, 12, 1, 30, 1, 0, "Dominion")
P333 = REF.primary(3, 9, 21, 10, 0, 10, 1, 0, "Dominion")
PINN_SL = REF.primary(4, 5, 10, 10, 0, 10, 1, 0, "Innovation")
PINN_UN = REF.primary(4, 5, 10, 10, 0, 10, 0, 0, "Innovation")
REFS = [
    ("Dominion 246 Sl", "Holder S2.40.12-30.45-Sl.step", P246, False),
    # The same row's first riser: calFirstSliderDistance 20.400 vs 9.600.
    ("Dominion 246 Sl (first)", "FirstHolder S2.40.12-30.45-Sl.step", P246, True),
    # Nine risers, the catalogue's shallowest rise.
    ("Dominion 333 Sl", "Holder S9.21.10.62-Sl.step", P333, False),
    # Innovation: SPANNING, four compartments, non-Dominion slot widths.
    ("Innovation M5.10.10 Sl", "Holder M5.10.10.45-Sl.step", PINN_SL, False),
    ("Innovation M5.10.10 Un", "Holder M5.10.10.32-Un.step", PINN_UN, False),
    # The four that close the parameter space: widths 63/68/70, counts 2, 5.
    ("Innovation XS5.15.10 Sl", "Holder XS5.15.10.45-Sl.step",
     row_params("Single Mini", 1), False),
    ("Compile S4.7.7 Sl", "Holder S4.7.7.32-Sl.step",
     row_params("105 Card", 1), False),
    ("FCM S4.18.12 Un", "Holder S4.18.12.32-Un.step",
     row_params("198 Card", 0), False),
    # `210 Card`, both sleevings, both RE-EXPORTED: the first exports were
    # mis-configured, not a rule (spec/HOLDER.md, "`210 Card` disagreed with
    # its own sibling"). The unsleeved one is the only reference at 68.000.
    ("Compile L5.7.7 Sl", "Holder L5.7.7.45-Sl.step",
     row_params("210 Card", 1), False),
    ("Compile L5.7.7 Un", "Holder L5.7.7.20-Un.step",
     row_params("210 Card", 0), False),
]

# Empty, but kept: parking a reference that fails a rule the others satisfy --
# rather than fitting the rule to it — is what got both `210` exports re-cut.
HELD_OUT = []
fails = []


def check(label, got, want, tol=1e-6):
    ok = abs(got - want) <= tol if isinstance(want, float) else got == want
    print(f"  {'ok  ' if ok else 'FAIL'} {label:54s} {got!r:>24} vs {want!r}")
    if not ok:
        fails.append(label)


def planes(shape, axis):
    out = set()
    for f in shape.faces():
        try:
            n = f.normal_at(f.center())
        except Exception:
            continue
        if abs(getattr(n, axis)) > 0.999:
            out.add(round(getattr(f.center(), axis), 3))
    return sorted(out)


def slants(shape):
    """{(slope, Z where the plane meets Y=0): total area} for the sloped faces.

    By the PLANE, not the face: Onshape splits the slant into pieces too small
    to find by area, and a drop between wall tops reads whichever of the two
    parallel planes that wall reaches, which differs per holder."""
    out = {}
    for f in shape.faces():
        try:
            n = f.normal_at(f.center())
        except Exception:
            continue
        if abs(n.X) < 1e-6 and 0.02 < abs(n.Z) < 0.999:
            c = f.center()
            slope = -n.Y / n.Z
            key = (round(slope, 4), round(c.Z + slope * (0.0 - c.Y), 3))
            out[key] = out.get(key, 0.0) + f.area
    return out


for name, fn, p, first in REFS:
    path = STEP_DIR / fn
    print(f"\n=== {name} ===")
    if not path.exists():
        # A missing reference is a FAILURE, not a skip: every STEP is in git.
        print(f"  FAIL — reference {path.name} not present")
        fails.append(f"{name}: reference {path.name} missing")
        continue
    ref = import_step(str(path)).solids()[0]
    d = D.derive(p)
    mine = holder.build(D.derive(p), first)
    rb, mb = ref.bounding_box(), mine.bounding_box()
    sd = holder.slider_distance(d, first)

    # Width is calSlotwidth * n + 9.800: the 246 pair shares it, nothing else.
    check("width = calSlotwidth * n + 9.800", round(rb.size.X, 3),
          round(holder.holder_width(d), 3), 1e-3)
    check("... and the build agrees", round(mb.size.X, 3),
          round(rb.size.X, 3), 1e-3)
    # X is NOT symmetric: the origin is the first compartment's centre.
    x0, x1 = holder.x_span(d)
    check("X starts at -(calSlotwidth/2 + 4.900)", round(rb.min.X, 3),
          round(x0, 3), 1e-3)
    check("X ends at the last compartment + the same", round(rb.max.X, 3),
          round(x1, 3), 1e-3)

    # Depth takes the holder's OWN slider distance, read as the BACK FACE and
    # not the bbox: the rear lip's tab stands proud in +Y of the body.
    check("the back face is at -(sliderDistance - 0.400)", round(rb.min.Y, 3),
          round(-holder.holder_depth(d, first), 3), 1e-3)
    check("... and the build agrees", round(mb.min.Y, 3),
          round(rb.min.Y, 3), 1e-3)
    # Y = 0 is the REAR face; the `Rear lip` tabs stand proud of it.
    check("the build stands as proud of Y=0 as the STEP does",
          round(mb.max.Y, 3), round(rb.max.Y, 3), 1e-3)

    check("base = -(CardHeight - 1.5)/2", round(rb.min.Z, 3),
          round(holder.base_z(d), 3), 1e-3)
    check("... and the build agrees", round(mb.min.Z, 3),
          round(rb.min.Z, 3), 1e-3)

    # `Top slant angle`: two PARALLEL planes 2.000 apart, meeting Y=0 at a Z.
    want = round(holder.slant_slope(d, first), 4)
    rival = round((d.calHeightIncrement - 1.0)
                  / ((d.calSliderDistance if first else d.calFirstSliderDistance)
                     - 1.2), 4)
    for who, shape in (("STEP", ref), ("build", mine)):
        found = slants(shape)
        tops = sorted({z for (s, z), a in found.items()
                       if abs(s - want) < 5e-4 and a > 20.0}, reverse=True)
        check(f"{who}: the slant slope is (HInc-1)/(sliderDistance-1.2)",
              bool(tops), True)
        if tops:
            check(f"{who}: the upper slant meets Y=0 at half the pocket",
                  tops[0], round(holder.slant_top(d), 3), 1e-3)
    # The STEP has the second plane too; the build does not build it yet.
    found = slants(ref)
    tops = sorted({z for (s, z), a in found.items()
                   if abs(s - want) < 5e-4 and a > 20.0}, reverse=True)
    check("STEP: and a second slant plane 2.000 below it",
          len(tops) >= 2 and abs((tops[0] - tops[1]) - holder.SLANT_STEP) < 1e-3,
          True)
    # The rival slider distance differs on the 246 pair and matches on 333.
    if abs(rival - want) > 5e-4:
        check("the OTHER slider distance would give a different slope",
              any(abs(s - rival) < 5e-4 for (s, z) in found), False)

    # The vertical datum, confirmed by where the `Hole outline` sketch lands.
    pz0, pz1 = holder.pocket_z(d)
    check("the pocket is CardHeight - 3.5 tall", round(pz1 - pz0, 3),
          round(d.CardHeight - 3.5, 3), 1e-3)
    check("... starting 2.000 above the base",
          round(pz0 - holder.base_z(d), 3), 2.000, 1e-3)
    outline_lo, outline_hi = pz0 + 2.0, pz1 - (d.calHeightIncrement + 10.0)
    # Both land on real faces: the lattice's bottom rail and its top rail.
    zs = planes(ref, "Z")
    for lbl, z in (("bottom", outline_lo), ("top", outline_hi - 2.0)):
        check(f"STEP has a Z-plane at the outline's {lbl}",
              any(abs(v - z) < 1e-3 for v in zs), True)

    # `Hole for cards`: inset WALL from both faces; the inner two Y-planes
    # move with the holder's own depth.
    want_y = [round(v, 3) for v in
              (-holder.holder_depth(d, first),
               -holder.holder_depth(d, first) + holder.WALL,
               -holder.WALL, 0.0)]
    # Present, not exhaustive: the side slots and the rear lip add more.
    for v in want_y:
        for who, shape in (("STEP", ref), ("build", mine)):
            check(f"{who} has the wall Y-plane at {v}",
                  any(abs(q - v) < 1e-3 for q in planes(shape, "Y")), True)
    # Compartment edges: DIVIDER/2 in from each slot edge, at calSlotwidth.
    edges = []
    for x in holder.compartment_x(d):
        edges += [round(x - (d.calSlotwidth - holder.DIVIDER) / 2, 3),
                  round(x + (d.calSlotwidth - holder.DIVIDER) / 2, 3)]
    for v in edges:
        check(f"STEP has the compartment edge at {v}",
              any(abs(q - v) < 1e-3 for q in planes(ref, "X")), True)

    # The lattice, on 7.0 references: the pre-`stout_lattice` grid.
    grid = holder.window_grid(d)
    check("15 windows per compartment", len(grid),
          holder.window_rows(d) * holder.COLS)
    check("every window is window_w wide",
          sorted({round(x1 - x0, 3) for x0, x1, _, _ in grid}),
          [round(holder.window_w(d), 3)])
    w, h, _ = holder.outline(d)
    check("the mullion is the pitch less the window, not a constant",
          round((w + 2.0) / holder.COLS - holder.window_w(d), 3),
          round((d.calSlotwidth - 6.0 + 2.0) / 5 - 10.0, 3), 1e-3)
    xs, zs = planes(ref, "X"), planes(ref, "Z")
    # NB not x0/x1 (the PART's ends): rebinding them put the side-slot probes
    # onto a window edge and both solids still passed — probe both, always.
    for wx0, wx1, wz0, wz1 in grid[:holder.COLS]:
        for v in (wx0, wx1):
            check(f"STEP has the window edge X = {round(v, 3)}",
                  any(abs(q - v) < 1e-3 for q in xs), True)
    for _, _, wz0, wz1 in grid[::holder.COLS]:
        for v in (wz0, wz1):
            check(f"STEP has the window edge Z = {round(v, 3)}",
                  any(abs(q - v) < 1e-3 for q in zs), True)
    # ... and so does the build.
    mxs, mzs = planes(mine, "X"), planes(mine, "Z")
    for wx0, wx1, wz0, wz1 in grid[:holder.COLS]:
        check(f"build has the window edge X = {round(wx0, 3)}",
              any(abs(q - wx0) < 1e-3 for q in mxs), True)
    for _, _, wz0, wz1 in grid[::holder.COLS]:
        check(f"build has the window edge Z = {round(wz0, 3)}",
              any(abs(q - wz0) < 1e-3 for q in mzs), True)

    # `Finger Cutouts` as a PROFILE at the front wall's mid-depth: `Fillet 1`
    # rounds eat the cylinder, so the STEP's edges read 12.400, not 12.000.
    def top_at(shape, x, y):
        col = Box(0.08, 0.06, 400).moved(Location((x, y, 0)))
        got = shape & col
        if not got or not got.solids():
            return None
        return round(max(q.bounding_box().max.Z for q in got.solids()), 3)

    check("the scallop's lowest point is slant_top - FINGER_R",
          round(holder.slant_top(d) - holder.FINGER_R, 3), 32.250, 1e-3)
    for x in (0.0, 3.0, 6.0, 10.0, 11.0):
        a, b = top_at(ref, x, -0.40), top_at(mine, x, -0.40)
        check(f"the scallop profile at x={x} matches the STEP", a, b)
    # ... and it is centred on each compartment, not just the first.
    for xc in holder.compartment_x(d)[1:]:
        a, b = top_at(ref, xc, -0.40), top_at(mine, xc, -0.40)
        check(f"... and at the compartment on x={round(xc, 1)}", a, b)

    # `Fillet 1` is MODELLED into the cut: OCCT's fillet(..., 0.400) fails on
    # every reference. Sampled ACROSS the wall, where a wrong bead shows.
    check("one torus per scallop, as the reference has",
          sum(1 for f in mine.faces() if f.geom_type == GeomType.TORUS),
          sum(1 for f in ref.faces() if f.geom_type == GeomType.TORUS))
    for y in (-0.05, -0.15, -0.40):
        for x in (0.0, 6.0, 11.0):
            check(f"the rounded scallop at y={y}, x={x} matches the STEP",
                  top_at(ref, x, y), top_at(mine, x, y))
    # The back wall carries NO fillet: the STEP's only torus is at the front.
    check("every torus is on the front wall's mid-depth",
          sorted({round(f.center().Y, 3) for f in ref.faces()
                  if f.geom_type == GeomType.TORUS}),
          [-round(holder.FINGER_FILLET, 3)])

    # The side slots are the box's slider rib plus clearance, so this group
    # is checked against a SECOND part, measured independently.
    check("the slot takes the box's rib with clearance a side",
          round((holder.SLOT_W - box.SLIDER_W) / 2, 3), 0.200, 1e-3)
    check("... and is as deep as the rib stands proud",
          round(holder.END_BLOCK, 3), round(box.SLIDER_PROUD, 3), 1e-3)
    dep = holder.holder_depth(d, first)
    for zc in (-44.0, -20.0, 0.0, 20.0):
        for xc in (x0 + 2.0, x1 - 2.0):
            cell = Box(0.3, dep + 2.0, 0.3).moved(Location((xc, -dep / 2, zc)))
            def bands(shape):
                got = shape & cell
                if not got or not got.solids():
                    return []
                return sorted(tuple(round(v, 3) for v in
                                    (s.bounding_box().min.Y,
                                     s.bounding_box().max.Y))
                              for s in got.solids())
            check(f"the end at x={round(xc, 1)}, z={zc} is slotted like the STEP",
                  bands(mine), bands(ref))

    # The mouth flare is a DELIBERATE DIVERGENCE (`spec/HOLDER.md`, "The mouth
    # of the slot is flared"): asserted from BOTH ends here because at 0.72
    # mm3, 0.004%, the corpus test's tolerance cannot see it.
    z0 = holder.base_z(d)
    cmf = holder.SLOT_MOUTH_CHAMFER

    def slot_w(shape, z):
        """The groove's width at z: the cell is 0.060 tall and the void is
        narrowest at its TOP, so this reads z + 0.030, as the wants say."""
        cell = Box(0.3, dep + 4.0, 0.06).moved(Location((x0 + 2.0, -dep / 2, z)))
        got = shape & cell
        if not got or len(got.solids()) != 2:
            return None
        lo, hi = sorted((s.bounding_box().min.Y, s.bounding_box().max.Y)
                        for s in got.solids())
        return round(hi[0] - lo[1], 3)

    at = 0.070                       # so the reading is taken at base + 0.100
    check("the STEP's slot is SQUARE at the base",
          slot_w(ref, z0 + at), round(holder.SLOT_W, 3), 1e-2)
    check("the build's slot is FLARED at the base",
          slot_w(mine, z0 + at),
          round(holder.SLOT_W + 2 * (cmf - (at + 0.03)), 3), 1e-2)
    check("the build is back to SLOT_W once the flare runs out",
          slot_w(mine, z0 + cmf + at), round(holder.SLOT_W, 3), 1e-2)
    check("... and there the STEP and the build agree again",
          slot_w(mine, z0 + cmf + at), slot_w(ref, z0 + cmf + at), 1e-2)

    # `Rear lip`: everything proud of Y = 0, as COUNT and VOLUME per solid --
    # only the volume catches a wrong chamfer base (12.052 against 12.400).
    def lips(shape):
        bb = shape.bounding_box()
        got = shape & Box(bb.size.X + 4, 20.0, bb.size.Z + 4).moved(
            Location((bb.center().X, 10.0 + 1e-4, bb.center().Z)))
        if not got or not got.solids():
            return []
        return sorted((round(x.bounding_box().min.X, 3), round(x.volume, 3))
                      for x in got.solids())

    a, b = lips(ref), lips(mine)
    check("two lips per compartment", len(b), 2 * p.HorizontalSlots)
    check("... and the same count as the STEP", len(b), len(a))
    check("every lip is where the STEP's is, and the same size", b, a)
    check("the lip reaches LIP_REACH along the slant",
          round(holder.lip_reach_y(d, first)
                * (1 + holder.slant_slope(d, first) ** 2) ** 0.5, 3),
          round(holder.LIP_REACH, 3), 1e-3)
    check("the lip's flat starts LIP_GAP out from the scallop's edge",
          round(holder.FINGER_R + holder.FINGER_FILLET + holder.LIP_GAP, 3),
          15.400, 1e-3)
    # Its section is the band between the TWO slant planes: the lower's use.
    check("the lip sits between the two slant planes",
          round(min(x.bounding_box().min.Z for x in
                    (ref & Box(rb.size.X + 4, 20.0, rb.size.Z + 4).moved(
                        Location((rb.center().X, 10.0 + 1e-4,
                                  rb.center().Z)))).solids()), 3),
          round(holder.slant_top(d) - holder.SLANT_STEP, 3), 1e-3)

    # `Card holder bottom`: the floor sits FLOOR_DROP below the sketch datum,
    # probed either side — an earlier 1.000-spaced probe straddled the step.
    pz0, _ = holder.pocket_z(d)
    for dz, want in ((-0.100, True), (+0.100, False)):
        cell = Box(0.4, 0.4, 0.05).moved(
            Location((0.0, -holder.holder_depth(d, first) / 2,
                      pz0 - holder.FLOOR_DROP + dz)))
        for who, shape in (("STEP", ref), ("build", mine)):
            got = shape & cell
            check(f"{who}: {'material' if want else 'none'} "
                  f"{abs(dz)} {'below' if dz < 0 else 'above'} the dropped floor",
                  bool(got and got.volume > 1e-9), want)

    # `Lip Rest` is an OBLIQUE prism, its near face at constant Y, exactly
    # 2 * calSlotDepth along the slant; only `333` can see a right prism.
    slope = holder.slant_slope(d, first)
    y_start = -2.0 * d.calSlotDepth / (1.0 + slope * slope) ** 0.5
    check("the rest starts 2*calSlotDepth along the slant",
          round(y_start, 3),
          round(-2.0 * d.calSlotDepth * math.cos(math.atan(slope)), 3), 1e-3)
    # It reaches the back wall on the shallow holders and not on the steep.
    yb = -holder.holder_depth(d, first)
    for frac, lbl in ((0.25, "near"), (0.75, "far")):
        yy = yb + holder.WALL * (1.0 - frac)
        zz = (holder.slant_top(d) - holder.SLANT_STEP / 2) + slope * yy
        x = holder.FINGER_R + holder.FINGER_FILLET + holder.LIP_GAP \
            + holder.LIP_LEN / 2
        cell = Box(0.3, 0.05, 0.3).moved(Location((x, yy, zz)))
        a = ref & cell
        b = mine & cell
        check(f"the back wall {lbl} the rest's line agrees with the STEP",
              bool(b and b.volume > 1e-9), bool(a and a.volume > 1e-9))

    # `Bottom Text`: the name in Orbitron Bold, the capacity in Open Sans,
    # checked as INK WIDTH, which identifies both the string and the font.
    name, cap_txt = holder.text_blocks(d, first)
    size = holder.text_size(d, first)
    by_depth = (holder.holder_depth(d, first) - 2.0) / TX.CAP
    capped = size < by_depth - 1e-6

    def ink_blocks(shape):
        """(left, right) spans of engraved ink on the underside: pulled past
        the END BLOCKS (the side slots read as ink too) and split at the
        LARGEST gap, since a block is broken by its own spaces."""
        dep = holder.holder_depth(d, first)
        lo, hi = x0 + holder.END_BLOCK + 1.0, x1 - holder.END_BLOCK - 1.0
        slab = Box(hi - lo, dep - 0.5, 1.0).moved(
            Location(((lo + hi) / 2, -dep / 2, holder.base_z(d) + 0.5)))
        void = slab - shape
        got = [q for q in void.solids() if q.volume > 0.02] if void else []
        if not got:
            return None
        spans = sorted((q.bounding_box().min.X, q.bounding_box().max.X)
                       for q in got)
        gaps = [(spans[i + 1][0] - spans[i][1], i) for i in range(len(spans) - 1)]
        if not gaps:
            return None
        _g, i = max(gaps)
        return ((spans[0][0], spans[i][1]), (spans[i + 1][0], spans[-1][1]))

    if not capped:
        # Where Onshape's own size fits, the build must reproduce it exactly.
        check("the text size is Onshape's (cap = depth - 2.000)",
              round(size, 4), round(by_depth, 4), 1e-4)
        blocks = ink_blocks(ref)
        for (lbl, txt, font), span in zip(
                (("name", name, TX.LOGO_FONT),
                 ("capacity", cap_txt, TX.DETAIL_FONT)), blocks):
            check(f"the STEP's {lbl} block is {txt!r} at this size",
                  round(span[1] - span[0], 2),
                  round(TX.ink(txt, font=font, size=size)[0], 2), 0.05)
    else:
        # The DIVERGENCE: Onshape's size collides, so ours is the lesser rule.
        check("Onshape's size would not fit both blocks",
              round(TX.ink(name, size=by_depth)[0]
                    + TX.ink(cap_txt, font=TX.DETAIL_FONT, size=by_depth)[0], 1)
              > round((x1 - x0) - 2 * (holder.END_BLOCK + holder.TEXT_INSET), 1),
              True)
        check("... so ours is smaller", size < by_depth, True)
        # Proof of the collision without knowing where the blocks divide: at
        # Onshape's size their ink exceeds the STEP's whole engraved span.
        want = (TX.ink(name, size=by_depth)[0]
                + TX.ink(cap_txt, font=TX.DETAIL_FONT, size=by_depth)[0])
        a, b = ink_blocks(ref), ink_blocks(mine)
        check("the STEP's blocks overlap each other",
              round(a[1][1] - a[0][0], 1) < round(want, 1), True)
        mine_ink = (TX.ink(name, size=size)[0]
                    + TX.ink(cap_txt, font=TX.DETAIL_FONT, size=size)[0])
        check("... and the build's do not",
              round(b[1][1] - b[0][0], 1) >= round(mine_ink, 1), True)
        check("the build's ink stays inside its inset",
              b[1][1] <= x1 - holder.END_BLOCK - holder.TEXT_INSET + 0.1, True)
    # Either way the engraving is ENGRAVE deep and no deeper.
    for who, shape in (("STEP", ref), ("build", mine)):
        cell = Box(x1 - x0, holder.holder_depth(d, first), 0.06).moved(
            Location(((x0 + x1) / 2, -holder.holder_depth(d, first) / 2,
                      holder.base_z(d) + holder.ENGRAVE + 0.05)))
        got = shape & cell
        check(f"{who}: material just above the engraving floor",
              bool(got and got.volume > 1.0), True)

    # ORIENTATION: ink width and volume are invariant under a mirror, which is
    # how the name block once shipped as mirror-writing. So ink is compared
    # LUMP BY LUMP in X order; where capped, the period is held to +Y.
    def ink_lumps(shape):
        dep = holder.holder_depth(d, first)
        lo, hi = x0 + holder.END_BLOCK + 1.0, x1 - holder.END_BLOCK - 1.0
        slab = Box(hi - lo, dep + 2.0, 1.0).moved(
            Location(((lo + hi) / 2, -dep / 2, holder.base_z(d) + 0.5)))
        void = slab - shape
        got = [q for q in void.solids() if q.volume > 0.02] if void else []
        return sorted(((q.bounding_box().min.X, q.bounding_box().max.X,
                        q.bounding_box().min.Y, q.bounding_box().max.Y)
                       for q in got), key=lambda b: (round(b[0], 1), b[2]))

    mine_lumps = ink_lumps(mine)
    band_mid = -holder.holder_depth(d, first) / 2
    period = min(mine_lumps, key=lambda b: (b[1] - b[0]) * (b[3] - b[2]))
    check("build: the smallest lump (a period) sits on the +Y side of the band",
          (period[2] + period[3]) / 2 > band_mid, True)
    if not capped:
        ref_lumps = ink_lumps(ref)
        check("the STEP and the build have the same number of ink lumps",
              len(mine_lumps), len(ref_lumps))
        if len(mine_lumps) == len(ref_lumps):
            dx = max(max(abs(a[0] - b[0]), abs(a[1] - b[1]))
                     for a, b in zip(mine_lumps, ref_lumps))
            dy = max(max(abs(a[2] - b[2]), abs(a[3] - b[3]))
                     for a, b in zip(mine_lumps, ref_lumps))
            # X to a twentieth (pen origins are placed, not fitted); Y to
            # holder.py `bottom_text`'s 0.4 -- a mirror is off a cap height.
            check("every lump's X box matches the STEP's", round(dx, 3), 0.0, 0.05)
            check("every lump's Y box matches the STEP's", round(dy, 3), 0.0, 0.4)


# The deep holder at the back: no reference is deep-at-back, so this is
# checked on the built part alone. Its scallop is centred on the raised rear
# top, not on `slant_top`, which put it deeper (measured off the print).
print("\n=== deep holder at the back: the scallop ===")
d8 = D.derive(row_params("Three Expansions", 0))
check("the row puts its deep slot at the back", holder.deep_at_back(d8, True), True)
check("... and its rear top rises above slant_top",
      holder.slant_rear(d8, True) - holder.slant_top(d8) > 1.0, True)
rear8 = holder.build(d8, True, text=False, rear=True)


def _top_at(shape, x, y):
    col = Box(0.08, 0.06, 400).moved(Location((x, y, 0)))
    got = shape & col
    if not got or not got.solids():
        return None
    return round(max(q.bounding_box().max.Z for q in got.solids()), 3)


for xc in holder.compartment_x(d8):
    check(f"the scallop's lowest point at x={round(xc, 1)} is slant_rear - FINGER_R",
          _top_at(rear8, xc, -0.40),
          round(holder.slant_rear(d8, True) - holder.FINGER_R, 3), 1e-3)
check("... which is NOT slant_top - FINGER_R",
      _top_at(rear8, 0.0, -0.40) != round(holder.slant_top(d8) - holder.FINGER_R, 3),
      True)
# Off the scallop: the raised top line, read at the probe's near edge -0.37.
check("beside the scallop the wall top is slant_rear",
      _top_at(rear8, holder.FINGER_R + holder.FINGER_FILLET + 1.0, -0.40),
      round(holder.slant_z(d8, True, -0.37), 3), 1e-3)


if HELD_OUT:
    print("\n=== held out ===")
for name, fn, short, sl in HELD_OUT:
    q = row_params(short, sl)
    e = D.derive(q)
    ref = import_step(str(STEP_DIR / fn)).solids()[0]
    want = holder.holder_depth(e, False)
    got = -ref.bounding_box().min.Y
    print(f"  {name}: depth {got:.3f}, rule says {want:.3f} "
          f"({(got + holder.DEPTH_GAP - 2.4) / e.calCardThickness:.2f} cards "
          f"against CardsPerSlidingSlot {q.CardsPerSlidingSlot})")

print("\nPASS" if not fails else "\nFAIL: " + ", ".join(fails))
sys.exit(1 if fails else 0)
