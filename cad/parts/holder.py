"""The Holder.

The card tray that rides the box's slider ribs. One per riser; a cascade's
holders form a staircase, and their sloped tops make one continuous diagonal
when the cascade is open. Measured in `spec/HOLDER.md`.

Local frame (the part studio's):
    X   0 at the centre of the FIRST compartment, +k * calSlotwidth for the rest
    Y   0 at the REAR face — `Rear lip`'s tabs stand proud of it, at Y > 0 —
        and NEGATIVE toward the front, which is the way the slant descends
    Z   0 midway between the base and the card pocket's TOP, both at
        (CardHeight - 1.5)/2

Two features here are MODELLED rather than asked for, because no kernel will
compute them: `Fillet 1` (`finger_tool`) and the chamfer on `Lip Rest`
(`lip_rests`)."""
import math

from build123d import (Axis, Box, BuildLine, BuildPart, BuildSketch, Cylinder,
                       Location, Plane, Polyline, Torus, Vector, extrude,
                       make_face)

from .. import derive as D
from ..geom import text_solid
from .. import text as T

# The vertical datum: the base and the TOP OF THE CARD POCKET are symmetric
# about Z = 0, and the pocket starts 2.000 above the base (spec/HOLDER.md,
# "The overall envelope").
HALF_TRIM = 1.500                         # half_height  = (CardHeight - 1.5)/2
POCKET_TRIM = 3.500                       # pocket height = CardHeight - 3.5

# Each end stands this far beyond the outer slot edge: END_BLOCK (carrying
# the side slot the box's rib runs in) plus 0.900 to the compartment wall.
# 30 of the 50 cached components still say 5.000 (spec/HOLDER.md).
END_EXTRA = 4.900
END_BLOCK = 4.000

WALL = 0.800                              # front and back wall thickness
DEPTH_GAP = 0.400                         # depth = sliderDistance - DEPTH_GAP

# `Top slant angle`: two PARALLEL planes, SLANT_STEP apart, both meeting the
# rear face (Y = 0) at the same Z, the upper at the top of the card pocket.
# The slope is the cascade diagonal (`slant_slope`) and `box.lip_slope` is its
# reciprocal. SLANT_STEP exists for the rear lip, whose section is the band.
SLANT_STEP = 2.000         # `#LipHeight`


def pocket_height(d):
    """`calMaxPocketHeight`'s first term."""
    return d.CardHeight - POCKET_TRIM


def half_height(d):
    """The base below, the card pocket's top the same distance above."""
    return (d.CardHeight - HALF_TRIM) / 2


def base_z(d):
    """The underside."""
    return -half_height(d)


def pocket_z(d):
    """(bottom, top) of `Hole for cards`."""
    top = half_height(d)
    return top - pocket_height(d), top


def slant_top(d):
    """Z where the upper slant plane meets the front face — constant whatever
    the slope."""
    return pocket_height(d) / 2


def slider_distance(d, first):
    """The holder's OWN slider distance: the first-riser holder is the same
    holder made deeper, so everything keyed to the slot depth takes
    `calFirstSliderDistance` instead."""
    return d.calFirstSliderDistance if first else d.calSliderDistance


def holder_depth(d, first):
    """Front face to back face: `sliderDistance - 0.400`."""
    return slider_distance(d, first) - DEPTH_GAP


def holder_width(d):
    """`calSlotwidth * HorizontalSlots + 9.800`."""
    return d.calSlotwidth * d.HorizontalSlots + 2 * END_EXTRA


def x_span(d):
    """(min, max) X. The frame's origin is the FIRST compartment's centre, so
    this is NOT symmetric: the part runs from -(calSlotwidth/2 + END_EXTRA) to
    the last compartment's centre plus the same."""
    half = d.calSlotwidth / 2 + END_EXTRA
    return -half, (d.HorizontalSlots - 1) * d.calSlotwidth + half


def deep_at_back(d, first):
    """Is this the deeper first-riser holder of a row that puts it at the BACK
    (`derive.isDeepSlotAtBack`)? Three things differ: NO rear lips, the PLAIN
    holders' slant anchored at the front edge so its rear rises instead, and a
    thumb scallop centred on that taller rear. spec/HOLDER.md, "The deep
    holder at the back"."""
    return bool(first) and bool(d.isDeepSlotAtBack)


