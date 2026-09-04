"""The Holder.

The card tray that rides the box's slider ribs. One per riser; a cascade's
holders form a staircase, and their sloped tops make one continuous diagonal
when the cascade is open. Measured in `spec/HOLDER.md` against ten
hand-exported STEPs; the Onshape feature tree it mirrors is, in order:

    Core holder     Pocket outline / Extrude 1 / Hole for cards / Hole outline /
                    Vertical slits in holder / Remove card holes /
                    Leftmost Pusher Pos / Horizontal capacity
    Finger Cutouts  Finger Cutout / Fillet 1 / Finger holes
                    Card holder bottom
                    Top slant angle / Side slot solid / Side slot /
                    Side slot hole / Mid plane / Mirror Side /
                    Remove Slant Angle / Middle
                    Hack to remove front lip / Remove little front lip
    Bottom Text     Name, Rev & Capacity / Extrude 2
    Rear lip        Lip / LipPlane / Rear Lip / Chamfer lip / Lip Rest /
                    Chamfer lip rest / Mirror Lip / Repeat Lips /
                    Repeat Mirror Lips / Mirror Lip Rest / Repeat lip rests

Local frame (the part studio's):
    X   0 at the centre of the FIRST compartment, +k * calSlotwidth for the rest
    Y   0 at the REAR face — `Rear lip`'s tabs stand proud of it, at Y > 0 —
        and NEGATIVE toward the front, which is the way the slant descends
    Z   0 midway between the base and the card pocket's TOP, both at
        (CardHeight - 1.5)/2 on every reference whatever the parameters

Every feature in that tree is built. Against all ten references the solid is
`+0.098%`, all but `+0.007%` of it the DELIBERATE text divergence on the two
holders Onshape engraves too big to fit (`text_size`). `tests/test_holder.py` is
what is proven against the STEPs, `tests/test_holder_corpus.py` what is proven
against the 50 cached components, and `tests/holder_diff.py` the dev loop.

Two features here are MODELLED rather than asked for, because no kernel will
compute them: `Fillet 1` (`finger_tool`) and the chamfer on `Lip Rest`
(`lip_rests`). Both are measured, and `spec/HOLDER.md` says how.
"""
import math

from build123d import (
    Align, Axis, Box, BuildLine, BuildPart, BuildSketch, Cylinder,
    Location, Mode, Plane, Polyline, Pos, Rectangle, Text, Torus, Vector,
    add, extrude, make_face,
)

from .. import derive as D
from .. import text as T

# The vertical datum. The base and the TOP OF THE CARD POCKET are symmetric
# about Z = 0, both at (CardHeight - 1.500)/2 = 45.250, and the pocket is
# CardHeight - 3.500 = 88.500 tall — `calMaxPocketHeight`'s first term — so it
# starts 2.000 above the base. Every one of those numbers is confirmed by the
# `Hole outline` sketch landing where it is measured: inset 2 from the pocket's
# bottom gives -41.250 on both rises, and inset `calHeightIncrement + 10` from
# its top gives 19.250 and 25.583, all four exact. See spec/HOLDER.md.
HALF_TRIM = 1.500                         # half_height  = (CardHeight - 1.5)/2
POCKET_TRIM = 3.500                       # pocket height = CardHeight - 3.5

# Each end stands this far beyond the outer slot edge: 4.000 of end block (which
# carries the side slot the box's rib runs in) plus 0.900 to the compartment
# wall. Measured 9.800 overall on all ten references. The studio used to say
# 5.000; 30 of the 50 cached components still do (spec/HOLDER.md).
END_EXTRA = 4.900
END_BLOCK = 4.000

WALL = 0.800                              # front and back wall thickness
DEPTH_GAP = 0.400                         # depth = sliderDistance - DEPTH_GAP

# `Top slant angle`. Two PARALLEL planes, SLANT_STEP apart, both meeting the
# rear face (Y = 0) at the same Z on every reference: the upper one exactly at
# the top of the card pocket. The slope is the cascade diagonal — see
# `slant_slope` — and `cad/parts/box.lip_slope` is its reciprocal.
#
# SLANT_STEP is `#LipHeight`, a constant 2.000 (Allan). It was measured here as
# the separation of the two planes before the variable was known, and the two
# agree — which is the only confirmation either has. Its whole purpose is the
# rear lip, whose section is the band between them.
SLANT_STEP = 2.000         # `#LipHeight`


