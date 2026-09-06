"""The Topper.

The cap that closes the top of a card slot. **Innovation only.** Six per
parameter set — one per expansion plus a `Blank` — and they are one shape with
different lettering, not six designs.

Measured in `spec/TOPPER.md`. The Onshape feature tree it mirrors is, in order:

    Import Holder   Leftmost Pusher Pos / Top slant angle / Mid plane /
                    Middle / GuideToTabs
    #TopperHeight
    Main topper     TriangleMatch / CardHeight / Inner Hole Outline /
                    Remove Inner Hole / Divider / Divider
    Remove most of front / Remove front section / Fillet front holes /
    Remove all front sections / More Dividers
    Tab-to-attach   Holder tab x3
    Room for Lips / Remove Lip Room / Fillet Lip Room / Other side /
    Linear pattern 1 / Upside Down / Top and front edges
    Expansion Name  (19 features — the mark and the name)

Local frame — the part studio's, which is also the assembly's:

    X   0 at the CENTRE OF THE FIRST SLOT, exactly as the Holder's is, so the
        part runs -calSlotwidth/2 .. calSlotwidth*(HorizontalSlots - 0.5)
    Y   NEGATIVE throughout: the front face at -depth and the rear at -2*depth,
        so the topper sits one full depth back from the origin
    Z   the base at Z_BASE, a measured constant, and the tabs' tops
        45.200 above it

## It does NOT import the Holder

Onshape's first feature is `Import Holder`, and every derived feature hung off
it is already a named function here — see `spec/TOPPER.md` for the table. The
one that matters is `TriangleMatch`, which extrudes the Holder's own
`Top slant angle` face: the measured slope of this part's section is
`holder.slant_slope` to six decimal places, on two different parameter sets.

Binding to the rule rather than to a body is the better dependency, and it is
the whole point of the rebuild. What it costs is the mate Onshape got for free,
so `tests/test_topper.py` asserts the tabs against `holder` independently.

The BLANK is complete: `build()` reproduces all three rolled-back exports and
the unfilleted one with zero symmetric difference in both directions, on two
parameter sets, and the filleted `Unseen` body holds nothing it lacks.

The `Expansion Name` group — the mark and the expansion's name, 19 features —
is written too, for all five labelled expansions (`MARKS`); `spec/TOPPER.md`
records the rules behind it.
"""
import math

from build123d import (
    Align, Box, BuildLine, BuildPart, BuildSketch, Circle, Line, Location,
    Mode, Plane, Polyline, Pos, Text, ThreePointArc, chamfer, extrude, fillet,
    make_face,
)

from .. import derive as D
from .. import tables as TB
from .. import text as TX
from . import holder as H

# Where the base sits in assembly. Constant on all 48 cached components and on
# every reference — and DERIVED since 2026-09-04: there is no mate (Allan); the
# topper RESTS on the holder, logo up, diagonal meeting diagonal, its fins in
# the holder's lip rooms. So its base is the holder's slant top plus its own
# rear thickness, `z_base` below, and that is `48.450` on every Innovation
# parameter set because all of them have five risers (the slant top) and the
# rear thickness does not vary. The constant is kept as the catalogue's value
# and `tests/test_topper.py` holds the two to each other on every set.
Z_BASE = 48.450


def z_base(p, d):
    """Where the topper's base sits: `H.slant_top(d) + topper_height(p, d)`,
    the holder's slant top and the topper's own rear thickness above it."""
    return H.slant_top(d) + topper_height(p, d)

FRONT_WALL = 0.800         # the front wall, and the flat left along the top
FLOOR = 1.200              # floor thickness
FRONT_WALL_RISE = 1.400    # how far the front wall stands above the floor's top

# At each slot boundary the part carries a RIB the full depth, and a wider
# BAND of front wall around it. Probing the reference band by band in Y is what
# separates them: at Z 55 the material at the front face (Y -6.1, -6.5) runs
# 26.10..40.90, and one step back (Y -6.9 and beyond) only 32.70..34.30. A T in
# plan, not a solid post — a plan section alone reads as one 14.800 block and
# is what an earlier revision of spec/TOPPER.md recorded.
RIB_W = D.WallThickness             # 1.600, the rib through the depth
# The band's half width is DERIVED below, once INNER_END_INSET is defined:
# `Remove most of front` (Allan's screenshot, 2026-09-04) is sketched on the
# `Remove Inner Hole` face and puts each opening's edge FRONT_MARGIN = 6.000
# from that pocket's end — which is INNER_END_INSET in from the part's end —
# and `6 + 0.6` from the rib's face, which is RIB_W / 2 from the boundary.
# Both readings are 7.400, and neither is `#FootDistanceFromWall`, which an
# earlier revision guessed.
FRONT_MARGIN = 6.000

# `Inner Hole Outline` is sketched IN THE SLANT PLANE — its sketch plane is
# `Face of TriangleMatch` — so its two dimensions are measured there, not in Y.
# The 0.800 is the inset from the slant's REAR edge and the 1.400 the inset
# from each END. Differencing the wedge against the `to Remove Inner Hole`
# rollback gives the tool exactly: a 6-face prism, and its rear face lands at
# 0.800 * cos(theta) in Y — 0.444 on M15-Sl at slope 1.4977, 0.242 on M10-Un at
# 3.1538. A plain Y-offset would be wrong by the slope, and wrong differently
# on every row, because the slope moves with calSlotDepth.
INNER_INSET = 0.800        # from the slant's rear edge, ALONG the slant
INNER_END_INSET = 1.400    # from each end of the part, in X
BAND_HALF = FRONT_MARGIN + INNER_END_INSET   # 7.400: the front band is 14.800
assert abs(BAND_HALF - (FRONT_MARGIN + 0.6 + RIB_W / 2)) < 1e-9, \
    "the sketch's two readings of the band, 6 + 1.4 and 6.6 + 0.8, disagree"

