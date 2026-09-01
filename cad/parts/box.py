"""The Box.

The open-topped tray the cascade lives in: card slots across its width, a front
pocket, a rear pusher store, and the rim cutouts that hang the pushers.
Measured in `spec/BOX.md`; the Onshape feature tree it mirrors is transcribed
there in full, and the group functions below follow it in order.

Local frame (the part studio's):
    X   width, 0 at the centre, +-BoxWidth/2 at the outer walls
    Y   depth, 0 at the centre, -BoxDepth/2 the FRONT, +BoxDepth/2 the back
    Z   height, 0 at the bed, BoxHeight at the rim

INCOMPLETE. `build()` currently raises everything past the shell; see
`spec/BOX.md` "Still open" for what is left and `tests/test_box.py` for what is
proven. Nothing writes a Box to build/ yet.
"""
from build123d import (
    Box, BuildPart, BuildSketch, Kind, Location, Mode, Plane, Rectangle,
    extrude, offset,
)

from .. import derive as D
from .. import lock as L

WALL = D.WallThickness       # 1.600, confirmed on the STEPs at +-110.550


def box_width(p, d):
    """`#BoxWidth`. Allan's sketch variable, verified on all 48 boxes."""
    return 2 * WALL + 11.1 + d.calSlotwidth * p.HorizontalSlots


def box_depth(p, d):
    """`#BoxDepth`. Same expression as `calLidDepth` less a constant 8.100."""
    return (6.0 + (p.RisingSliders - 1) * d.calSliderDistance
            + d.calFirstSliderDistance) + d.calFrontPocketDepth


def pusher_slots(p, d):
    """Centreline X of each rear pusher-storage slot, left to right.

    `#dBackSlotWidth` is the pitch, and it is `calPusherTotalDepth + 4.000` —
    the stored pusher's own depth plus 2.00 of clearance a side. The slots pack
    from the LEFT INNER WALL, each centred in its own cell, so the first is half
    a pitch in. Read off the rim cutouts of four STEPs spanning 2 and 3 slots
    and C2/C3/C5; `tests/test_box.py` holds it to them.
    """
    pitch = d.calPusherTotalDepth + 4.0
    x0 = -box_width(p, d) / 2 + WALL
    return [x0 + (k + 0.5) * pitch for k in range(pusher_slot_count(p))]


def pusher_slot_count(p):
    """`#calPusherSlots`. 2 for an S box and for every Innovation box, else 3.

    `components.pushers_for` computes the same thing from the size letter and
    gets Innovation XS wrong (no `XS` key, so it falls through to 3 against the
    box's 2). `isOnlyTwoPusherSlots` is the CAD's own answer and is used here.
    """
    if p.GameName == "Innovation":
        return 2
    return 2 if p.HorizontalSlots <= 3 else 3


def finger_hole_offset(p, d):
    """`#calFingerHoleOffset` — where the rear thumb cutout sits.

        (#calPusherSlots - 1 + (#HorizontalSlots - #calPusherSlots)/2)
        * #calSlotwidth

    Allan's expression, verbatim. It reads as: step right by one slot width per
    pusher slot after the first, then centre what is left over. Checks out at
    162.5 on `M4.21.10.45-Sl`, which is the value his feature tree shows.
    """
    n = pusher_slot_count(p)
    return (n - 1 + (p.HorizontalSlots - n) / 2) * d.calSlotwidth


def shell(p, d):
    """`Create box shape` — Top of box / Extrude solid box / Hollow out box.

    A plain rectangle, extruded the full BoxHeight and hollowed to WALL with
    the top face removed. The sketch is centred on the origin: the STEPs put
    the outer walls at exactly +-#BoxWidth/2.
    """
    with BuildPart() as part:
        with BuildSketch(Plane.XY):
            Rectangle(box_width(p, d), box_depth(p, d))
        extrude(amount=d.BoxHeight)
        top = part.faces().sort_by(lambda f: f.center().Z)[-1]
        offset(amount=-WALL, openings=top, kind=Kind.INTERSECTION,
               mode=Mode.REPLACE)
    return part.part


# The front pocket's back wall. Measured 1.000 thick on all five references —
# a panel at y = -#BoxDepth/2 + WALL + calFrontPocketDepth .. + 1.000 — and the
# bottom slot starts at its back face, so the constant belongs here until the
# Front pocket group is written and can own it.
FRONT_DIVIDER = 1.000


def side_floor(d):
    """How much floor is left standing at each end — `calSlotwidth / 2`.

    This is the point of the cut, and the better way round to state it: the
    floor is not removed to make room for something, it is removed EXCEPT here,
    because the **holders rest on these two strips when the box is not in use**
    (Allan). So the width is set by what has to be left, not by what goes.
    """
    return d.calSlotwidth / 2