def slant_slope(d, first):
    """`dZ/dY` of `Top slant angle` — the cascade diagonal. The deeper
    first-riser holder is therefore SHALLOWER, dropping the same rise over
    more depth, unless it is at the BACK (`deep_at_back`)."""
    if deep_at_back(d, first):
        return D.cascade_slope(d, slider_distance(d, False))
    return D.cascade_slope(d, slider_distance(d, first))


def slant_rear(d, first):
    """Z where the upper slant plane meets the REAR face (Y = 0): `slant_top`
    on every holder — except the deep holder at the back, whose front edge
    stays where its own slant would put it (that is where the next holder's
    lips land in play) and whose rear top rises to suit."""
    if not deep_at_back(d, first):
        return slant_top(d)
    if d.rev.seated_lips:
        # The plain diagonal continued through it: the holder in front only
        # seats its lips if this one's front edge is on that line
        # (`spec/HOLDER.md`, "Lips that seat").
        return (slant_top(d) + slant_slope(d, first) * slider_distance(d, first)
                - d.calHeightIncrement)
    own = D.cascade_slope(d, slider_distance(d, first))
    return slant_top(d) + (slant_slope(d, first) - own) * holder_depth(d, first)


def slant_z(d, first, y, lower=False):
    """Z of the slant plane at depth `y` (y <= 0)."""
    return slant_rear(d, first) - (SLANT_STEP if lower else 0.0) + slant_slope(d, first) * y


def shell(d, first):
    """`Pocket outline` / `Extrude 1`, cut by `Top slant angle`. Built as its
    YZ section swept along X rather than as a block minus a half-space, so the
    slope enters as two corner heights and there is no rotated tool."""
    x0, x1 = x_span(d)
    depth = holder_depth(d, first)
    z0 = base_z(d)
    with BuildPart() as part:
        with BuildSketch(Plane.YZ):
            with BuildLine():
                Polyline((0.0, z0), (-depth, z0),
                         (-depth, slant_z(d, first, -depth)),
                         (0.0, slant_z(d, first, 0.0)),
                         close=True)
            make_face()
        extrude(amount=x1 - x0)
    return part.part.moved(Location((x0, 0, 0)))


# `Horizontal capacity` patterns the compartment along X at calSlotwidth; the
# wall between two compartments is DIVIDER thick, so a pocket is that much
# narrower than its slot.
DIVIDER = 1.600


def compartment_x(d):
    """Centre X of each card compartment. The frame's origin is the first."""
    return [k * d.calSlotwidth for k in range(d.HorizontalSlots)]


# `Card holder bottom` drops the pocket's floor FLOOR_DROP below the sketch
# datum. The `Hole outline` sketch is still measured from the UNDROPPED datum,
# so `pocket_z` returns the datum and this is applied only to the cut.
FLOOR_DROP = 0.200


def card_pockets(d, first, part):
    """`Hole for cards`, plus `Card holder bottom`'s FLOOR_DROP — inset WALL
    from both faces and DIVIDER/2 from each slot edge."""
    depth = holder_depth(d, first)
    z0, z1 = pocket_z(d)
    z0 -= FLOOR_DROP
    w = d.calSlotwidth - DIVIDER
    over = 10.0                            # cut through whatever is above
    tool = Box(w, depth - 2 * WALL, z1 - z0 + over)
    # Every per-compartment feature here is ONE boolean with all its tools
    # (see box.rear_storage): they are disjoint, so the shape is the same,
    # and the body is walked once.
    return part.cut(*[tool.moved(Location((x, -depth / 2, (z0 + z1 + over) / 2)))
                      for x in compartment_x(d)])


