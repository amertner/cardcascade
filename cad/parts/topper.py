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

INCOMPLETE — the blank is being built first (Allan), and the `Expansion Name`
group is not written. `spec/TOPPER.md` records every rule it will need.
"""
from build123d import (
    Align, Box, BuildLine, BuildPart, BuildSketch, GeomType, Location, Mode,
    Plane, Polyline, Pos, Rot, extrude, fillet, make_face,
)

from .. import derive as D
from . import holder as H

# Where the base sits in assembly. Constant on all 48 cached components and on
# every reference, whatever the capacity, size or sleeving — and NOT yet
# derived. See spec/TOPPER.md, "Still open".
Z_BASE = 48.450

# The tabs' tops, above Z_BASE. Also constant on all 48.
TOTAL_HEIGHT = 45.200

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
BAND_HALF = 7.400                   # so the front band is 14.800 wide
# 7.400 is `#FootDistanceFromWall`. That would read as the band straddling the
# pusher's path, and it is a hypothesis — the `Divider` sketch gives the
# profile but not where the width comes from. Not encoded as that.

# `Inner Hole Outline` is sketched IN THE SLANT PLANE — its sketch plane is
# `Face of TriangleMatch` — and inset this far from the slant's own edge. The
# rear wall then measures 0.242 in Y on the M10-Un reference, which is
# 0.800 * cos(72.4 deg): the Y component of 0.800 along a slant of 3.1538. A
# Y-offset instead would be wrong by the slope, and wrong differently on every
# row, because the slope moves with calSlotDepth.
INNER_INSET = 0.800

TAB_W = D.WallThickness    # 1.600
TAB_INSET = 1.300          # from each end of the part

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
    because `Remove Inner Hole` stops END_INSET short of them.
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
        with BuildSketch(Plane.YZ) as sk:
            with BuildLine():
                pts = wedge_profile(p, d)
                Polyline(*pts, close=True)
            make_face()
        extrude(amount=x1 - x0)
    return part.part.moved(Location((x0, 0, 0)))
