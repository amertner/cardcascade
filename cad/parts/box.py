"""The Box.

The open-topped tray the cascade lives in: card slots across its width, a front
pocket, a rear pusher store, and the rim cutouts that hang the pushers.
Measured in `spec/BOX.md`; the Onshape feature tree it mirrors is transcribed
there in full, and the group functions below follow it in order.

Local frame (the part studio's):
    X   width, 0 at the centre, +-BoxWidth/2 at the outer walls
    Y   depth, 0 at the centre, -BoxDepth/2 the FRONT, +BoxDepth/2 the back
    Z   height, 0 at the bed, BoxHeight at the rim

INCOMPLETE. `build()` stops after the label holders; the engraved text and
`Smooth box edges` are still to come. See `spec/BOX.md` "Still open" for what is
left and `tests/test_box.py` for what is proven. Nothing writes a Box to build/
yet.
"""
from build123d import (
    Align, Axis, Box, BuildLine, BuildPart, BuildSketch, Cylinder, Kind, Line,
    Location, Mode, Plane, Polygon, Pos, Rectangle, SlotOverall, Text,
    ThreePointArc, add, chamfer, extrude, fillet, make_face, offset, revolve,
)

from .. import derive as D
from .. import lock as L
from .. import text as T

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
PUSHER_REST_CAP = 25.000  # `Remove material, don't let pushers drop through`:
#                           the cavity floor never sits higher than this
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
REAR_THUMB_FILLET = 0.600   # `Fillet rear thumb hole` — NOT the front thumb's
#                             0.400; the wall it cuts is 1.600, not 1.000


def pusher_rest(p, d):
    """The cavity floor — how high a stored pusher sits.

        min(25.000, BoxHeight - calPusherTotalHeight - 0.500)

    A pusher is stored on EDGE and upright: `#dBackSlotWidth` is its own
    `calPusherTotalDepth` plus clearance measured along the box's WIDTH, so its
    staircase height stands vertically. The rest is then placed to bring the
    top of that staircase to `0.500` below the rim, where the tabs meet the box
    rim cutouts — until the cap takes over for a short pusher.

    Read off all 44 canonical Boxes in `individual/` by ray-probing the meshes
    (0 API calls). Three distinct values, two of them below the cap: `25.000`
    wherever `calPusherTotalHeight <= 79.5`, `24.500` at `80.000`, and `17.500`
    at `87.000` — which is the ceiling `calHeightIncrement` imposes, and so the
    lowest rest any cascade can have.
    """
    return min(PUSHER_REST_CAP, d.BoxHeight - d.calPusherTotalHeight - 0.5)


def _except(lo, hi, blocks):
    """`[lo, hi]` with every interval in `blocks` taken out of it."""
    out = [(lo, hi)]
    for a, b in blocks:
        keep = []
        for c, e in out:
            if b <= c or a >= e:
                keep.append((c, e))
                continue
            if c < a:
                keep.append((c, a))
            if b < e:
                keep.append((b, e))
        out = keep
    return [(a, b) for a, b in out if b - a > 1e-9]


def storage_dividers(p, d):
    """(x0, x1) of each `Divider` between rear storage slots.

    `n` dividers for `n` slots: one at every cavity boundary except the left
    inner wall, which already is one, and the last CLOSING the run on the
    right."""
    left = -box_width(p, d) / 2 + WALL
    pitch = d.calPusherTotalDepth + 4.0
    return [(left + k * pitch, left + k * pitch + DIVIDER_W)
            for k in range(1, pusher_slot_count(p) + 1)]


def rear_thumb_x(p, d):
    """Centre X of the `Thumb Cutout in back`.

        -#BoxWidth/2 + WallThickness + #calFingerHoleOffset
        + #dBackSlotWidth + 1.600

    So `calFingerHoleOffset` is NOT measured from the left inner wall but from
    the left edge of the SECOND storage cavity — one slot pitch and one divider
    in. Exact on all five references, whose pitches run 22.000 to 71.200, which
    is what separates that reading from a plain offset.
    """
    return (-box_width(p, d) / 2 + WALL + finger_hole_offset(p, d)
            + d.calPusherTotalDepth + 4.0 + DIVIDER_W)


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
        # It starts at the SLOT BAND, not at the sketch box: a divider reaches
        # SLOT_BITE forward of #BoxDepth/2, and cutting only from there left
        # that 0.300 sliver of each divider standing all the way to the rim.
        slab(-inner, inner, y0, BD / 2 + REAR_DEPTH, REAR_TOP, top),
        # Right of the pusher slots — and of the divider that CLOSES the run —
        # the slot band is empty from the floor up.
        slab(left + n * pitch + DIVIDER_W, inner, y0, y1, WALL, top),
    ]
    # One cavity per pusher slot, open from the rest up — what stands below it
    # is `Remove material, don't let pushers drop through`, and the hanging
    # holes cut through that too, so it is a lattice and not a plug. A DIVIDER_W
    # wall
    # stands at every boundary EXCEPT the left inner wall, which already is one:
    # n dividers for n slots, the last closing the run on the right. So cavity k
    # starts one divider in, and ends at its own boundary.
    for k in range(n):
        cuts.append(slab(left + k * pitch + (DIVIDER_W if k else 0.0),
                         left + (k + 1) * pitch, y0, y1,
                         pusher_rest(p, d), top))
    # `Hanging holes` — through the back wall in full, and on through the slot
    # band EXCEPT where a divider stands.
    #
    # DELIBERATE DIVERGENCE FROM ONSHAPE (Allan). There the holes are one
    # prism from the card side to the outer wall, so they cut the dividers
    # too — on `Box Dominion 244S` all three are severed clean through at
    # every hole row, and no reference escapes with fewer than one. The
    # openings are wanted; sawing through the pusher hangers is not. See
    # spec/BOX.md.
    divs = storage_dividers(p, d)
    for x_lo, x_hi in hanging_holes(p, d):
        for z_lo, z_hi in hole_rows():
            cuts.append(slab(x_lo, x_hi, BD / 2 - WALL, y0, z_lo, z_hi))
            for a, e in _except(x_lo, x_hi, divs):
                cuts.append(slab(a, e, BD / 2 - WALL, y1, z_lo, z_hi))
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
    # `Thumb Cutout in back` — a THUMB_R hole through the OUTER back wall only,
    # centred on REAR_TOP so the storage's cap takes its top half off. It falls
    # in the empty run to the right of the last divider on every reference, so
    # it never meets a pusher slot, and it does not touch the 1.300 inner back
    # wall: that reads as one unbroken piece at this height on all five.
    # `over` is 2.000, not the default: forward of the outer wall is the slot
    # band, empty at this X, but 5.000 would reach the inner back wall behind it.
    return part - round_hole(y1, BD / 2 + REAR_DEPTH, D.ThumbCutoutRadius,
                             REAR_THUMB_FILLET, rear_thumb_x(p, d), REAR_TOP,
                             over=2.0)


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


