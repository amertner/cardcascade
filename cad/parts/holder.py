"""The Holder.

The card tray that rides the box's slider ribs. One per riser; a cascade's
holders form a staircase, and their sloped tops make one continuous diagonal
when the cascade is open. Measured in `spec/HOLDER.md` against three
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

INCOMPLETE. `build()` stops after the rear lips. See `spec/HOLDER.md`
"Still open" for what is left and `tests/test_holder.py` for what is proven.
Nothing writes a Holder to build/ yet.
"""
import math

from build123d import (
    Axis, Box, BuildLine, BuildPart, BuildSketch, Cylinder, Location,
    Plane, Polyline, Torus, extrude, make_face,
)

from .. import derive as D

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
# wall. Measured 9.800 overall on all three references.
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
    """The underside. -45.250 on all three references."""
    return -half_height(d)


def pocket_z(d):
    """(bottom, top) of `Hole for cards` — 2.000 above the base, 88.500 tall."""
    top = half_height(d)
    return top - pocket_height(d), top


def slant_top(d):
    """Z where the upper slant plane meets the front face.

    Measured 44.250 on all three references whatever the slope. That is both
    half the pocket height and the pocket's top less 1.000 — the two are the
    same expression, so no reference is needed to tell them apart.
    """
    return pocket_height(d) / 2


# COMPILE holds a fixed card count in the depth, NOT `CardsPerSlidingSlot`.
#
# On `210 Card` (`CardsPerSlidingSlot` 7) the reference's slider distance is
# 12.000 sleeved and 7.200 unsleeved against `calSliderDistance` 8.000 and
# 5.200. Both come to exactly COMPILE_DEPTH_CARDS cards — 12 * 0.800 + 2.4 and
# 12 * 0.400 + 2.4 — and substituting that one number fixes EVERY Compile
# failure at once: the slant slope becomes the measured 1.5185 / 2.7333, both
# slant planes land on 44.250 and 42.250, and the lip's reach is 2.100 again.
# So the model is right and only the input differs.
#
# **Where 12 comes from is NOT known**, and the corpus says it is new: the old
# `Holder 5x7-r5-Sl.3mf` measures 8.404 deep, which is the 7-card rule. Compile
# has two rows and only `210 Card` has a reference, so a `105 Card` export would
# say whether 12 is a constant or something derived (it is also
# `CardsPerSlidingSlot + HorizontalSlots` and `+ RisingSliders` on this row,
# which disagree on the other). Until then this is measured, not derived.
COMPILE_DEPTH_CARDS = 12


def slider_distance(p, d, first):
    """The holder's OWN slider distance.

    The first-riser holder is the same box's holder made deeper, so everything
    keyed to the slot depth takes `calFirstSliderDistance` instead. The 246 pair
    is the only evidence that could tell these apart — everywhere else the two
    are equal — and it settles both the depth and the slant.
    """
    if p.GameName == "Compile":
        return d.calCardThickness * COMPILE_DEPTH_CARDS + 2.0 + D.CardHolderGap
    return d.calFirstSliderDistance if first else d.calSliderDistance


def holder_depth(p, d, first):
    """Front face to back face: `sliderDistance - 0.400`.

    9.200 / 20.000 / 8.000 on the three references against 9.600 / 20.400 /
    8.400, exact.
    """
    return slider_distance(p, d, first) - DEPTH_GAP


def holder_width(p, d):
    """`calSlotwidth * HorizontalSlots + 9.800`, measured exact on all 38 of
    the corpus holders that map to a parts.csv row as well as on the STEPs."""
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
    return (d.calHeightIncrement - 1.0) / (slider_distance(p, d, first) - 1.2)


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


def card_pockets(p, d, first, part):
    """`Hole for cards` — one pocket per compartment, cut clean out of the top.

    Inset WALL from both faces (measured: the walls are the only material left
    at a lattice rail's height) and DIVIDER/2 from each slot edge.
    """
    depth = holder_depth(p, d, first)
    z0, z1 = pocket_z(d)
    w = d.calSlotwidth - DIVIDER
    over = 10.0                            # cut through whatever is above
    tool = Box(w, depth - 2 * WALL, z1 - z0 + over)
    for x in compartment_x(p, d):
        part = part - tool.moved(Location((x, -depth / 2, (z0 + z1 + over) / 2)))
    return part


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
    for x0, x1, z0, z1 in window_grid(p, d):
        tool = Box(x1 - x0, depth + 2.0, z1 - z0)
        for xc in compartment_x(p, d):
            part = part - tool.moved(
                Location((xc + (x0 + x1) / 2, -depth / 2, (z0 + z1) / 2)))
    return part


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
    core = Cylinder(FINGER_R, depth + 2.0, rotation=(90, 0, 0)).moved(
        Location((0, -depth / 2, 0)))
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
    for x in compartment_x(p, d):
        part = part - tool.moved(Location((x, 0.0, slant_top(d))))
    return part


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
    for xc in compartment_x(p, d):
        for sign in (+1, -1):
            lip = one if sign > 0 else one.mirror(Plane.YZ)
            lip = lip.moved(Location((xc, 0, 0)))
            band = slant_band(p, d, first,
                              xc - 30.0, xc + 30.0)
            part = part + (lip & band)
    return part


def build(p, first=False):
    """`p` is a params.Primary. Returns the Holder as a build123d Part.

    INCOMPLETE — see the module docstring.
    """
    d = D.derive(p)
    part = shell(p, d, first)
    part = card_pockets(p, d, first, part)
    part = lattice(p, d, first, part)
    part = finger_cutouts(p, d, first, part)
    part = side_slots(p, d, first, part)
    return rear_lips(p, d, first, part)