def pocket_height(d):
    """`calMaxPocketHeight`'s first term — 88.500, and constant."""
    return d.CardHeight - POCKET_TRIM


def half_height(d):
    """45.250: the base below, the card pocket's top the same distance above."""
    return (d.CardHeight - HALF_TRIM) / 2


def base_z(d):
    """The underside. -45.250 on every reference, whatever the parameters."""
    return -half_height(d)


def pocket_z(d):
    """(bottom, top) of `Hole for cards` — 2.000 above the base, 88.500 tall."""
    top = half_height(d)
    return top - pocket_height(d), top


def card_top(d):
    """Z where a card in the pocket tops out.

    The pocket's floor — `FLOOR_DROP` below the sketch datum — plus
    `CardHeight`. 48.550 on every game, since `CardHeight` is 92.000 for all of
    them. It is what the Topper caps, so `cad/assembly.topper` reads it.
    """
    return pocket_z(d)[0] - FLOOR_DROP + d.CardHeight


def slant_top(d):
    """Z where the upper slant plane meets the front face.

    Measured 44.250 on every reference whatever the slope. That is both
    half the pocket height and the pocket's top less 1.000 — the two are the
    same expression, so no reference is needed to tell them apart.
    """
    return pocket_height(d) / 2


def slider_distance(p, d, first):
    """The holder's OWN slider distance.

    The first-riser holder is the same box's holder made deeper, so everything
    keyed to the slot depth takes `calFirstSliderDistance` instead. The 246 pair
    is the only evidence that could tell these apart — everywhere else the two
    are equal — and it settles both the depth and the slant.

    Takes the Primary for consistency with its siblings here, not because it
    reads it. It nearly did: Compile's `210 Card` was 12 cards deep where its
    own row and its own sibling row both said 7, which looked like a per-game
    or per-row term. It was a mis-configured export — re-exported, it lands on
    this rule to the thousandth under both card thicknesses. Nothing is
    special-cased, and there is nothing here left for the game to change.
    """
    return d.calFirstSliderDistance if first else d.calSliderDistance


def holder_depth(p, d, first):
    """Front face to back face: `sliderDistance - 0.400`.

    Exact on all ten references, `4.800` to `20.000`, and that includes the
    first-riser holder at `calFirstSliderDistance`.
    """
    return slider_distance(p, d, first) - DEPTH_GAP


def holder_width(p, d):
    """`calSlotwidth * HorizontalSlots + 9.800`.

    Exact on all ten STEPs and on the 20 cached components exported since the
    studio trimmed the end block. The other 30 say `10.000` and are the older
    geometry — see spec/HOLDER.md, "`individual/` is a mixed catalogue".
    """
    return d.calSlotwidth * p.HorizontalSlots + 2 * END_EXTRA


def x_span(p, d):
    """(min, max) X. The frame's origin is the FIRST compartment's centre, so
    this is NOT symmetric: the part runs from -(calSlotwidth/2 + END_EXTRA) to
    the last compartment's centre plus the same."""
    half = d.calSlotwidth / 2 + END_EXTRA
    return -half, (p.HorizontalSlots - 1) * d.calSlotwidth + half


def slant_slope(p, d, first):
    """`dZ/dY` of `Top slant angle` — the cascade diagonal.

        (calHeightIncrement - 1.0) / (sliderDistance - 1.2)

    Measured off the slant faces' normals: 1.7857 / 0.7812 / 1.2037 on the three
    references, against 1.7857 / 0.7812 / 1.2037 predicted. The rival reading
    (the other slider distance) is 2.3x out on the 246 pair.
    """
    return D.cascade_slope(d, slider_distance(p, d, first))


def slant_z(p, d, first, y, lower=False):
    """Z of the slant plane at depth `y` (y <= 0)."""
    return slant_top(d) - (SLANT_STEP if lower else 0.0) + slant_slope(p, d, first) * y