# `Hole outline` / `Vertical slits in holder` / `Remove card holes` — the
# lattice, cut clean through both walls. Rows are `window_rows` windows with a
# RAIL between and above them; columns are COLS windows of a FIXED `window_w`
# at (W + 2)/COLS pitch, LEFT-ALIGNED, so the MULLION absorbs the variation
# and the leftover on the right is the reference's asymmetry, not an error
# (spec/HOLDER.md, "The lattice column is a FIXED `10.000`").
#
# 7.0's window width is `#LipLength` REUSED. `LIP_LEN` below is the same
# variable doing its actual job on the rear lip and it does NOT move; from
# 7.1c the two part company, which is why the window is named separately.
WINDOW_W = 10.000          # 7.0: `#LipLength`, a constant
RAIL = 2.000               # between the window rows
ROWS = 3
COLS = 5
# From 7.1c the lattice is STOUTER (`stout_lattice`): the mullion was an
# island thin enough to snap mid-print. Sides stay vertical and tops
# horizontal — filleting these corners was tried on real prints and is WORSE.
# `spec/HOLDER.md`, "A stouter lattice".
WINDOW_W_STOUT = 9.000
ROWS_STOUT = 4
OUTLINE_INSET = 3.000      # each side of the slot
OUTLINE_BASE = 2.000       # above the card pocket's bottom
OUTLINE_TOP_TERM = 76.500  # HoleOutlineHeight = this - calHeightIncrement


def outline(d):
    """(width, height, bottom Z) of one compartment's `Hole outline`."""
    return (d.calSlotwidth - 2 * OUTLINE_INSET,
            OUTLINE_TOP_TERM - d.calHeightIncrement,
            pocket_z(d)[0] + OUTLINE_BASE)


def window_w(d):
    """The window's width. `stout_lattice` narrows it to widen the mullion;
    the PITCH does not move, so only a window's +X edge does."""
    return WINDOW_W_STOUT if d.rev.stout_lattice else WINDOW_W


def window_rows(d):
    """How many rows the outline is divided into."""
    return ROWS_STOUT if d.rev.stout_lattice else ROWS


def window_grid(d):
    """(x0, x1, z0, z1) of every lattice window in the FIRST compartment."""
    w, h, z0 = outline(d)
    rows = window_rows(d)
    win_h = (h - rows * RAIL) / rows
    pitch = (w + 2.0) / COLS
    out = []
    for r in range(rows):
        zr = z0 + r * (win_h + RAIL)
        for c in range(COLS):
            xc = -w / 2 + c * pitch
            out.append((xc, xc + window_w(d), zr, zr + win_h))
    return out


def windows(d, first, part):
    """Cut the lattice windows through both walls, in every compartment."""
    depth = holder_depth(d, first)
    tools = []
    for x0, x1, z0, z1 in window_grid(d):
        tool = Box(x1 - x0, depth + 2.0, z1 - z0)
        for xc in compartment_x(d):
            tools.append(tool.moved(
                Location((xc + (x0 + x1) / 2, -depth / 2, (z0 + z1) / 2))))
    return part.cut(*tools)


# `Finger Cutouts` — one per compartment, on its centre: a plain circle of
# FINGER_R centred ON the upper slant plane where it meets the Y = 0 face
# (`slant_rear`), so it stays FINGER_R deep even on the deep holder at the
# back, the one holder whose `slant_rear` is not `slant_top`.
#
# The radius is 12.000 and NOT the 12.400 the circular edges report — the same
# trap as the Box's thumb: `Fillet 1` consumes the cylindrical face entirely,
# leaving only torus, so only a section at mid-wall recovers the true circle.
FINGER_R = 12.000
FINGER_FILLET = 0.400


def finger_tool(depth):
    """The scallop cut, with `Fillet 1` MODELLED rather than filleted: the
    front wall is `2 * FINGER_FILLET` thick, so its two rounds merge into a
    single torus — a degenerate case NO kernel will compute (spec/HOLDER.md,
    "`Fillet 1` is MODELLED")."""
    # It stops at the BACK wall's inner face: the reference keeps that wall
    # whole behind the scallop, which is what holds the cards in — easy to
    # miss, since sampling the front wall alone cannot see it.
    reach = depth - WALL
    core = Cylinder(FINGER_R, reach + 1.0, rotation=(90, 0, 0)).moved(
        Location((0, (1.0 - reach) / 2, 0)))
    ring = (Cylinder(FINGER_R + FINGER_FILLET, 2 * FINGER_FILLET,
                     rotation=(90, 0, 0))
            - Cylinder(FINGER_R, 2 * FINGER_FILLET + 1.0, rotation=(90, 0, 0)))
    bead = ring - Torus(FINGER_R + FINGER_FILLET, FINGER_FILLET).rotate(
        Axis.X, 90)
    return core + bead.moved(Location((0, -FINGER_FILLET, 0)))


