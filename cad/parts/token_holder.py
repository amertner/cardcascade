"""The TokenHolder, and its Half sibling.

An open tray that drops into the last compartment of the box's front pocket —
the one `calFrontSlotsExceptTokenHolderSlot` does NOT count — and holds the
game's tokens instead of cards. Dominion only. Two configurations, FULL and
HALF, which are the same part at two depths.

Measured in `spec/TOKENHOLDER.md` against two hand-exported STEPs and all 18
cached meshes in `individual/Dominion/`.

Unlike the Pusher, the Box and the Lid, the Onshape feature tree for this part
has NOT been seen — only three sketches of it. Those name four features:
`Extrude 1` and `Shell 1` (from the sketch planes the other two are drawn on),
`Token divider` and `Branding`. The rim's round and the grip are not named
anywhere, and this file does not invent names for them.

What IS measured is that the rim's round is missing exactly where the grip
stands, and that the reference carries it as two cylinders rather than one — so
whatever the features are called, the grip exists before the rim is rounded.
`build()` does it the other way and patches, because that is what OCCT will
build; the resulting solid is the same bar one blend. See `spec/TOKENHOLDER.md`.

Local frame (the part studio's, which is also the assembly's — a cached 3MF
sits at exactly these coordinates):

    X   0 at the LEFT EDGE OF THE SLOT, the part starting CLEARANCE in
    Y   0 at the FRONT EDGE OF THE SLOT and NEGATIVE going back, the part
        again starting CLEARANCE in
    Z   0 at the base, the wall tops at FrontPocketHeight

So the origin is the slot's corner, not the part's: the part is the slot inset
`CLEARANCE` on all four sides, which is what makes it drop in. Every one of the
18 cached components is at these coordinates, so `build()` needs no assembly
transform — unlike the Pusher.

FULL and HALF differ in ONE number, the depth, and in nothing else: the two
reference STEPs have the same 231 faces and 644 edges. `spec/TOKENHOLDER.md`
has the arithmetic.
"""
from build123d import (
    Align, Box, BuildPart, BuildSketch, Cylinder, GeomType, Location, Plane,
    Pos, Rot, extrude, fillet,
)

from .. import derive as D
from .. import text as T

# The part is the slot inset this far on all four sides — the clearance that
# lets it drop into the front pocket. Confirmed as the part's own origin: every
# reference starts at X +0.400 and Y -0.400, and its width and depth are each
# 2 * CLEARANCE short of the opening they sit in.
CLEARANCE = 0.400

# The sketch takes calTokenHolderSlotWidth less this before the clearance is
# applied — Allan's `#calTokenHolderSlotWidth-0.5mm`, which reads 63.9 against
# a 64.4 slot on the sketch he sent. So the finished width is
# calTokenHolderSlotWidth - 1.300, exact on all 18 cached holders across two
# card widths and both Mat states.
SLOT_TRIM = 0.500

# The HALF holder is not half of the FULL one — it is `2.600 + half the front
# pocket`, from Allan's sketch (`2.6mm+#calFrontPocketDepth/2`, reading 8.9
# against a 12.6 pocket). Confirmed on all four cached half holders: 8.100 and
# 13.800 sleeved, 5.790 and 9.400 unsleeved, each exactly HALF_BASE plus half
# the pocket less the two clearances.
HALF_BASE = 2.600

SIDE_WALL = 1.900          # the two ends, in X
END_WALL = 1.400           # front and back, in Y
FLOOR = 1.400              # floor thickness; the cavity starts here
RIM_ROUND = 0.600          # on the INNER top edge only; the outer stays sharp

# `Token divider`: one wall across the middle, dividing the tray in two. It is
# CENTRED on the part and there is exactly one however wide the part gets — a
# merged holder is twice as wide and still has a single divider, confirmed on
# all eight merged references. It stops DIVIDER_DROP below the rim and is
# capped by a half-round, so its top is a 2.000 bead at Z = 65.000.
DIVIDER_W = 2.000
DIVIDER_DROP = 10.000