TAB_W = D.WallThickness    # 1.600
TAB_INSET = 1.300          # from each end of the part
TAB_RISE = 44.000          # "extruded to 44 mm blind" (Allan), off the FLOOR
# How far the tab stops short of the pocket's rear wall. NOT a constant offset
# from the rear FACE: measured 1.442 in on M10-Un and 1.644 on M15-Sl, and the
# difference is exactly INNER_INSET * (cos 0.55529 - cos 0.30224). Taken off the
# pocket's own rear face it is 1.200 on both, to six decimals.
TAB_REAR_GAP = 1.200
TAB_CHAMFER = 0.500        # the top all round, and the two REAR vertical edges

# The tabs' tops, above Z_BASE. Constant on all 48 — and now derived: the tab
# starts on the floor and is 44 mm blind.
TOTAL_HEIGHT = FLOOR + TAB_RISE                                       # 45.200

# `Room for Lips` — the notch each Holder rear lip needs in the topper's rear
# wall. Its X extent is not a number of the topper's own: it is the HOLDER's
# lip base, `holder.lip_plan`, with NO clearance at all — |x| 14.200..26.600
# from the slot centre on both parameter sets, against a lip base that measures
# 14.200..26.600. That is the same relationship `spec/HOLDER.md` records for
# `Lip Rest`, and it is why this binds to holder.lip_plan rather than to
# 20.400 +- 6.200.
#
# LIP_ROOM_RISE is 2.000 on both sets, which is `#LipHeight`. Two constants
# cannot tell a constant from a variable. It IS `holder.SLANT_STEP` (Allan,
# 2026-09-04): the `Divider` sketch carries no dimensions of its own and maps
# onto points imported from the holder, so the notch floor is the holder's
# slant step by construction, and it is bound to it.
LIP_ROOM_RISE = H.SLANT_STEP   # the notch floor, above the topper's floor top

LIP_FILLET = 1.400         # `Fillet Lip Room`
FRONT_FILLET = 2.000       # `Fillet front holes`
EDGE_ROUND = 0.800         # `Top and front edges`


def width(p, d):
    """`calSlotwidth * HorizontalSlots` — the Holder less its two end blocks."""
    return d.calSlotwidth * p.HorizontalSlots


def depth(p, d):
    """The Holder's own depth, `2.000 + calSlotDepth`. Exact on all 48."""
    return H.holder_depth(p, d, first=False)


def topper_height(p, d):
    """`#TopperHeight` — Allan's expression, and the REAR thickness.

        BoxHeight - WallThickness*2 - PusherFootThickness
                  - calPocketHeight - 4mm - 3.5mm

    4.200 on every Innovation row, because `calPocketHeight` pins at 88.500,
    but the expression is real rather than a constant. Confirmed a second way
    off the geometry: the section's rear measures 52.650 - 48.450.
    """
    return (d.BoxHeight - D.WallThickness * 2 - D.PusherFootThickness
            - d.calPocketHeight - 4.0 - 3.5)


def x_span(p, d):
    """(x0, x1). X = 0 is the centre of the FIRST slot, as the Holder's is."""
    x0 = -d.calSlotwidth / 2
    return x0, x0 + width(p, d)


def y_span(p, d):
    """(front, rear), both negative — the topper sits one depth back."""
    dp = depth(p, d)
    return -dp, -2 * dp


def slant_slope(p, d):
    """The Holder's `Top slant angle`, and not a second transcription of it.

    Measured `1.497717` on the M15-Sl sample against `holder.slant_slope`'s
    `1.497717`, and `3.153846` on the M10-Un one. This IS `TriangleMatch`.
    """
    return H.slant_slope(p, d, first=False)


def slant_z(p, d, y):
    """Z of the slant plane at a given Y.

    Anchored at the REAR, where the section is `#TopperHeight` thick — the one
    place the slant's height is stated rather than inferred.
    """
    _, rear = y_span(p, d)
    return Z_BASE + topper_height(p, d) + slant_slope(p, d) * (y - rear)


def post_x(p, d):
    """Centre X of each full post — the slot boundaries.

    `calSlotwidth * (k + 0.5)`, which is `HorizontalSlots - 1` of them: the
    count `More Dividers` patterns. The two ends carry half a post each,
    because `Remove Inner Hole` stops INNER_END_INSET short of them.
    """
    return [d.calSlotwidth * (k + 0.5) for k in range(p.HorizontalSlots - 1)]


def band_x(p, d):
    """(x0, x1) of each 14.800 front-wall band, and the half-bands at the ends.

    The ends carry half a band each, because the band is centred on a slot
    boundary and the part stops half a slot out from the first one.
    """
    x0, x1 = x_span(p, d)
    out = [(x0, x0 + BAND_HALF)]
    out += [(c - BAND_HALF, c + BAND_HALF) for c in post_x(p, d)]
    out.append((x1 - BAND_HALF, x1))
    return out