def bottom_slot(p, d):
    """`Hole in bottom of box` — the rectangle cut clean through the floor,
    as (width, depth, y centre).

    Everything between the two side floors goes, so the width is

        #BoxWidth - 2*WallThickness - 2*side_floor
                  = 11.1 + calSlotwidth * (HorizontalSlots - 1)

    and in depth it runs from the back of the front pocket's divider to the
    inner face of the back wall — exactly the sliding card area.

    One plain rectangular prism, not one slot per pusher: on all six references
    the removed volume equals its own bounding box exactly, so there is nothing
    else in it. It is NOT aligned with the rear pusher storage slots, which sit
    at their own `#dBackSlotWidth` pitch.
    """
    width = box_width(p, d) - 2 * WALL - 2 * side_floor(d)
    y_front = -box_depth(p, d) / 2 + WALL + d.calFrontPocketDepth + FRONT_DIVIDER
    y_back = box_depth(p, d) / 2 - WALL
    return width, y_back - y_front, (y_front + y_back) / 2


# `Add depth to back`. The rear storage stands 4.500 proud of the sketch box —
# half of the 6.100 depth offset — and is where the pushers are stowed. In
# section, as offsets from #BoxDepth/2 (constant on all six references):
#
#     -1.600 .. -0.300   the back wall, 1.300: a 1.600 wall with 0.300 eaten
#     -0.300 .. +2.900   the pusher slot, 3.200 = LOCK_STANDARD's box slot depth
#     +2.900 .. +4.500   the outer back wall, 1.600
REAR_DEPTH = 4.500
SLOT_BITE = 0.300        # how far the pusher slot eats into the back wall


REAR_TOP = 85.000        # `Top of back` — the storage is capped here; only the
#                          END WALLS carry on to BoxHeight
PUSHER_REST = 3.000      # `Remove material, don't let pushers drop through`:
#                          the slot's floor, so a stored pusher rests 3.000 up
DIVIDER_W = 1.600        # `Divider` between adjacent pusher slots
HOLE_W = 10.000          # `Hanging holes` — the lattice through the back
HOLES_PER_SLOT = 5
HOLE_INSET = 8.300       # first hole, from the left inner wall
HOLE_ROWS = 3
HOLE_ROW_BOTTOM = 3.000
HOLE_ROW_TOP = 69.500
HOLE_ROW_GAP = 2.000
# The rim cutouts run from here to the rim: 5.000 tall, NOT the 5.25 that
# LOCK_STANDARD.md records ("z 99.75 -> 105.00"). Measured 100.000..105.000 on
# the unfilleted reference, where a cutout's volume is exactly
# 4.500 x 1.300 x 5.000 = 29.250. See spec/BOX.md.
RIM_CUTOUT_Z = 100.000


def rear_block(p, d):
    """`Add depth to back` — the solid the rest of the group carves.

    It reaches WALL/2 INTO the back wall rather than meeting it at
    y = #BoxDepth/2. Fusing two solids across an exactly coincident planar face
    leaves that face inside the result as a lamina: the solid still reports
    valid and still measures the right volume, but every later boolean against
    it fails — `ref & mine` came back as None. Half a wall of genuine overlap
    costs nothing (the back wall is solid there) and keeps the fuse honest.
    """
    y0 = box_depth(p, d) / 2 - WALL / 2
    depth = REAR_DEPTH + WALL / 2
    return Box(box_width(p, d), depth, d.BoxHeight).moved(
        Location((0, y0 + depth / 2, d.BoxHeight / 2)))


def slot_band(p, d):
    """(y0, y1) of the pusher slot itself — `LOCK_STANDARD.md`'s 3.200 box slot
    depth. It starts 0.300 INSIDE the sketch box, which is why the back wall
    measures 1.300 rather than WallThickness."""
    y0 = box_depth(p, d) / 2 - SLOT_BITE
    return y0, y0 + L.BOX_SLOT_DEPTH


def hanging_holes(p, d):
    """(x0, x1) of every opening in the back, left to right.

    Five per horizontal slot, `HOLE_W` wide, at a pitch of
    `(calSlotwidth - 2.000) / 5` within a slot; the groups themselves repeat at
    `calSlotwidth`, so the pier between two slots is 2.000 wider than the piers
    inside one. First hole `HOLE_INSET` from the left inner wall — a constant on
    every reference.
    """
    pitch = (d.calSlotwidth - 2.0) / HOLES_PER_SLOT
    x0 = -box_width(p, d) / 2 + WALL + HOLE_INSET
    return [(x0 + k * d.calSlotwidth + j * pitch,
             x0 + k * d.calSlotwidth + j * pitch + HOLE_W)
            for k in range(p.HorizontalSlots) for j in range(HOLES_PER_SLOT)]


def hole_rows():
    """(z0, z1) of each lattice row. Constant — the same three rows on every
    reference, so this is not a function of the riser count."""
    h = (HOLE_ROW_TOP - HOLE_ROW_BOTTOM - (HOLE_ROWS - 1) * HOLE_ROW_GAP) / HOLE_ROWS
    return [(HOLE_ROW_BOTTOM + i * (h + HOLE_ROW_GAP),
             HOLE_ROW_BOTTOM + i * (h + HOLE_ROW_GAP) + h) for i in range(HOLE_ROWS)]