# `Round top box corners`. Above `Lower the front` only the two END WALLS reach
# the rim, and their top-front and top-back edges carry a big round: measured
# 4.600 on all six references, front and back alike, the arc starting at
# z = 105.000 - 4.600. It is the one number in this group.
CORNER_R = 4.600


def round_top_corners(p, d, part):
    """`Round top box corners` — a CORNER_R round on each end wall's top edges.

    Cut with a tool rather than a `fillet()` on picked edges: the two edges are
    trivially described (the whole rim, front and back) but hard to select
    stably, and a tool is also what keeps the tree order honest — anything
    ADDED above z = 100.4 later on, which is what the label holders and closing
    bumps do lower down, is untouched by a cut that has already happened.
    """
    BD, top = box_depth(p, d), d.BoxHeight
    width = box_width(p, d) + 20

    def corner(y_edge, inward):
        yc, zc = y_edge + inward * CORNER_R, top - CORNER_R
        far = CORNER_R + 10                      # into empty space, so the cut
        blank = Box(width, far, far).moved(      # has no coincident faces
            Location((0, yc - inward * far / 2, zc + far / 2)))
        return blank - Cylinder(CORNER_R, width + 2, rotation=(0, 90, 0)).moved(
            Location((0, yc, zc)))

    part = part - corner(-BD / 2, +1)                       # the front edge
    return part - corner(BD / 2 + REAR_DEPTH, -1)           # and the back one


# `Sliders`. Vertical ribs on both end walls, one per riser, that the holders
# ride on. Constant section on every reference: 1.500 wide in Y, standing
# 4.000 proud of the inner end wall, full height from the floor to the rim,
# with the top rounded.
SLIDER_W = 1.500
SLIDER_PROUD = 4.000
SLIDER_TOP_R = 0.700     # `Round top of slider`, on the two long top edges only


def slider_ribs(p, d):
    """(y0, y1) of each rib, BACK to front.

    A rib's BACK FACE sits on the centre of its card slot, and the slots are
    measured from the inner back wall: `calSliderDistance` each, except the
    last (frontmost) one, which is `calFirstSliderDistance`. So

        rib j back face = #BoxDepth/2 - WallThickness - (j*sd + sd/2)
        first slider    = #BoxDepth/2 - WallThickness - ((R-1)*sd + fsd/2)

    which is the tree's split exactly: `Replicate sliders` lays down the R-1
    plain ones at a `calSliderDistance` pitch, and `First Slider` places the
    odd one out. `Box Dominion 246S` is the only reference that can tell the
    two distances apart (20.400 against 9.600) and it lands on the nose.
    """
    back = box_depth(p, d) / 2 - WALL
    sd, fsd = d.calSliderDistance, d.calFirstSliderDistance
    ys = [back - (j * sd + sd / 2) for j in range(p.RisingSliders - 1)]
    ys.append(back - ((p.RisingSliders - 1) * sd + fsd / 2))
    return [(y - SLIDER_W, y) for y in ys]


def sliders(p, d, part):
    """`Sliders` — the ribs, mirrored to both end walls.

    Each rib reaches WALL/2 INTO the wall it stands on. That overlap is free
    (a union never removes material, and the wall is solid there) and it keeps
    the fuse off an exactly coincident face — the same trap `rear_block`
    documents.
    """
    inner = box_width(p, d) / 2 - WALL
    thick = SLIDER_PROUD + WALL / 2
    rib = Box(thick, SLIDER_W, d.BoxHeight)
    # `Round top of slider` rounds ACROSS the rib, not along it: the two top
    # edges parallel to X, leaving a 0.100 flat between two 0.700 radii. The
    # rib's front face stays square to the rim.
    rib = fillet(rib.faces().sort_by(Axis.Z)[-1].edges().filter_by(Axis.X),
                 SLIDER_TOP_R)
    for y0, y1 in slider_ribs(p, d):
        for sign in (-1, +1):
            part = part + rib.moved(Location((
                sign * (inner - (SLIDER_PROUD - WALL / 2) / 2),
                (y0 + y1) / 2, d.BoxHeight / 2)))
    return part


