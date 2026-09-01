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

A hand-exported STEP arrives in ASSEMBLY position, and the transform is not
constant across parts: X is +3.000 and Y is 0 on both references, but Z is
-18.000 on Compile 105 Sl and -16.000 on Dominion 246 Sl. Align on the
bounding box when comparing, as tests/test_pusher.py does, rather than on a
fixed offset.
"""
from build123d import (
    BuildPart, BuildSketch, BuildLine, Polyline, Plane, Location, Locations,
    Box, Mode, Pos, Rot, add, make_face, extrude, fillet, Align, Text,
)

from .. import derive as D
from .. import lock as L
from .. import text as T

CHAMFER = 2.000           # Chamfer 1 / Chamfer 2, 45 degrees, full thickness
ROUND_FIRST = 1.000       # Round step 1
ROUND_STEP = 0.800        # Round top of step
ENGRAVE = 0.400           # text depth


def slider_drops(p, d):
    """The Y drop at each step, leading edge first, summing to
    calPusherTotalDepth.

    UNVERIFIED where a first-riser override exists: which of the R steps takes
    calFirstSliderDistance is not determinable from the one STEP we have, which
    has no override. The leading edge is assumed, because that is the step
    Onshape rounds separately (`First Step` / `Round step 1` is the lowest one,
    at x = calHeightIncrement). Confirm against a Dominion 246 or 472 export.
    """
    drops = [d.calSliderDistance] * p.RisingSliders
    if p.isFirstSlidingSlotOverride:
        drops[0] = d.calFirstSliderDistance
    return drops


def profile_points(p, d, notch=True):
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
    y = -W + CHAMFER
    for k, drop in enumerate(slider_drops(p, d), start=1):
        y_top = -(W - sum(slider_drops(p, d)[:k]))
        if k == p.RisingSliders:
            y_top = -CHAMFER                    # Chamfer 2 clips the last riser
        pts.append((k * inc, y_top))
        if k < p.RisingSliders:
            pts.append(((k + 1) * inc, y_top))
    pts += [(H - CHAMFER, 0.0), (0.0, 0.0)]
    return pts


def build(p, text=True):
    """`p` is a params.Primary. Returns the Pusher as a build123d Part."""
    d = D.derive(p)
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
        for txt, size, x0, baseline in T.logo_lines(p, d):
            glyphs = Text(txt, font_size=size, font_path=T.LOGO_FONT,
                          align=(Align.MIN, Align.MIN))
            cuts.append(extrude(Pos(x0, baseline, L.PLATE - ENGRAVE) * glyphs,
                                amount=ENGRAVE))
        # The detail line reads down the depth, so it is turned -90 degrees:
        # that maps +X to -Y and +Y to +X, leaving the baseline running along
        # -Y with the glyphs standing up +X. Align.MIN then Rot puts the ink's
        # min X and max Y at the origin, so the anchor is a plain translation.
        txt, size, bx, y0 = T.detail_placement(p, d)
        glyphs = Rot(0, 0, -90) * Text(txt, font_size=size,
                                       font_path=T.DETAIL_FONT,
                                       align=(Align.MIN, Align.MIN))
        cuts.append(extrude(Pos(bx, y0, L.PLATE - ENGRAVE) * glyphs,
                            amount=ENGRAVE))

    with BuildPart() as pusher:
        with BuildSketch(Plane.XY) as sk:
            with BuildLine():
                Polyline(*profile_points(p, d, notch=L.has_notch(s)))
            make_face()
        extrude(amount=L.PLATE)

        # Round top of step / Round step 1 — the riser faces are filleted on
        # both Z edges, r=1.000 on the step nearest the leading edge and
        # r=0.800 on the replicated ones. This is why the riser faces measure
        # (PLATE - 2r) tall rather than PLATE.
        for k in range(1, p.RisingSliders + 1):
            r = ROUND_FIRST if k == 1 else ROUND_STEP
            edges = [e for e in pusher.edges()
                     if abs(e.center().X - k * inc) < 1e-6
                     and abs(e.length) > r * 2
                     and min(abs(e.center().Z), abs(e.center().Z - L.PLATE)) < 1e-6]
            if edges:
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
