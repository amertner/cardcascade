"""The Lid.

The shallow tray that closes over the top of the Box, and stows the pushers
while the cascade is open: a `1.600` shell with the pusher sockets standing on
its floor, a closing groove in each end wall for the Box's bumps, and every
outer edge rounded `1.000`. Measured in `spec/LID.md`.

Local frame (the part studio's, and the assembly's — a Lid is not offset):
    X   width, 0 at the centre, +-lid_width/2 at the outer walls
    Y   depth, 0 at the centre, +-calLidDepth/2. The BOX sits 2.250 forward of
        this: the lid is 8.100 deeper than `#BoxDepth` and takes the box's
        4.500 of rear storage, so `lid_y = box_y - 2.250`
    Z   0 at the outside of the floor, LidHeight at the rim, opening UP

INCOMPLETE. `build()` stops after the closing grooves. The floor carries three
embossed lines and a `ProductName` + staircase logo that are not written yet,
and the underside carries the logo pattern's pocket, which is deferred with the
pattern itself. See `spec/LID.md` "Still open".
"""
from build123d import (
    Axis, Box, BuildPart, BuildSketch, Kind, Location, Mode, Plane, Rectangle,
    chamfer, extrude, fillet, offset,
)

from . import box as box_part
from .. import derive as D
from .. import lock as L

WALL = D.WallThickness       # 1.600, confirmed on the STEP at +-105.350

# The lid stands 4.600 wider than the box's sketch box — 2.300 a side, which is
# the box's 1.000 of running clearance plus the lid's own 1.600 wall less the
# 0.300 the closing bump needs. Exact on all 46 lids in `individual/` and on
# the reference STEP; the depth needs no such constant, because `calLidDepth`
# IS the lid's measured depth, to 0.001 on every one of them.
WIDTH_OVER_BOX = 4.600

OUTER_ROUND = 1.000          # every outer edge: 4 vertical, 4 top, 4 bottom


def lid_width(p, d):
    """`#BoxWidth + 4.600`.

    `box.box_width` rather than a second copy of the expression: it is one
    quantity, and derive.py's rule — every formula once — is what keeps the
    inner box width identical across the parts that have to agree on it.
    """
    return box_part.box_width(p, d) + WIDTH_OVER_BOX


def lid_depth(d):
    """`calLidDepth`, straight out of the studio — see `spec/LID.md`."""
    return d.calLidDepth


def shell(p, d):
    """The tray: a rectangle extruded to `LidHeight` and hollowed to WALL with
    the TOP face removed, so the floor and the four walls are 1.600."""
    with BuildPart() as part:
        with BuildSketch(Plane.XY):
            Rectangle(lid_width(p, d), lid_depth(d))
        extrude(amount=d.LidHeight)
        top = part.faces().sort_by(lambda f: f.center().Z)[-1]
        offset(amount=-WALL, openings=top, kind=Kind.INTERSECTION,
               mode=Mode.REPLACE)
    return part.part


# --- the pusher sockets ----------------------------------------------------
#
# One socket per stored pusher, standing on the floor: a block with a channel
# down the middle that takes the pusher's plate on edge, the two tab recesses
# in one channel wall, and — from C3 up — the key rib that fills the pusher's
# notch. Every dimension below is `LOCK_STANDARD.md`'s or is constant across
# the whole corpus; see `spec/LID.md` for what each was measured on.
SOCKET_H = 5.000             # above the floor, which is the tab's own length
SOCKET_WALL = 2.950          # either side of the channel
SOCKET_W = 2 * SOCKET_WALL + L.LID_CHANNEL_W          # 9.200
SOCKET_BACK = 9.000          # the socket's back edge, in from the lid's back
KEY_RIB_LEN = 5.000          # along the channel, on the centreline
SOCKET_X_CENTRE = -0.300     # the socket SET's centre — see spec/LID.md


def socket_count(p):
    """2 sockets for XS and S, 3 for M and L.

    NB this is the plain size rule and NOT `isOnlyTwoPusherSlots`: an
    Innovation M lid carries three sockets where its box has two rear storage
    slots and its cascade ships two pushers. Measured on all 46 lids —
    `spec/LID.md` records it as Onshape's own inconsistency, reproduced here.
    """
    return 2 if p.HorizontalSlots <= 3 else 3


def socket_centres(p, d):
    """Channel centre X of each socket, left to right.

    The set spans `(HorizontalSlots - 1) * calSlotwidth` — the card slots'
    own span — and is centred on `SOCKET_X_CENTRE`. Exact on all 46 lids.
    """
    n = socket_count(p)
    span = (p.HorizontalSlots - 1) * d.calSlotwidth
    return [SOCKET_X_CENTRE - span / 2 + k * span / (n - 1) for k in range(n)]


def socket_span(p, d):
    """(y0, y1) of a socket. Its length is the standard's `D - 0.400` and its
    BACK edge sits `SOCKET_BACK` in from the lid's back face — constant on all
    46 lids, whose depths run 34.98 to 111.30."""
    y1 = lid_depth(d) / 2 - SOCKET_BACK
    return y1 - (d.calPusherTotalDepth - L.LID_SOCKET_CLEARANCE), y1