# `Front pocket`. The fixed pocket across the front of the box, divided into
# one compartment per horizontal slot. Every number here is measured exact on
# all six references.
FRONT_PAD = D.FrontPocketSidePaddingWidth   # 5.800, `Pad outermost slots`
FRONT_DIVIDER_W = 0.800                     # `Divider for front pocket`
POCKET_CUT_TOP = 87.500                     # where `Angled cutout` lands


# `Thumb and Lip`. The finger hole through the divider panel, one per
# horizontal slot, and the lip behind it.
THUMB_R = D.ThumbCutoutRadius     # 12.000, the studio constant
THUMB_Z = 87.500                  # the height the angled cutout reaches, too
THUMB_FILLET = 0.400              # `Fillet thumb hole`, on BOTH panel faces


def thumb_centres(p, d):
    """Centre X of each thumb hole, left to right — one per horizontal slot.

        -#BoxWidth/2 + WallThickness + calSliderSpaceLeftRight
        - 0.800 + calSlotwidth/2 + k*calSlotwidth

    i.e. half a slot in from the left inner wall, shifted by the side spacing
    less the divider width. Exact on all six references, at HorizontalSlots 3,
    4 and 5, and `MatPocket` does not move them even though it drops a divider.
    """
    x0 = (-box_width(p, d) / 2 + WALL + d.calSliderSpaceLeftRight
          - FRONT_DIVIDER_W + d.calSlotwidth / 2)
    return [x0 + k * d.calSlotwidth for k in range(p.HorizontalSlots)]


def round_hole(y0, y1, r, f, x, z, over=5.0):
    """A radius-`r` hole on Y from `y0` to `y1`, filleted `f` into BOTH faces,
    centred on (`x`, `z`). Revolved from its profile.

    Both thumbs use this — the one through the front pocket's divider panel and
    the one through the outer back wall — with different radii of fillet.

    `over` is how far the tool runs past each face, at the flared radius `r+f`,
    so the cut is clean rather than coincident with the face. It has to clear
    the face and STOP: the rear thumb's default 5.000 reached back through the
    empty slot band and bored a 12.600 hole in the 1.300 inner back wall, worth
    about 630 mm³ that the STEP does not remove.
    """
    m = f * (1 - 2 ** -0.5)          # the arc's midpoint, off its own corner
    with BuildPart() as tool:
        with BuildSketch(Plane.XY):
            with BuildLine():
                Line((0.0, y0 - over), (r + f, y0 - over))
                Line((r + f, y0 - over), (r + f, y0))
                ThreePointArc((r + f, y0), (r + m, y0 + m), (r, y0 + f))
                Line((r, y0 + f), (r, y1 - f))
                ThreePointArc((r, y1 - f), (r + m, y1 - m), (r + f, y1))
                Line((r + f, y1), (r + f, y1 + over))
                Line((r + f, y1 + over), (0.0, y1 + over))
                Line((0.0, y1 + over), (0.0, y0 - over))
            make_face()
        revolve(axis=Axis.Y)
    return tool.part.moved(Location((x, 0, z)))


def thumb_tool(p, d, x):
    """One thumb hole: a THUMB_R cylinder through the panel on Y, filleted
    THUMB_FILLET into both faces.

    Revolved from its profile rather than cut-then-`fillet()`: the angled
    cutout takes the top off the hole, so its edge is an ARC and not a circle,
    and picking that reliably is harder than stating the section once.

    The quarter arcs are given by three points, not by a radius: `RadiusArc`
    has four candidates through two points and picked one that left the hole a
    plain 12.400 cylinder — which the STEP's own profile caught at once.
    """
    _fw, fb, back = pocket_span(p, d)
    return round_hole(fb, back, THUMB_R, THUMB_FILLET, x, THUMB_Z)


# `Lip`. Two per thumb, symmetric about it, standing proud of the panel's BACK
# face for the front holder to catch on.
LIP_OFFSET = 20.400               # lip centre, from the thumb centre
LIP_LENGTH = D.LipLength          # 10.000, the top face
LIP_DEPTH = D.LipDepth            # 2.100, along the ramp
LIP_HEIGHT = D.LipHeight          # 2.000, in Z
LIP_CHAMFER = D.LipChamfer        # 1.200, 45 degrees in the XY plane
LIP_Z = 85.500                    # where it leaves the panel's back face


def lip_slope(d):
    """tan of the lip's angle from vertical.

        (calFirstSliderDistance - 1.200) / (calHeightIncrement - 1.000)

    **It is the HOLDER's diagonal cutout angle** (Allan) — the group opens with
    `Import Holder patterns` and this is what comes across. Confirmed against
    the diagonal face normal of all 46 canonical Holders in `individual/`
    (0 API calls), over four games, both sleevings, rises from 9.667 to 22.000
    and slider distances from 4.800 to 20.400; every one agrees.

    It is the FIRST slider distance because the lip meets the front holder.
    `Box Dominion 246S` is the only reference that can tell them apart —
    `20.400` against `9.600` — and it reads 1.280, not 0.560.
    """
    return (d.calFirstSliderDistance - 1.2) / (d.calHeightIncrement - 1.0)