def finger_cutouts(d, first, part):
    depth = holder_depth(d, first)
    tool = finger_tool(depth)
    # Centred on the Y = 0 wall's OWN top line: `slant_rear`, NOT `slant_top`,
    # which on the deep holder at the back would cut that much deeper than
    # FINGER_R into the wall.
    return part.cut(*[tool.moved(Location((x, 0.0, slant_rear(d, first))))
                      for x in compartment_x(d)])


# `Side slot solid` / `Side slot` / `Side slot hole` / `Mirror Side` — the
# groove each end runs on, which is the BOX's slider rib plus 0.200 a side of
# clearance. The two parts were measured independently and agree without
# either having been fitted to the other (spec/HOLDER.md, "The side slot is
# the BOX's rib").
SLOT_W = 1.900

# The MOUTH of the slot is flared, a DELIBERATE DIVERGENCE: the holder prints
# base down, so the slot's bottom edge is its FIRST LAYER and an elephant's
# foot closes the groove exactly where the holder sits when the cascade is
# shut. It is also the lead-in for dropping the holder onto the rib.
#
# The BOX's rib gets no matching chamfer, deliberately: its flank is buried in
# the floor slab until `box.floor_top`, so a chamfer at its base would be cut
# inside the slab. `spec/HOLDER.md`, "The mouth of the slot is flared".
SLOT_MOUTH_CHAMFER = 0.300


def mouth_flare(d, first):
    """The prism that opens the slot's mouth: `SLOT_MOUTH_CHAMFER` wider a
    side than the groove below the base, back to `SLOT_W` over the same
    height, so the wall runs out at 45 degrees — self-supporting, printed base
    down. Centred on X = 0 so the caller places it like `tool`."""
    c = SLOT_MOUTH_CHAMFER
    yc = -holder_depth(d, first) / 2
    z0 = base_z(d)
    half = SLOT_W / 2
    reach = END_BLOCK + 1.0
    with BuildPart() as prism:
        with BuildSketch(Plane.YZ):
            with BuildLine():
                Polyline((yc - half - c, z0 - 1.0),
                         (yc + half + c, z0 - 1.0),
                         (yc + half + c, z0),
                         (yc + half, z0 + c),
                         (yc - half, z0 + c),
                         (yc - half - c, z0),
                         close=True)
            make_face()
        extrude(amount=reach)
    return prism.part.moved(Location((-reach / 2, 0, 0)))


def side_slots(d, first, part):
    x0, x1 = x_span(d)
    depth = holder_depth(d, first)
    z0 = base_z(d)
    tall = slant_rear(d, first) - z0 + 2.0
    # END_BLOCK deep, plus 1.0 of overshoot past the end so the cut leaves no
    # coincident face; likewise 1.0 below the base and above the slant.
    tool = Box(END_BLOCK + 1.0, SLOT_W, tall)
    lead = mouth_flare(d, first)
    for x, inward in ((x0, +1), (x1, -1)):
        cx = x + inward * (END_BLOCK / 2 - 0.5)
        part = part - tool.moved(
            Location((cx, -depth / 2, z0 - 1.0 + tall / 2)))
        part = part - lead.moved(Location((cx, 0, 0)))
    return part


# `Rear lip` — two tabs per compartment, standing proud of the Y = 0 face,
# which is the face Onshape calls the REAR: that fixes the frame's sense.
#
# In section they are the band between the TWO slant planes. In plan each is
# LIP_LEN long, starting LIP_GAP out from the scallop's filleted edge;
# `Chamfer lip` widens the BASE by LIP_CHAMFER a side at 45 degrees in Y,
# truncated where the lip is shorter in Y than the chamfer (spec/HOLDER.md,
# "`Rear lip`, and what the second slant plane is for").
LIP_LEN = 10.000           # `#LipLength`
LIP_GAP = 3.000            # `#LipDistanceFromFingerHole`, from the scallop edge
LIP_CHAMFER = 1.200        # `Chamfer lip`, 45 degrees, measured in Y
# NOT `#LipHeight` — that is SLANT_STEP, the band's VERTICAL thickness. This
# is how far the lip reaches ALONG the slant; no studio variable is known for
# it, and it is measured on all five references.
LIP_REACH = 2.100          # along the slant plane, from Y = 0 — 7.0 to 7.2d