def shell(p, d, first):
    """`Pocket outline` / `Extrude 1`, cut by `Top slant angle`.

    Built as its YZ section swept along X rather than as a block minus a
    half-space: the section IS the outline — flat base, vertical front and back,
    and the slant closing the top — so the slope enters as two corner heights
    and there is no rotated tool to place. The scallops, the side slots and the
    lips all come off this.
    """
    x0, x1 = x_span(p, d)
    depth = holder_depth(p, d, first)
    z0 = base_z(d)
    with BuildPart() as part:
        with BuildSketch(Plane.YZ) as sec:
            with BuildLine():
                Polyline((0.0, z0), (-depth, z0),
                         (-depth, slant_z(p, d, first, -depth)),
                         (0.0, slant_z(p, d, first, 0.0)),
                         close=True)
            make_face()
        extrude(amount=x1 - x0)
    return part.part.moved(Location((x0, 0, 0)))


# `Horizontal capacity` patterns the compartment along X at calSlotwidth. The
# wall between two compartments is DIVIDER thick, so a pocket is that much
# narrower than its slot; at the ends the same half-divider is what leaves
# END_EXTRA + DIVIDER/2 = 5.700 of material outside the outermost pocket.
DIVIDER = 1.600


def compartment_x(p, d):
    """Centre X of each card compartment. The frame's origin is the first."""
    return [k * d.calSlotwidth for k in range(p.HorizontalSlots)]


# `Card holder bottom` drops the pocket's floor FLOOR_DROP below the sketch
# datum. It is invisible to a probe coarser than 0.200 — an earlier check at
# -43.750 and -42.750 straddled it and concluded the feature needed no code —
# and shows in the diff as one lump per compartment, exactly the pocket's
# footprint by 0.200: 63.400 * 7.600 * 0.200 = 96.368 on `246`.
#
# The `Hole outline` sketch is still measured from the UNDROPPED datum, which is
# what keeps its 2.000 inset landing on -41.250; `pocket_z` therefore returns
# the datum and this is applied only to the cut.
FLOOR_DROP = 0.200


def card_pockets(p, d, first, part):
    """`Hole for cards`, plus `Card holder bottom`'s FLOOR_DROP.

    Inset WALL from both faces (measured: the walls are the only material left
    at a lattice rail's height) and DIVIDER/2 from each slot edge.
    """
    depth = holder_depth(p, d, first)
    z0, z1 = pocket_z(d)
    z0 -= FLOOR_DROP
    w = d.calSlotwidth - DIVIDER
    over = 10.0                            # cut through whatever is above
    tool = Box(w, depth - 2 * WALL, z1 - z0 + over)
    # Every per-compartment feature here is ONE boolean with all its tools
    # (see box.rear_storage): they are disjoint, so the shape is the same,
    # and the body is walked once.
    return part.cut(*[tool.moved(Location((x, -depth / 2, (z0 + z1 + over) / 2)))
                      for x in compartment_x(p, d)])


# `Hole outline` / `Vertical slits in holder` / `Remove card holes` — the
# lattice, cut clean through both walls.
#
# The outline is inset 3.000 each side of the slot and sits on the floor:
#
#     HoleOutlineWidth  = calSlotwidth - 6.000
#     HoleOutlineHeight = 76.500 - calHeightIncrement
#
# Rows are three windows of (H - 6)/3 with a RAIL between and above them, so the
# three windows and three rails fill H exactly. Columns are five windows of a
# FIXED LIP_LENGTH at (W + 2)/5 pitch, left-aligned on the outline, and the
# mullion absorbs every bit of the variation. That last point is measured, not
# assumed: across five slot widths and three games the corpus reads
#
#     65 -> 10.0 2.2 ...   67 -> 10.0 2.6 ...   68 -> 10.0 2.8 ...
#     69 -> 10.0 3.0 ...   70 -> 10.0 3.2 ...
#
# with the window a flat 10.000 every time. Because the pattern is left-aligned
# and 5 windows plus 4 mullions come to 4*pitch + 10, `pitch - 12.000` is left
# over on the right; that asymmetry is the reference's, not an error.
LIP_LENGTH = 10.000        # `#LipLength`, a constant (Allan)
RAIL = 2.000               # between the window rows
ROWS = 3
COLS = 5
OUTLINE_INSET = 3.000      # each side of the slot
OUTLINE_BASE = 2.000       # above the card pocket's bottom
OUTLINE_TOP_TERM = 76.500  # HoleOutlineHeight = this - calHeightIncrement


def outline(p, d):
    """(width, height, bottom Z) of one compartment's `Hole outline`."""
    return (d.calSlotwidth - 2 * OUTLINE_INSET,
            OUTLINE_TOP_TERM - d.calHeightIncrement,
            pocket_z(d)[0] + OUTLINE_BASE)