def lip_tool(p, d, x):
    """One lip, centred on `x`.

    In section it is a PARALLELOGRAM: from the panel's back face at LIP_Z, up
    and back along LIP_DEPTH at `lip_slope`, LIP_HEIGHT tall in Z. Seen from
    above it is LIP_LENGTH long with a LIP_CHAMFER 45-degree chamfer at each
    end — which a shallow lip truncates, so the top face measures
    `LIP_LENGTH + 2*(LIP_CHAMFER - protrusion)` until the protrusion passes
    1.200.

    Built as the intersection of the section swept across X with the chamfered
    footprint swept up Z, so each is stated once and neither needs an edge pick.
    """
    _fw, _fb, back = pocket_span(p, d)
    m = lip_slope(d)
    unit = (1.0 + m * m) ** 0.5
    rise, out = LIP_DEPTH / unit, LIP_DEPTH * m / unit
    half = LIP_LENGTH / 2 + LIP_CHAMFER
    with BuildPart() as prism:
        with BuildSketch(Plane.YZ):
            # The first and last points reach 0.800 INTO the panel, so the fuse
            # is not across a coincident face. That tab is trimmed with the
            # panel by the angled cutout, which is why the lip goes into the
            # composite before the cut rather than after it.
            Polygon((back - 0.8, LIP_Z), (back, LIP_Z),
                    (back + out, LIP_Z + rise),
                    (back + out, LIP_Z + rise + LIP_HEIGHT),
                    (back, LIP_Z + LIP_HEIGHT), (back - 0.8, LIP_Z + LIP_HEIGHT),
                    align=None)
        extrude(amount=half + 1, both=True)
    with BuildPart() as foot:
        with BuildSketch(Plane.XY):
            Polygon((-half, back - 1.0), (half, back - 1.0), (half, back),
                    (half - LIP_CHAMFER, back + LIP_CHAMFER),
                    (half - LIP_CHAMFER, back + LIP_DEPTH + 1),
                    (-half + LIP_CHAMFER, back + LIP_DEPTH + 1),
                    (-half + LIP_CHAMFER, back + LIP_CHAMFER),
                    (-half, back), align=None)
        extrude(amount=LIP_Z + LIP_HEIGHT + LIP_DEPTH + 5)
    return (prism.part & foot.part).moved(Location((x, 0, 0)))


def front_dividers(p, d):
    """Right-edge X of each front-pocket divider, left to right.

        first = -#BoxWidth/2 + WallThickness + #calFirstLeftFrontDividerDist
        then step by #calSlotwidth

    `calFirstLeftFrontDividerDist` is `calSlotwidth + calFrontDividerLeftSpacing`
    and the studio's own variable, so the first compartment is one slot wide
    plus the side spacing and the rest are a slot each. Exact on all six.

    **`MatPocket` drops the RIGHTMOST divider**, merging the last two
    compartments into one wide slot for the mat — which is what
    `calFrontSlotsForCards = HorizontalSlots - 2` counts. Confirmed against the
    pair `Box Dominion 244S` / `Box Dominion 202S Merged`: same box, same
    envelope, and the only difference across the section is that one divider.
    """
    x0 = -box_width(p, d) / 2 + WALL + d.calFirstLeftFrontDividerDist
    n = p.HorizontalSlots - 1 - (1 if p.MatPocket else 0)
    return [x0 + k * d.calSlotwidth for k in range(n)]


def pocket_span(p, d):
    """(front wall inner face, divider panel front, divider panel back) in Y."""
    fw = -box_depth(p, d) / 2 + WALL
    return fw, fw + d.calFrontPocketDepth, fw + d.calFrontPocketDepth + FRONT_DIVIDER


def angled_cutout(p, d):
    """`Angled cutout of front holder` — one plane, and it cuts the lot.

    It runs from the TOP OF THE LOWERED FRONT WALL, `(y = -#BoxDepth/2 +
    WallThickness, z = 68.600)`, back and up to the divider panel's BACK face
    at `z = 87.500`, and everything in the pocket — padding, dividers and the
    panel itself — is simply where that plane happens to cross it. Both
    endpoints are exact on all six references, which is what says it is one
    plane and not three separately-topped features; the slope varies from
    `0.349` to `1.323` across them purely because `calFrontPocketDepth` does.

    Cut as a polygon swept along X, so the plane is stated once. It is applied
    to the pocket's own solids BEFORE they are fused to the box — see
    `front_pocket` — so it can run the full width without touching the end
    walls, which the STEP leaves square to the rim.
    """
    BD = box_depth(p, d)
    fw, _fb, back = pocket_span(p, d)
    top = d.BoxHeight + 5
    out = -BD / 2 - 5                       # clear of the box, into empty space
    with BuildPart() as tool:
        with BuildSketch(Plane.YZ):
            Polygon((fw, FRONT_TOP), (back, POCKET_CUT_TOP), (back, top),
                    (out, top), (out, FRONT_TOP), align=None)
        extrude(amount=box_width(p, d) / 2 + 5, both=True)
    return tool.part


