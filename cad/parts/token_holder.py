"""The TokenHolder, and its Half sibling.

An open tray that drops into the last compartment of the box's front pocket —
the one `calFrontSlotsExceptTokenHolderSlot` does NOT count — and holds the
game's tokens instead of cards. Dominion only. FULL and HALF are the same part
differing in the DEPTH alone. Measured in `spec/TOKENHOLDER.md`.

Local frame (the part studio's, which is also the assembly's — a cached 3MF
sits at exactly these coordinates, so `build()` needs no assembly transform,
unlike the Pusher):

    X   0 at the LEFT EDGE OF THE SLOT, the part starting CLEARANCE in
    Y   0 at the FRONT EDGE OF THE SLOT and NEGATIVE going back, the part
        again starting CLEARANCE in
    Z   0 at the base, the wall tops at FrontPocketHeight

So the origin is the slot's corner, not the part's: the part is the slot inset
`CLEARANCE` on all four sides, which is what makes it drop in."""
from build123d import (
    Align, Box, Cylinder, GeomType, Location, Plane, Pos, Rot, fillet,
)

from .. import derive as D
from ..geom import text_solid
from .. import text as T

# The slot inset on all four sides, and the part's own origin.
CLEARANCE = 0.400

# The sketch takes calTokenHolderSlotWidth less this before the clearance, so
# the finished width is calTokenHolderSlotWidth - 1.300.
SLOT_TRIM = 0.500

# A HALF holder is NOT half of a FULL one: it is HALF_BASE plus half the front
# pocket (spec/TOKENHOLDER.md, "The two sketched numbers").
HALF_BASE = 2.600

SIDE_WALL = 1.900          # the two ends, in X
END_WALL = 1.400           # front and back, in Y
FLOOR = 1.400              # floor thickness; the cavity starts here
RIM_ROUND = 0.600          # on the INNER top edge only; the outer stays sharp

# `Token divider`: ONE wall across the middle, CENTRED on the part however
# wide it gets — a merged holder is twice as wide and still has a single
# divider. It stops DIVIDER_DROP below the rim under a half-round cap.
DIVIDER_W = 2.000
DIVIDER_DROP = 10.000

# `Grip`: the thumb tab above the rear wall, a half-disc the wall's thickness
# plus the 0.200 it stands proud into the cavity. Its apex is at
# FrontPocketHeight + GRIP_R on every reference, so the overall height is a
# constant.
GRIP_R = 7.500
GRIP_T = D.WallThickness   # 1.600 — 0.200 more than the wall it stands on
GRIP_ROUND = 0.500

# `Branding` — `CC <version> <model>` engraved into the UNDERSIDE.
ENGRAVE = 0.200
TEXT_INSET = 10.000        # the text box's left edge

# The ink stops `text.box_trail` em short of the right-hand TEXT_INSET —
# a constant of the LAYOUT, not of the string (spec/TOKENHOLDER.md,
# "The branding"). `text.box_run` applies it, in `text_size`.


def width(d):
    """The outer width: `calTokenHolderSlotWidth - 1.300`."""
    return d.calTokenHolderSlotWidth - SLOT_TRIM - 2 * CLEARANCE


def depth(d, half):
    """The outer depth: the whole front pocket, or the half rule."""
    pocket = (HALF_BASE + d.calFrontPocketDepth / 2 if half
              else d.calFrontPocketDepth)
    return pocket - 2 * CLEARANCE


def height():
    """The wall top — `FrontPocketHeight`, a constant on every reference."""
    return D.FrontPocketHeight


def model_name(d):
    """`calTokenHolderModel` — `M21.Sl`, the string the underside carries. The
    size letter comes from `HorizontalSlots`, which the legacy dedup key does
    NOT carry, so two Dominion rows share one cached file under one stamp
    (spec/TOKENHOLDER.md, "One file, two model codes")."""
    return d.calTokenHolderModel


def text_line(d):
    """`CC 7.0 M21.Sl` — the version and the model, no separator. The Holder
    writes the game's name instead; a token holder's identity is its slot."""
    return f"{d.calVersion} {model_name(d)}"


def text_size(d, half):
    """The em size, fitting BOTH dimensions — a DELIBERATE DIVERGENCE. Onshape
    constrains the WIDTH alone, which overruns the underside on three merged
    references; the depth is a second bound here, binding on exactly those
    three (spec/TOKENHOLDER.md, "Where the build deliberately differs")."""
    txt = text_line(d)
    # Read the width out of the FONT, not off rendered ink: `T.ink` at size
    # 1.0 is a bounding box and moves the em in the fourth decimal.
    by_width = (width(d) - 2 * TEXT_INSET) / T.box_run(txt, T.LOGO_FONT)

    by_depth = (depth(d, half) / 2 - CLEARANCE) / cap_reach(txt)
    # And no smaller than the cut floor (`cad/text.py`, "floors").
    size = T.floored(min(by_width, by_depth), T.LOGO_FONT)
    if size > min(by_width, by_depth) + 1e-9 and \
            size * cap_reach(txt) > depth(d, half) / 2:
        raise T.DoesNotFit(f"{txt!r} at its floor overruns the tray")
    return size