def rib_x(p, d):
    """(x0, x1) of each rib — RIB_W wide, centred on a slot boundary."""
    return [(c - RIB_W / 2, c + RIB_W / 2) for c in post_x(p, d)]


def wedge_profile(p, d):
    """The section `TriangleMatch` + `CardHeight` make, as (Y, Z) points.

    Read straight off the unfilleted reference at a post:

        (-12.000, 48.450) -> (-6.000, 48.450)   the base
        (-6.000, 48.450) -> (-6.000, 69.050)    the front face
        (-6.000, 69.050) -> (-6.800, 69.050)    the FRONT_WALL flat on top
        (-6.800, 69.050) -> (-12.000, 52.650)   the slant
        (-12.000, 52.650) -> (-12.000, 48.450)  the rear, #TopperHeight tall
    """
    front, rear = y_span(p, d)
    # The front is the LESS negative edge, so going into the part subtracts.
    z_front = slant_z(p, d, front - FRONT_WALL)
    z_rear = Z_BASE + topper_height(p, d)
    return [(rear, Z_BASE), (front, Z_BASE), (front, z_front),
            (front - FRONT_WALL, z_front), (rear, z_rear)]


def wedge(p, d):
    """The base solid: the profile swept the full width."""
    x0, x1 = x_span(p, d)
    with BuildPart() as part:
        with BuildSketch(Plane.YZ):
            with BuildLine():
                pts = wedge_profile(p, d)
                Polyline(*pts, close=True)
            make_face()
        extrude(amount=x1 - x0)
    return part.part.moved(Location((x0, 0, 0)))


def slant_cos(p, d):
    """cos of the slant's angle to Y — how a distance ALONG the slant projects.

    `1/sqrt(1 + m^2)`. This is the factor that turns `Inner Hole Outline`'s
    0.800, which is measured in the slant plane, into the rear wall's Y
    thickness: 0.4442 at slope 1.4977 and 0.2418 at 3.1538, against 0.444 and
    0.242 measured.
    """
    m = slant_slope(p, d)
    return 1.0 / math.sqrt(1.0 + m * m)


def inner_hole(p, d):
    """`Remove Inner Hole` — the pocket, as the solid to subtract.

    Differencing `wedge()` against the `to Remove Inner Hole` rollback gives
    this exactly: ONE prism of SIX faces, swept along X, whose top is the
    wedge's own slant plane. So it needs no separate top — the cut simply runs
    out through the slant.

        floor   Z_BASE + FLOOR
        front   FRONT_WALL in from the front face
        rear    INNER_INSET along the slant from the rear edge
        ends    INNER_END_INSET in from each end
    """
    x0, x1 = x_span(p, d)
    front, rear = y_span(p, d)
    y_front = front - FRONT_WALL
    y_rear = rear + INNER_INSET * slant_cos(p, d)
    z_floor = Z_BASE + FLOOR
    with BuildPart() as part:
        with BuildSketch(Plane.YZ):
            with BuildLine():
                Polyline((y_front, z_floor), (y_front, slant_z(p, d, y_front)),
                         (y_rear, slant_z(p, d, y_rear)), (y_rear, z_floor),
                         close=True)
            make_face()
        extrude(amount=(x1 - x0) - 2 * INNER_END_INSET)
    return part.part.moved(Location((x0 + INNER_END_INSET, 0, 0)))


def slot_x(p, d):
    """Centre X of each SLOT — `calSlotwidth * k`, one per HorizontalSlots.

    The front-wall removal is centred on these, where the ribs and bands are
    centred on the BOUNDARIES between them.
    """
    return [d.calSlotwidth * k for k in range(p.HorizontalSlots)]


def _arc(start, centre, end):
    """A quarter arc from `start` to `end` about `centre`, as a ThreePointArc
    through the arc's midpoint.

    Given explicitly rather than with a signed RadiusArc: which side a radius
    arc takes is exactly the thing that would silently invert a fillet.
    """
    ux, uz = ((start[0] - centre[0]) + (end[0] - centre[0]),
              (start[1] - centre[1]) + (end[1] - centre[1]))
    n = math.hypot(ux, uz)
    r = math.hypot(start[0] - centre[0], start[1] - centre[1])
    mid = (centre[0] + r * ux / n, centre[1] + r * uz / n)
    return ThreePointArc(start, mid, end)