def front_pocket(p, d, part):
    """The whole `Front pocket` group, in the tree's order.

    The floor stays solid under it — `bottom_slot` already starts at the
    panel's back face — so everything here stands on it.

    Built as ONE composite that is shaped and only then fused. Every piece
    reaches WALL/2 into the wall it stands on, to keep the fuse off a
    coincident face, and the angled cutout has to reach those overlaps or they
    survive it as slivers standing to the rim — which is exactly what happened
    when the cut was clipped to the inner width, and what the corner-round
    probe caught, 1.816 mm3 at each end.
    """
    BD = box_depth(p, d)
    inner = box_width(p, d) / 2 - WALL
    fw, fb, back = pocket_span(p, d)
    H = d.BoxHeight

    def slab(x_lo, x_hi, ylo, yhi, zlo, zhi):
        return Box(x_hi - x_lo, yhi - ylo, zhi - zlo).moved(
            Location(((x_lo + x_hi) / 2, (ylo + yhi) / 2, (zlo + zhi) / 2)))

    # `Front divider` — the panel that closes the pocket, 1.000 thick and
    # carrying the same lattice as the back wall (cut below).
    add = slab(-inner - WALL / 2, inner + WALL / 2, fb, back, 0.0, H)
    # `Divider for front pocket` / `Additional dividers`
    for x in front_dividers(p, d):
        add = add + slab(x - FRONT_DIVIDER_W, x, fw - WALL / 2, back, 0.0, H)
    # `Pad outermost slots` — FrontPocketSidePaddingWidth of solid against each
    # end wall, filling the pocket from the front wall to the panel.
    for sign in (-1, +1):
        lo, hi = sorted((sign * (inner - FRONT_PAD), sign * (inner + WALL / 2)))
        add = add + slab(lo, hi, fw - WALL / 2, back, 0.0, H)
    # `Slits in front pocket` — the SAME openings as the back's hanging holes,
    # at the same X and the same three rows. The padding starts 5.800 in and
    # the first hole 8.300 in, so no slit ever meets a pad or a divider.
    for x_lo, x_hi in hanging_holes(p, d):
        for z_lo, z_hi in hole_rows():
            add = add - slab(x_lo, x_hi, fb - 1.0, back + 1.0, z_lo, z_hi)
    # `Thumb and Lip` — the finger hole, one per slot, and two lips behind it.
    # THUMB_R never reaches a pad (5.800 in) or a divider, and neither does a
    # lip, so both only ever meet the panel.
    for x in thumb_centres(p, d):
        add = add - thumb_tool(p, d, x)
        for sign in (-1, +1):
            add = add + lip_tool(p, d, x + sign * LIP_OFFSET)
    return part + (add - angled_cutout(p, d))


# `Closing mechanism`. A pad on each end wall that the lid grips. Its position
# is a CONSTANT in the box frame — identical on references whose #BoxDepth runs
# 27.600 to 103.200 — so it is not measured from either face.
BUMP_DEPTH = D.ClosingBumpDepth   # 1.000, how far it stands proud
BUMP_Y0, BUMP_Y1 = -1.750, 6.250  # 8.000 long
BUMP_Z0, BUMP_Z1 = 87.000, 90.000
BUMP_CHAMFER = 0.500              # `Chamfer 1`, on the outer face's four edges


def closing_bumps(p, d, part):
    """`Closing mechanism` — `Side bump` / `Extrude 1` / `Chamfer 1` / `Mirror 1`.

    The chamfer is on the OUTER face only, so the pad's sides rise square for
    the first 0.500 and are cut back over the last 0.500. That is what makes
    the volume 21.4167 mm³ rather than the 24.000 of a plain pad, and the diff
    found exactly 21.417.
    """
    BW = box_width(p, d)
    thick = BUMP_DEPTH + WALL / 2      # reaches into the wall, so the fuse is
    for sign in (-1, +1):              # not across a coincident face
        pad = Box(thick, BUMP_Y1 - BUMP_Y0, BUMP_Z1 - BUMP_Z0)
        outer = pad.faces().sort_by(Axis.X)[0 if sign < 0 else -1]
        pad = chamfer(outer.edges(), BUMP_CHAMFER)
        part = part + pad.moved(Location((
            sign * (BW / 2 + BUMP_DEPTH - thick / 2),
            (BUMP_Y0 + BUMP_Y1) / 2, (BUMP_Z0 + BUMP_Z1) / 2)))
    return part


# `Front Label Holder` and `Side Label Holder`. One section serves both: a pad
# standing LABEL_PROUD off the wall, chamfered on its bottom and two ends but
# NOT its top, with a LABEL_GROOVE slot swept behind the rim and the middle cut
# clean through. Only the length differs — and the front one carries two
# fasteners the side one does not.
LABEL_PROUD = 1.600
LABEL_Z0, LABEL_Z1 = 40.500, 64.500
LABEL_CHAMFER = 1.600      # `Chamfer 2` / `Chamfer 3`, on the outer face
LABEL_GROOVE = 0.800       # how deep the label slot is
LABEL_GROOVE_IN = 1.300    # inset where the slot's own chamfer meets the wall
LABEL_OPEN_IN = 4.000      # inset of the opening cut clean through
LABEL_ROOT = 0.800         # how far the pad reaches INTO the wall