def lip_reach_y(d, first):
    """How far a lip stands proud in Y. From 7.2e (`rev.seated_lips`) the gap
    to the holder behind plus its front wall, so the lip spans the gap, fills
    the rest notched through that wall and stops at the wall's inner face
    (`spec/HOLDER.md`, "Lips that seat"); before it, LIP_REACH along the
    slant."""
    if d.rev.seated_lips:
        return D.CardHolderGap + WALL
    slope = slant_slope(d, first)
    return LIP_REACH / math.sqrt(1.0 + slope * slope)


def lip_plan(d, first):
    """The lip's plan-view outline, as (x, y) relative to its own inner edge.
    x is |x| from the compartment centre; the caller mirrors it."""
    y1 = lip_reach_y(d, first)
    lo = FINGER_R + FINGER_FILLET + LIP_GAP
    hi = lo + LIP_LEN
    # The base is ALWAYS the full LIP_CHAMFER out: where the lip is shorter in
    # Y than LIP_CHAMFER the chamfer plane runs out of lip, it does not start
    # closer in. (`<=` with a hair of slack: from 7.2e the reach equals the
    # chamfer to within a rounding error, and the six-point outline would then
    # carry a zero-length edge.)
    if y1 <= LIP_CHAMFER + 1e-6:
        return [(lo - LIP_CHAMFER, 0.0), (hi + LIP_CHAMFER, 0.0),
                (hi + LIP_CHAMFER - y1, y1), (lo - LIP_CHAMFER + y1, y1)]
    return [(lo - LIP_CHAMFER, 0.0), (hi + LIP_CHAMFER, 0.0),
            (hi, LIP_CHAMFER), (hi, y1), (lo, y1), (lo, LIP_CHAMFER)]


def lip_band_z(d, first, y, lower=False):
    """Z of the plane a rear lip's top (or `lower`, its underside) follows at
    `y` behind the rear face: the holder's own slant through 7.2d, and from
    7.2e (`rev.seated_lips`) the PLAIN slope from `slant_top` whatever the
    holder, because a lip is a key for the rest of the plain holder behind
    it. Both slants meet the rear face at `slant_top`."""
    if d.rev.seated_lips:
        z = slant_top(d) + slant_slope(d, False) * y
        return z - SLANT_STEP if lower else z
    return slant_z(d, first, y, lower)


def slant_band(d, first, x0, x1):
    """The prism between the two lip planes (`lip_band_z`), over X in
    [x0, x1]."""
    with BuildPart() as part:
        with BuildSketch(Plane.YZ):
            with BuildLine():
                Polyline((0.0, lip_band_z(d, first, 0.0, lower=True)),
                         (0.0, lip_band_z(d, first, 0.0)),
                         (4.0, lip_band_z(d, first, 4.0)),
                         (4.0, lip_band_z(d, first, 4.0, lower=True)),
                         close=True)
            make_face()
        extrude(amount=x1 - x0)
    return part.part.moved(Location((x0, 0, 0)))


def rear_lips(d, first, part, rear=False):
    """Add the lips: the plan outline, clipped to the band between the slants.
    NONE on a REAR holder (`rear`) or on the deep holder at the back
    (`deep_at_back`) — the lips hook the holder behind, and behind the
    rearmost holder is only the box's back wall."""
    if rear or deep_at_back(d, first):
        return part
    pts = lip_plan(d, first)
    # Tall enough to reach the slant band, which the origin does not.
    tall = 200.0
    with BuildPart() as blank:
        with BuildSketch(Plane.XY):
            with BuildLine():
                Polyline(*pts, close=True)
            make_face()
        extrude(amount=tall, both=True)
    one = blank.part
    # The band is the same prism at every compartment: built once, moved.
    band = slant_band(d, first, -30.0, 30.0)
    lips = []
    for xc in compartment_x(d):
        at = Location((xc, 0, 0))
        for sign in (+1, -1):
            lip = one if sign > 0 else one.mirror(Plane.YZ)
            lips.append(lip.moved(at) & band.moved(at))
    return part.fuse(*lips)