# `Grip`: the thumb tab standing above the rear wall, a half-disc the wall's own
# thickness plus the 0.200 it stands proud into the cavity. Centred in X, and
# its apex at FrontPocketHeight + GRIP_R = 82.500 on every reference whatever
# the parameters, which is why the overall height is a constant.
GRIP_R = 7.500
GRIP_T = D.WallThickness   # 1.600 — 0.200 more than the wall it stands on
GRIP_ROUND = 0.500

# `Branding` — `CC <version> <model>` engraved into the UNDERSIDE, in Orbitron
# Bold, the same face and depth the Pusher and the Holder use.
ENGRAVE = 0.200
TEXT_INSET = 10.000        # the text box's left edge, from Allan's sketch

# How far short of the right-hand TEXT_INSET the ink stops, in EM: a quarter
# of Orbitron Bold's space advance, `text.box_trail` — what an Onshape text box
# does at its right edge, whatever the last glyph. It was a measured 0.0754
# here (off the STEP, with the em read from the cap band, ±0.002), 0.0764
# ±0.001 on the 18 cached trays, and 0.0761 ±0.0004 on Allan's right-aligned
# sample; 0.0765 is inside every one of those and is the same rule that gives
# the Holder's Open Sans number. It is a constant of the LAYOUT, not the
# string, which is what said it was not a fudge. Compare `text._LSB_C`, its
# counterpart at the leading edge.
TRAIL = T.box_trail(T.LOGO_FONT)


def width(d):
    """The outer width. `calTokenHolderSlotWidth - 1.300`, exact on all 18."""
    return d.calTokenHolderSlotWidth - SLOT_TRIM - 2 * CLEARANCE


def depth(p, d, half):
    """The outer depth: the whole front pocket, or Allan's half rule."""
    pocket = (HALF_BASE + d.calFrontPocketDepth / 2 if half
              else d.calFrontPocketDepth)
    return pocket - 2 * CLEARANCE


def height():
    """The wall top. `#FrontPocketHeight`, and a constant on every reference."""
    return D.FrontPocketHeight


def model_name(d):
    """`calTokenHolderModel` — `M21.Sl`, the string the underside carries.

    NB the size letter comes from `HorizontalSlots`, which `plan_exports` does
    NOT carry in the TokenHolder's dedup key `(capacity, merged, sleeved)`. The
    geometry is right to leave it out — HorizontalSlots cancels out of
    `calTokenHolderSlotWidth` — but the ENGRAVING is not: Dominion `324 Card`
    (4 slots) and `333 Card` (3 slots) share one cached file, and it is stamped
    `M21.Sl` for both. See spec/TOKENHOLDER.md, "One file, two model codes".
    """
    return d.calTokenHolderModel


def text_line(p, d):
    """`CC 7.0 M21.Sl` — the version and the model, no separator.

    The Holder writes `CC <version> - <GameName>`; this one carries the model
    code instead, because a token holder's identity is its slot, not its game
    (it only has one).
    """
    return f"CC {p.Version} {model_name(d)}"