FRONT_LABEL_WIDE = 156.400   # the front label itself; the holder is 3.600 more
FRONT_LABEL_NARROW = 62.000  # ... where the wide one will not fit
SIDE_LABEL_EXTRA = 3.800   # + calSideLabelWidth
SIDE_LABEL_Y = 2.250       # the same centre the closing bump uses

FASTENER_LEN = 10.000      # `Fastener` — a ROUNDED ridge above the frame
FASTENER_R = 1.000         # every one of its faces is a 1.000 cylinder
FASTENER_TALL = 1.000      # z LABEL_Z1 .. LABEL_Z1 + 1.000


def label_holder(length, fasteners=()):
    """One label holder, in a canonical frame: the wall's outer face is y = 0,
    the holder stands proud in -Y, and it is centred on x = 0.

    Measured off the STEPs' own faces, which give round numbers throughout:
    the pad spans `z 40.500..64.500`, its chamfer is `1.600`, the slot's rim is
    `2.100` in (its chamfer starting `1.300` in), and the opening is `4.000` in.
    The side holder is the same section at `calSideLabelWidth + 3.800` long.
    """
    half = length / 2
    depth = LABEL_PROUD + LABEL_ROOT
    height = LABEL_Z1 - LABEL_Z0

    def slab(u, y_lo, y_hi, z_lo, z_hi):
        return Box(u, y_hi - y_lo, z_hi - z_lo).moved(
            Location((0, (y_lo + y_hi) / 2, (z_lo + z_hi) / 2)))

    # `Tag holder` + `Chamfer 2`: the chamfer is measured from the OUTER face,
    # so it reaches the wall exactly. The top edge is left square — that is the
    # side the label slides in from.
    pad = slab(length, -LABEL_PROUD, LABEL_ROOT, LABEL_Z0, LABEL_Z1)
    outer = pad.faces().sort_by(Axis.Y)[0]
    pad = chamfer([e for e in outer.edges() if e.center().Z < LABEL_Z1 - 1e-6],
                  LABEL_CHAMFER)
    # `Cutout` + `Sweep`: the slot, chamfered the same way off its own deep face.
    cut = slab(length - 2 * LABEL_GROOVE_IN, -LABEL_GROOVE, LABEL_ROOT + 1.0,
               LABEL_Z0 + LABEL_GROOVE_IN, LABEL_Z1 + 2.0)
    deep = cut.faces().sort_by(Axis.Y)[0]
    cut = chamfer([e for e in deep.edges()
                   if e.center().Z < LABEL_Z1 + 2.0 - 1e-6], LABEL_GROOVE)
    pad = pad - cut
    # ... and the middle, clean through.
    pad = pad - slab(length - 2 * LABEL_OPEN_IN, -depth - 1.0, LABEL_ROOT + 1.0,
                     LABEL_Z0 + LABEL_OPEN_IN, LABEL_Z1 + 2.0)
    if not fasteners:
        return pad
    # `Fastener` / `Round Fastener` / `Mirror 2` — ridges just above the frame
    # that grip the label's top edge, at `fasteners` (absolute X positions).
    #
    # It is the INTERSECTION OF THREE 1.000 CYLINDERS, every axis lying in the
    # wall face — read straight off the STEP's surfaces, all four of which are
    # GeomType.CYLINDER of radius exactly 1.000. Two run along X at the ridge's
    # bottom and top, and their lens-shaped overlap is the section: it peaks
    # 0.866025 proud, halfway up. The third is the stadium that rounds the ends
    # — an 8.000 segment dilated by the same 1.000 — and it is a PRISM in Z,
    # which is why the end faces are cylinders about vertical axes and not
    # spherical caps.
    #
    # A section through the middle looks like a triangular ridge with 60-degree
    # flanks, and it is not; the flanks are arcs and the peak is an edge, which
    # is why there are two faces along X and not one.
    with BuildPart() as foot:
        with BuildSketch(Plane.XY):
            SlotOverall(FASTENER_LEN, 2 * FASTENER_R)
        extrude(amount=LABEL_Z1 + FASTENER_TALL + 2.0)
    tab = foot.part
    for z in (LABEL_Z1, LABEL_Z1 + FASTENER_TALL):
        tab = tab & Cylinder(FASTENER_R, FASTENER_LEN + 2.0,
                             rotation=(0, 90, 0)).moved(Location((0, 0, z)))
    for x in fasteners:
        pad = pad + tab.moved(Location((x, 0, 0)))
    return pad


def fastener_centres(p, d):
    """Where the front holder's fasteners sit, in X.

    The wide holder carries TWO, at the thirds of its length — `Box Dominion
    244U` puts them at exactly the same absolute positions as every other wide
    reference, so they belong to the holder and not to the box.

    **The narrow one carries ONE, in the middle. That is a DELIBERATE
    DIVERGENCE** (Allan): `Box Innovation 130U` has none at all, and a label
    with nothing gripping its top edge is the thing being fixed. One is what
    fits — two at the thirds of `65.600` would sit `10.933` out, and each ridge
    is `10.000` long.
    """
    length = front_label_len(p, d)
    if length < FRONT_LABEL_WIDE + 3.600:
        return (0.0,)
    return (-length / 6, length / 6)