def front_removal(p, d):
    """`Remove most of front` .. `Fillet front holes`, as the solid to subtract.

    The front wall is taken away above the floor's `FRONT_WALL_RISE`, over
    `calSlotwidth - 2*BAND_HALF` centred on each SLOT CENTRE — which is what
    leaves the 14.800 band at each boundary — and then `Fillet front holes`
    rounds all four corners of every opening at `FRONT_FILLET`.

    That fillet is built INTO THE TOOL rather than run on the body, because
    OCCT will not put a 2.000 round on an 0.800 wall and Onshape's "allow edge
    overflow" is precisely the permission to do it anyway. The reference says
    what the answer is: 16 quarter-cylinders of `r 2.000`, each spanning the
    wall's own 0.800, four per opening.

    The two kinds go opposite ways, which is the whole subtlety:

        BOTTOM corners  the opening's side meets its own floor, a notch in the
                        material, so the round ADDS material inside the opening
                        and the tool's corner is cut away
        TOP corners     the opening's side meets the WALL'S TOP FACE, so the
                        round REMOVES material and the tool grows FRONT_FILLET
                        into the band on each side

    They are equal and opposite: `(4 - pi) * FRONT_FILLET**2 * FRONT_WALL` is
    `0.6867` mm3 a corner, 8 of each, so the volume balances exactly and volume
    alone would pass a tool with neither. The symmetric difference is what
    catches it — `tests/test_topper.py` asserts both directions separately.
    """
    front, _rear = y_span(p, d)
    z0 = Z_BASE + FLOOR + FRONT_WALL_RISE
    z1 = slant_z(p, d, front - FRONT_WALL)
    r = FRONT_FILLET
    hw = (d.calSlotwidth - 2 * BAND_HALF) / 2
    out = None
    for c in slot_x(p, d):
        xl, xr = c - hw, c + hw
        with BuildPart() as part:
            with BuildSketch(Plane.XZ):
                with BuildLine():
                    _arc((xl + r, z0), (xl + r, z0 + r), (xl, z0 + r))
                    Line((xl, z0 + r), (xl, z1 - r))
                    _arc((xl, z1 - r), (xl - r, z1 - r), (xl - r, z1))
                    # up and over the wall's top, so the tool's top face is not
                    # coincident with it; there is nothing above z1 at this Y.
                    Polyline((xl - r, z1), (xl - r, z1 + 1.0),
                             (xr + r, z1 + 1.0), (xr + r, z1))
                    _arc((xr + r, z1), (xr + r, z1 - r), (xr, z1 - r))
                    Line((xr, z1 - r), (xr, z0 + r))
                    _arc((xr, z0 + r), (xr - r, z0 + r), (xr - r, z0))
                    Line((xr - r, z0), (xl + r, z0))
                make_face()
            extrude(amount=FRONT_WALL)
        b = part.part.moved(Location((0, front, 0)))
        out = b if out is None else out + b
    return out


def holder_tabs(p, d):
    """`Tab-to-attach` — two plates that clip the topper onto the Holder.

    One at each end, `TAB_W` thick and `TAB_INSET` in, standing off the FLOOR
    and `TAB_RISE` tall. In Y they fill the pocket's own footprint less
    `TAB_REAR_GAP` at the rear. `TAB_CHAMFER` runs all round the top and down
    the two REAR vertical edges — the front edges are square, because the tab
    merges into the front wall there.
    """
    x0, x1 = x_span(p, d)
    front, rear = y_span(p, d)
    y_front = front - FRONT_WALL
    y_rear = rear + INNER_INSET * slant_cos(p, d) + TAB_REAR_GAP
    z0 = Z_BASE + FLOOR
    z1 = z0 + TAB_RISE
    out = None
    for xc in (x0 + TAB_INSET + TAB_W / 2, x1 - TAB_INSET - TAB_W / 2):
        b = (Pos(xc, (y_front + y_rear) / 2, (z0 + z1) / 2)
             * Box(TAB_W, y_front - y_rear, z1 - z0))
        es = [e for e in b.edges()
              if abs(e.center().Z - z1) < 1e-6
              or (abs(e.center().Y - y_rear) < 1e-6
                  and abs(e.length - (z1 - z0)) < 1e-6)]
        b = chamfer(es, TAB_CHAMFER)
        out = b if out is None else out + b
    return out


def lip_room_x(p, d):
    """(x0, x1) of every lip notch — the HOLDER's lip base, not a number here.

    Two per slot, mirrored about the slot centre, `HorizontalSlots` times over:
    that is `Remove Lip Room` + `Other side` + `Linear pattern 1`, and it gives
    the 8 notches and 16 `r 1.400` cylinders the M15-Sl rollback carries.
    """
    xs = [x for x, _y in H.lip_plan(p, d, first=False)]
    lo, hi = min(xs), max(xs)
    return sorted((c - hi, c - lo) if s < 0 else (c + lo, c + hi)
                  for c in slot_x(p, d) for s in (+1, -1))


def lip_rooms(p, d):
    """`Room for Lips` .. `Linear pattern 1`, as the solid to subtract.

    A notch through the rear wall, floor at `LIP_ROOM_RISE` above the topper's
    own floor and open upward through the slant, with `LIP_FILLET` on its two
    bottom corners. The tool runs a little past the wall both ways: behind it
    is outside the part and in front of it is the pocket, so the extra is air
    either way and no face of the cut is coincident with a face of the body.
    """
    _front, rear = y_span(p, d)
    z0 = Z_BASE + FLOOR + LIP_ROOM_RISE
    z1 = Z_BASE + TOTAL_HEIGHT + 1.0
    r = LIP_FILLET
    depth_y = INNER_INSET * slant_cos(p, d) + 2.0
    out = None
    for xl, xr in lip_room_x(p, d):
        with BuildPart() as part:
            with BuildSketch(Plane.XZ):
                with BuildLine():
                    _arc((xl + r, z0), (xl + r, z0 + r), (xl, z0 + r))
                    Polyline((xl, z0 + r), (xl, z1), (xr, z1), (xr, z0 + r))
                    _arc((xr, z0 + r), (xr - r, z0 + r), (xr - r, z0))
                    Line((xr - r, z0), (xl + r, z0))
                make_face()
            extrude(amount=depth_y)
        b = part.part.moved(Location((0, rear - 1.0 + depth_y, 0)))
        out = b if out is None else out + b
    return out


