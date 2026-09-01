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
    BuildPart, BuildSketch, Plane, Rectangle, Mode, extrude, offset, Kind,
)

from .. import derive as D

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


def build(p):
    """`p` is a params.Primary. Returns the Box as a build123d Part.

    Only the shell so far — every other feature group is still to be written.
    """
    d = D.derive(p)
    return shell(p, d)