def front_label_len(p, d):
    """Overall length of the front label holder — the label plus 3.600.

    The wide label does not fit every box. `cc.cfg` has known this all along
    from the labels' side: "The XS box is only 150.9 mm wide, too narrow for
    the 156.4 front label, so the 62 is a FRONT there (its pocket is cut for it
    at 62.4 mm outer)" — and 62.400 is exactly what `Box Innovation 130U`
    measures. 62 is `calSideLabelWidth`'s widest rung, so the XS box's front
    takes what is elsewhere a large SIDE label.

    Keyed on whether the wide holder fits rather than on the size letter,
    because that is the reason. XS is the only row in the catalogue it catches:
    every S box is at least 209.300 wide.
    """
    wide = FRONT_LABEL_WIDE + 3.600
    return wide if box_width(p, d) >= wide else FRONT_LABEL_NARROW + 3.600


def label_holders(p, d, part):
    """`Front Label Holder` and `Side Label Holder`, behind
    `isLabelHoldersOnBox`.

    Every feature in both groups carries Onshape's `fx` marker, which nothing
    else in the tree does — conditional suppression on that variable. No
    catalogue row can exercise the `0` branch (it needs Colours or a single
    horizontal slot), but Allan wants the option real, so it is built behind the
    flag rather than unconditionally.

    The side holder is on the **-X end only**, which is the whole of the box's
    asymmetric 2.600 width offset: 1.600 here against the closing bump's 1.000.
    """
    if not d.isLabelHoldersOnBox:
        return part
    BW, BD = box_width(p, d), box_depth(p, d)
    part = part + label_holder(front_label_len(p, d),
                               fastener_centres(p, d)).moved(
        Location((0, -BD / 2, 0)))
    side = label_holder(d.calSideLabelWidth + SIDE_LABEL_EXTRA)
    return part + side.rotate(Axis.Z, -90).moved(
        Location((-BW / 2, SIDE_LABEL_Y, 0)))


# `Model name` and the `Logo` group — the engraving in the two side floors.
# Allan supplied the four sketches; every placement below is one of their
# dimensions, and each is confirmed on all five references.
ENGRAVE = 0.400            # the same depth the Pusher's text uses
TEXT_INSET = 3.000         # cap top, in from the side floor's inner edge —
#                            `#calSlotwidth/2 - 3mm` on the -X sketch
MODEL_GAP = 3.000          # between the two -X lines, baseline to cap top
LOGO_MARGIN = 2.500        # the +X text box, off the FRONT of the card area
MODEL_MARGIN = 6.900       # the -X block measured, total. Its sketch box is
#                            5.000 like the +X one, but the text does not fill
#                            it; Allan: the size "is a bit arbitrary, I just
#                            wanted to make it fit".
CAPACITY_GAP = 2 / 3       # x #LogoHeight, ProductName baseline to cap top
VERSION_GAP = 1 / 2        # x #LogoHeight, capacity baseline to cap top
VERSION_CAP = 3 / 4        # x #LogoHeight


def logo_margin(p, d):
    """The +X text box's inset at the BACK of the card area.

        #RisingSliders <= 8 ? 2.5 mm
                            : 2.5mm + (#RisingSliders - 8) * #calSliderDistance

    Allan's sketch. Past eight risers the extra term is exactly the depth those
    risers add to the card area, so the logo block STOPS GROWING and holds the
    size it had at eight. He experimented with ten and twelve; one catalogue row
    reaches the branch, Dominion's `333 Card` at `S9.21.10`.
    """
    return LOGO_MARGIN + max(0, p.RisingSliders - 8) * d.calSliderDistance


def card_area(p, d):
    """(front, back) of the sliding-card area in Y — what the text is fitted
    to. Its front is the divider panel's back face and its back the inner back
    wall, which is exactly `bottom_slot`'s span."""
    return (-box_depth(p, d) / 2 + WALL + d.calFrontPocketDepth + FRONT_DIVIDER,
            box_depth(p, d) / 2 - WALL)


def engrave_line(txt, size, baseline, start, toward, sign):
    """One line of engraved text, as a solid to subtract.

    `baseline` is the line's baseline in X, `start` where its pen begins in Y,
    and `toward` +1 or -1 the reading direction. The glyphs are placed by the
    PEN ORIGIN — `cad.text.metrics` gives the bearings, which no measurement of
    rendered ink can recover.
    """
    _adv, lsb, lo, _hi = T.metrics(txt)
    with BuildPart() as part:
        with BuildSketch(Plane.XY.offset(WALL - ENGRAVE)):
            # Mode.PRIVATE, or `Text` adds itself to the sketch where it stands
            # AND the shifted copy is added on top of it.
            glyphs = Text(txt, font_size=size, font_path=T.LOGO_FONT,
                          align=(Align.MIN, Align.MIN), mode=Mode.PRIVATE)
            # align=MIN puts the INK's corner on the origin, which leaves the
            # pen origin at -lsb and the baseline at -lo. Shift by +lsb, +lo to
            # bring BOTH to zero.
            add(Pos(lsb * size, lo * size) * glyphs)
        extrude(amount=ENGRAVE)
    solid = part.part.rotate(Axis.Z, 90 * (1 if toward > 0 else -1))
    return solid.moved(Location((baseline, start, 0)))