def dividers(p, d):
    """`Divider` and `More Dividers` — the ribs, as the solid to ADD.

    Each is the inner hole's own profile, `RIB_W` wide, centred on a slot
    boundary: differencing the rollbacks gives three solids of six faces whose
    YZ section is identical to the pocket's, to four decimal places. So a rib
    is the pocket filled back in over 1.600, not a shape of its own.
    """
    out = None
    hole = inner_hole(p, d)                 # the same prism under every rib
    for c in post_x(p, d):
        strip = Pos(c, 0, 0) * Box(RIB_W, 1000, 1000)
        r = hole & strip
        out = r if out is None else out + r
    return out

def top_and_front_edges(p, d, part):
    """`Top and front edges` — the last feature of the blank, `r EDGE_ROUND`.

    Named for the SKETCH's orientation; `Upside Down` sits between, so the
    sketch's top and front are the assembly's BOTTOM and ends. The filleted
    `M10-Un` reference says exactly which edges, and there are only eight
    cylinders and no tori:

        the bottom face's whole perimeter   4, of `width - 2r` and `depth - 2r`
        the ends' FRONT vertical edges      2, `Z_BASE + r` up to the wall top
        the ends' REAR vertical edges       2, trimmed by the SLANT, which is
                                            why they reach `55.173` on M10-Un
                                            and not the rear's own `52.650`

    That last one is the tell that this is one fillet on a connected chain and
    not four separate ones: the rear edge stops where the slant begins, and the
    fillet surface runs past it until the slant face cuts it off — `slant_z` at
    `rear + r`, to three decimals on both parameter sets.

    It has to be built BEFORE the lettering (Allan): the logo and the name are
    offset from the edge of these fillets, so `Expansion Name` does not work
    without it.
    """
    x0, x1 = x_span(p, d)
    front, rear = y_span(p, d)

    def on_side(pt):
        return (min(abs(pt.X - x0), abs(pt.X - x1)) < 1e-6
                or min(abs(pt.Y - front), abs(pt.Y - rear)) < 1e-6)

    es = []
    for e in part.edges():
        a, b = e.start_point(), e.end_point()
        # The bottom PERIMETER, and stated as such rather than as "everything
        # in the bottom plane". Those are the same set today, because
        # `Expansion Name` is cut after this — but the glyph outlines lie in
        # this plane too, so the loose form is one reordering away from
        # rounding the lettering.
        if (abs(a.Z - Z_BASE) < 1e-6 and abs(b.Z - Z_BASE) < 1e-6
                and on_side(a) and on_side(b)):
            es.append(e)
        elif (abs(a.X - b.X) < 1e-6 and abs(a.Y - b.Y) < 1e-6
              and min(abs(a.X - x0), abs(a.X - x1)) < 1e-6
              and min(abs(a.Y - front), abs(a.Y - rear)) < 1e-6):
            es.append(e)
    return fillet(es, EDGE_ROUND)


# --- the marks ------------------------------------------------------------
# Each is drawn in the READING frame — x right, y up, origin at the centre of
# `mark_box` — and sized entirely by `calLogoSidelength`. Nothing here is a
# traced outline: every number below is a fraction of L that reproduces the
# reference to better than 0.0002 mm.


def _unseen_mark(L):
    """A shield, and five rays on an arc below it.

    Differenced exactly out of the M10-Un blank, the shield is TWO arcs:

        lower   a semicircle of radius L/2 about C = (0, 5L/14)
        upper   an arc from (-L/2, 5L/14) to (L/2, 5L/14) peaking at (0, L/2)

    `5L/14` is `L/2 - L/7`, which is the `L/7` inset Allan's sketch carries;
    it puts the shield's bottom tip at `-L/7` and its apex on the box's top
    edge. The upper arc's radius follows and is not a number of its own —
    `(a**2 + s**2) / 2s` for `a = L/2`, `s = L/7`, which is 3.99866 against
    3.9987 measured.

    The five rays are `L/5` by `L/10` rectangles at 0 and +-25 and +-50
    degrees, and the pivot is **C itself**, not the box centre: about C they
    sit at one radius to 3e-5, and about the box centre they do not (2.2387,
    1.6479, 1.3782). Their inner edge is `L/12` clear of the semicircle's own
    rim, which is the `L/12` the sketch carries.
    """
    c = 5 * L / 14
    r = L / 2
    with BuildSketch() as sk:
        with BuildLine():
            _arc((-r, c), (0.0, c), (0.0, c - r))
            _arc((0.0, c - r), (0.0, c), (r, c))
            # the upper arc, by its three points: the two shoulders and the apex
            ThreePointArc((r, c), (0.0, r), (-r, c))
        make_face()
    out = sk.sketch
    # from C: the semicircle's own rim, L/12 of clearance, then half the ray
    r_mid = r + L / 12 + L / 10
    for phi in (-50.0, -25.0, 0.0, 25.0, 50.0):
        a = math.radians(phi)
        # `long` points outward along the ray, `wide` across it
        lx, ly = math.sin(a), -math.cos(a)
        wx, wy = math.cos(a), math.sin(a)
        mx, my = lx * r_mid, c + ly * r_mid
        hl, hw = L / 5 / 2, L / 10 / 2
        pts = [(mx + sx * hl * lx + sy * hw * wx, my + sx * hl * ly + sy * hw * wy)
               for sx, sy in ((-1, -1), (-1, +1), (+1, +1), (+1, -1))]
        with BuildSketch() as ray:
            with BuildLine():
                Polyline(*pts, close=True)
            make_face()
        out = out + ray.sketch
    return out