# `Lip Rest` / `Chamfer lip rest` — the recess the NEXT holder's lip drops
# into. A REMOVE: the lip's own face, extruded along `LipPlane` "through all".
# `LipPlane`'s direction is ALONG the slant, down and back, so the swept prism
# LEANS at the cascade angle (spec/HOLDER.md, "`Lip Rest` is an OBLIQUE
# prism"). LIP_REST_THROUGH is "through all": the removed volume stops
# changing well before it, so it is the same cut from any start.
LIP_REST_THROUGH = 200.0
REST_CHAMFER = 1.500   # `Chamfer lip rest`, 45 degrees — 7.0 to 7.2d
# From 7.2e: the rest is the lip's BASE plus this a side, and the lip's band
# plus this deep, so the TREAD carries the holder and the lip floats clear of
# the rest's floor.
REST_CLEARANCE = 0.200


def rest_depth(d):
    """How deep the rest is cut below the upper slant plane, from 7.2e: the
    lip band plus `REST_CLEARANCE`, or deeper where the Box's fixed lip needs
    it (`assembly.box_lip_seat`). One number per cascade, cut on every holder
    kind."""
    if d.rev.ribs_forward:
        # The box lip's band is the top of the rest band at the wall's face
        # from 7.2f (`box.lip_z`), so every rest is the plain depth.
        return SLANT_STEP + REST_CLEARANCE
    from .. import assembly as A
    return max(SLANT_STEP, A.box_lip_seat(d)) + REST_CLEARANCE


def lip_rests(d, first, part):
    """Cut the lip rests.

    From 7.2e (`rev.seated_lips`, `spec/HOLDER.md` "Lips that seat") the
    section is a plain rectangle — the lip's base plus `REST_CLEARANCE` a
    side, `rest_depth` below the upper plane and 1.000 above it so no face of
    the cut is coincident with the slant — starting MID-CAVITY, so the whole
    front wall is notched. Through 7.2d it is the 7.0 reading: the lip's OWN
    LENGTH by SLANT_STEP, with `Chamfer lip rest` widening the mouth into a
    trapezoid narrower at the bottom by the section height times the slant's
    COSINE, not its sine.

    An OBLIQUE prism, not a right one: the section lies in the plane Y = 0 and
    is extruded ALONG the slant, which is NOT its normal. Built as a rotated
    box it gets perpendicular end faces and misplaces the near end.
    """
    slope = slant_slope(d, first)
    unit = 1.0 / math.sqrt(1.0 + slope * slope)
    dirv = Vector(0.0, -unit, -slope * unit)
    if d.rev.seated_lips:
        t0 = holder_depth(d, first) / 2 / unit          # mid-cavity, along the slant
        half_w = LIP_LEN / 2 + LIP_CHAMFER + REST_CLEARANCE
        up, down = 1.0, rest_depth(d)
        with BuildSketch(Plane.XZ) as sk:
            with BuildLine():
                Polyline((-half_w, -down), (half_w, -down), (half_w, up),
                         (-half_w, up), close=True)
            make_face()
        z_at = 0.0
    else:
        t0 = 2.0 * d.calSlotDepth
        top = LIP_LEN / 2 + REST_CHAMFER
        bottom = LIP_LEN / 2 + REST_CHAMFER - SLANT_STEP * unit
        h = SLANT_STEP / 2
        with BuildSketch(Plane.XZ) as sk:
            with BuildLine():
                Polyline((-bottom, -h), (bottom, -h), (top, h), (-top, h), close=True)
            make_face()
        z_at = -SLANT_STEP / 2
    x_mid = FINGER_R + FINGER_FILLET + LIP_GAP + LIP_LEN / 2
    tools = []
    for xc in compartment_x(d):
        for sign in (+1, -1):
            at = Vector(xc + sign * x_mid, 0.0,
                        slant_rear(d, first) + z_at) + dirv * t0
            face = sk.sketch.moved(Location(at))
            tools.append(extrude(face, amount=LIP_REST_THROUGH, dir=dirv))
    return part.cut(*tools)


# `Bottom Text` — two blocks engraved into the underside, in TWO faces as the
# Pusher is. The name reads `CC <version> - <GameName>`; the capacity is the
# holder's OWN card count, so the first-riser holder shows
# `FirstSlidingSlotCards`. Both are inset TEXT_INSET past the end blocks, the
# name left-aligned and the capacity right-aligned.
ENGRAVE = 0.200
TEXT_INSET = 10.000        # past the end block
TEXT_GAP = 4.000           # the least space left between the two blocks
# The capacity's ink stops `text.box_trail` em short of the right-hand inset —
# a quarter of Open Sans Bold's space advance; `text.box_run` applies it, in
# `engraving`.


