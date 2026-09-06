"""The Pusher.

A staircase plate that hangs in the box slot and locks into the lid socket.
Measured from a hand-exported STEP in `spec/PUSHER.md`; the Onshape feature
tree it mirrors is, in order: Triangle shape / Single step / Round top of step /
Replicate steps / First Step / Round step 1 / Centre Notch / Tabs / text /
Chamfer 1 / Chamfer 2.

Local frame (the part studio's, not the assembly's):
    X   rise, 0 at the leading edge, up to calPusherTotalHeight
    Y   depth, 0 at the front edge, down to -calPusherTotalDepth
    Z   thickness, 0 at the back face, PLATE at the front, tabs stand proud

A hand-exported STEP, and a component 3MF, arrive in ASSEMBLY position:
`assembly_offset` below is that transform. Tests still align on the bounding
box, as tests/test_pusher.py does, because that stays right whatever the
placement turns out to be.
"""
from build123d import (BuildPart, BuildSketch, BuildLine, Polyline, Plane,
                       Locations, Box, Mode, Pos, Rot, add, make_face, extrude,
                       fillet, Align, Text)

from .. import lock as L
from .. import text as T

# Assembly position. A component 3MF (and a hand-exported STEP) arrives from
# Onshape placed by the `Lay down` / `Fix to lid` mates, and all 32 pushers on
# disk sit at exactly the same rule: X shifted by ASSEMBLY_X, Y unchanged (the
# part already runs 0 .. -calPusherTotalDepth), and Z at -calHeightIncrement.
# So the Z that spec/PUSHER.md recorded as "not constant" — -18.000 on Compile
# 105, -16.000 on Dominion 246 — is not arbitrary; those are their rises.
ASSEMBLY_X = 3.000        # constant on all 32; equals PusherThickness

CHAMFER = 2.000           # Chamfer 1 / Chamfer 2, 45 degrees, full thickness
ROUND_FIRST = 1.000       # Round step 1
ROUND_STEP = 0.800        # Round top of step
ENGRAVE = 0.400           # text depth


def slider_drops(d):
    """The Y drop at each step, leading edge first, summing to
    calPusherTotalDepth.

    The override goes on the LEADING edge — settled by the Dominion 246 STEP,
    whose outline drops 20.400 (calFirstSliderDistance) at the first step and
    9.600 (calSliderDistance) at the second. That is also the step Onshape
    rounds separately (`First Step` / `Round step 1`, at x = calHeightIncrement),
    and its riser face measures PLATE - 2r for r = 1.000 rather than 0.800.
    """
    drops = [d.calSliderDistance] * d.RisingSliders
    if d.isFirstSlidingSlotOverride:
        drops[0] = d.calFirstSliderDistance
    return drops


def profile_points(d, notch=True):
    """The staircase outline, in order, starting at the leading edge.

    `notch` mirrors the CAD's suppression formula on `Remove Centre Notch`:
    C1 and C2 have no room for a 5.400 notch between tabs 6.20 / 10.20 apart
    (the lands would be -1.50 and 0.50), so those six sizes lock by tabs alone
    and their lids lose the key rib.
    """
    H, W = d.calPusherTotalHeight, d.calPusherTotalDepth
    inc = d.calHeightIncrement
    yc = -W / 2
    pts = [(0.0, 0.0)]
    if notch:
        pts += [(0.0, yc + L.NOTCH_W / 2),
                (L.NOTCH_D, yc + L.NOTCH_W / 2), (L.NOTCH_D, yc - L.NOTCH_W / 2),
                (0.0, yc - L.NOTCH_W / 2)]
    pts += [(0.0, -W),
           (inc - CHAMFER, -W), (inc, -W + CHAMFER)]
    drops = slider_drops(d)
    for k in range(1, len(drops) + 1):
        y_top = -(W - sum(drops[:k]))
        if k == d.RisingSliders:
            y_top = -CHAMFER                    # Chamfer 2 clips the last riser
        pts.append((k * inc, y_top))
        if k < d.RisingSliders:
            pts.append(((k + 1) * inc, y_top))
    pts += [(H - CHAMFER, 0.0), (0.0, 0.0)]
    return pts