def _cities_mark(L):
    """An eight-pointed star: EIGHT triangles through the centre, not a traced
    outline.

    `Cities Draft` carries `L/8` and `L/5`, and those are the two BASES:

        4 on the axes       apex L/2 out,  base L/5 across the centre
        4 on the diagonals  apex (L/4, L/4), base L/8 across the centre

    The 16 vertices of the finished star are then where adjacent triangles'
    edges cross, and nothing places them directly. Predicted `(1.086307,
    0.636398)` against `(1.08649, 0.63645)` measured, and the outer tips fall
    out at `L/2` and `L/(2*sqrt(2))` exactly.
    """
    out = None
    for k in range(8):
        a = math.radians(45.0 * k)
        dx, dy = math.cos(a), math.sin(a)
        if k % 2 == 0:
            apex, half = L / 2, L / 10
        else:
            apex, half = L / (2 * math.sqrt(2.0)), L / 16
        with BuildSketch() as tri:
            with BuildLine():
                Polyline((apex * dx, apex * dy),
                         (-half * dy, half * dx),
                         (half * dy, -half * dx), close=True)
            make_face()
        out = tri.sketch if out is None else out + tri.sketch
    return out


def _echoes_mark(L):
    """A diamond: a square turned 45 degrees, its four vertices on the box's
    edge midpoints. Area `L**2 / 2` — 36.44439 against 36.4444 measured."""
    r = L / 2
    with BuildSketch() as sk:
        with BuildLine():
            Polyline((0.0, r), (-r, 0.0), (0.0, -r), (r, 0.0), close=True)
        make_face()
    return sk.sketch


def _artifacts_mark(L):
    """Two tall triangles that OVERLAP, and the overlap is the whole point.

    Each has its base on the box's bottom edge and its apex `L/4` in from a
    top corner, and the bases cross the centre line by `L/8`:

        left    (-L/2, -L/2)  (L/8, -L/2)  (-L/4, L/2)
        right   ( L/2, -L/2) (-L/8, -L/2)  ( L/4, L/2)

    Their union has five edges, not six: below the crossing the two bases are
    one line. The notch where the inner edges meet falls out at
    `(0, -1.42292)`, which is `-L/2 + L/3`, and the reference reads
    `(0.0000, -1.4229)`.
    """
    r = L / 2
    out = None
    for sgn in (-1.0, +1.0):
        with BuildSketch() as tri:
            with BuildLine():
                Polyline((sgn * r, -r), (-sgn * L / 8, -r),
                         (sgn * L / 4, r), close=True)
            make_face()
        out = tri.sketch if out is None else out + tri.sketch
    return out


def _figures_mark(L):
    """An ANNULUS — the ring alone, not a disc with a ring round it.

    That was the open question, and the reference answers it directly: the
    mark is ONE solid with TWO wires, and a disc with a separate ring would be
    two solids. Outer radius `L/2`, inner `L/2 - L/5`, so the radial gap is the
    `L/5` Allan's sketch carries: `2.56125` against `2.5613` measured, and the
    area `36.63797` against `36.6380`.
    """
    with BuildSketch() as sk:
        Circle(L / 2)
        Circle(L / 2 - L / 5, mode=Mode.SUBTRACT)
    return sk.sketch


MARKS = {"Artifacts": _artifacts_mark, "Cities": _cities_mark,
         "Echoes": _echoes_mark, "Figures": _figures_mark,
         "Unseen": _unseen_mark}
assert tuple(sorted(MARKS)) == TB.TOPPER_EXPANSIONS, \
    "cad/tables.TOPPER_EXPANSIONS is the catalogue's copy of MARKS' keys"


# ---------------------------------------------------------------------------
# `Expansion Name` — the mark and the expansion's name, engraved in the
# UNDERSIDE. The placement and all five marks; see spec/TOPPER.md.

FONT = str(TX.FONT_DIR / "NotoSerif-Bold.ttf")   # Noto Serif Bold (Allan)

# The cap band as a fraction of the em. Measured 0.72025 / 0.72030 / 0.72016 /
# 0.72016 on four different words, agreeing to 1.5e-4, and NOT the face's own
# sCapHeight of 0.714 — which suggests Onshape constrains a nominal 0.72 em box
# rather than the cap height. That last part is an inference; 0.7202 is the
# measurement. See spec/TOPPER.md, "The typeface".
BAND_EM = 0.7202

# How deep the mark and the name are cut. 0.810, not the 0.800 the wall and
# the fillet make it tempting to assume: the pocket runs Z 48.450..49.260 on
# all three references. The STEP's separate inlay solids are 0.810 TALL too but
# sit at 48.440..49.250, so they stand 0.010 proud of the underside and leave
# 0.010 clear at the pocket's top — the same trick the Lid's logo inlays use.
ENGRAVE = 0.810
ENGRAVE_OVERSHOOT = 0.500   # below the face, so the cut has no coincident face
INLAY_PROUD = 0.010         # the inlays stand this far below the underside (spec/TOPPER.md)
MARK_GAP = 1.000           # the mark box's left edge, past calLogoSidelength/2
TEXT_GAP = 3.000           # the sketch's `+3mm`, past calLogoSidelength*3/2