def floor_text(p, d, part):
    """`Model name` and the `Logo` group, cut ENGRAVE into the floor's top.

    Five lines, all Orbitron Bold, on the two side floors. `#LogoHeight` is the
    `ProductName` line's cap height and everything on the +X side hangs off it.
    """
    inner = box_width(p, d) / 2 - WALL
    edge = inner - side_floor(d)          # the side floor's INNER edge
    y_front, y_back = card_area(p, d)
    span = y_back - y_front

    # --- -X: calModelName, then GameName, one size, reading toward -Y -------
    size = T.fit_size(d.calModelName, span - MODEL_MARGIN)
    cap = T.CAP * size
    x = -edge - TEXT_INSET                # the first line's cap top
    for txt in (d.calModelName, p.GameName):
        part = part - engrave_line(txt, size, x - cap, y_back - MODEL_GAP,
                                   -1, -1)
        x = x - cap - MODEL_GAP           # next line, one gap further out
    # --- +X: ProductName, calCapacityLabel, calVersion, reading toward +Y ---
    start = y_front + LOGO_MARGIN
    logo_len = span - LOGO_MARGIN - logo_margin(p, d)
    logo_size = T.fit_size(d.ProductName, logo_len)
    logo_cap = T.CAP * logo_size          # this is #LogoHeight
    base = edge + TEXT_INSET + logo_cap
    part = part - engrave_line(d.ProductName, logo_size, base, start, +1, +1)
    cap_size = T.fit_size(d.calCapacityLabel, logo_len)
    base = base + CAPACITY_GAP * logo_cap + T.CAP * cap_size
    part = part - engrave_line(d.calCapacityLabel, cap_size, base, start, +1, +1)
    # `calVersion` — the Onshape sketch still reads "Rev <version>"; Allan:
    # it should say CC, as the Lid does. A DELIBERATE DIVERGENCE, and
    # tests/test_box.py asserts both sides of it.
    ver_size = VERSION_CAP * logo_cap / T.CAP
    base = base + VERSION_GAP * logo_cap + VERSION_CAP * logo_cap
    return part - engrave_line(d.calVersion, ver_size, base, start, +1, +1)


# `Smooth box edges` — a SMOOTH_R fillet on `#SharpEdges`.
#
# Onshape's query is CONVEX edges intersected with the edges CREATED BY the
# shell-level features. build123d carries no feature provenance and none of the
# ways of recovering it work (spec/BOX.md records three), so the set is STATED
# here instead, from Allan's own pictures of it. Everything it needs is a model
# constant, so it generalises across the catalogue.
#
# Deliberately conservative for now: this is the part of the set that is certain,
# and it grows by review. `spec/BOX.md` lists what is still out.
SMOOTH_R = 0.600


def sharp_edges(p, d, part):
    """The edges `Smooth box edges` rounds, as an explicit geometric set.

    Two exclusions are the reference's own, and both also happen to be what
    OCCT will not fillet — which is a good sign the rule is the right one:

    * **the back wall's rim** is notched for the pusher tabs and stays sharp
      (Allan), so only the END WALLS' rim is rounded, and only its outer edge:
      on the inner one the slider ribs' 0.700 top rounds run into the fillet;
    * **`Lower the front`** is not rounded AT ALL. Its inner edge is where the
      pocket's pads and dividers land, and two adjacent segments of it are the
      minimal pair OCCT refuses; its outer edge survives all three reference
      fillets untouched, merely growing 1.200 longer as the two vertical
      corners are cut back beside it.
    """
    BW, BD = box_width(p, d), box_depth(p, d)
    inner, x_out = BW / 2 - WALL, BW / 2
    y_front, y_back = -BD / 2, BD / 2 + REAR_DEPTH
    tol = 1e-3

    def near(a, b):
        return abs(a - b) < tol

    out = []
    for e in part.edges():
        m, t = e @ 0.5, e.tangent_at(0.5)
        flat, upright = abs(t.Z) < 1e-6, abs(t.Z) > 1 - 1e-6
        if flat and near(m.Z, 0.0) and (near(abs(m.X), x_out)
                                        or near(m.Y, y_front)
                                        or near(m.Y, y_back)):
            out.append(e)          # the box's footprint, all four sides
        elif upright and near(abs(m.X), x_out) and (near(m.Y, y_front)
                                                    or near(m.Y, y_back)):
            out.append(e)          # the four outer vertical corners
        elif flat and near(m.Z, d.BoxHeight) and near(abs(m.X), x_out):
            out.append(e)          # the END WALLS' rim, OUTER edge only

        elif (flat and near(m.Z, REAR_TOP) and abs(t.X) > 1 - 1e-6
              and (near(m.Y, y_back) or near(m.Y, y_back - WALL))):
            out.append(e)          # the `Top of back` ledge, across the OUTER
#                                    back wall. The short segments around the
#                                    dividers and the end-wall junction are the
#                                    three OCCT will not take with the rest.
    return out


def smooth_edges(p, d, part):
    """One fillet, one call — no retries, and the same edges every time."""
    edges = sharp_edges(p, d, part)
    return fillet(edges, SMOOTH_R) if edges else part


def build(p):
    """`p` is a params.Primary. Returns the Box as a build123d Part.

    Feature groups in the studio's own order, which is what `spec/BOX.md`
    transcribes. Everything from `Front pocket` on is still to be written.
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
    part = lower_front(p, d, part)
    part = round_top_corners(p, d, part)
    part = sliders(p, d, part)
    part = front_pocket(p, d, part)
    part = closing_bumps(p, d, part)
    part = label_holders(p, d, part)
    return smooth_edges(p, d, floor_text(p, d, part))
