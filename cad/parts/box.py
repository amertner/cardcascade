"""The Box.

The open-topped tray the cascade lives in: card slots across its width, a front
pocket, a rear pusher store, and the rim cutouts that hang the pushers.
Measured in `spec/BOX.md`; the Onshape feature tree it mirrors is transcribed
there in full, and the group functions below follow it in order.

Local frame (the part studio's):
    X   width, 0 at the centre, +-BoxWidth/2 at the outer walls
    Y   depth, 0 at the centre, -BoxDepth/2 the FRONT, +BoxDepth/2 the back
    Z   height, 0 at the bed, BoxHeight at the rim

INCOMPLETE. `build()` stops after `Front pocket`; see `spec/BOX.md` "Still
open" for what is left and `tests/test_box.py` for what is proven. Nothing
writes a Box to build/ yet.
"""
from build123d import (
    Axis, Box, BuildPart, BuildSketch, Cylinder, Kind, Location, Mode, Plane,
    Polygon, Rectangle, extrude, fillet, offset,
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
    return part + (add - angled_cutout(p, d))


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
    return front_pocket(p, d, part)