def logo_edge_dist(p, d):
    """`#LogoEdgeDist` — a PART-STUDIO variable, so it lives here and not in
    `derive.py`, which is the variable studio's transcription."""
    if p.CardsPerSlidingSlot > 10:
        return 1.2 if p.isSleeved else 0.8
    return 1.0 if p.isSleeved else 0.6


def face_datum(p, d):
    """Where every `Expansion Name` offset is measured from: the FLAT part of
    the underside, i.e. inside `Top and front edges`.

    Returns `(x, y_rear, y_front)`. This is the whole reason the fillet has to
    be built before the lettering (Allan) — an offset taken from the part's own
    edge instead is wrong by EDGE_ROUND, on every one of the six.
    """
    x0, _x1 = x_span(p, d)
    front, rear = y_span(p, d)
    return x0 + EDGE_ROUND, rear + EDGE_ROUND, front - EDGE_ROUND


def cap_band(p, d):
    """The band the lettering's CAP HEIGHT fills.

        depth - 2 * EDGE_ROUND - 3 * LogoEdgeDist

    The `2 * EDGE_ROUND` is the two `Top and front edges` fillets, NOT the two
    walls: the front wall is 0.800 but the rear one is 0.242 on M10-Un, so a
    rule written off the walls happens to be right on one term and would be
    wrong the moment either moved. `3 *` is the two margins, LogoEdgeDist at
    the top and twice that at the bottom.
    """
    return depth(p, d) - 2 * EDGE_ROUND - 3 * logo_edge_dist(p, d)


# The deepest descender any expansion name has: `Figures`' `g`, and Onshape's
# `g`, which reaches 0.00459 em deeper than the vendored font's
# (spec/TOPPER.md, "The vendored Noto Serif Bold"). The doubled bottom
# margin exists to hold it, and it is what stops the floor being reached.
DESCENDER_EM = -(TX.metrics("Figures", FONT)[2] - 0.00459)


def font_size(p, d):
    """The em that puts `cap_band` at BAND_EM of it — or the CUT floor
    (`cad/text.py`, "floors") where that is larger.

    Cut, not proud, although the sketch stands the inlay 0.010 proud: the
    topper prints face down and flat, the lettering is a second-filament
    fill in a pocket, and the 0.010 is there to make the sliver work, not
    to raise the text (Allan, 2026-09-04). Noto Serif Bold's hairline is
    0.054 em, so the floor is 3.70 em. Every size in the catalogue fits at
    5.4 em or more except the two 10-card unsleeved ones (`S10-Un`,
    `M10-Un`), which fit at 3.61 and are raised to the floor; their 4.40
    flat holds 4.07 em with the sketch's 1:2 margins and `Figures`' `g`
    under the band (DESCENDER_EM), so the raise fits, and `baseline_y`
    shares what the flat has left in that 1:2. A floor the flat could not
    hold would raise `DoesNotFit` rather than put the `g` into the round —
    which is what the PROUD floor's 4.63 em did before this was settled.
    """
    fitted = cap_band(p, d) / BAND_EM
    floor = TX.floor_size(FONT)
    if fitted >= floor:
        return fitted
    _x, rear, front = face_datum(p, d)
    flat = front - rear
    # The largest em whose band AND deepest descender fit with the 1:2 split:
    #   2/3 (flat - BAND_EM s) >= DESCENDER_EM s
    holds = 2 * flat / (3 * DESCENDER_EM + 2 * BAND_EM)
    if holds < floor:
        raise TX.DoesNotFit(f"topper lettering at its floor ({floor:.3f} em) "
                            f"does not fit the {flat:.2f} flat with `Figures`' "
                            f"g; it holds {holds:.3f}")
    return floor


def baseline_y(p, d):
    """Y of the lettering's baseline: `LogoEdgeDist * 2` in from the flat
    face's FRONT edge. Exact on all three filleted references — -8.000,
    -10.400, -14.950 — against ink that overshoots it by a round letter's
    0.036, 0.055 and 0.090."""
    _x, y_rear, y_front = face_datum(p, d)
    # `2 * LogoEdgeDist` is two thirds of what the flat has left once the cap
    # band is out of it — `3 * LogoEdgeDist` — and it is written that way so
    # a band raised to its floor (`font_size`) keeps the sketch's 1:2 split
    # of the margins instead of walking off the rear round. Identical where
    # the floor does not bind, which is everywhere but the 10-card unsleeved.
    left = (y_front - y_rear) - font_size(p, d) * BAND_EM
    return y_front - 2 * left / 3


def text_origin_x(p, d):
    """The PEN's start, `calLogoSidelength*3/2 + 3` past the flat face's end.

    Not the ink's start: what is left over is the first glyph's own left
    bearing, and it reads 0.01609 em and 0.01610 em for `U` on two parameter
    sets whose sizes differ by 54%. That agreement is what says the rule places
    the pen and the font does the rest.
    """
    x, _rear, _front = face_datum(p, d)
    return x + 1.5 * d.calLogoSidelength + TEXT_GAP


