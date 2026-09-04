#!/usr/bin/env python3
"""Check cad/parts/holder.py against the hand-exported Onshape STEPs.

    .venv/bin/python tests/test_holder.py

Ten references in `spec/reference/`, listed in `spec/HOLDER.md`, and all ten
are asserted against. Between them they cover every slot width (63 to 70),
every compartment count (2 to 5), all four games, both sleevings and both
slider distances, so a rule that survives here is general rather than
Dominion's.

The 246 pair is what makes this worth doing: it is ONE configuration exported
twice, as `Holder` and as `FirstHolder`, so the two differ only in what `first`
changes, and its `calSliderDistance` and `calFirstSliderDistance` differ by more
than a factor of two. Every reading below that involves a slider distance is
therefore asserted against a case that would fail if the wrong one were used.

Every feature in the tree is asserted here: the envelope (width, depth, the
base), the `Top slant angle` plane pair and its slope, the vertical datum,
`Hole for cards`, the lattice, the finger scallops and their modelled fillet,
the side slots, the rear lips, the dropped floor, the lip rests and the engraved
bottom text — the last both where it reproduces Onshape and where it
deliberately does not. `tests/test_holder_corpus.py` is the other half: the
written 3MFs against the 50 cached components.
"""
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from build123d import import_step, Box, Location, GeomType   # noqa: E402
from cad import params, derive as D, text as TX      # noqa: E402
from cad.parts import holder, box                    # noqa: E402

STEP_DIR = ROOT / "spec" / "reference"
_ROWS = list(params.load_rows(ROOT / "automation" / "parts.csv"))


def row_params(short_name, sleeved):
    """The Primary for a parts.csv row, by its Short name.

    Read from the CSV rather than hand-written: Compile rows leave `Front
    capacity` blank, and transcribing nine positional ints per reference is a
    good way to test the wrong parameters against the right STEP.
    """
    for row in _ROWS:
        if row.get("Short name") == short_name:
            return params.from_row(row, sleeved)
    raise KeyError(short_name)


P246 = params.Primary(3, 2, 40, 12, 1, 30, 1, 0, "Dominion")
P333 = params.Primary(3, 9, 21, 10, 0, 10, 1, 0, "Dominion")
PINN_SL = params.Primary(4, 5, 10, 10, 0, 10, 1, 0, "Innovation")
PINN_UN = params.Primary(4, 5, 10, 10, 0, 10, 0, 0, "Innovation")
REFS = [
    ("Dominion 246 Sl", "Holder S2.40.12-30.45-Sl.step", P246, False),
    # The same row's first riser: same box, deeper holder. calFirstSliderDistance
    # 20.400 against calSliderDistance 9.600.
    ("Dominion 246 Sl (first)", "FirstHolder S2.40.12-30.45-Sl.step", P246, True),
    # Nine risers, the catalogue's shallowest rise, and the cascade whose Box
    # and Pusher are already references.
    ("Dominion 333 Sl", "Holder S9.21.10.62-Sl.step", P333, False),
    # Innovation: a SPANNING game, FOUR compartments, and two slot widths that
    # are neither Dominion's. Every reading above was confirmed at
    # calSlotwidth 65.000 only until these arrived.
    ("Innovation M5.10.10 Sl", "Holder M5.10.10.45-Sl.step", PINN_SL, False),
    ("Innovation M5.10.10 Un", "Holder M5.10.10.32-Un.step", PINN_UN, False),
    # The four that close the parameter space. Between them these add every
    # remaining slot width (63, 68, 70), both remaining compartment counts
    # (2 and 5), and the two games that had no reference at all.
    ("Innovation XS5.15.10 Sl", "Holder XS5.15.10.45-Sl.step",
     row_params("Single Mini", 1), False),
    ("Compile S4.7.7 Sl", "Holder S4.7.7.32-Sl.step",
     row_params("105 Card", 1), False),
    ("FCM S4.18.12 Un", "Holder S4.18.12.32-Un.step",
     row_params("198 Card", 0), False),
    # `210 Card`, both sleevings, both RE-EXPORTED. The first exports of this
    # row were 12 cards deep where the row says 7, and were the only things in
    # the catalogue that did not satisfy the depth rule; the re-exports measure
    # 7.600 and 4.800, which is the rule exactly under each card thickness. So
    # they were mis-configured exports, not a rule -- and the `105 Card`
    # reference, which had already refused a `COMPILE_DEPTH_CARDS` override by
    # satisfying the plain rule, was right to. FIVE compartments, the widest
    # holders in the catalogue, and the unsleeved one is the only reference at
    # `calSlotwidth 68.000`.
    ("Compile L5.7.7 Sl", "Holder L5.7.7.45-Sl.step",
     row_params("210 Card", 1), False),
    ("Compile L5.7.7 Un", "Holder L5.7.7.20-Un.step",
     row_params("210 Card", 0), False),
]