def rear_storage(p, d, part):
    """The whole `Pusher holder & Rear Storage` group, less its thumb cutout.

    Every cut is a PLAIN rectangular box, and they are disjoint. Composing the
    negative first — empty the slot band, then subtract the rest and the
    dividers back out of that — produces a tool build123d cannot subtract with:
    the result measures the right volume and reports valid, but every later
    boolean against it returns nothing (`ref & mine` came back as None). The
    cavities are already separated by their dividers, so they can simply be
    listed.
    """
    BW, BD = box_width(p, d), box_depth(p, d)
    inner = BW / 2 - WALL
    y0, y1 = slot_band(p, d)
    n = pusher_slot_count(p)
    pitch = d.calPusherTotalDepth + 4.0
    left, top = -inner, d.BoxHeight + 1

    def slab(x_lo, x_hi, ylo, yhi, zlo, zhi):
        return Box(x_hi - x_lo, yhi - ylo, zhi - zlo).moved(
            Location(((x_lo + x_hi) / 2, (ylo + yhi) / 2, (zlo + zhi) / 2)))

    part = part + rear_block(p, d)
    cuts = [
        # `Top of back` — the storage is capped at REAR_TOP between the end
        # walls; the end walls run the full height and the full added depth.
        slab(-inner, inner, BD / 2, BD / 2 + REAR_DEPTH, REAR_TOP, top),
        # Right of the pusher slots — and of the divider that CLOSES the run —
        # the slot band is empty from the floor up.
        slab(left + n * pitch + DIVIDER_W, inner, y0, y1, WALL, top),
    ]
    # One cavity per pusher slot, open from PUSHER_REST up — the rest below it
    # is `Remove material, don't let pushers drop through`. A DIVIDER_W wall
    # stands at every boundary EXCEPT the left inner wall, which already is one:
    # n dividers for n slots, the last closing the run on the right. So cavity k
    # starts one divider in, and ends at its own boundary.
    for k in range(n):
        cuts.append(slab(left + k * pitch + (DIVIDER_W if k else 0.0),
                         left + (k + 1) * pitch, y0, y1, PUSHER_REST, top))
    # `Hanging holes` — through the back wall AND the dividers, reaching from
    # the card side to the outer wall.
    for x_lo, x_hi in hanging_holes(p, d):
        for z_lo, z_hi in hole_rows():
            cuts.append(slab(x_lo, x_hi, BD / 2 - WALL, y1, z_lo, z_hi))
    # The rim cutouts — the box's half of the pusher lock, at each slot's
    # centreline +- s. They cut the 1.300 back wall only; the outer wall is
    # already gone above REAR_TOP, which is why they are invisible from behind.
    _cls, sv = L.lock_class(d.calPusherTotalDepth)
    for centre in pusher_slots(p, d):
        for sign in (-1, +1):
            x = centre + sign * sv
            cuts.append(slab(x - L.BOX_CUTOUT_W / 2, x + L.BOX_CUTOUT_W / 2,
                             BD / 2 - WALL, y0, RIM_CUTOUT_Z, top))
    for c in cuts:
        part = part - c
    return part


# `Lower the front`. The front wall stops here instead of at BoxHeight, so the
# cards can be seen and reached. Measured at exactly 68.600 on all five
# references, and constant: every catalogue box has calPocketHeight 88.5 and
# calPocketDrop 8.0 (calMaxPocketHeight is CardHeight - 3.5 = 88.5 for every
# game but Colours and CraftGutermann), so nothing in the derived set varies
# here and a formula cannot be told from a constant. Treat it as measured.
FRONT_TOP = 68.600


def lower_front(p, d, part):
    """`Lower the front` — take the front wall down to FRONT_TOP.

    Only between the end walls: at z = 69.0 the front band still carries
    material over x +-(#BoxWidth/2 - WallThickness) .. +-#BoxWidth/2 on every
    reference, so the end walls run their full height.
    """
    BD = box_depth(p, d)
    inner = box_width(p, d) / 2 - WALL
    return part - Box(2 * inner, WALL + 1, d.BoxHeight + 1 - FRONT_TOP).moved(
        Location((0, -BD / 2 + (WALL - 1) / 2,
                  (FRONT_TOP + d.BoxHeight + 1) / 2)))


def build(p):
    """`p` is a params.Primary. Returns the Box as a build123d Part.

    Only the shell so far — every other feature group is still to be written.
    """
    d = D.derive(p)
    part = shell(p, d)
    w, depth, y = bottom_slot(p, d)
    # Cut Z from below the floor up to exactly WALL, so the boolean is clean
    # underneath and nothing above the floor is touched — the tree cuts this
    # before the sliders and dividers exist, and this keeps that true whatever
    # order the code ends up in.
    part = part - Box(w, depth, WALL + 1).moved(Location((0, y, (WALL - 1) / 2)))
    part = rear_storage(p, d, part)
    return lower_front(p, d, part)
