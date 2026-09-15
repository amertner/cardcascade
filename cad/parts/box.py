"""The Box.

The open-topped tray the cascade lives in: card slots across its width, a front
pocket, a rear pusher store, and the rim cutouts that hang the pushers.
Measured in `spec/BOX.md`, which transcribes the Onshape feature tree the
group functions below follow in order.

Local frame (the part studio's):
    X   width, 0 at the centre, +-BoxWidth/2 at the outer walls
    Y   depth, 0 at the centre, -BoxDepth/2 the FRONT, +BoxDepth/2 the back
    Z   height, 0 at the bed, BoxHeight at the rim"""
import math

from build123d import (Axis, Box, BuildLine, BuildPart, BuildSketch, Cylinder,
                       GeomType, Line, Location, Plane, Polygon, SlotOverall,
                       ThreePointArc, chamfer, extrude, fillet, make_face,
                       revolve)

from .. import derive as D
from . import holder as holder_part      # its WALL, which the box lip reaches through
from ..geom import slab, text_solid, tray
from .. import lock as L
from .. import tables as TB
from .. import text as T

WALL = D.WallThickness       # 1.600

# The FLOOR is the one thickness that is NOT the wall's, from 7.1, and it
# grows UPWARD (`shell`), so every bed-referenced feature stays where it is
# and the 0.400 comes out of the cavity. The Lid keeps its 1.600.
# `spec/BOX.md`, "The floor is 2.000, and it grows UPWARD".
THICK_FLOOR = 2.000


def floor_top(d):
    """The floor's top face in Z, which is also its thickness. The datum for
    everything on the floor and everything cut into it — read THIS rather
    than `WALL`, which is the same number only through 7.0."""
    return THICK_FLOOR if d.rev.thick_floor else WALL


def box_width(d):
    """`#BoxWidth`. `derive.py` owns the expression; this is the name every
    caller uses."""
    return d.BoxWidth


def box_depth(d):
    """`#BoxDepth`. Same expression as `calLidDepth` less a constant 8.100 —
    both less `calRearTrim` from 7.2f (`rev.shorter_box`, derive.py)."""
    return (6.0 + (d.RisingSliders - 1) * d.calSliderDistance
            + d.calFirstSliderDistance) + d.calFrontPocketDepth - d.calRearTrim


def pusher_slots(d):
    """Centreline X of each rear pusher-storage slot, left to right: they pack
    from the LEFT INNER WALL at `#dBackSlotWidth` pitch, each centred in its
    cell, so the first is half a pitch in."""
    pitch = D.back_slot_pitch(d)
    x0 = -box_width(d) / 2 + WALL
    return [x0 + (k + 0.5) * pitch for k in range(storage_slot_count(d))]


def pusher_slot_count(d):
    """`#calPusherSlots` — how many pushers the CASCADE ships (`derive.py`
    owns the rule). NOT how many the BACK hangs: that is
    `storage_slot_count`. The Lid reads THIS one (`lid.socket_count`), so a
    box with a variant back still takes the cascade's own lid."""
    return d.calPusherSlots