def window_grid(p, d):
    """(x0, x1, z0, z1) of every lattice window in the FIRST compartment."""
    w, h, z0 = outline(p, d)
    win_h = (h - ROWS * RAIL) / ROWS
    pitch = (w + 2.0) / COLS
    out = []
    for r in range(ROWS):
        zr = z0 + r * (win_h + RAIL)
        for c in range(COLS):
            xc = -w / 2 + c * pitch
            out.append((xc, xc + LIP_LENGTH, zr, zr + win_h))
    return out


def lattice(p, d, first, part):
    """Cut the windows through both walls, in every compartment."""
    depth = holder_depth(p, d, first)
    tools = []
    for x0, x1, z0, z1 in window_grid(p, d):
        tool = Box(x1 - x0, depth + 2.0, z1 - z0)
        for xc in compartment_x(p, d):
            tools.append(tool.moved(
                Location((xc + (x0 + x1) / 2, -depth / 2, (z0 + z1) / 2))))
    return part.cut(*tools)


# `Finger Cutouts` — one per compartment, on its centre. A plain circle of
# FINGER_R with its centre ON the upper slant plane at the front face, so its
# lowest point is `slant_top - FINGER_R` = 32.250, which is one of the constant
# Z-planes on all three references whatever the depth or the rise.
#
# The radius is 12.000 and NOT the 12.400 the circular edges report — the same
# trap as the Box's thumb, and for the same reason: `Fillet 1` puts 0.400 on
# each face, and since the wall is 0.800 the two fillets meet in the middle and
# consume the cylindrical face entirely, leaving only torus. Sectioning at
# mid-wall recovers the true circle; the residual there is exactly the probe
# window's width times the local slope.
FINGER_R = 12.000
FINGER_FILLET = 0.400


def finger_tool(depth):
    """The scallop cut, with `Fillet 1` MODELLED rather than filleted.

    `Fillet 1` rounds the FRONT wall's scallop edges only — the reference has
    exactly one torus face per scallop, centred at `y = -0.400`, and nothing on
    the back wall. Because the wall is `2 * FINGER_FILLET` thick, the rounds
    from its two faces merge into that single torus, and OCCT will not compute
    such a fillet at all: `fillet(..., 0.400)` fails on every reference. That is
    a degenerate case for any kernel, not a build123d quirk, so the cut is
    constructed with the rounding already in it.

    The bead is the annulus between FINGER_R and FINGER_R + FINGER_FILLET across
    the front wall, less the torus the fillet rolls. At the face the torus
    reduces to a point, so the hole is the full FINGER_R + FINGER_FILLET; at
    mid-wall the torus fills the annulus, so the hole necks to FINGER_R.
    """
    # It stops at the BACK wall's inner face — the reference keeps that wall
    # whole behind the scallop, which is what holds the cards in. Easy to miss:
    # sampling only the front wall cannot see it, and on a steep holder like
    # `246` the slant has already removed the back wall at the scallop's height
    # so even a volume diff stays silent. `333`, the shallowest rise, is where
    # the back wall still reaches up there and the difference shows.
    reach = depth - WALL
    core = Cylinder(FINGER_R, reach + 1.0, rotation=(90, 0, 0)).moved(
        Location((0, (1.0 - reach) / 2, 0)))
    ring = (Cylinder(FINGER_R + FINGER_FILLET, 2 * FINGER_FILLET,
                     rotation=(90, 0, 0))
            - Cylinder(FINGER_R, 2 * FINGER_FILLET + 1.0, rotation=(90, 0, 0)))
    bead = ring - Torus(FINGER_R + FINGER_FILLET, FINGER_FILLET).rotate(
        Axis.X, 90)
    return core + bead.moved(Location((0, -FINGER_FILLET, 0)))


def finger_cutouts(p, d, first, part):
    """Cut the finger scallops through the full depth."""
    depth = holder_depth(p, d, first)
    tool = finger_tool(depth)
    return part.cut(*[tool.moved(Location((x, 0.0, slant_top(d))))
                      for x in compartment_x(p, d)])