def socket(p, d, x):
    """One socket, centred on channel X `x`.

    The block is `SOCKET_W` x span x `SOCKET_H` and everything else is taken
    out of it:

    * the **channel**, `L.LID_CHANNEL_W` wide, open at both ends and running
      the full height — the pusher's `3.000` plate with the standard's
      `0.300` of running clearance;
    * the **key rib**, `KEY_RIB_LEN` of channel left standing on the socket's
      centreline, which is what the pusher's notch keys onto. C1 and C2 have
      no notch and get no rib (`L.has_notch`);
    * the two **tab recesses**, `L.LID_RECESS_LEN` long and `L.LID_RECESS_STEP`
      deep, cut into the channel's **-X wall only** — the pusher's tabs stand
      proud of one face — at the socket's centreline +- `s`.
    """
    y0, y1 = socket_span(p, d)
    z0, z1 = WALL, WALL + SOCKET_H
    _cls, s = L.lock_class(d.calPusherTotalDepth)
    centre = (y0 + y1) / 2

    def slab(x_lo, x_hi, ylo, yhi):
        return Box(x_hi - x_lo, yhi - ylo, z1 - z0).moved(
            Location(((x_lo + x_hi) / 2, (ylo + yhi) / 2, (z0 + z1) / 2)))

    block = slab(x - SOCKET_W / 2, x + SOCKET_W / 2, y0, y1)
    chan_lo, chan_hi = x - L.LID_CHANNEL_W / 2, x + L.LID_CHANNEL_W / 2
    cuts = []
    if L.has_notch(s):
        for a, b in ((y0, centre - KEY_RIB_LEN / 2),
                     (centre + KEY_RIB_LEN / 2, y1)):
            cuts.append(slab(chan_lo, chan_hi, a, b))
    else:
        cuts.append(slab(chan_lo, chan_hi, y0, y1))
    for sign in (-1, +1):
        c = centre + sign * s
        cuts.append(slab(chan_lo - L.LID_RECESS_STEP, chan_lo,
                         c - L.LID_RECESS_LEN / 2, c + L.LID_RECESS_LEN / 2))
    for cut in cuts:
        block = block - cut
    return block


def sockets(p, d, part):
    """Every socket, fused to the floor."""
    for x in socket_centres(p, d):
        part = part + socket(p, d, x)
    return part


# --- the closing grooves ---------------------------------------------------
#
# The receptacle for the Box's `Closing mechanism` — a pad `1.000` proud on
# each of its end walls, `8.000` long and `3.000` tall at box `z 87.000..90.000`.
# The lid goes on over the box's rim, so a box height `h` arrives at
# `WALL + BoxHeight - h` in the lid's frame: the bump's TOP lands exactly on
# the groove's BOTTOM edge, which is what stops the lid, and the groove's extra
# `0.800` is on the side the bump comes in from.
GROOVE_DEPTH = 1.000
GROOVE_LEN = 10.000          # 8.000 of bump with 1.000 clear at each end
GROOVE_HEIGHT = 3.800        # 3.000 of bump and 0.800 of lead-in
GROOVE_CHAMFER = 0.500       # on the two horizontal edges of the groove FLOOR
BUMP_TOP = 90.000            # `box.BUMP_Z1` — the box's own frame


def groove_span(d):
    """(z0, z1) of the groove. `z0` is the box bump's top, transferred."""
    z0 = WALL + d.BoxHeight - BUMP_TOP
    return z0, z0 + GROOVE_HEIGHT


def closing_grooves(p, d, part):
    """One groove in each end wall, mirrored.

    Centred on `y = 0`, which is where the box's bump lands: the bump sits at
    box `y -1.750..6.250` and the box is 2.250 forward of the lid, so it
    arrives at `-4.000..4.000`. The groove's own `10.000` leaves 1.000 clear
    at each end.

    The chamfer is on the groove's FLOOR, not its mouth — the two horizontal
    edges where the `1.000`-deep floor meets the ends of the pocket. That is
    the face the bump cams over, and it leaves the mouth a square step. The
    tool is built for +X and mirrored, rather than picked by a sign-dependent
    index: sorting a moved solid's faces gets the deep one wrong on one side,
    and an unchamfered groove costs exactly the 5.000 mm3 of the four
    chamfers — which is how this was caught.
    """
    z0, z1 = groove_span(d)
    inner = lid_width(p, d) / 2 - WALL
    over = 1.0                       # inward, so the cut is not coincident
    tool = Box(GROOVE_DEPTH + over, GROOVE_LEN, z1 - z0)
    deep = tool.faces().sort_by(Axis.X)[-1]
    tool = chamfer(deep.edges().filter_by(Axis.Y), GROOVE_CHAMFER)
    tool = tool.moved(Location((inner + GROOVE_DEPTH - (GROOVE_DEPTH + over) / 2,
                                0, (z0 + z1) / 2)))
    return part - tool - tool.mirror(Plane.YZ)


# --- the outer rounds ------------------------------------------------------


def outer_edges(p, d, part):
    """The twelve edges of the outer envelope — four vertical, four at the
    rim, four at the bottom.

    Stated rather than picked: an edge qualifies when its midpoint lies on two
    of the six outer faces. Nothing else on the lid is within reach of them,
    so this needs none of the care `box.sharp_edges` does.
    """
    W, DD, H = lid_width(p, d) / 2, lid_depth(d) / 2, d.LidHeight
    tol = 1e-6
    out = []
    for e in part.edges():
        m = e @ 0.5
        on = ((abs(abs(m.X) - W) < tol) + (abs(abs(m.Y) - DD) < tol)
              + (abs(m.Z) < tol) + (abs(m.Z - H) < tol))
        if on >= 2:
            out.append(e)
    return out


def build(p):
    """`p` is a params.Primary. Returns the Lid as a build123d Part.

    The floor's embossed text and logo, and the underside pattern pocket, are
    still to come — see the module docstring.
    """
    d = D.derive(p)
    part = shell(p, d)
    part = sockets(p, d, part)
    part = closing_grooves(p, d, part)
    return fillet(outer_edges(p, d, part), OUTER_ROUND)