def assembly_offset(d):
    """Part frame -> the assembly position an Onshape export arrives in."""
    return (ASSEMBLY_X, 0.0, -d.calHeightIncrement)


def build(d, text=True):
    """The Pusher as a build123d Part, from a `derive.Derived`."""
    if L.lock_generation(d.Version) != L.GENERATION:
        raise ValueError(
            f"cad/ builds the {L.GENERATION} lock only, so a Primary at "
            f"{d.Version!r} would get {L.GENERATION} tabs under a "
            f"'CC {d.Version}' stamp — the mixed-generation part parts.csv's "
            f"Build column exists to prevent. Leave the 6.6 pushers to "
            f"individual/ until their cascades migrate. (A release that shares "
            f"the 7.0 lock is admitted in lock.SAME_LOCK; what else differs "
            f"between releases is cad/revisions.py.)")
    W = d.calPusherTotalDepth
    inc = d.calHeightIncrement
    yc = -W / 2
    name, s = L.lock_class(W)
    if not L.check_edge(W, s):
        raise ValueError(f"{name} leaves under {L.EDGE_MIN} mm of plate "
                         f"outboard of a tab at depth {W}")

    # Text objects are only valid inside a BuildSketch, so the engraving
    # solids are made first, in algebra mode, and subtracted below.
    cuts = []
    if text:
        for txt, size, x0, baseline in T.logo_lines(d):
            glyphs = Text(txt, font_size=size, font_path=T.LOGO_FONT,
                          align=(Align.MIN, Align.MIN))
            cuts.append(extrude(Pos(x0, baseline, L.PLATE - ENGRAVE) * glyphs,
                                amount=ENGRAVE))
        # The detail line reads down the depth, so it is turned -90 degrees:
        # that maps +X to -Y and +Y to +X, leaving the baseline running along
        # -Y with the glyphs standing up +X. Align.MIN then Rot puts the ink's
        # min X and max Y at the origin, so the anchor is a plain translation.
        txt, size, bx, y0 = T.detail_placement(d)
        glyphs = Rot(0, 0, -90) * Text(txt, font_size=size,
                                       font_path=T.DETAIL_FONT,
                                       align=(Align.MIN, Align.MIN))
        cuts.append(extrude(Pos(bx, y0, L.PLATE - ENGRAVE) * glyphs,
                            amount=ENGRAVE))

    with BuildPart() as pusher:
        with BuildSketch(Plane.XY):
            with BuildLine():
                Polyline(*profile_points(d, notch=L.has_notch(s)))
            make_face()
        extrude(amount=L.PLATE)

        # Round top of step / Round step 1 — the riser faces are filleted on
        # both Z edges, r=1.000 on the step nearest the leading edge and
        # r=0.800 on the replicated ones. This is why the riser faces measure
        # (PLATE - 2r) tall rather than PLATE.
        for k in range(1, d.RisingSliders + 1):
            r = ROUND_FIRST if k == 1 else ROUND_STEP
            edges = [e for e in pusher.edges()
                     if abs(e.center().X - k * inc) < 1e-6
                     and abs(e.length) > r * 2
                     and min(abs(e.center().Z), abs(e.center().Z - L.PLATE)) < 1e-6]
            if len(edges) != 2:
                raise ValueError(f"riser {k}: expected its two Z edges to round, "
                                 f"found {len(edges)}")
            fillet(edges, radius=r)

        # Tabs — flush with the leading edge, standing TAB_PROUD off the front
        # face only, at the centreline +- s.
        with Locations(*[(0, yc + sign * s, L.PLATE) for sign in (+1, -1)]):
            Box(L.TAB_L, L.TAB_W, L.TAB_PROUD,
                align=(Align.MIN, Align.CENTER, Align.MIN), mode=Mode.ADD)

        # The engraving: two Orbitron lines along the rise and the Open Sans
        # detail line down the depth.
        for cut in cuts:
            add(cut, mode=Mode.SUBTRACT)
    return pusher.part