# `Side slot solid` / `Side slot` / `Side slot hole` / `Mirror Side` — the groove
# each end runs on, which is the BOX's slider rib plus clearance. Measured on
# the holder: SLOT_W wide, centred on the holder's mid-depth, END_BLOCK deep
# from each end, and running the full height (the slant is what stops it, and it
# already has). Identical on all three references, whatever the depth.
#
# Against `cad/parts/box.py`, measured independently on the other part:
#
#     box SLIDER_W      1.500      holder SLOT_W    1.900   -> 0.200 a side
#     box SLIDER_PROUD  4.000      holder END_BLOCK 4.000   -> the same
#
# so the two parts agree without either having been fitted to the other.
SLOT_W = 1.900


def side_slots(p, d, first, part):
    """Cut the two end grooves."""
    x0, x1 = x_span(p, d)
    depth = holder_depth(p, d, first)
    z0 = base_z(d)
    tall = slant_top(d) - z0 + 2.0
    # END_BLOCK deep, plus 1.0 of overshoot past the end so the cut leaves no
    # coincident face; likewise 1.0 below the base and above the slant.
    tool = Box(END_BLOCK + 1.0, SLOT_W, tall)
    for x, inward in ((x0, +1), (x1, -1)):
        cx = x + inward * (END_BLOCK / 2 - 0.5)
        part = part - tool.moved(
            Location((cx, -depth / 2, z0 - 1.0 + tall / 2)))
    return part


# `Rear lip` — two tabs per compartment, standing proud of the Y = 0 face. This
# is the face Onshape calls the REAR, which is what fixes the frame's sense.
#
# In section they are the band between the TWO slant planes — that is what the
# second one is for — and they reach LIP_REACH ALONG the slant, so their Y
# extent is LIP_REACH / sqrt(1 + slope^2) and their top rides the upper plane
# extended past Y = 0. Measured Y 1.026 / 1.655 / 1.342 / 0.892 / 0.635 on the
# five references against slopes 1.7857 / 0.7812 / 1.2037 / 2.1299 / 3.1538,
# and Y * sqrt(1 + slope^2) is 2.100 every time.
#
# In plan the flat runs |x| 15.400 .. 25.400 from the compartment's centre:
# LIP_LEN long, starting LIP_GAP out from the scallop's own filleted edge at
# FINGER_R + FINGER_FILLET. `Chamfer lip` then widens the BASE by LIP_CHAMFER a
# side at 45 degrees in Y. Where the lip is shorter in Y than LIP_CHAMFER the
# chamfer is truncated and the tip stays wide, which is what the references
# show: tips of 10.000 / 10.000 / 10.354 / 10.622 / 11.135 against reaches of
# 1.342 / 1.655 / 1.026 / 0.892 / 0.635.
LIP_LEN = 10.000           # `#LipLength`
LIP_GAP = 3.000            # `#LipDistanceFromFingerHole`, from the scallop edge
LIP_CHAMFER = 1.200        # `Chamfer lip`, 45 degrees, measured in Y
# NOT `#LipHeight` — that is SLANT_STEP, the band's VERTICAL thickness. This is
# how far the lip reaches ALONG the slant, and no studio variable is known for
# it; it is measured 2.100 on all five references across five different slopes.
LIP_REACH = 2.100          # along the slant plane, from Y = 0


def lip_reach_y(p, d, first):
    """How far a lip stands proud in Y — LIP_REACH taken along the slant."""
    slope = slant_slope(p, d, first)
    return LIP_REACH / math.sqrt(1.0 + slope * slope)


def lip_plan(p, d, first):
    """The lip's plan-view outline, as (x, y) relative to its own inner edge.

    x is |x| from the compartment centre; the caller mirrors it.
    """
    y1 = lip_reach_y(p, d, first)
    lo = FINGER_R + FINGER_FILLET + LIP_GAP
    hi = lo + LIP_LEN
    # The base is ALWAYS the full LIP_CHAMFER out. Where the lip is shorter in Y
    # than LIP_CHAMFER the chamfer plane simply runs out of lip; it does not
    # start closer in. Getting that backwards leaves the base 12.052 wide
    # instead of 12.400 on the three references where y1 < LIP_CHAMFER.
    if y1 <= LIP_CHAMFER:
        return [(lo - LIP_CHAMFER, 0.0), (hi + LIP_CHAMFER, 0.0),
                (hi + LIP_CHAMFER - y1, y1), (lo - LIP_CHAMFER + y1, y1)]
    return [(lo - LIP_CHAMFER, 0.0), (hi + LIP_CHAMFER, 0.0),
            (hi, LIP_CHAMFER), (hi, y1), (lo, y1), (lo, LIP_CHAMFER)]


