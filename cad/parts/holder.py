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
    Y   0 at the front face, NEGATIVE going back
    Z   0 at the CENTRE of the card pocket; the base is at BASE_Z on every
        reference whatever the parameters

INCOMPLETE. `build()` stops after the card pocket. See `spec/HOLDER.md`
"Still open" for what is left and `tests/test_holder.py` for what is proven.
Nothing writes a Holder to build/ yet.
"""
from build123d import (
    Box, BuildLine, BuildPart, BuildSketch, Location, Plane, Polyline,
    extrude, make_face,
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
# front face (Y = 0) at the same Z on every reference: the upper one exactly at
# the top of the card pocket. The slope is the cascade diagonal — see
# `slant_slope` — and `cad/parts/box.lip_slope` is its reciprocal.
SLANT_STEP = 2.000


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


def slider_distance(d, first):
    """The holder's OWN slider distance.

    The first-riser holder is the same box's holder made deeper, so everything
    keyed to the slot depth takes `calFirstSliderDistance` instead. The 246 pair
    is the only evidence that could tell these apart — everywhere else the two
    are equal — and it settles both the depth and the slant.
    """
    return d.calFirstSliderDistance if first else d.calSliderDistance


def holder_depth(d, first):
    """Front face to back face: `sliderDistance - 0.400`.

    9.200 / 20.000 / 8.000 on the three references against 9.600 / 20.400 /
    8.400, exact.
    """
    return slider_distance(d, first) - DEPTH_GAP


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


def slant_slope(d, first):
    """`dZ/dY` of `Top slant angle` — the cascade diagonal.

        (calHeightIncrement - 1.0) / (sliderDistance - 1.2)

    Measured off the slant faces' normals: 1.7857 / 0.7812 / 1.2037 on the three
    references, against 1.7857 / 0.7812 / 1.2037 predicted. The rival reading
    (the other slider distance) is 2.3x out on the 246 pair.
    """
    return (d.calHeightIncrement - 1.0) / (slider_distance(d, first) - 1.2)


def slant_z(d, first, y, lower=False):
    """Z of the slant plane at depth `y` (y <= 0)."""
    return slant_top(d) - (SLANT_STEP if lower else 0.0) + slant_slope(d, first) * y


def shell(p, d, first):
    """`Pocket outline` / `Extrude 1`, cut by `Top slant angle`.

    Built as its YZ section swept along X rather than as a block minus a
    half-space: the section IS the outline — flat base, vertical front and back,
    and the slant closing the top — so the slope enters as two corner heights
    and there is no rotated tool to place. The scallops, the side slots and the
    lips all come off this.
    """
    x0, x1 = x_span(p, d)
    depth = holder_depth(d, first)
    z0 = base_z(d)
    with BuildPart() as part:
        with BuildSketch(Plane.YZ) as sec:
            with BuildLine():
                Polyline((0.0, z0), (-depth, z0),
                         (-depth, slant_z(d, first, -depth)),
                         (0.0, slant_z(d, first, 0.0)),
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

    Inset WALL from the front and back faces (measured: the walls are the only
    material left at a lattice rail's height) and DIVIDER/2 from each slot edge.
    """
    depth = holder_depth(d, first)
    z0, z1 = pocket_z(d)
    w = d.calSlotwidth - DIVIDER
    over = 10.0                            # cut through whatever is above
    tool = Box(w, depth - 2 * WALL, z1 - z0 + over)
    for x in compartment_x(p, d):
        part = part - tool.moved(Location((x, -depth / 2, (z0 + z1 + over) / 2)))
    return part


def build(p, first=False):
    """`p` is a params.Primary. Returns the Holder as a build123d Part.

    INCOMPLETE — see the module docstring.
    """
    d = D.derive(p)
    part = shell(p, d, first)
    return card_pockets(p, d, first, part)