def storage_slot_count(d):
    """How many pusher cavities the BACK carries — cavities, dividers and rim
    cutouts alike. The cascade's own count, unless the row ships a variant
    back (`rev.back_pocket_variants`): `BACK_OPEN` hangs NONE, so the pocket
    is the full inner width, and `BACK_NOTCHES` hangs as many as the width
    TAKES, which is why the count is DERIVED. A variant is a BOX-only concern:
    `pusher_slot_count` is untouched, so the pair's two boxes share one lid.
    `spec/BOX.md`, "Two back pockets, and no ordinary box".
    """
    if d.BackPocket == TB.BACK_OPEN:
        return 0
    if d.BackPocket == TB.BACK_NOTCHES:
        inner = box_width(d) - 2 * WALL
        return int((inner - DIVIDER_W) // D.back_slot_pitch(d))
    return pusher_slot_count(d)


def finger_hole_offset(d):
    """`#calFingerHoleOffset` — where the rear thumb cutout sits: step right
    by one slot width per pusher slot after the first, then centre the
    rest."""
    n = pusher_slot_count(d)
    return (n - 1 + (d.HorizontalSlots - n) / 2) * d.calSlotwidth


def shell(d):
    """`Create box shape`. From 7.1 the floor is thicker than the wall and the
    difference is FUSED ON TOP of the hollowed tray rather than passed to
    `tray`, which keeps the Lid's 1.600 untouched. The slab reaches WALL/2
    into each wall — the idiom for keeping a fuse off a coincident face."""
    part = tray(box_width(d), box_depth(d), d.BoxHeight, WALL)
    if floor_top(d) > WALL:
        bw, bd = box_width(d), box_depth(d)
        part = part + slab(-bw / 2 + WALL / 2, bw / 2 - WALL / 2,
                           -bd / 2 + WALL / 2, bd / 2 - WALL / 2,
                           WALL, floor_top(d))
    return part


# The front pocket's back wall. A front-pocket feature, but the bottom slot
# starts at its back face, so it is stated here where both read it.
FRONT_DIVIDER = 1.000


def side_floor(d):
    """How much floor is left standing at each end — `calSlotwidth / 2`. The
    **holders rest on these two strips when the box is shut**, so the width is
    set by what has to be LEFT, not by what goes."""
    return d.calSlotwidth / 2


def bottom_slot(d):
    """`Hole in bottom of box` — the rectangle cut clean through the floor, as
    (width, depth, y centre): everything between the two side floors, over
    exactly the sliding card area. ONE plain prism, not one slot per pusher,
    and NOT aligned with the rear storage slots, which have their own
    pitch."""
    width = box_width(d) - 2 * WALL - 2 * side_floor(d)
    y_front = -box_depth(d) / 2 + WALL + d.calFrontPocketDepth + FRONT_DIVIDER
    y_back = box_depth(d) / 2 - WALL
    return width, y_back - y_front, (y_front + y_back) / 2


# `Add depth to back`. The rear storage stands REAR_DEPTH proud of the sketch
# box and is where the pushers are stowed. In section, from #BoxDepth/2: the
# back wall 1.300 (a 1.600 wall with SLOT_BITE eaten), then the pusher slot,
# then the outer back wall (spec/BOX.md, "The back, in section").
REAR_DEPTH = 4.500
SLOT_BITE = 0.300        # how far the pusher slot eats into the back wall


REAR_TOP = 85.000        # `Top of back` — the storage is capped here; only the
#                          END WALLS carry on to BoxHeight
PUSHER_REST_CAP = 25.000  # `Remove material, don't let pushers drop through`:
#                           the cavity floor never sits higher than this
DIVIDER_W = 1.600        # `Divider` between adjacent pusher slots
HOLE_W = 10.000          # `Hanging holes` — the lattice through the back
# From 7.1c the lattice is STOUTER (`stout_lattice`): the PIER between two
# windows is what breaks, so the window narrows (the pitch is fixed) and a
# fourth row shortens its free run. `spec/BOX.md`, "A stouter lattice".
HOLE_W_STOUT = 9.000
HOLE_ROWS_STOUT = 4
HOLES_PER_SLOT = 5
HOLE_INSET = 8.300       # first hole, from the left inner wall
# A hanging hole stops this short of a storage divider's face when its own
# edge would otherwise land EXACTLY on it, leaving wall and divider touching
# corner to corner — non-manifold. `hole_openings` applies it;
# `hanging_holes` stays the transcription of the sketch.
HOLE_CLEAR = 0.200
HOLE_ROWS = 3
HOLE_ROW_BOTTOM = 3.000
HOLE_ROW_TOP = 69.500
HOLE_ROW_GAP = 2.000
# The rim cutouts run from here to the rim: 5.000 tall, NOT the 5.25
# LOCK_STANDARD.md records (spec/BOX.md).
RIM_CUTOUT_Z = 100.000
REAR_THUMB_FILLET = 0.600   # `Fillet rear thumb hole` — NOT the front thumb's
#                             0.400; the wall it cuts is 1.600, not 1.000
# From 7.1b the back pocket gets a cutout every REAR_THUMB_PITCH of its
# width. The pitch is a CEILING, not a target. REAR_THUMB_CLEAR is the wall
# left at each end, and also what has to stand BETWEEN two cutouts for the
# second to be worth cutting.
REAR_THUMB_PITCH = 70.000
REAR_THUMB_CLEAR = 10.000


def pusher_rest(d):
    """The cavity floor — how high a stored pusher sits. A pusher is stored on
    EDGE and upright, so its staircase height stands vertically, and the rest
    brings its top to 0.500 below the rim, where the tabs meet the rim
    cutouts, until PUSHER_REST_CAP takes over for a short pusher."""
    return min(PUSHER_REST_CAP, d.BoxHeight - d.calPusherTotalHeight - 0.5)


def _interval_minus(lo, hi, blocks):
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


def storage_dividers(d):
    """(x0, x1) of each `Divider` between rear storage slots: `n` for `n`
    slots — one at every boundary but the left inner wall, which already is
    one, and the last CLOSING the run on the right."""
    left = -box_width(d) / 2 + WALL
    pitch = D.back_slot_pitch(d)
    return [(left + k * pitch, left + k * pitch + DIVIDER_W)
            for k in range(1, storage_slot_count(d) + 1)]


def rear_thumb_x(d):
    """Centre X of the `Thumb Cutout in back`. `calFingerHoleOffset` is NOT
    measured from the left inner wall but from the left edge of the SECOND
    storage cavity — one slot pitch and one divider in."""
    return (-box_width(d) / 2 + WALL + finger_hole_offset(d)
            + D.back_slot_pitch(d) + DIVIDER_W)


def rear_pocket(d):
    """(x0, x1) of the back pocket — the empty run right of the last divider,
    and the one stretch of the back a thumb cutout can go through. With NO
    cavities (`BACK_OPEN`, 7.2g) there is no divider closing the run either,
    so the pocket is the whole inner width (`make_posters.pocket_w`)."""
    left = -box_width(d) / 2 + WALL
    n = storage_slot_count(d)
    return (left + (n * D.back_slot_pitch(d) + DIVIDER_W if n else 0.0),
            box_width(d) / 2 - WALL)


def rear_thumbs_x(d):
    """Centre X of every `Thumb Cutout in back`, left to right.

    Before 7.1b there is exactly one, at `rear_thumb_x`. From 7.1b the POCKET
    places them (`d.rev.rear_thumbs_spread`): keep REAR_THUMB_CLEAR of wall at
    each end and spread cutouts evenly over what is left, at the largest gap
    no wider than REAR_THUMB_PITCH (`ceil` makes the pitch a CEILING, not a
    target). A second cutout has to EARN its place, so a narrow pocket keeps
    ONE, centred; a `BACK_NOTCHES` box (7.2g) has NONE.
    """
    if d.BackPocket == TB.BACK_NOTCHES:
        return []
    if not d.rev.rear_thumbs_spread:
        return [rear_thumb_x(d)]
    x0, x1 = rear_pocket(d)
    r = D.ThumbCutoutRadius
    lo, hi = x0 + r + REAR_THUMB_CLEAR, x1 - r - REAR_THUMB_CLEAR
    if hi - lo < 2 * r + REAR_THUMB_CLEAR:
        return [(x0 + x1) / 2]
    n = math.ceil((hi - lo) / REAR_THUMB_PITCH)
    return [lo + k * (hi - lo) / n for k in range(n + 1)]


def rear_block(d):
    """`Add depth to back` — the solid the rest of the group carves. It
    reaches WALL/2 INTO the back wall rather than meeting it at #BoxDepth/2:
    fusing across an exactly coincident planar face leaves a LAMINA inside the
    result, and every later boolean against it then fails."""
    y0 = box_depth(d) / 2 - WALL / 2
    depth = REAR_DEPTH + WALL / 2
    return Box(box_width(d), depth, d.BoxHeight).moved(
        Location((0, y0 + depth / 2, d.BoxHeight / 2)))


def slot_band(d):
    """(y0, y1) of the pusher slot itself. It starts SLOT_BITE INSIDE the
    sketch box, which is why the back wall measures 1.300, not WALL."""
    y0 = box_depth(d) / 2 - SLOT_BITE
    return y0, y0 + L.BOX_SLOT_DEPTH


def hole_w(d):
    """The window's width. `stout_lattice` narrows it to widen the pier; the
    PITCH does not move, so only a window's +X edge does."""
    return HOLE_W_STOUT if d.rev.stout_lattice else HOLE_W


def hanging_holes(d):
    """(x0, x1) of every opening in the back, left to right: five per
    horizontal slot at `(calSlotwidth - 2.000) / 5`, the groups repeating at
    `calSlotwidth`, so the pier between slots is 2.000 wider than the rest."""
    pitch = (d.calSlotwidth - 2.0) / HOLES_PER_SLOT
    x0 = -box_width(d) / 2 + WALL + HOLE_INSET
    return [(x0 + k * d.calSlotwidth + j * pitch,
             x0 + k * d.calSlotwidth + j * pitch + hole_w(d))
            for k in range(d.HorizontalSlots) for j in range(HOLES_PER_SLOT)]


def hole_openings(d):
    """`hanging_holes`, less HOLE_CLEAR at any edge that coincides with a
    storage divider's face. Identical to `hanging_holes` on every box but the
    three sleeved Innovation ones (see HOLE_CLEAR), and what `rear_storage`
    actually cuts."""
    faces = [x for a, e in storage_dividers(d) for x in (a, e)]
    out = []
    for lo, hi in hanging_holes(d):
        if any(abs(lo - f) < 1e-6 for f in faces):
            lo += HOLE_CLEAR
        if any(abs(hi - f) < 1e-6 for f in faces):
            hi -= HOLE_CLEAR
        out.append((lo, hi))
    return out


def hole_rows(d):
    """(z0, z1) of each lattice row. The BAND is constant, NOT a function of
    the riser count, and the rows divide it with `HOLE_ROW_GAP` between
    them."""
    rows = HOLE_ROWS_STOUT if d.rev.stout_lattice else HOLE_ROWS
    h = (HOLE_ROW_TOP - HOLE_ROW_BOTTOM - (rows - 1) * HOLE_ROW_GAP) / rows
    return [(HOLE_ROW_BOTTOM + i * (h + HOLE_ROW_GAP),
             HOLE_ROW_BOTTOM + i * (h + HOLE_ROW_GAP) + h) for i in range(rows)]


def rear_storage(d, part, lattice=True):
    """The whole `Pusher holder & Rear Storage` group, thumb cutout included.
    Every cut is a PLAIN rectangular box, and they are disjoint: composing
    the negative first produces a tool build123d cannot subtract with
    (spec/BOX.md, "build123d cannot subtract two boxes with one envelope")."""
    BW, BD = box_width(d), box_depth(d)
    inner = BW / 2 - WALL
    y0, y1 = slot_band(d)
    n = storage_slot_count(d)
    pitch = D.back_slot_pitch(d)
    left, top = -inner, d.BoxHeight + 1

    part = part + rear_block(d)
    cuts = [
        # `Top of back` — the storage is capped at REAR_TOP between the end
        # walls, which run the full height. It starts at the SLOT BAND, not at
        # the sketch box: a divider reaches SLOT_BITE forward of #BoxDepth/2,
        # and cutting from there left a sliver of it standing to the rim.
        slab(-inner, inner, y0, BD / 2 + REAR_DEPTH, REAR_TOP, top),
        # Right of the pusher slots — and of the divider that CLOSES the run —
        # the slot band is empty from the floor up. With no cavities at all
        # (`BACK_OPEN`) that is the WHOLE band.
        slab(left + (n * pitch + DIVIDER_W if n else 0.0), inner, y0, y1,
             floor_top(d), top),
    ]
    # One cavity per pusher slot, open from the rest up — what stands below is
    # `Remove material, don't let pushers drop through`, a lattice, not a
    # plug. A divider stands at every boundary EXCEPT the left inner wall,
    # which already is one.
    for k in range(n):
        cuts.append(slab(left + k * pitch + (DIVIDER_W if k else 0.0),
                         left + (k + 1) * pitch, y0, y1,
                         pusher_rest(d), top))
    # `Hanging holes` — through the back wall in full, and on through the slot
    # band EXCEPT where a divider stands.
    #
    # DELIBERATE DIVERGENCE: Onshape's holes are one prism from the card side
    # to the outer wall, so they SEVER the dividers. The openings are wanted;
    # sawing through the pusher hangers is not (spec/BOX.md, "The hanging
    # holes do NOT cut the dividers").
    divs = storage_dividers(d)
    for x_lo, x_hi in (hole_openings(d) if lattice else []):
        for z_lo, z_hi in hole_rows(d):
            cuts.append(slab(x_lo, x_hi, BD / 2 - WALL, y0, z_lo, z_hi))
            for a, e in _interval_minus(x_lo, x_hi, divs):
                cuts.append(slab(a, e, BD / 2 - WALL, y1, z_lo, z_hi))
    # The rim cutouts — the box's half of the pusher lock, at each slot's
    # centreline +- s. They cut the 1.300 back wall only; the outer wall is
    # already gone above REAR_TOP, which is why they are invisible from behind.
    _cls, sv = L.lock_class(d.calPusherTotalDepth)
    for centre in pusher_slots(d):
        for sign in (-1, +1):
            x = centre + sign * sv
            cuts.append(slab(x - L.BOX_CUTOUT_W / 2, x + L.BOX_CUTOUT_W / 2,
                             BD / 2 - WALL, y0, RIM_CUTOUT_Z, top))
    # ONE boolean with every tool, not one per tool: the tools are disjoint
    # rectangles, so the result is the same and OCCT walks the body once. This
    # is NOT the "compose the negative first" the docstring warns of — nothing
    # is fused before the cut.
    part = part.cut(*cuts)
    # `Thumb Cutout in back` — a THUMB_R hole through the OUTER back wall
    # only, centred on REAR_TOP so the storage's cap takes its top half off.
    # `over` is 2.000, not the default: 5.000 would reach the inner back wall
    # behind it. From 7.1b there are several (`rear_thumbs_x`), disjoint, so
    # ONE boolean as above.
    return part.cut(*[round_hole(y1, BD / 2 + REAR_DEPTH, D.ThumbCutoutRadius,
                                 REAR_THUMB_FILLET, x, REAR_TOP, over=2.0)
                      for x in rear_thumbs_x(d)])


# `Lower the front`, so the cards can be seen and reached. Nothing in the
# derived set varies here, so a formula cannot be told from a constant —
# treat it as MEASURED.
FRONT_TOP = 68.600


def lower_front(d, part):
    """`Lower the front` — the front wall down to FRONT_TOP, between the end
    walls only, which run their full height."""
    BD = box_depth(d)
    inner = box_width(d) / 2 - WALL
    return part - Box(2 * inner, WALL + 1, d.BoxHeight + 1 - FRONT_TOP).moved(
        Location((0, -BD / 2 + (WALL - 1) / 2,
                  (FRONT_TOP + d.BoxHeight + 1) / 2)))


# `Round top box corners`. Above `Lower the front` only the two END WALLS
# reach the rim, and their top-front and top-back edges carry a big round.
CORNER_R = 4.600


def round_top_corners(d, part):
    """`Round top box corners` — a CORNER_R round on each end wall's top
    edges, cut with a TOOL rather than a `fillet()` on picked edges: they are
    describe but hard to select stably, and a tool keeps the tree order honest
    — anything ADDED later is untouched by a cut already made."""
    BD, top = box_depth(d), d.BoxHeight
    width = box_width(d) + 20

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
# ride on: constant section, full height from the floor to the rim, top
# rounded.
SLIDER_W = 1.500
SLIDER_PROUD = 4.000
SLIDER_TOP_R = 0.700     # `Round top of slider`, on the two long top edges only


def slider_ribs(d):
    """(y0, y1) of each rib, BACK to front. A rib's BACK FACE sits on the
    centre of its card slot, and the slots are measured from the inner back
    wall — `calSliderDistance` each, except the frontmost, which is
    `calFirstSliderDistance`. That is the tree's own split."""
    back = box_depth(d) / 2 - WALL - rib_shift(d)
    sd, fsd = d.calSliderDistance, d.calFirstSliderDistance
    if d.isDeepSlotAtBack:
        # The odd one out is the BACK slot (`Deep slot = back`, cad/ only):
        # the first rib sits on its centre and the plain ones follow at the
        # `calSliderDistance` pitch from there.
        ys = [back - fsd / 2]
        ys += [back - (fsd + j * sd + sd / 2) for j in range(d.RisingSliders - 1)]
        return [(y - SLIDER_W, y) for y in ys]
    ys = [back - (j * sd + sd / 2) for j in range(d.RisingSliders - 1)]
    ys.append(back - ((d.RisingSliders - 1) * sd + fsd / 2))
    return [(y - SLIDER_W, y) for y in ys]


def rib_shift(d):
    """How far FORWARD of the studio's position every rib sits — 0.000 through
    7.2e, and from 7.2f (`rev.ribs_forward`) whatever puts the front holder
    `CardHolderGap` from the divider panel, as every holder is from the one
    behind it. DERIVED from the slots, the pocket and the panel, never a
    constant (spec/BOX.md, "The ribs move forward")."""
    if not d.rev.ribs_forward:
        return 0.0
    slots = (d.RisingSliders - 1) * d.calSliderDistance + d.calFirstSliderDistance
    slot_front = box_depth(d) / 2 - WALL - slots
    overhang = SLIDER_W / 2 - holder_part.DEPTH_GAP / 2
    return (slot_front - pocket_span(d)[2]) - overhang - D.CardHolderGap


def sliders(d, part):
    """`Sliders` — the ribs, mirrored to both end walls. Each reaches WALL/2
    INTO the wall it stands on, which keeps the fuse off an exactly coincident
    face (the trap `rear_block` documents)."""
    inner = box_width(d) / 2 - WALL
    thick = SLIDER_PROUD + WALL / 2
    rib = Box(thick, SLIDER_W, d.BoxHeight)
    # `Round top of slider` rounds ACROSS the rib, not along it: the two top
    # edges parallel to X. The rib's front face stays square to the rim.
    rib = fillet(rib.faces().sort_by(Axis.Z)[-1].edges().filter_by(Axis.X),
                 SLIDER_TOP_R)
    ribs = [rib.moved(Location((sign * (inner - (SLIDER_PROUD - WALL / 2) / 2),
                                (y0 + y1) / 2, d.BoxHeight / 2)))
            for y0, y1 in slider_ribs(d) for sign in (-1, +1)]
    return part.fuse(*ribs)


# `Front pocket`, one compartment per horizontal slot.
FRONT_PAD = D.FrontPocketSidePaddingWidth   # 5.800, `Pad outermost slots`
FRONT_DIVIDER_W = 0.800                     # `Divider for front pocket`
POCKET_CUT_TOP = 87.500                     # where `Angled cutout` lands


# `Thumb and Lip`. The finger hole through the divider panel, one per
# horizontal slot, and the lip behind it.
THUMB_R = D.ThumbCutoutRadius     # 12.000, the studio constant
THUMB_Z = POCKET_CUT_TOP          # the same measured 87.500: the angled cutout's top
THUMB_FILLET = 0.400              # `Fillet thumb hole`, on BOTH panel faces


def thumb_centres(d):
    """Centre X of each thumb hole, one per horizontal slot: half a slot in
    from the left inner wall, shifted by the side spacing less the divider
    width (`MatPocket` does NOT move them)."""
    x0 = (-box_width(d) / 2 + WALL + d.calSliderSpaceLeftRight
          - FRONT_DIVIDER_W + d.calSlotwidth / 2)
    return [x0 + k * d.calSlotwidth for k in range(d.HorizontalSlots)]


def round_hole(y0, y1, r, f, x, z, over=5.0):
    """A radius-`r` hole on Y from `y0` to `y1`, filleted `f` into BOTH faces,
    centred on (`x`, `z`), revolved from its profile. Both thumbs use it.

    `over` is how far the tool runs past each face, so the cut is not
    coincident with it. It has to clear the face and STOP, or the rear thumb
    bores on through the empty slot band into the inner back wall.
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


def thumb_tool(d):
    """One thumb hole, centred on x = 0; `front_pocket` moves a copy to each
    slot.

    Revolved from its profile rather than cut-then-`fillet()`: the angled
    cutout takes the top off the hole, so its edge is an ARC, not a circle.
    The quarter arcs are given by THREE POINTS — `RadiusArc` has four
    candidates through two points and picked the wrong one.
    """
    _fw, fb, back = pocket_span(d)
    return round_hole(fb, back, THUMB_R, THUMB_FILLET, 0.0, THUMB_Z)


# `Lip`. Two per thumb, symmetric about it, standing proud of the panel's BACK
# face for the front holder to catch on.
LIP_OFFSET = 20.400               # lip centre, from the thumb centre
LIP_LENGTH = D.LipLength          # 10.000, the top face
LIP_DEPTH = D.LipDepth            # 2.100, along the ramp — 7.0 to 7.2d
LIP_HEIGHT = D.LipHeight          # 2.000, in Z
LIP_CHAMFER = D.LipChamfer        # 1.200, 45 degrees in the XY plane
LIP_Z = 85.500                    # where it leaves the panel's back face — through 7.2e
# From 7.2f (`rev.ribs_forward`) the lip is a wedge that BITES the front
# holder's wall by LIP_BITE, so the holder slides in with a little flex. A
# holder goes into the box STRAIGHT DOWN its ribs, so no fixed lip may fill
# its wall's footprint; LIP_BITE is inside the 0.200 the holder has on its
# rib. `cad.fit --state closed` sweeps it.
LIP_BITE = 0.150
# The wedge's flat top is LIP_SINK below the front holder's slant at the
# wall's face, which ends the lip a little below the next slider.
LIP_SINK = 0.200
POST_ROOT = 4.500                 # from 7.2f: how far the lip's post reaches down into the panel


def lip_reach(d):
    """How far the lip stands proud of the panel's back face, in Y, from
    7.2f: the gap to the front holder (`assembly.front_holder_gap`, 0.400
    with the ribs forward) plus LIP_BITE. (7.2e: gap + wall; before, 2.100
    along the ramp — `lip_tool`.)"""
    from .. import assembly as A
    return A.front_holder_gap(d) + LIP_BITE


def lip_z(d):
    """Z of the lip's UNDERSIDE at its tip, where it leaves the panel's back
    face: `LIP_Z` through 7.2e; from 7.2f (`rev.ribs_forward`) the wedge's
    point, `SLANT_STEP` below `assembly.box_lip_top` — REST_CLEARANCE above
    the rest's floor, exactly as a holder's lips are, and above the panel's
    top, which is what the post is for (`flat_lip_tool`)."""
    if d.rev.ribs_forward:
        from .. import assembly as A
        return A.box_lip_top(d) - holder_part.SLANT_STEP
    return LIP_Z


def lip_top(d):
    """Z of the lip's flat top from 7.2f: LIP_SINK below the front holder's
    slant at the wall's face in play — `assembly.box_lip_top` is that
    surface LIP_BITE further in, so back down the slant by that."""
    from .. import assembly as A
    return A.box_lip_top(d) - LIP_BITE / lip_slope(d) - LIP_SINK


def lip_slope(d):
    """tan of the lip's angle from vertical. **It is the HOLDER's diagonal
    cutout angle**, at the FIRST slider distance because the lip meets the
    front holder — or at the plain one when the deep slot is at the BACK
    (`isDeepSlotAtBack`). One formula with the Holder's `slant_slope`:
    `derive.cascade_slope`, inverted."""
    sd = d.calSliderDistance if d.isDeepSlotAtBack else d.calFirstSliderDistance
    return 1.0 / D.cascade_slope(d, sd)


def lip_tool(d):
    """One lip, centred on x = 0; `front_pocket` moves a copy to each. In
    section a PARALLELOGRAM, in plan LIP_LENGTH long with a 45-degree
    LIP_CHAMFER at each end that a shallow lip TRUNCATES. Built as the section
    swept across X intersected with the footprint swept up Z, so neither needs
    an edge pick."""
    _fw, _fb, back = pocket_span(d)
    m = lip_slope(d)
    unit = (1.0 + m * m) ** 0.5
    lz = lip_z(d)
    if d.rev.ribs_forward:
        return flat_lip_tool(d)
    if d.rev.seated_lips:
        # The gap to the front holder plus its front wall, in Y — the same
        # rule as the holder's own lips (`holder.lip_reach_y`): across the
        # gap, through the rest, and no further. Before 7.2e the lip reached
        # only six front holders (`spec/HOLDER.md`, "Lips that seat").
        from .. import assembly as A
        out = A.front_holder_gap(d) + holder_part.WALL
        rise = out / m
    else:
        rise, out = LIP_DEPTH / unit, LIP_DEPTH * m / unit
    half = LIP_LENGTH / 2 + LIP_CHAMFER
    with BuildPart() as prism:
        with BuildSketch(Plane.YZ):
            # The first and last points reach 0.800 INTO the panel, so the
            # fuse is not across a coincident face; the angled cutout trims
            # that tab, which is why the lip joins the composite BEFORE the
            # cut. From 7.2f it stands above the panel's bevelled top, so the
            # tab becomes a POST, fused AFTER the cut (`flat_lip_tool`).
            root = lz - (POST_ROOT if d.rev.ribs_forward else 0.0)
            Polygon((back - 0.8, root), (back, root), (back, lz),
                    (back + out, lz + rise),
                    (back + out, lz + rise + LIP_HEIGHT),
                    (back, lz + LIP_HEIGHT), (back - 0.8, lz + LIP_HEIGHT),
                    align=None)
        extrude(amount=half + 1, both=True)
    with BuildPart() as foot:
        with BuildSketch(Plane.XY):
            Polygon((-half, back - 1.0), (half, back - 1.0), (half, back),
                    (half - LIP_CHAMFER, back + LIP_CHAMFER),
                    (half - LIP_CHAMFER, back + out + 1),
                    (-half + LIP_CHAMFER, back + out + 1),
                    (-half + LIP_CHAMFER, back + LIP_CHAMFER),
                    (-half, back), align=None)
        extrude(amount=lz + LIP_HEIGHT + rise + 5)
    return prism.part & foot.part


def flat_lip_tool(d):
    """The lip from 7.2f (`rev.ribs_forward`): a WEDGE `lip_reach` proud of
    the panel's back face. Its point is at `lip_z`; its front face rises
    straight back to a RIDGE at `lip_top`, from which the panel's own bevel
    runs down to the pocket face. Its UNDERSIDE lies on the SLANT, parallel to
    the rest floor it floats over, so the clearance is the same along the
    whole lip — and, the box printing upright, it overhangs at the slant's
    angle, not flat. On a POST rooted POST_ROOT into the panel below its
    bevel, fused AFTER the angled cutout (`front_pocket`).
    """
    fw, fb, back = pocket_span(d)
    lz, out = lip_z(d), lip_reach(d)
    top, root = lip_top(d), lz - POST_ROOT
    under_root = lz - out / lip_slope(d)      # the slant, `1/lip_slope` = dZ/dY
    # The post's top continues the panel's own bevel (`angled_cutout`): a
    # ridge, no flat and no square corner.
    bevel = (POCKET_CUT_TOP - FRONT_TOP) / (back - fw)
    front_top = top - bevel * (back - fb)      # the bevel's end at the pocket face
    # The root stays a millimetre under that end: on a shallow pocket with a
    # steep bevel it reached below POST_ROOT and FOLDED the section.
    root = min(root, front_top - 1.0)
    half = LIP_LENGTH / 2 + LIP_CHAMFER
    with BuildPart() as prism:
        with BuildSketch(Plane.YZ):
            # A wedge: underside on the slant to the point at the tip, front
            # face back up to the ridge, then the bevel across the panel.
            Polygon((fb, root), (back, root), (back, under_root),
                    (back + out, lz), (back, top), (fb, front_top),
                    align=None)
        extrude(amount=half + 1, both=True)
    with BuildPart() as foot:
        with BuildSketch(Plane.XY):
            Polygon((-half, back - 1.0), (half, back - 1.0), (half, back),
                    (half - LIP_CHAMFER, back + LIP_CHAMFER),
                    (half - LIP_CHAMFER, back + out + 1),
                    (-half + LIP_CHAMFER, back + out + 1),
                    (-half + LIP_CHAMFER, back + LIP_CHAMFER),
                    (-half, back), align=None)
        extrude(amount=top + 5)
    return prism.part & foot.part


def front_dividers(d):
    """Right-edge X of each front-pocket divider, left to right: the first at
    `-#BoxWidth/2 + WallThickness + #calFirstLeftFrontDividerDist`, then a
    `#calSlotwidth` step. **`MatPocket` drops the RIGHTMOST divider**, merging
    the last two compartments into one wide slot for the mat — what
    `calFrontSlotsForCards = HorizontalSlots - 2` counts."""
    x0 = -box_width(d) / 2 + WALL + d.calFirstLeftFrontDividerDist
    n = d.HorizontalSlots - 1 - (1 if d.MatPocket else 0)
    return [x0 + k * d.calSlotwidth for k in range(n)]


def pocket_span(d):
    """(front wall inner face, divider panel front, divider panel back) in Y."""
    fw = -box_depth(d) / 2 + WALL
    return fw, fw + d.calFrontPocketDepth, fw + d.calFrontPocketDepth + FRONT_DIVIDER


def angled_cutout(d):
    """`Angled cutout of front holder` — ONE plane, and it cuts the lot: from
    the TOP OF THE LOWERED FRONT WALL up to the panel's BACK face at
    POCKET_CUT_TOP, with padding, dividers and panel simply where it crosses
    them. Applied to the pocket's solids BEFORE they are fused to the box, so
    it runs the full width without touching the end walls."""
    BD = box_depth(d)
    fw, _fb, back = pocket_span(d)
    top = d.BoxHeight + 5
    out = -BD / 2 - 5                       # clear of the box, into empty space
    with BuildPart() as tool:
        with BuildSketch(Plane.YZ):
            Polygon((fw, FRONT_TOP), (back, POCKET_CUT_TOP), (back, top),
                    (out, top), (out, FRONT_TOP), align=None)
        extrude(amount=box_width(d) / 2 + 5, both=True)
    return tool.part


def front_pocket(d, part, lattice=True):
    """The whole `Front pocket` group, in the tree's order: ONE composite that
    is shaped and only then fused. Every piece reaches WALL/2 into the wall it
    stands on, and the angled cutout has to REACH those overlaps or they
    survive it as slivers standing to the rim."""
    inner = box_width(d) / 2 - WALL
    fw, fb, back = pocket_span(d)
    H = d.BoxHeight

    # `Front divider` — the panel that closes the pocket, 1.000 thick and
    # carrying the same lattice as the back wall (cut below).
    pocket = slab(-inner - WALL / 2, inner + WALL / 2, fb, back, 0.0, H)
    # Each group of features is ONE boolean (see `rear_storage`): the pieces
    # within a group are disjoint, and the groups keep the tree's order.
    # `Divider for front pocket` / `Additional dividers`
    solids = [slab(x - FRONT_DIVIDER_W, x, fw - WALL / 2, back, 0.0, H)
              for x in front_dividers(d)]
    # `Pad outermost slots` — FrontPocketSidePaddingWidth of solid against each
    # end wall, filling the pocket from the front wall to the panel.
    for sign in (-1, +1):
        lo, hi = sorted((sign * (inner - FRONT_PAD), sign * (inner + WALL / 2)))
        solids.append(slab(lo, hi, fw - WALL / 2, back, 0.0, H))
    pocket = pocket.fuse(*solids)
    # `Slits in front pocket` — the SAME openings as the back's hanging holes,
    # at the same X and rows: one sketch in the tree, one here.
    if lattice:
        pocket = pocket.cut(*[slab(x_lo, x_hi, fb - 1.0, back + 1.0, z_lo, z_hi)
                        for x_lo, x_hi in hanging_holes(d)
                        for z_lo, z_hi in hole_rows(d)])
    # `Thumb and Lip` — neither reaches a pad or a divider, so both only ever
    # meet the panel. Both tools are built ONCE at x = 0 and a copy moved.
    centres = thumb_centres(d)
    thumb, lip = thumb_tool(d), lip_tool(d)
    pocket = pocket.cut(*[thumb.moved(Location((x, 0, 0))) for x in centres])
    lips = [lip.moved(Location((x + sign * LIP_OFFSET, 0, 0)))
            for x in centres for sign in (-1, +1)]
    if d.rev.ribs_forward:
        # The lip stands above the panel's top on its post from 7.2f, so it
        # goes on after the cut that bevels the panel (`lip_tool`).
        return part + ((pocket - angled_cutout(d)).fuse(*lips))
    pocket = pocket.fuse(*lips)
    return part + (pocket - angled_cutout(d))


# `Closing mechanism`. A pad on each end wall that the lid grips. Its position
# is a CONSTANT in the box frame, not measured from either face.
BUMP_DEPTH = D.ClosingBumpDepth   # 1.000, how far it stands proud
BUMP_Y0, BUMP_Y1 = -1.750, 6.250  # 8.000 long
BUMP_Z0, BUMP_Z1 = 87.000, 90.000
BUMP_CHAMFER = 0.500              # `Chamfer 1`, on the outer face's four edges


def closing_bumps(d, part):
    """`Closing mechanism`. The chamfer is on the OUTER face only, so the
    pad's sides rise square for the first 0.500 and are cut back over the
    last."""
    BW = box_width(d)
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
# NOT its top (the side the label slides in from), with a LABEL_GROOVE slot
# behind the rim and the middle cut clean through. Only the LENGTH differs,
# and the fasteners the front one carries.
LABEL_PROUD = 1.600
LABEL_Z0, LABEL_Z1 = 40.500, 64.500
LABEL_CHAMFER = 1.600      # `Chamfer 2` / `Chamfer 3`, on the outer face
LABEL_GROOVE = 0.800       # how deep the label slot is
LABEL_GROOVE_IN = 1.300    # inset where the slot's own chamfer meets the wall
LABEL_OPEN_IN = 4.000      # inset of the opening cut clean through
LABEL_ROOT = 0.800         # how far the pad reaches INTO the wall

FRONT_LABEL_WIDE = 156.400   # the front label itself; the holder is LABEL_HOLDER_EXTRA more
FRONT_LABEL_NARROW = 62.000  # ... where the wide one will not fit
LABEL_HOLDER_EXTRA = 3.600   # a label holder is its label plus this, 1.800 of frame each end
SIDE_LABEL_EXTRA = 3.800   # + calSideLabelWidth
SIDE_LABEL_Y = 2.250       # the same centre the closing bump uses

FASTENER_LEN = 10.000      # `Fastener` — a ROUNDED ridge above the frame
FASTENER_R = 1.000         # every one of its faces is a 1.000 cylinder
FASTENER_TALL = 1.000      # z LABEL_Z1 .. LABEL_Z1 + 1.000


def label_holder(length, fasteners=()):
    """One label holder, in a canonical frame: the wall's outer face is y = 0,
    the holder stands proud in -Y, and it is centred on x = 0."""
    half = length / 2
    depth = LABEL_PROUD + LABEL_ROOT

    # `Tag holder` + `Chamfer 2`: the chamfer is measured from the OUTER face,
    # so it reaches the wall exactly; the top edge is left square.
    pad = slab(-half, half, -LABEL_PROUD, LABEL_ROOT, LABEL_Z0, LABEL_Z1)
    outer = pad.faces().sort_by(Axis.Y)[0]
    pad = chamfer([e for e in outer.edges() if e.center().Z < LABEL_Z1 - 1e-6],
                  LABEL_CHAMFER)
    # `Cutout` + `Sweep`: the slot, chamfered the same way off its own deep face.
    cut = slab(-half + LABEL_GROOVE_IN, half - LABEL_GROOVE_IN,
               -LABEL_GROOVE, LABEL_ROOT + 1.0,
               LABEL_Z0 + LABEL_GROOVE_IN, LABEL_Z1 + 2.0)
    deep = cut.faces().sort_by(Axis.Y)[0]
    cut = chamfer([e for e in deep.edges()
                   if e.center().Z < LABEL_Z1 + 2.0 - 1e-6], LABEL_GROOVE)
    pad = pad - cut
    # ... and the middle, clean through.
    pad = pad - slab(-half + LABEL_OPEN_IN, half - LABEL_OPEN_IN,
                     -depth - 1.0, LABEL_ROOT + 1.0,
                     LABEL_Z0 + LABEL_OPEN_IN, LABEL_Z1 + 2.0)
    if not fasteners:
        return pad
    # `Fastener` / `Round Fastener` / `Mirror 2` — ridges just above the frame
    # that grip the label's top edge, at `fasteners` (absolute X positions).
    # The INTERSECTION OF THREE 1.000 CYLINDERS: two along X whose lens-shaped
    # overlap is the section, and a stadium PRISM in Z rounding the ends. It
    # LOOKS like a 60-degree triangular ridge and is not — the flanks are arcs
    # (`spec/BOX.md`, "The fastener is three cylinders").
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


def fastener_centres(d):
    """Where the front holder's fasteners sit, in X. The wide holder carries
    TWO, at the thirds of its length; **the narrow one carries ONE, in the
    middle: a DELIBERATE DIVERGENCE**, where Onshape has none at all."""
    length = front_label_len(d)
    if length < FRONT_LABEL_WIDE + LABEL_HOLDER_EXTRA:
        return (0.0,)
    return (-length / 6, length / 6)


def front_label_len(d):
    """Overall length of the front label holder. The wide label does not fit
    every box: the XS box's front takes what is elsewhere a large SIDE label.
    Keyed on whether the wide holder FITS rather than on the size letter,
    because that is the reason."""
    wide = FRONT_LABEL_WIDE + LABEL_HOLDER_EXTRA
    return (wide if box_width(d) >= wide
            else FRONT_LABEL_NARROW + LABEL_HOLDER_EXTRA)


def label_holders(d, part):
    """`Front Label Holder` and `Side Label Holder`, behind
    `isLabelHoldersOnBox` — no catalogue row can exercise the `0` branch, but
    the option is real in the tree. The side holder is on the **-X end only**,
    which is the whole of the box's asymmetric 2.600 width offset."""
    if not d.isLabelHoldersOnBox:
        return part
    BW, BD = box_width(d), box_depth(d)
    part = part + label_holder(front_label_len(d),
                               fastener_centres(d)).moved(
        Location((0, -BD / 2, 0)))
    side = label_holder(d.calSideLabelWidth + SIDE_LABEL_EXTRA)
    return part + side.rotate(Axis.Z, -90).moved(
        Location((-BW / 2, SIDE_LABEL_Y, 0)))


# `Model name` and the `Logo` group — the engraving in the two side floors.
# Every placement below is one of the four sketches' dimensions
# (spec/BOX.md, "The placement, from Allan's four sketches").
ENGRAVE = 0.400            # the same depth the Pusher's text uses
TEXT_INSET = 3.000         # cap top, in from the side floor's inner edge
MODEL_GAP = 3.000          # between the two -X lines, baseline to cap top
LOGO_FRONT_INSET = 2.500   # the +X text box, off the FRONT of the card area
MODEL_MARGIN = 6.900       # the -X block, total — no formula behind it
CAPACITY_GAP = 2 / 3       # x #LogoHeight, ProductName baseline to cap top
VERSION_GAP = 1 / 2        # x #LogoHeight, capacity baseline to cap top
VERSION_CAP = 3 / 4        # x #LogoHeight


def logo_margin(d):
    """The +X text box's inset at the BACK of the card area,
    `2.5mm + max(0, #RisingSliders - 8) * #calSliderDistance`: past eight
    risers the extra term is exactly the depth those risers add, so the logo
    block STOPS GROWING at the size it had there."""
    return LOGO_FRONT_INSET + max(0, d.RisingSliders - 8) * d.calSliderDistance


def card_area(d):
    """(front, back) of the sliding-card area in Y — what the text is fitted
    to. Its front is the divider panel's back face and its back the inner back
    wall, which is exactly `bottom_slot`'s span."""
    return (-box_depth(d) / 2 + WALL + d.calFrontPocketDepth + FRONT_DIVIDER,
            box_depth(d) / 2 - WALL)


def engrave_line(txt, size, baseline, start, toward, top):
    """One line of engraved text, as a solid to subtract. `baseline` is its
    baseline in X, `start` where its pen begins in Y, `toward` +1 or -1 the
    reading direction, and `top` the floor's top face, the glyphs sitting
    ENGRAVE below it. Placed by the PEN ORIGIN."""
    solid = text_solid(txt, T.LOGO_FONT, size, ENGRAVE, z=top - ENGRAVE)
    solid = solid.rotate(Axis.Z, 90 * (1 if toward > 0 else -1))
    return solid.moved(Location((baseline, start, 0)))


def floor_text(d, part):
    """`Model name` and the `Logo` group, cut ENGRAVE into the floor's top:
    five lines on the two side floors. `#LogoHeight` is the `ProductName`
    line's cap height, and everything on the +X side hangs off it."""
    inner = box_width(d) / 2 - WALL
    edge = inner - side_floor(d)          # the side floor's INNER edge
    y_front, y_back = card_area(d)
    span = y_back - y_front

    # --- -X: calModelName, then GameName, one size, reading toward -Y -------
    # Every size here is FLOORED (`cad/text.py`, "floors"): fitted to the
    # sketch's box, and raised to the stroke floor where the box is too short
    # for it. A floored line may use the margin the sketch leaves; it may not
    # overrun the card area, which is what `_fits` checks.
    size = T.floored(T.fit_size(d.calModelName, span - MODEL_MARGIN))
    _fits(d.calModelName, size, span)
    cap = T.CAP * size
    x = -edge - TEXT_INSET                # the first line's cap top
    tools = []                            # all five lines, cut at the end
    for txt in (d.calModelName, d.GameName):
        tools.append(engrave_line(txt, size, x - cap, y_back - MODEL_GAP,
                                  -1, floor_top(d)))
        x = x - cap - MODEL_GAP           # next line, one gap further out
    # --- +X: ProductName, calCapacityLabel, calVersion, reading toward +Y ---
    start = y_front + LOGO_FRONT_INSET
    logo_len = span - LOGO_FRONT_INSET - logo_margin(d)
    logo_size = T.floored(T.fit_size(d.ProductName, logo_len))
    _fits(d.ProductName, logo_size, span)
    logo_cap = T.CAP * logo_size          # this is #LogoHeight
    base = edge + TEXT_INSET + logo_cap
    tools.append(engrave_line(d.ProductName, logo_size, base, start, +1,
                              floor_top(d)))
    cap_size = T.floored(T.fit_size(d.calCapacityLabel, logo_len))
    _fits(d.calCapacityLabel, cap_size, span)
    base = base + CAPACITY_GAP * logo_cap + T.CAP * cap_size
    tools.append(engrave_line(d.calCapacityLabel, cap_size, base, start, +1,
                              floor_top(d)))
    # `calVersion` — the Onshape sketch still reads "Rev <version>" where this
    # says CC, as the Lid does: a DELIBERATE DIVERGENCE. Three quarters of the
    # logo's cap, no smaller than the floor and never larger than that cap.
    ver_size = min(logo_size, T.floored(VERSION_CAP * logo_size))
    ver_cap = T.CAP * ver_size
    base = base + VERSION_GAP * logo_cap + ver_cap
    tools.append(engrave_line(d.calVersion, ver_size, base, start, +1,
                              floor_top(d)))
    return part.cut(*tools)


def _fits(txt, size, span):
    """A floored line may eat its margin; it may not leave the card area."""
    ink = T.ink(txt, size=size)[0]
    if ink > span + 1e-9:
        raise T.DoesNotFit(f"{txt!r} at {size:.3f} em is {ink:.2f} of ink in a "
                           f"{span:.2f} card area")


# `Smooth box edges` — a SMOOTH_R fillet on `#SharpEdges`.
#
# Onshape's query is CONVEX edges intersected with the edges CREATED BY the
# shell-level features. build123d carries no feature provenance and no way of
# recovering it works, so the set is STATED here instead, from model constants
# (spec/BOX.md, "`#SharpEdges` is a rule"). Deliberately conservative: this is
# the part of the set that is certain, and it grows by review.
SMOOTH_R = 0.600


def sharp_edges(d, part):
    """The edges `Smooth box edges` rounds, as an explicit geometric set.

    Most of it is the **perimeter of an end wall**, on both faces: the
    footprint at the bed, the front and back corners, the CORNER_R arcs and
    the rim. Two exclusions are the reference's own: **the back wall's rim**,
    notched for the pusher tabs, and **`Lower the front`**, not rounded.

    Three more are KERNEL LIMITS, not design decisions (spec/BOX.md, "Two of
    those families are a KERNEL LIMIT"): the end walls' rim on the INNER face,
    where a slider rib leaves a flat only `SLIDER_W - 2 * SLIDER_TOP_R` wide
    for a SMOOTH_R fillet to die into; with it that face's front vertical
    corner and the arc above it (`rear_ok`); and the `Top of back` ledge's
    OUTER face, which several thumb cutouts break into a chain OCCT refuses,
    killing the whole box — so it is listed only while there is ONE cutout.
    Listing it was always redundant and dropping it costs no geometry, but it
    moves bytes in the written mesh, hence the switch on the cutout count.
    """
    BW, BD = box_width(d), box_depth(d)
    inner, x_out = BW / 2 - WALL, BW / 2
    y_front, y_back = -BD / 2, BD / 2 + REAR_DEPTH
    one_thumb = len(rear_thumbs_x(d)) == 1
    tol = 1e-3

    def near(a, b):
        return abs(a - b) < tol

    def rear_ok(m):
        """True unless this is the INNER face's front corner or its arc — one
        tangent chain OCCT refuses however it is given. The outer face's front
        corner and both back corners are fine, so only this chain is
        dropped."""
        return near(abs(m.X), x_out) or abs(m.Y - y_back) < abs(m.Y - y_front)

    out = []
    for e in part.edges():
        m, t = e @ 0.5, e.tangent_at(0.5)
        flat, upright = abs(t.Z) < 1e-6, abs(t.Z) > 1 - 1e-6
        along_x, along_y = abs(t.X) > 1 - 1e-6, abs(t.Y) > 1 - 1e-6
        # Both faces of an end wall; the perimeter clauses below want either.
        end_wall = near(abs(m.X), x_out) or near(abs(m.X), inner)

        if flat and near(m.Z, 0.0) and (near(abs(m.X), x_out)
                                        or near(m.Y, y_front)
                                        or near(m.Y, y_back)):
            out.append(e)          # the box's footprint, all four sides
        elif upright and end_wall and (near(m.Y, y_front)
                                       or near(m.Y, y_back)) and rear_ok(m):
            out.append(e)          # the end walls' vertical corners: all four
#                                    outside, inside the BACK pair only.
        elif flat and along_y and near(m.Z, d.BoxHeight) and near(abs(m.X), x_out):
            out.append(e)          # the end walls' rim, OUTER edge only
        elif (end_wall and abs(t.X) < 1e-6 and rear_ok(m)
              and e.geom_type == GeomType.CIRCLE and near(e.radius, CORNER_R)):
            out.append(e)          # `Round top box corners` leaves one arc on
#                                    each face of each end wall; rounding them
#                                    closes the perimeter chain above.

        elif (flat and near(m.Z, REAR_TOP) and along_x
              and (near(m.Y, y_back - WALL)
                   or (one_thumb and near(m.Y, y_back)))):
            out.append(e)          # the `Top of back` ledge — both faces of
#                                    the outer back wall while the pocket has
#                                    ONE cutout, its inner face alone once it
#                                    has several (see above).
    return out


def smooth_edges(d, part):
    """One fillet, one call — no retries, and the same edges every time."""
    edges = sharp_edges(d, part)
    return fillet(edges, SMOOTH_R) if edges else part


def build(d, lattice=True):
    """The Box as a build123d Part, from a `derive.Derived`: feature groups
    in the studio's own order. `lattice=False` leaves the back wall's hanging
    holes and the front pocket's slits uncut: a test print (`cad.testkit`),
    never a catalogue box."""
    part = shell(d)
    w, depth, y = bottom_slot(d)
    # Cut Z from below the floor up to exactly the floor's TOP face, so the
    # boolean is clean underneath and nothing above the floor is touched. It
    # follows `floor_top`: a THROUGH cut, and stopping it at WALL would leave
    # a 0.400 membrane across the card area at 7.1.
    fl = floor_top(d)
    part = part - Box(w, depth, fl + 1).moved(Location((0, y, (fl - 1) / 2)))
    part = rear_storage(d, part, lattice)
    part = lower_front(d, part)
    part = round_top_corners(d, part)
    part = sliders(d, part)
    part = front_pocket(d, part, lattice)
    part = closing_bumps(d, part)
    part = label_holders(d, part)
    # The floor text stays LAST before the rounds, though it is the most
    # expensive cut. Cutting it into the bare shell first, the way the Lid
    # takes its logo pocket, gives identical geometry and nearly TWICE the
    # build time, because every boolean after it then carries the text's
    # hundreds of spline faces. Spline text is the cost, not the order.
    return smooth_edges(d, floor_text(d, part))