def slant_band(p, d, first, x0, x1):
    """The prism between the two slant planes, over X in [x0, x1]."""
    with BuildPart() as part:
        with BuildSketch(Plane.YZ):
            with BuildLine():
                Polyline((0.0, slant_z(p, d, first, 0.0, lower=True)),
                         (0.0, slant_z(p, d, first, 0.0)),
                         (4.0, slant_z(p, d, first, 4.0)),
                         (4.0, slant_z(p, d, first, 4.0, lower=True)),
                         close=True)
            make_face()
        extrude(amount=x1 - x0)
    return part.part.moved(Location((x0, 0, 0)))


def rear_lips(p, d, first, part):
    """Add the lips: the plan outline, clipped to the band between the slants."""
    y1 = lip_reach_y(p, d, first)
    pts = lip_plan(p, d, first)
    # Tall enough to reach the slant band, which sits around Z = 44; extruding
    # +-40 about the origin misses it entirely.
    tall = 200.0
    with BuildPart() as blank:
        with BuildSketch(Plane.XY) as sk:
            with BuildLine():
                Polyline(*pts, close=True)
            make_face()
        extrude(amount=tall, both=True)
    one = blank.part
    lips = []
    for xc in compartment_x(p, d):
        band = slant_band(p, d, first, xc - 30.0, xc + 30.0)
        for sign in (+1, -1):
            lip = one if sign > 0 else one.mirror(Plane.YZ)
            lips.append(lip.moved(Location((xc, 0, 0))) & band)
    return part.fuse(*lips)


# `Lip Rest` / `Chamfer lip rest` — the recess the NEXT holder's lip drops into.
# A REMOVE: the lip's own face, extruded along `LipPlane` "through all" from a
# starting offset of `#calSlotDepth * 2`.
#
# `LipPlane`'s direction is ALONG the slant, down and back, so the swept prism
# leans at the cascade angle. Both parts of that are measured. On `333` the cut
# first meets material at `Y -7.668`, and `calSlotDepth * 2 = 12.000` taken
# along the slant from `Y = 0` lands at `-7.673`. On `246` the offset is
# `14.400`, which puts the start inside the cavity, so the cut shows only where
# it crosses the back wall at `Y -8.400 .. -9.200` — and there its Z runs
# `25.822 .. 29.249` against `25.821 .. 29.250` measured.
#
# The section is the lip's OWN band — `LIP_LEN + 2 * LIP_CHAMFER` wide, exactly
# the lip's base, with NO clearance. Allowing 0.300 a side leaves 14.66 of error
# against 4.88 without it.
# `Through all` in the dialog, and the geometry agrees: the removed volume
# stops changing once the sweep passes ~20, so anything longer is the same
# cut. 200 clears the tallest holder's diagonal from any start.
LIP_REST_THROUGH = 200.0
LIP_REST_CHAMFER = 1.500   # `Chamfer lip rest`, 45 degrees (Allan)


def lip_rests(p, d, first, part):
    """Cut the lip rests."""
    slope = slant_slope(p, d, first)
    t0 = 2.0 * d.calSlotDepth
    width = LIP_LEN + 2 * LIP_CHAMFER
    # An OBLIQUE prism, not a right one: the lip's face lies in the plane Y = 0
    # and is extruded ALONG the slant, which is not its normal, so every
    # cross-section at constant Y is that same upright rectangle translated.
    # Building it as a rotated box instead gives perpendicular end faces, and
    # the near end then reaches 0.769 further forward in Y and sits 0.6 low in
    # Z — both measurable against `333`, whose cut starts at Y -7.668 where
    # `2 * calSlotDepth` along the slant lands, not at the -6.899 a right prism
    # would give.
    unit = 1.0 / math.sqrt(1.0 + slope * slope)
    dirv = Vector(0.0, -unit, -slope * unit)
    # `Chamfer lip rest` — LIP_REST_CHAMFER at 45 degrees on the rest's two long
    # side edges, so the section is a HEXAGON and not a rectangle: `width` at
    # the top and `width - 2 * LIP_REST_CHAMFER` at the bottom. Which PAIR of
    # edges is measured, not assumed. Against the ten references the residual
    # in this band is 4.88 for the lower pair, 25.59 for the upper, and 66.32
    # for a plain rectangle.
    c = LIP_REST_CHAMFER
    w, h = width / 2, SLANT_STEP / 2
    lo = -1.0                              # the LOWER pair
    with BuildSketch(Plane.XZ) as sk:
        with BuildLine():
            Polyline((-w, -lo * h), (w, -lo * h), (w, lo * (c - h)),
                     (w - c, lo * h), (-(w - c), lo * h), (-w, lo * (c - h)),
                     close=True)
        make_face()
    x_mid = FINGER_R + FINGER_FILLET + LIP_GAP + LIP_LEN / 2
    tools = []
    for xc in compartment_x(p, d):
        for sign in (+1, -1):
            at = Vector(xc + sign * x_mid, 0.0,
                        slant_top(d) - SLANT_STEP / 2) + dirv * t0
            face = sk.sketch.moved(Location(at))
            tools.append(extrude(face, amount=LIP_REST_THROUGH, dir=dirv))
    return part.cut(*tools)