def cap_reach(txt):
    """How far the ink reaches from the part's centre, per em. The CAP BAND is
    what is centred, not the ink: `l` reaches past the caps on one side only,
    so the ink stands `cap/2` one way and the rest the other, and the taller
    side has to fit."""
    lo, hi = T.metrics(txt, T.LOGO_FONT)[2:]
    return max(T.CAP / 2, (hi - lo) - T.CAP / 2)


def cavity(d, half):
    """(x0, x1, y0, y1) of the inner walls, in the part's own frame."""
    x0 = CLEARANCE + SIDE_WALL
    x1 = CLEARANCE + width(d) - SIDE_WALL
    y1 = -CLEARANCE - END_WALL
    y0 = -CLEARANCE - depth(d, half) + END_WALL
    return x0, x1, y0, y1


def divider_x(d):
    """The divider's centre — the part's own centre, whatever the width."""
    return CLEARANCE + width(d) / 2




def build(d, half=False):
    """The finished solid, in assembly position — which is the part's own.

    Order matters once: the grip stands on the rim BEFORE the rim is rounded,
    so the round breaks either side of it, which is what the reference has.
    """
    if d.GameName != "Dominion":
        raise ValueError(f"TokenHolder is Dominion-only; got {d.GameName!r}")
    w, dp, h = width(d), depth(d, half), height()
    cx0, cx1, cy0, cy1 = cavity(d, half)
    xc, yc = CLEARANCE + w / 2, -CLEARANCE - dp / 2
    back = -CLEARANCE - dp                       # the rear outer face

    # --- Shell -----------------------------------------------------------
    outer = Pos(xc, yc, h / 2) * Box(w, dp, h)
    # The cavity runs from the top of the floor clean out through the rim.
    hole = (Pos((cx0 + cx1) / 2, (cy0 + cy1) / 2, FLOOR + (h - FLOOR + 1) / 2)
            * Box(cx1 - cx0, cy1 - cy0, h - FLOOR + 1))
    part = outer - hole

    # `Round rim`: the INNER top edge only — the outer stays sharp.
    rim = [e for e in part.edges().filter_by(GeomType.LINE)
           if abs(e.center().Z - h) < 1e-7
           and cx0 - 1e-6 <= e.center().X <= cx1 + 1e-6
           and cy0 - 1e-6 <= e.center().Y <= cy1 + 1e-6]
    part = fillet(rim, RIM_ROUND)

    # ...except where the grip stands: there the rear wall runs straight to
    # the rim, so the round's footprint goes back in over the grip's chord.
    # Onshape gets that by rounding after the grip exists; here the round goes
    # on first and is patched, because a fillet running out against the grip's
    # flank is what OCCT will not build.
    part = part + Pos(xc, cy0 - RIM_ROUND / 2, h - RIM_ROUND / 2) * Box(
        2 * GRIP_R, RIM_ROUND, RIM_ROUND)

    # --- Grip --------------------------------------------------------------
    # A half-disc on the rear wall, GRIP_T thick inward from the rear outer
    # face. The round goes on it ALONE, before it is fused: on the finished
    # solid the same fillet SEGFAULTS OCCT.
    disc = (Pos(xc, back, h) * Rot(-90, 0, 0)
            * Cylinder(GRIP_R, GRIP_T,
                       align=(Align.CENTER, Align.CENTER, Align.MIN)))
    below = Pos(xc, back + GRIP_T / 2, h - (GRIP_R + 1) / 2) * Box(
        2 * GRIP_R + 2, GRIP_T, GRIP_R + 1)
    grip = disc - below
    arc = [e for e in grip.edges().filter_by(GeomType.CIRCLE)
           if abs(e.radius - GRIP_R) < 1e-6]
    part = part + fillet(arc, GRIP_ROUND)

    # --- Token divider -----------------------------------------------------
    dx, bead = divider_x(d), h - DIVIDER_DROP
    r = DIVIDER_W / 2
    stem = (Pos(dx, (cy0 + cy1) / 2, (FLOOR + bead - r) / 2)
            * Box(DIVIDER_W, cy1 - cy0, bead - r - FLOOR))
    cap = (Pos(dx, (cy0 + cy1) / 2, bead - r) * Rot(-90, 0, 0)
           * Cylinder(r, cy1 - cy0, align=(Align.CENTER, Align.CENTER,
                                           Align.CENTER)))
    part = part + stem + cap

    return part - branding(d, half)


def branding(d, half):
    """The engraved text, as the solid to subtract from the underside.

    The glyphs run toward **-Y**, not +Y: this is sketched on the bottom face,
    whose outward normal is -Z, and a right-handed sketch there runs (+X, -Y).
    Built +Y it is legible from the wrong side. Placed by the PEN ORIGIN, as
    the Holder's `engrave` is: X so the text box's origin lands TEXT_INSET in
    from the part's left edge, Y so the CAP BAND — not the ink — centres on
    the part's depth.
    """
    txt = text_line(d)
    em = text_size(d, half)
    x = CLEARANCE + TEXT_INSET
    baseline = -CLEARANCE - depth(d, half) / 2 + T.CAP * em / 2
    return text_solid(txt, T.LOGO_FONT, em, ENGRAVE).mirror(Plane.XZ).moved(
        Location((x, baseline, 0)))