def text_size(p, d, half):
    """The em size, fitting BOTH dimensions — a DELIBERATE DIVERGENCE.

    Onshape constrains the WIDTH alone: the text box runs from TEXT_INSET to
    `width - TEXT_INSET` and the height falls out. That reproduces 15 of the 18
    cached holders exactly and BREAKS the other three, all of them on a MERGED
    box — which is where the rule is asked for the most, because merging
    DOUBLES the width the text is fitted to while leaving the depth alone or,
    on a half holder, nearly halving it:

        HalfTokenHolder 21-Sl merged   9.105 mm of ink in an 8.100 mm part
        HalfTokenHolder 21-Un merged   7.180                   5.790
        TokenHolder     21-Un merged   7.180                   7.180

    On each the engraving runs off the underside and nicks the outer faces of
    the front and back walls. The tell is that the ink's Y extent equals the
    part's OWN to three decimals: that is an outline clipping a sketch, not a
    size that happens to fit.

    So the depth is a second bound here, with the same CLEARANCE of margin the
    part keeps from its slot. It binds on exactly those three and on nothing
    else — including `TokenHolder 21-Sl merged`, which is the tightest of the
    ones that do fit and stays untouched. That is the point: everywhere the
    Onshape rule works this reproduces it, and where it does not this is what
    changes. `tests/test_token_holder_corpus.py` asserts both halves.
    """
    txt = text_line(p, d)
    adv = T.metrics(txt, T.LOGO_FONT)[0]
    rsb = T.right_bearing(txt, T.LOGO_FONT)

    # Width: the ink runs from TEXT_INSET + lsb to (width - TEXT_INSET) - TRAIL,
    # so the span the em has to fill is the advance less the last glyph's right
    # bearing (which is where the ink actually stops) plus TRAIL. Read out of
    # the font rather than off rendered ink: `T.ink` at size 1.0 is a rendered
    # bounding box and is out by enough to move the em in the fourth decimal.
    by_width = (width(d) - 2 * TEXT_INSET) / (adv - rsb + TRAIL)

    by_depth = (depth(p, d, half) / 2 - CLEARANCE) / cap_reach(txt)
    # And no smaller than the cut floor (`cad/text.py`, "floors"): 4.93 em is
    # the catalogue's smallest against 1.70, so it binds nowhere today.
    size = T.floored(min(by_width, by_depth), T.LOGO_FONT)
    if size > min(by_width, by_depth) + 1e-9 and \
            size * cap_reach(txt) > depth(p, d, half) / 2:
        raise T.DoesNotFit(f"{txt!r} at its floor overruns the tray")
    return size


def cap_reach(txt):
    """How far the ink reaches from the part's centre, per em.

    The CAP BAND is what is centred, measured exactly: the band's midpoint is
    the part's own midpoint on every reference, while the INK's is not, because
    `l` reaches 0.051 past the caps on one side only. So the ink stands
    `cap/2` one way and the rest the other, and the taller side is the one that
    has to fit.
    """
    lo, hi = T.metrics(txt, T.LOGO_FONT)[2:]
    return max(T.CAP / 2, (hi - lo) - T.CAP / 2)


def cavity(p, d, half):
    """(x0, x1, y0, y1) of the inner walls, in the part's own frame."""
    x0 = CLEARANCE + SIDE_WALL
    x1 = CLEARANCE + width(d) - SIDE_WALL
    y1 = -CLEARANCE - END_WALL
    y0 = -CLEARANCE - depth(p, d, half) + END_WALL
    return x0, x1, y0, y1


def divider_x(d):
    """The divider's centre — the part's own centre, whatever the width."""
    return CLEARANCE + width(d) / 2