def text_blocks(d, first):
    """(name, capacity) — the two strings, in reading order."""
    cards = d.FirstSlidingSlotCards if first else d.CardsPerSlidingSlot
    return (f"{d.calVersion} - {d.GameName}",
            f"{cards} {'Sleeved' if d.isSleeved else 'Unsleeved'}")


def text_size(d, first):
    """The em size, and a DELIBERATE DIVERGENCE: Onshape sizes by the DEPTH
    alone and takes no account of how long the strings are, so on a short or a
    deep holder the blocks collide and run off the part. This is the LESSER of
    Onshape's and one that makes both fit between their insets, which changes
    only what was broken (spec/HOLDER.md, "The size")."""
    name, cap = text_blocks(d, first)
    by_depth = (holder_depth(d, first) - 2.0) / T.CAP
    x0, x1 = x_span(d)
    room = (x1 - x0) - 2 * (END_BLOCK + TEXT_INSET) - TEXT_GAP
    per_em = (T.ink(name, size=1.0)[0]
              + T.ink(cap, font=T.DETAIL_FONT, size=1.0)[0])
    # And no smaller than either face's cut floor (`cad/text.py`, "floors").
    floor = max(T.floor_size(T.LOGO_FONT), T.floor_size(T.DETAIL_FONT))
    size = max(min(by_depth, room / per_em), floor)
    if size * per_em > room + 1e-9:
        raise T.DoesNotFit(f"holder text at its floor ({size:.3f} em) does "
                           f"not fit between the insets")
    return size


def engrave(txt, font, size, x, baseline):
    """One block, as a solid to subtract from the underside, placed by the PEN
    ORIGIN. The glyphs are turned over in Y (mirrored about XZ), which keeps
    their X order and puts glyph-up toward -Y — what an UNDERSIDE engraving
    must do to read the right way round. Mirrored in X instead it reads a half
    turn out, unmirrored it is mirror-writing, and neither ink width nor
    volume can tell (spec/HOLDER.md, "Orientation, and the mirror")."""
    return text_solid(txt, font, size, ENGRAVE).mirror(Plane.XZ).moved(
        Location((x, baseline, 0)))


def engraving(d, first):
    """The two text blocks as positioned solids — what `bottom_text` cuts.
    Exposed so a caller can price the engraving without cutting it."""
    name, cap = text_blocks(d, first)
    size = text_size(d, first)
    x0, x1 = x_span(d)
    depth = holder_depth(d, first)
    # The cap band centred in the depth, and the glyphs hanging toward -Y from
    # the baseline (`engrave`), so the baseline is the band's +Y edge.
    baseline = -(depth - T.CAP * size) / 2
    z = base_z(d)
    # The name is left-aligned on its pen origin. The capacity is
    # right-aligned: its text box's right edge is on the inset, and the pen
    # origin is one `T.box_run` back from it.
    cap_pen = x1 - END_BLOCK - TEXT_INSET - T.box_run(cap, T.DETAIL_FONT) * size
    return [engrave(txt, font, size, xa, baseline).moved(Location((0, 0, z)))
            for txt, font, xa in ((name, T.LOGO_FONT, x0 + END_BLOCK + TEXT_INSET),
                                  (cap, T.DETAIL_FONT, cap_pen))]


def bottom_text(d, first, part):
    return part.cut(*engraving(d, first))


def build(d, first=False, text=True, rear=False, lattice=True):
    """The Holder as a build123d Part. `first` is the DEEPER first-riser
    holder; `rear` is the REARMOST one, which carries no rear lips.
    `text=False` leaves the underside blank, for a caller pricing the
    engraving separately; `lattice=False` leaves the walls' windows uncut — a
    test print (`cad.testkit`), never a catalogue holder."""
    part = shell(d, first)
    part = card_pockets(d, first, part)
    if lattice:
        part = windows(d, first, part)
    part = finger_cutouts(d, first, part)
    part = side_slots(d, first, part)
    part = rear_lips(d, first, part, rear)
    part = lip_rests(d, first, part)
    return bottom_text(d, first, part) if text else part