def mark_box(p, d):
    """(x0, y0, x1, y1) of the `calLogoSidelength` square the mark fills.

    Left edge at `calLogoSidelength/2 + MARK_GAP` past the flat face's end —
    which puts its RIGHT edge at `calLogoSidelength*3/2 + 1`, exactly 2.000
    before the pen. Centred in the depth: the two fillets cancel, so the box's
    centre is the face's own centre and not something that moves with
    EDGE_ROUND.

    Predicted box tops -11.1125 / -14.8625 / -21.89375 against measured
    -11.112 / -14.862 / -21.894, for calLogoSidelength 4.225 / 5.725 / 8.5375.
    Cities fills the square exactly; Unseen's shield fills its width and its
    top edge, and its rays hang below.
    """
    x, _rear, _front = face_datum(p, d)
    front, rear = y_span(p, d)
    L = d.calLogoSidelength
    x0 = x + L / 2 + MARK_GAP
    cy = (front + rear) / 2
    return x0, cy - L / 2, x0 + L, cy + L / 2


def name_sketch(p, d, word):
    """The expansion's name, as a sketch in the reading frame with the pen's
    origin at (0, 0) — so the caller places it by `text_origin_x` and
    `baseline_y` and nothing here has to know where the part is."""
    size = font_size(p, d)
    _adv, lsb, lo, _hi = TX.metrics(word, FONT)
    with BuildSketch() as sk:
        Text(word, font_size=size, font_path=FONT, align=(Align.MIN, Align.MIN))
    return sk.sketch.moved(Location((lsb * size, lo * size, 0)))


def name_and_mark(p, d, expansion):
    """`Expansion Name`'s sketch — the mark and the word, placed on the
    underside in the reading frame — from which both the cut and the inlays
    are extruded."""
    def place(sketch, x, y):
        """Reading frame at the origin -> the underside, at (x, y)."""
        return Pos(x, y, 0) * sketch.mirror(Plane.XZ)

    mx0, my0, mx1, my1 = mark_box(p, d)
    sk = place(name_sketch(p, d, expansion),
               text_origin_x(p, d), baseline_y(p, d))
    mark = MARKS.get(expansion)
    if mark is not None:
        sk = sk + place(mark(d.calLogoSidelength),
                        (mx0 + mx1) / 2, (my0 + my1) / 2)
    return sk


def expansion_name(p, d, expansion):
    """`Expansion Name` — the mark and the word, as the solid to subtract."""
    # Dropped OVERSHOOT below the underside so no face of the tool is
    # coincident with the face it cuts. Without it OCCT quietly leaves 0.713
    # of the 19.294 behind and warns only "Boolean operation unable to clean".
    return Pos(0, 0, Z_BASE - ENGRAVE_OVERSHOOT) * extrude(
        name_and_mark(p, d, expansion), amount=ENGRAVE + ENGRAVE_OVERSHOOT)


def inlays(p, d, expansion):
    """The lettering as the SECOND-FILAMENT solids a print needs: one per
    region of the mark and the word, ENGRAVE tall, standing INLAY_PROUD below
    the underside so they leave that much clear at the pocket's top — the
    same trick the Lid's logo inlays use, and what every hand-exported STEP
    and cached topper carries beside its body. A topper written without
    them prints its name as an empty pocket; `cad.compare` found the built
    files that way on 2026-09-05."""
    if expansion == "Blank":
        return []
    solid = Pos(0, 0, Z_BASE - INLAY_PROUD) * extrude(name_and_mark(p, d, expansion),
                                                    amount=ENGRAVE)
    return sorted(solid.solids(), key=lambda q: (q.bounding_box().min.X, q.bounding_box().min.Y))


EXPANSIONS = TB.TOPPERS


def build(p, d=None, expansion="Blank"):
    """One Topper, in the Onshape tree's own order.

    `Blank` carries no name and no logo. The other five are the same body with
    `Expansion Name` engraved — the name and the mark from `MARKS`. Asking for
    an expansion `MARKS` does not know raises rather than quietly writing a
    topper with a name and no mark.
    """
    if p.GameName != "Innovation":
        raise ValueError(f"the Topper is Innovation-only, not {p.GameName!r}")
    if expansion not in EXPANSIONS:
        raise ValueError(f"no such Innovation expansion: {expansion!r}")
    if d is None:
        d = D.derive(p)
    part = wedge(p, d) - inner_hole(p, d)                 # Main topper
    part = part - front_removal(p, d)                     # Remove .. front
    part = part + dividers(p, d)                          # Divider, More
    part = part + holder_tabs(p, d)                       # Tab-to-attach
    part = part - lip_rooms(p, d)                         # Room for Lips ..
    part = top_and_front_edges(p, d, part)                # Top and front edges
    if expansion == "Blank":
        return part
    return part - expansion_name(p, d, expansion)         # Expansion Name


def build_all(p, d=None, expansion="Blank"):
    """(the Topper BODY, its lettering inlays) — what a topper file carries."""
    if d is None:
        d = D.derive(p)
    return build(p, d, expansion), inlays(p, d, expansion)


# NB `Solid.volume` is NOT the metric to check a NAMED topper with. OCCT's
# GProp over-reports a body carrying this many small BSpline faces: the M10-Un
# Unseen body reads 4101.406 where `blank - named` says it must be 4100.663,
# and the hand-exported STEP of the same part reads 4100.698 with the same kind
# of error in it. The tessellated volume agrees to 0.0014% and the engraving
# differenced back out agrees to 0.03%, so `tests/test_topper.py` uses those.
# An hour went into "fixing" a boolean that was correct all along.