def build(p, half=False):
    """The finished solid, in assembly position — which is the part's own.

    Built in algebra mode: the tray is one box less its cavity, the two rounds
    are the only fillets, and everything goes on in the studio's order. That
    order matters once — the grip stands on the rim BEFORE the rim is rounded,
    so the round breaks either side of it, which is what the reference has.
    """
    if p.GameName != "Dominion":
        # Not a refusal on principle — no other game has ever had one, and no
        # other parts.csv row asks for one, so there is no reference to say
        # what it would look like.
        raise ValueError(f"TokenHolder is Dominion-only; got {p.GameName!r}")
    d = D.derive(p)
    w, dp, h = width(d), depth(p, d, half), height()
    cx0, cx1, cy0, cy1 = cavity(p, d, half)
    xc, yc = CLEARANCE + w / 2, -CLEARANCE - dp / 2
    back = -CLEARANCE - dp                       # the rear outer face

    # --- Shell -----------------------------------------------------------
    outer = Pos(xc, yc, h / 2) * Box(w, dp, h)
    # The cavity runs from the top of the floor clean out through the rim.
    hole = (Pos((cx0 + cx1) / 2, (cy0 + cy1) / 2, FLOOR + (h - FLOOR + 1) / 2)
            * Box(cx1 - cx0, cy1 - cy0, h - FLOOR + 1))
    part = outer - hole

    # `Round rim`: the INNER top edge only — the outer stays sharp, measured on
    # every reference as an 0.800 flat at the front and back and 1.300 at the
    # ends, which is each wall less the round.
    rim = [e for e in part.edges().filter_by(GeomType.LINE)
           if abs(e.center().Z - h) < 1e-7
           and cx0 - 1e-6 <= e.center().X <= cx1 + 1e-6
           and cy0 - 1e-6 <= e.center().Y <= cy1 + 1e-6]
    part = fillet(rim, RIM_ROUND)

    # ...except where the grip stands. At the grip's own X the rear wall runs
    # straight to the rim — the reference's section has the inner face at
    # Y -10.800 from Z 65 to 75 and then the 0.200 ledge, with no arc between,
    # where every other X has one — so the round's footprint goes back in over
    # the grip's chord. In Onshape that falls out of rounding the rim after the
    # grip exists; here the round is put on first and patched, because a fillet
    # that has to run out against the grip's flank is what OCCT will not build.
    part = part + Pos(xc, cy0 - RIM_ROUND / 2, h - RIM_ROUND / 2) * Box(
        2 * GRIP_R, RIM_ROUND, RIM_ROUND)

    # --- Grip --------------------------------------------------------------
    # A half-disc standing on the rear wall, GRIP_T thick from the rear outer
    # face inward — 0.200 more than the wall it stands on, which is the ledge
    # at the rim. `Round grip` is applied to it ALONE, before it is fused: on
    # the finished solid the same fillet segfaults OCCT, and on its own the two
    # edges are clean semicircles.
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

    # --- Branding ----------------------------------------------------------
    return part - branding(p, d, half)


def branding(p, d, half):
    """The engraved text, as the solid to subtract from the underside.

    The glyphs run toward **-Y**, not +Y. That is not a guess: the reference's
    `.` sits at Y -4.995..-4.248, hard against -4.248, and a period rests on
    the baseline — so -4.248 is the baseline and the ascender of `l`, which
    reaches 0.051 em past the caps, goes to -8.642 on the far side of it. It is
    what an underside engraving has to be. Onshape sketched this on the bottom
    face, whose outward normal is -Z, and a right-handed sketch on that face
    runs (+X, -Y). Built +Y and it is legible from the wrong side.
    """
    from build123d import Text, mirror

    txt = text_line(p, d)
    em = text_size(p, d, half)
    lsb = T.metrics(txt, T.LOGO_FONT)[1]
    with BuildPart() as cut:
        with BuildSketch(Plane.XY):
            Text(txt, font_size=em, font_path=T.LOGO_FONT,
                 align=(Align.MIN, Align.MIN))
        extrude(amount=ENGRAVE)
    # Mirroring in Y keeps the X order and turns the glyphs over, which is the
    # underside's orientation; the ink then hangs BELOW the baseline at y = 0.
    flipped = mirror(cut.part, about=Plane.XZ)
    # `Text` aligns on its INK, so place the ink's own corner: X so the text
    # box's origin lands TEXT_INSET in from the part's left edge (the ink
    # starts one left bearing later, which is where every reference has it),
    # and Y so the CAP BAND — not the ink — centres on the part's depth. The
    # cap band's centre is the part's centre on every reference; the ink's is
    # not, because `l` reaches past the caps on one side only.
    x = CLEARANCE + TEXT_INSET + lsb * em
    baseline = -CLEARANCE - depth(p, d, half) / 2 + T.CAP * em / 2
    return flipped.moved(Location((x, baseline, 0)))