# `Bottom Text` — two blocks engraved ENGRAVE into the underside, in TWO faces
# as the Pusher is: the name in Orbitron Bold and the capacity in Open Sans
# Bold. Confirmed exactly, calculated against measured ink width:
#
#     246 Sl   'CC 7.0 - Dominion'    97.230 / 97.231   '12 Sleeved'   50.967 / 50.947
#     333 Sl   'CC 7.0 - Dominion'    81.025 / 81.026   '10 Sleeved'   42.472 / 42.456
#     InnoMSl  'CC 7.0 - Innovation'  94.981 / 94.982   '10 Sleeved'   46.012 / 45.994
#     Cmp105   'CC 7.0 - Compile'     70.684 / 70.685   '7 Sleeved'    35.444 / 35.436
#     FCM198   'CC 7.0 - FCM'         45.328 / 45.328   '12 Unsleeved' 40.888 / 40.876
#
# The name reads `CC <version> - <GameName>` — `GameName`, so FCM gets its short
# form, which is what the studio has. The capacity is the holder's OWN card
# count, so the first-riser holder shows `FirstSlidingSlotCards`.
#
# Both blocks are inset TEXT_INSET past the end blocks, the name left-aligned
# and the capacity right-aligned, and both are engraved ENGRAVE deep.
ENGRAVE = 0.200
TEXT_INSET = 10.000        # past the end block, from Allan's sketch
TEXT_GAP = 4.000           # the least space left between the two blocks
# How far short of the right-hand inset the capacity's INK stops, in EM.
# Measured, not derived, like the TokenHolder's `TRAIL`: with the block
# right-aligned on its advance the build sat 0.0130 em left of every
# reference (0.0119 on `246`), at five different sizes, so it scales with
# the em and is a property of Onshape's right alignment rather than of the
# inset. It is not the last glyph's right bearing (`d` is 0.0776 in Open
# Sans Bold), and it is not the TokenHolder's 0.0754 either — that one is
# Orbitron — so the two are recorded separately rather than pretended one.
CAP_TRAIL = 0.0646


def text_blocks(p, d, first):
    """(name, capacity) — the two strings, in reading order."""
    cards = p.FirstSlidingSlotCards if first else p.CardsPerSlidingSlot
    return (f"CC {p.Version} - {p.GameName}",
            f"{cards} {'Sleeved' if p.isSleeved else 'Unsleeved'}")


def text_size(p, d, first):
    """The em size, and a DELIBERATE DIVERGENCE.

    Onshape sizes by the DEPTH alone — the cap height is `depth - 2.000`, which
    reproduces every reference to a thousandth. It also takes no account of how
    long the strings are, and Onshape can only constrain a text box in one
    dimension, so on a short or a deep holder the two blocks collide: on
    `FirstHolder 246` they fuse into bars 46 and 62 mm wide, 5.8x the ink of a
    legible one, and run off the end of the part. Allan asked for that fixed.

    So the size is the LESSER of Onshape's and one that makes both blocks fit
    between their insets. That changes only what was broken — on all five
    references whose text does not collide the depth term is the smaller and the
    result is Onshape's own size exactly.
    """
    name, cap = text_blocks(p, d, first)
    by_depth = (holder_depth(p, d, first) - 2.0) / T.CAP
    x0, x1 = x_span(p, d)
    room = (x1 - x0) - 2 * (END_BLOCK + TEXT_INSET) - TEXT_GAP
    per_em = (T.ink(name, size=1.0)[0]
              + T.ink(cap, font=T.DETAIL_FONT, size=1.0)[0])
    # And no smaller than either face's cut floor (`cad/text.py`, "floors");
    # the shallowest holder in the catalogue is 3.17 em against a 2.00 floor,
    # so today this binds nowhere.
    floor = max(T.floor_size(T.LOGO_FONT), T.floor_size(T.DETAIL_FONT))
    size = max(min(by_depth, room / per_em), floor)
    if size * per_em > room + 1e-9:
        raise T.DoesNotFit(f"holder text at its floor ({size:.3f} em) does "
                           f"not fit between the insets")
    return size