# Nothing is held out any more. The list stays because the mechanism is worth
# keeping: a reference that fails a rule every other reference satisfies is a
# question about that reference, and parking it here -- rather than fitting the
# rule to it -- is what got both `210` exports re-cut. See spec/HOLDER.md.
HELD_OUT = []
fails = []


def check(label, got, want, tol=1e-6):
    ok = abs(got - want) <= tol if isinstance(want, float) else got == want
    print(f"  {'ok  ' if ok else 'FAIL'} {label:54s} {got!r:>24} vs {want!r}")
    if not ok:
        fails.append(label)


def planes(shape, axis):
    """Offsets of every planar face whose normal is along `axis`."""
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

    Aggregated by the PLANE, not by the face: Onshape leaves the slant split
    into several faces, and on the 246 pair no single piece is large enough to
    find by area alone. Reading the plane off the normals is also what keeps
    this honest — measuring the slope as a drop between wall tops picks up
    whichever of the two parallel planes that wall happens to reach, which is
    not the same one on every holder.
    """
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
        # A missing reference is a FAILURE, not a skip: every STEP in
        # spec/reference is checked in, and a suite that turns green
        # when one goes missing is not a suite.
        print(f"  FAIL — reference {path.name} not present")
        fails.append(f"{name}: reference {path.name} missing")
        continue
    ref = import_step(str(path)).solids()[0]
    d = D.derive(p)
    mine = holder.build(p, first)
    rb, mb = ref.bounding_box(), mine.bounding_box()
    sd = holder.slider_distance(p, d, first)

    # --- the envelope ------------------------------------------------------
    # Width is calSlotwidth * n + 9.800 and has nothing to do with the depth;
    # the two 246 holders share it and differ in everything else.
    check("width = calSlotwidth * n + 9.800", round(rb.size.X, 3),
          round(holder.holder_width(p, d), 3), 1e-3)
    check("... and the build agrees", round(mb.size.X, 3),
          round(rb.size.X, 3), 1e-3)
    # X is NOT symmetric: the origin is the first compartment's centre.
    x0, x1 = holder.x_span(p, d)
    check("X starts at -(calSlotwidth/2 + 4.900)", round(rb.min.X, 3),
          round(x0, 3), 1e-3)
    check("X ends at the last compartment + the same", round(rb.max.X, 3),
          round(x1, 3), 1e-3)

    # Depth takes the holder's OWN slider distance. 9.200 / 20.000 / 8.000.
    # Measured as the BACK FACE, not the bounding box: the rear lip's tab stands
    # proud in +Y (1.026 / 1.655 / 1.342 on the three), so the STEP's bbox is
    # wider than the body and would compare against nothing meaningful.
    check("the back face is at -(sliderDistance - 0.400)", round(rb.min.Y, 3),
          round(-holder.holder_depth(p, d, first), 3), 1e-3)
    check("... and the build agrees", round(mb.min.Y, 3),
          round(rb.min.Y, 3), 1e-3)
    # Y = 0 is the REAR face — the `Rear lip` tabs stand proud of it — so the
    # bounding box reaches past it by exactly the lip's reach.
    check("the build stands as proud of Y=0 as the STEP does",
          round(mb.max.Y, 3), round(rb.max.Y, 3), 1e-3)

    # The base is (CardHeight - 1.5)/2 below the origin on every holder.
    check("base = -(CardHeight - 1.5)/2", round(rb.min.Z, 3),
          round(holder.base_z(d), 3), 1e-3)
    check("... and the build agrees", round(mb.min.Z, 3),
          round(rb.min.Z, 3), 1e-3)

    # --- `Top slant angle` --------------------------------------------------
    # Two PARALLEL planes 2.000 apart, both meeting Y = 0 at the same Z on every
    # reference whatever the slope. Asserted on the STEP and on the build.
    want = round(holder.slant_slope(p, d, first), 4)
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
    # The rival slider distance is a different number on the 246 pair, and the
    # same one on 333 — which is exactly why the pair had to be exported.
    if abs(rival - want) > 5e-4:
        check("the OTHER slider distance would give a different slope",
              any(abs(s - rival) < 5e-4 for (s, z) in found), False)

    # --- the vertical datum -------------------------------------------------
    # Confirmed independently by where the `Hole outline` sketch lands: inset
    # 2.000 from the pocket's bottom and calHeightIncrement + 10 from its top.
    pz0, pz1 = holder.pocket_z(d)
    check("the pocket is CardHeight - 3.5 tall", round(pz1 - pz0, 3),
          round(d.CardHeight - 3.5, 3), 1e-3)
    check("... starting 2.000 above the base",
          round(pz0 - holder.base_z(d), 3), 2.000, 1e-3)
    outline_lo, outline_hi = pz0 + 2.0, pz1 - (d.calHeightIncrement + 10.0)
    # Those two land on real faces of the STEP: the lattice's bottom rail sits
    # on the first and its top rail on the second.
    zs = planes(ref, "Z")
    for lbl, z in (("bottom", outline_lo), ("top", outline_hi - 2.0)):
        check(f"STEP has a Z-plane at the outline's {lbl}",
              any(abs(v - z) < 1e-3 for v in zs), True)

    # --- `Hole for cards` ---------------------------------------------------
    # The walls are the only material left at a lattice rail's height, so the
    # pocket is inset WALL from both faces. Four Y-planes, and the two inner
    # ones move with the holder's own depth.
    want_y = [round(v, 3) for v in
              (-holder.holder_depth(p, d, first),
               -holder.holder_depth(p, d, first) + holder.WALL,
               -holder.WALL, 0.0)]
    # Present, not exhaustive: the side slots add two more Y-planes of their own,
    # and the rear lip will add more again.
    for v in want_y:
        for who, shape in (("STEP", ref), ("build", mine)):
            check(f"{who} has the wall Y-plane at {v}",
                  any(abs(q - v) < 1e-3 for q in planes(shape, "Y")), True)
    # The compartment edges: DIVIDER/2 in from each slot edge, patterned at
    # calSlotwidth. Every one of them is a face of the STEP too.
    edges = []
    for x in holder.compartment_x(p, d):
        edges += [round(x - (d.calSlotwidth - holder.DIVIDER) / 2, 3),
                  round(x + (d.calSlotwidth - holder.DIVIDER) / 2, 3)]
    for v in edges:
        check(f"STEP has the compartment edge at {v}",
              any(abs(q - v) < 1e-3 for q in planes(ref, "X")), True)

    # --- the lattice --------------------------------------------------------
    # Three window rows of (H-6)/3 between 2.000 rails, five columns of a FIXED
    # 10.000 at (W+2)/5 pitch. Every window edge is a face of the STEP too.
    grid = holder.window_grid(p, d)
    check("15 windows per compartment", len(grid), holder.ROWS * holder.COLS)
    check("every window is LIP_LENGTH wide",
          sorted({round(x1 - x0, 3) for x0, x1, _, _ in grid}),
          [round(holder.LIP_LENGTH, 3)])
    w, h, _ = holder.outline(p, d)
    check("the mullion is the pitch less LIP_LENGTH, not a constant",
          round((w + 2.0) / holder.COLS - holder.LIP_LENGTH, 3),
          round((d.calSlotwidth - 6.0 + 2.0) / 5 - 10.0, 3), 1e-3)
    xs, zs = planes(ref, "X"), planes(ref, "Z")
    # NB not x0/x1: those are the PART's ends, used again further down, and
    # rebinding them here made the side-slot probes sample a window edge. They
    # still passed, because both solids were probed at the same wrong place —
    # which is the whole reason this file probes the STEP and the build
    # together and never the build alone.
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

    # --- `Finger Cutouts` ---------------------------------------------------
    # Compared as a PROFILE, sampled at the front wall's mid-depth, which is the
    # only place the true circle survives: `Fillet 1` puts 0.400 on each face of
    # an 0.800 wall, so the two fillets meet and consume the cylindrical face
    # entirely — every scallop surface in the STEP is torus, and the circular
    # edges report 12.400 rather than the real 12.000. Same trap as the Box's
    # thumb. Sampling the STEP and the build the same way sidesteps it.
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
    for xc in holder.compartment_x(p, d)[1:]:
        a, b = top_at(ref, xc, -0.40), top_at(mine, xc, -0.40)
        check(f"... and at the compartment on x={round(xc, 1)}", a, b)

    # `Fillet 1` is MODELLED into the cut, because OCCT will not compute it:
    # the wall is 2 * FINGER_FILLET thick so the rounds from its two faces meet,
    # and fillet(..., 0.400) fails on every reference. Checked by sampling ACROSS
    # the wall — at the face, part way in, and at mid-wall — which is where a
    # wrong bead would show up and a bounding box would not.
    check("one torus per scallop, as the reference has",
          sum(1 for f in mine.faces() if f.geom_type == GeomType.TORUS),
          sum(1 for f in ref.faces() if f.geom_type == GeomType.TORUS))
    for y in (-0.05, -0.15, -0.40):
        for x in (0.0, 6.0, 11.0):
            check(f"the rounded scallop at y={y}, x={x} matches the STEP",
                  top_at(ref, x, y), top_at(mine, x, y))
    # The back wall carries NO fillet: the reference's only torus is at the
    # front wall's mid-depth, so the back edge must stay sharp.
    check("every torus is on the front wall's mid-depth",
          sorted({round(f.center().Y, 3) for f in ref.faces()
                  if f.geom_type == GeomType.TORUS}),
          [-round(holder.FINGER_FILLET, 3)])

    # --- the side slots -----------------------------------------------------
    # SLOT_W wide, centred on mid-depth, END_BLOCK deep from each end. This is
    # the one group that can be checked against a SECOND part: it is the box's
    # slider rib plus clearance, and both parts were measured independently.
    check("the slot takes the box's rib with clearance a side",
          round((holder.SLOT_W - box.SLIDER_W) / 2, 3), 0.200, 1e-3)
    check("... and is as deep as the rib stands proud",
          round(holder.END_BLOCK, 3), round(box.SLIDER_PROUD, 3), 1e-3)
    dep = holder.holder_depth(p, d, first)
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

    # --- `Rear lip` ---------------------------------------------------------
    # Everything standing proud of Y = 0 is lip. Compared as COUNT and VOLUME
    # per solid, which catches the chamfer: the base is always LIP_CHAMFER out,
    # and where the lip is shorter in Y than that the chamfer plane simply runs
    # out of lip rather than starting closer in. Getting that backwards leaves
    # the base 12.052 wide instead of 12.400 and shows up only in the volume —
    # the bounding box, the reach and the tip width are all still right.
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
          round(holder.lip_reach_y(p, d, first)
                * (1 + holder.slant_slope(p, d, first) ** 2) ** 0.5, 3),
          round(holder.LIP_REACH, 3), 1e-3)
    check("the lip's flat starts LIP_GAP out from the scallop's edge",
          round(holder.FINGER_R + holder.FINGER_FILLET + holder.LIP_GAP, 3),
          15.400, 1e-3)
    # Its section is the band between the TWO slant planes — which is what the
    # lower one, otherwise unused, is for.
    check("the lip sits between the two slant planes",
          round(min(x.bounding_box().min.Z for x in
                    (ref & Box(rb.size.X + 4, 20.0, rb.size.Z + 4).moved(
                        Location((rb.center().X, 10.0 + 1e-4,
                                  rb.center().Z)))).solids()), 3),
          round(holder.slant_top(d) - holder.SLANT_STEP, 3), 1e-3)

    # --- `Card holder bottom` and `Lip Rest` --------------------------------
    # The floor sits FLOOR_DROP below the sketch datum. Probed either side of
    # it, which is the check an earlier 1.000-spaced probe was too coarse to
    # make: it straddled the step and reported the feature as absent.
    pz0, _ = holder.pocket_z(d)
    for dz, want in ((-0.100, True), (+0.100, False)):
        cell = Box(0.4, 0.4, 0.05).moved(
            Location((0.0, -holder.holder_depth(p, d, first) / 2,
                      pz0 - holder.FLOOR_DROP + dz)))
        for who, shape in (("STEP", ref), ("build", mine)):
            got = shape & cell
            check(f"{who}: {'material' if want else 'none'} "
                  f"{abs(dz)} {'below' if dz < 0 else 'above'} the dropped floor",
                  bool(got and got.volume > 1e-9), want)

    # The rest is an OBLIQUE prism: its cross-sections are upright, so its near
    # face is at constant Y, exactly `2 * calSlotDepth` along the slant. A right
    # prism puts that face 0.769 further forward and 0.6 low, which `333` — the
    # only reference whose cut starts INSIDE the back wall — can see.
    slope = holder.slant_slope(p, d, first)
    y_start = -2.0 * d.calSlotDepth / (1.0 + slope * slope) ** 0.5
    check("the rest starts 2*calSlotDepth along the slant",
          round(y_start, 3),
          round(-2.0 * d.calSlotDepth * math.cos(math.atan(slope)), 3), 1e-3)
    # It reaches the back wall on the shallow holders and not on the steep ones,
    # and either way the build must agree with the STEP about which.
    yb = -holder.holder_depth(p, d, first)
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

    # --- `Bottom Text` ------------------------------------------------------
    # Two blocks in TWO faces, as the Pusher has: the name in Orbitron Bold and
    # the capacity in Open Sans Bold. Checked as INK WIDTH against the STEP's
    # own engraving, which is what identifies both the string and the font — the
    # capacity block is 42.456 wide on `333`, which is `10 Sleeved` in Open Sans
    # (42.472) and not in Orbitron (51.342).
    name, cap_txt = holder.text_blocks(p, d, first)
    size = holder.text_size(p, d, first)
    by_depth = (holder.holder_depth(p, d, first) - 2.0) / TX.CAP
    capped = size < by_depth - 1e-6

    def ink_blocks(shape):
        """(left, right) spans of engraved ink on the underside.

        The slab is pulled in past the END BLOCKS, because the side slots are
        voids too and would read as ink. The two blocks are then separated at
        the LARGEST gap: a block is itself broken by its spaces, so a fixed
        threshold splits it in the wrong place.
        """
        dep = holder.holder_depth(p, d, first)
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
        # The DIVERGENCE. Onshape's size makes the two blocks collide; ours is
        # the lesser of its rule and one that fits. Asserted from BOTH ends.
        check("Onshape's size would not fit both blocks",
              round(TX.ink(name, size=by_depth)[0]
                    + TX.ink(cap_txt, font=TX.DETAIL_FONT, size=by_depth)[0], 1)
              > round((x1 - x0) - 2 * (holder.END_BLOCK + holder.TEXT_INSET), 1),
              True)
        check("... so ours is smaller", size < by_depth, True)
        # Proof of the collision, without needing to know where the two blocks
        # were meant to divide: at Onshape's size their ink comes to more than
        # the STEP's total engraved SPAN, so they must be overlapping. The
        # build's span, by construction, is at least their sum.
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
        cell = Box(x1 - x0, holder.holder_depth(p, d, first), 0.06).moved(
            Location(((x0 + x1) / 2, -holder.holder_depth(p, d, first) / 2,
                      holder.base_z(d) + holder.ENGRAVE + 0.05)))
        got = shape & cell
        check(f"{who}: material just above the engraving floor",
              bool(got and got.volume > 1.0), True)

    # --- the engraving's ORIENTATION ------------------------------------
    # Ink width and volume are both invariant under a mirror, which is how
    # the name block shipped as mirror-writing for a while: built glyph-up
    # toward +Y on an underside that reads from -Z. So the ink is compared
    # LUMP BY LUMP — one connected piece of ink at a time, in X order, each
    # lump's box against the STEP's. A block mirrored in Y moves its period
    # by a cap height; one mirrored in X reverses the lump order. Only where
    # the size is Onshape's can the lumps correspond; where it is capped the
    # build's own period is held to the +Y side of the band, which is what
    # "reads the right way round from below" means in this frame.
    def ink_lumps(shape):
        dep = holder.holder_depth(p, d, first)
        lo, hi = x0 + holder.END_BLOCK + 1.0, x1 - holder.END_BLOCK - 1.0
        slab = Box(hi - lo, dep + 2.0, 1.0).moved(
            Location(((lo + hi) / 2, -dep / 2, holder.base_z(d) + 0.5)))
        void = slab - shape
        got = [q for q in void.solids() if q.volume > 0.02] if void else []
        return sorted(((q.bounding_box().min.X, q.bounding_box().max.X,
                        q.bounding_box().min.Y, q.bounding_box().max.Y)
                       for q in got), key=lambda b: (round(b[0], 1), b[2]))

    mine_lumps = ink_lumps(mine)
    band_mid = -holder.holder_depth(p, d, first) / 2
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
            # X to a twentieth: the pen origins are placed, not fitted. Y to
            # the 0.4 the centring rule is known to sit within (holder.py,
            # `bottom_text`) — a mirror is off by a whole cap height.
            check("every lump's X box matches the STEP's", round(dx, 3), 0.0, 0.05)
            check("every lump's Y box matches the STEP's", round(dy, 3), 0.0, 0.4)


if HELD_OUT:
    print("\n=== held out ===")
for name, fn, short, sl in HELD_OUT:
    q = row_params(short, sl)
    e = D.derive(q)
    ref = import_step(str(STEP_DIR / fn)).solids()[0]
    want = holder.holder_depth(q, e, False)
    got = -ref.bounding_box().min.Y
    print(f"  {name}: depth {got:.3f}, rule says {want:.3f} "
          f"({(got + holder.DEPTH_GAP - 2.4) / e.calCardThickness:.2f} cards "
          f"against CardsPerSlidingSlot {q.CardsPerSlidingSlot})")

print("\nPASS" if not fails else "\nFAIL: " + ", ".join(fails))
sys.exit(1 if fails else 0)