def engrave(txt, font, size, x, baseline):
    """One block, as a solid to subtract from the underside.

    Placed by the PEN ORIGIN — `cad.text.metrics` gives the bearings, which no
    measurement of rendered ink can recover. The glyphs are turned over in Y
    (mirrored about XZ), which keeps their X order and puts glyph-up toward
    -Y: the orientation an UNDERSIDE engraving has to have to read the right
    way round once the holder is turned over, and the one every reference
    has — the period of `7.0` sits hard against the baseline on the +Y side
    of the cap band, and the descender of `p` reaches past it on the -Y side.
    The TokenHolder's `branding` is the same rule for the same reason. A
    block mirrored in X instead reads a half turn out, and one not mirrored
    at all is mirror-writing; ink width and volume cannot tell either apart.
    """
    _adv, lsb, lo, _hi = T.metrics(txt, font)
    with BuildPart() as part:
        with BuildSketch(Plane.XY):
            glyphs = Text(txt, font_size=size, font_path=font,
                          align=(Align.MIN, Align.MIN), mode=Mode.PRIVATE)
            add(Pos(lsb * size, lo * size) * glyphs)
        extrude(amount=ENGRAVE)
    return part.part.mirror(Plane.XZ).moved(Location((x, baseline, 0)))


def engraving(p, d, first):
    """The two text blocks as positioned solids — what `bottom_text` cuts.

    Exposed so a caller can price the engraving without cutting it:
    `tests/test_holder_corpus.py` builds the holder once with `text=False`
    and subtracts the engraving at either version's string, instead of
    building it twice.
    """
    name, cap = text_blocks(p, d, first)
    size = text_size(p, d, first)
    x0, x1 = x_span(p, d)
    depth = holder_depth(p, d, first)
    # The cap band centred in the depth, and the glyphs hanging toward -Y from
    # the baseline (`engrave`), so the baseline is the band's +Y edge. The
    # reference's baseline moves with the string's own ink extents and lands
    # within 0.4 of this; since the size is a divergence anyway, centring is
    # the rule that stays sensible when it binds.
    baseline = -(depth - T.CAP * size) / 2
    z = base_z(d)
    # The name is left-aligned on its pen origin, exact to 0.0004 against
    # every reference. The capacity is right-aligned: its ink stops CAP_TRAIL
    # short of the inset, and the pen origin is that less the ink's own run
    # (advance less the last right bearing), both read from the font.
    cap_adv = T.metrics(cap, T.DETAIL_FONT)[0]
    cap_rsb = T.right_bearing(cap, T.DETAIL_FONT)
    cap_pen = (x1 - END_BLOCK - TEXT_INSET
               - (CAP_TRAIL + cap_adv - cap_rsb) * size)
    return [engrave(txt, font, size, xa, baseline).moved(Location((0, 0, z)))
            for txt, font, xa in ((name, T.LOGO_FONT, x0 + END_BLOCK + TEXT_INSET),
                                  (cap, T.DETAIL_FONT, cap_pen))]


def bottom_text(p, d, first, part):
    """Cut both blocks into the underside, in one boolean."""
    return part.cut(*engraving(p, d, first))


def build(p, first=False, text=True):
    """`p` is a params.Primary. Returns the Holder as a build123d Part.

    `text=False` leaves the underside blank — the Pusher has the same flag —
    for a caller that wants to price the engraving separately (`engraving`).
    """
    d = D.derive(p)
    part = shell(p, d, first)
    part = card_pockets(p, d, first, part)
    part = lattice(p, d, first, part)
    part = finger_cutouts(p, d, first, part)
    part = side_slots(p, d, first, part)
    part = rear_lips(p, d, first, part)
    part = lip_rests(p, d, first, part)
    return bottom_text(p, d, first, part) if text else part
