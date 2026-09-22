"""The Lid.

The shallow tray that closes over the top of the Box and stows the pushers
while the cascade is open. Measured in `spec/LID.md`.

Local frame (the part studio's, and the assembly's — a Lid is not offset):
    X   width, 0 at the centre, +-lid_width/2 at the outer walls
    Y   depth, 0 at the centre, +-calLidDepth/2. The BOX sits 2.250 forward
        of this, so `lid_y = box_y - 2.250`
    Z   0 at the outside of the floor, LidHeight at the rim, opening UP

A cascade ships up to three VARIANTS of it (`tables.LID_VARIANTS`, below).
The logo pattern is where `cad/` parts company with Onshape on purpose: the
mark is FITTED to the lid (`spec/LID.md`, "Sizing the mark")."""
from build123d import (Axis, Box, BuildPart, BuildSketch, Location, Plane,
                       Polygon, chamfer, extrude, fillet)

from . import box as box_part
from .. import derive as D
from ..geom import slab, text_solid, tray
from .. import lock as L
from .. import marks as MK
from ..refuse import refuse
from .. import tables as TB
from .. import text as T

WALL = D.WallThickness       # 1.600, confirmed on the STEP at +-105.350

# The lid stands this much wider than the box's sketch box: the box's running
# clearance plus the lid's own wall less what the closing bump needs. The
# DEPTH needs no such constant — `calLidDepth` IS the lid's measured depth.
WIDTH_OVER_BOX = 4.600

OUTER_ROUND = 1.000          # every outer edge: 4 vertical, 4 top, 4 bottom

# --- the three VARIANTS of a lid ----------------------------------------------
#
# Every function below that reads the mark or the floor text takes which lid
# as `variant`, one of `tables.LID_VARIANTS`: `LID_OWN`, `LID_ALTERNATE` (the
# game's other edition, 7.1d) or `LID_UNMARKED` (no mark, CREDIT where the
# game's name is, 7.2b). They live in `tables.py` so `build.py` and
# `project.py` can name them without loading build123d (`cad/lazy.py`). A
# lid's GEOMETRY is the same across all three.

# What the unmarked lid says where the others say the game's name.
CREDIT = TB.CREDIT


def lid_width(d):
    """`#BoxWidth + 4.600`, off `box.box_width`: one quantity, stated once."""
    return box_part.box_width(d) + WIDTH_OVER_BOX


def lid_depth(d):
    """`calLidDepth`, straight out of the studio — see `spec/LID.md`."""
    return d.calLidDepth


def shell(d):
    """The tray, hollowed to WALL with the TOP face removed."""
    return tray(lid_width(d), lid_depth(d), d.LidHeight, WALL)


# --- the pusher sockets ----------------------------------------------------
#
# One socket per stored pusher, standing on the floor: a block with a channel
# down the middle taking the pusher's plate on edge, two tab recesses in one
# channel wall, and — from C3 up — the key rib that fills the pusher's notch.
SOCKET_H = 5.000             # above the floor, which is the tab's own length
SOCKET_BACK = D.FootDistanceFromWall + WALL   # 9.000 from the lid's BACK FACE,
#                              i.e. #FootDistanceFromWall in from its inner one
KEY_RIB_LEN = 5.000          # along the channel, on the centreline


def socket_count(d):
    """How many pusher sockets the floor carries — a RELEASE change. 7.0
    counts by SIZE; from 7.1 it is one per pusher shipped, and dropping it
    moves nothing else because `socket_centres` keeps the same span.
    `spec/LID.md`, "The middle socket is gone"."""
    if d.rev.lid_socket_per_pusher:
        return box_part.pusher_slot_count(d)
    return 2 if d.HorizontalSlots <= 3 else 3


def socket_centres(d):
    """Channel centre X of each socket, left to right. The FIRST is placed off
    the left inner wall and the rest step across the CARD SLOTS' span, so the
    set is NOT centred on the lid and the span does not move with the socket
    count (`socket_count`)."""
    n = socket_count(d)
    span = (d.HorizontalSlots - 1) * d.calSlotwidth
    first = (-(lid_width(d) / 2 - WALL) + d.calSlotwidth / 2
             + d.calSliderSpaceLeftRight / 2 + d.calFootTotalWidth / 2)
    return [first + k * span / (n - 1) for k in range(n)]


# The tread a socket's pusher offers a holder sits this far forward of the
# holder's rib with the sockets at SOCKET_BACK (`spec/ASSEMBLY.md`). From 7.2f
# the sockets follow the ribs and the offset is nil: `socket_back`.
TREAD_OFFSET_STUDIO = 0.150


def socket_back(d):
    """How far in from the lid's back face a socket's BACK edge sits.
    `SOCKET_BACK` through 7.2e; from 7.2f (`rev.shorter_box`) the sockets move
    with the ribs, so a holder sits centred on its tread."""
    if d.rev.shorter_box:
        return SOCKET_BACK - (TREAD_OFFSET_STUDIO - box_part.rib_shift(d))
    return SOCKET_BACK


def socket_span(d):
    """(y0, y1) of a socket: the standard's `D - 0.400` long, its BACK edge
    `socket_back` in from the lid's back face."""
    y1 = lid_depth(d) / 2 - socket_back(d)
    return y1 - (d.calPusherTotalDepth - L.LID_SOCKET_CLEARANCE), y1


def socket(d, x):
    """One socket, centred on channel X `x`: a block with the channel, the key
    rib (none where the pusher has no notch, `L.has_notch`) and the two tab
    recesses taken out of it. The recesses are in the channel's **-X wall
    only**, because the pusher's tabs stand proud of one face."""
    y0, y1 = socket_span(d)
    z0, z1 = WALL, WALL + SOCKET_H
    _cls, s = L.lock_class(d.calPusherTotalDepth)
    centre = (y0 + y1) / 2

    block = slab(x - d.calFootTotalWidth / 2, x + d.calFootTotalWidth / 2,
                 y0, y1, z0, z1)
    chan_lo, chan_hi = x - L.LID_CHANNEL_W / 2, x + L.LID_CHANNEL_W / 2
    cuts = []
    if L.has_notch(s):
        for a, b in ((y0, centre - KEY_RIB_LEN / 2),
                     (centre + KEY_RIB_LEN / 2, y1)):
            cuts.append(slab(chan_lo, chan_hi, a, b, z0, z1))
    else:
        cuts.append(slab(chan_lo, chan_hi, y0, y1, z0, z1))
    for sign in (-1, +1):
        c = centre + sign * s
        cuts.append(slab(chan_lo - L.LID_RECESS_STEP, chan_lo,
                         c - L.LID_RECESS_LEN / 2, c + L.LID_RECESS_LEN / 2,
                         z0, z1))
    for cut in cuts:
        block = block - cut
    return block


def sockets(d, part):
    return part.fuse(*[socket(d, x) for x in socket_centres(d)])


# --- the closing grooves ---------------------------------------------------
#
# The receptacle for the Box's `Closing mechanism`. The lid goes on over the
# box's rim, so a box height `h` arrives at `WALL + BoxHeight - h` here: the
# bump's TOP lands on the groove's BOTTOM edge, which is what stops the lid.
GROOVE_DEPTH = 1.000
GROOVE_LEN = 10.000          # 8.000 of bump with 1.000 clear at each end
GROOVE_HEIGHT = 3.800        # 3.000 of bump and 0.800 of lead-in
GROOVE_CHAMFER = 0.500       # on the two horizontal edges of the groove FLOOR
BUMP_TOP = 90.000            # `box.BUMP_Z1` — the box's own frame


def groove_span(d):
    """(z0, z1) of the groove. `z0` is the box bump's top, transferred."""
    z0 = WALL + d.BoxHeight - (BUMP_TOP + D.rim_drop(d))
    return z0, z0 + GROOVE_HEIGHT


def closing_grooves(d, part):
    """One groove in each end wall, mirrored, centred on `y = 0` where the
    box's bump lands. The chamfer is on the groove's FLOOR, not its mouth —
    that is the face the bump cams over. The tool is built for +X and
    MIRRORED rather than picked by a sign-dependent index: sorting a moved
    solid's faces gets the deep one wrong on one side."""
    z0, z1 = groove_span(d)
    inner = lid_width(d) / 2 - WALL
    over = 1.0                       # inward, so the cut is not coincident
    tool = Box(GROOVE_DEPTH + over, GROOVE_LEN, z1 - z0)
    deep = tool.faces().sort_by(Axis.X)[-1]
    tool = chamfer(deep.edges().filter_by(Axis.Y), GROOVE_CHAMFER)
    tool = tool.moved(Location((inner + GROOVE_DEPTH - (GROOVE_DEPTH + over) / 2,
                                0, (z0 + z1) / 2)))
    return part - tool - tool.mirror(Plane.YZ)


# --- the floor's engraving -------------------------------------------------
#
# Two blocks, both EMBOSSED — where the Box's floor text is engraved. On the
# +X side three right-aligned lines reading up in Y; on the -X side the
# `Card Cascade` logo, its version, and the staircase. `spec/LID.md`.
TEXT_PROUD = 0.400           # calModelName, GameName, calCapacityLabel, version
LOGO_PROUD = 0.600           # ProductName and its staircase
CAP_MODEL = 3.000            # calModelName's cap height
CAP_LINE = 3.500             # GameName's and calCapacityLabel's
LINE_GAP = 2.000             # a line's cap top to the baseline above it
VERSION_DROP = 2.000         # ProductName's baseline to the version's cap top
LOGO_DROP = 1.000            # + FootDistanceFromWall, to ProductName's cap top

# How far the +X text block may be SCALED UP, from 7.2c
# (`rev.larger_lid_text`, `text_scale`): it grows until it is LINE_GAP from
# what is to its left or keeps at the front wall what it keeps at the back,
# and never past this. The Card Cascade block does NOT scale.
# `spec/LID.md`, "The text block grows with the lid".
TEXT_SCALE_MAX = 1.500


def text_offset(d):
    """How far the +X text block's right edge sits in from the right inner
    wall: `#calLidTextOffset + 2*#calSlotwidth/3 + #calFootTotalWidth + 2mm`.
    NO conditional, unlike the logo block's — which is what puts an XS lid's
    two blocks on top of each other rather than side by side."""
    return (d.calLidTextOffset + 2 * d.calSlotwidth / 3
            + d.calFootTotalWidth + 2.0)


def logo_offset(d):
    """The same, for the -X logo block's left edge from the left inner wall,
    with `#calFootTotalWidth + 2mm` added only where `#HorizontalSlots > 2`:
    so on every lid but an XS one the two blocks are mirror images."""
    extra = d.calFootTotalWidth + 2.0 if d.HorizontalSlots > 2 else 0.0
    return d.calLidTextOffset + 2 * d.calSlotwidth / 3 + extra


def logo_width(d):
    """`#LogoWidth` — the box `ProductName` is fitted to and the staircase's
    own width, which makes the logo's size a pure function of the slot
    width."""
    return d.calSlotwidth - 12.0 - d.calFootTotalWidth


def logo_size(d):
    """`ProductName`'s font size, and with it `#LogoHeight` (its cap) and
    `#LogoHeight23` (the version's). Fitted to `#LogoWidth` by ADVANCE;
    Onshape's own advance for this string is slightly wider than the font
    file's, so this comes out that much larger than the reference
    (`cad/README.md`, "Text sizing is a rule")."""
    return T.floored(T.fit_size(d.ProductName, logo_width(d)), proud=True)


def emboss(txt, size, x_pen, baseline, proud):
    """One line of embossed text, as a solid to fuse. Placed by the PEN ORIGIN
    (`geom.text_solid`), which no measurement of rendered ink recovers."""
    return text_solid(txt, T.LOGO_FONT, size, proud, z=WALL).moved(
        Location((x_pen, baseline, 0)))


def right_aligned(txt, size, right, baseline, proud):
    """A line whose text box ENDS at `right`."""
    adv = T.metrics(txt)[0]
    return emboss(txt, size, right - adv * size, baseline, proud)


def middle_line(d, variant=TB.LID_OWN):
    """The block's middle line — the one line of floor text a variant
    changes."""
    return CREDIT if variant == TB.LID_UNMARKED else d.GameName


TEXT_LINES = (CAP_LINE, CAP_LINE, CAP_MODEL)   # the block's three lines, top down


def text_anchor(d):
    """(right edge, cap top of the first line) — where the +X block hangs:
    right-aligned on `text_offset`, its cap top
    `#HorizontalSlots > 2 ? 2mm : 15mm` below the socket's back edge, which is
    why an XS lid's text sits lower. NEITHER anchor moves with the scale
    (`text_scale`); the block grows away from them, left and down."""
    right = lid_width(d) / 2 - WALL - text_offset(d)
    if d.HeightClass and d.HorizontalSlots <= 2:
        # A class XS lid's 44 slot leaves the studio's anchor too far left for
        # the block to clear the left socket: it hangs off the RIGHT socket
        # instead, and `text_scale` fits it between the two, which is all the
        # box's bottom slot leaves it in play (`spec/LID.md`).
        right = socket_centres(d)[1] - d.calFootTotalWidth / 2 - LINE_GAP
    gap = 2.0 if d.HorizontalSlots > 2 else 15.0
    return right, lid_depth(d) / 2 - WALL - D.FootDistanceFromWall - gap


def text_block_size(d):
    """(width, depth) of the block at scale 1: the widest of the FOUR lines a
    cascade's lids carry, by ADVANCE. All four and not the three of ONE lid,
    so a cascade's own and unmarked lids share one scale."""
    lines = ((d.calCapacityLabel, CAP_LINE), (d.GameName, CAP_LINE),
             (CREDIT, CAP_LINE), (d.calModelName, CAP_MODEL))
    w = max(T.metrics(txt)[0] * cap / T.CAP for txt, cap in lines)
    return w, sum(TEXT_LINES) + LINE_GAP * (len(TEXT_LINES) - 1)


def text_room(d):
    """(width, depth) the block may grow into, from its anchors: to LINE_GAP
    from whatever is to its LEFT in its band — the Card Cascade block, or on
    an XS lid the left socket — and to the front inner wall plus what the
    block keeps at the back."""
    right, top = text_anchor(d)
    if d.HorizontalSlots > 2:
        left = -(lid_width(d) / 2 - WALL) + logo_offset(d) + logo_width(d)
    else:
        left = socket_centres(d)[0] + d.calFootTotalWidth / 2
    front = -lid_depth(d) / 2 + WALL + D.FootDistanceFromWall + 2.0
    return right - left - LINE_GAP, top - front


def text_scale(d):
    """The factor the +X block is drawn at: 1.0 before 7.2c, then the largest
    of 1.0 .. TEXT_SCALE_MAX at which it fits `text_room`. One number per
    cascade; every cap and gap takes it."""
    if not d.rev.larger_lid_text:
        return 1.0
    (rw, rd), (bw, bd) = text_room(d), text_block_size(d)
    # A class lid may also SHRINK the block to fit: the box stands on this
    # floor in play, and text outside the room lands under its floor.
    least = 0.0 if d.HeightClass else 1.0
    return max(least, min(TEXT_SCALE_MAX, rw / bw, rd / bd))


def text_block(d, variant=TB.LID_OWN):
    """`calCapacityLabel`, `GameName`, `calModelName` — the +X block:
    right-aligned on `text_anchor`'s right edge, reading UP in Y at
    `CAP_LINE / CAP_LINE / CAP_MODEL` times `text_scale`, each line's cap top
    `LINE_GAP` (times the same) below the baseline above it."""
    right, top = text_anchor(d)
    s = text_scale(d)
    base = top - CAP_LINE * s
    out = []
    lines = ((d.calCapacityLabel, CAP_LINE), (middle_line(d, variant), CAP_LINE),
             (d.calModelName, CAP_MODEL))
    for i, (txt, cap) in enumerate(lines):
        out.append(right_aligned(txt, T.floored(cap * s / T.CAP, proud=True),
                                 right, base, TEXT_PROUD))
        if i + 1 < len(lines):
            # The NEXT line's cap, not this one's: the gap is measured to that
            # line's cap TOP, so a 3.000 line follows 2.000 + 3.000 below.
            base = base - (LINE_GAP + lines[i + 1][1]) * s
    return out


def logo_block(d):
    """`ProductName`, `calVersion` and the staircase — the -X block.
    `ProductName`'s box is `logo_offset` in from the left inner wall and
    `logo_width` long; the version is right-aligned on the same box."""
    left = -(lid_width(d) / 2 - WALL) + logo_offset(d)
    size = logo_size(d)
    cap = T.CAP * size                       # #LogoHeight
    cap23 = 2 * cap / 3                      # #LogoHeight23
    base = (lid_depth(d) / 2 - WALL
            - (D.FootDistanceFromWall + LOGO_DROP)) - cap
    out = [emboss(d.ProductName, size, left, base, LOGO_PROUD),
           right_aligned(d.calVersion, cap23 / T.CAP, left + logo_width(d),
                         base - VERSION_DROP - cap23, TEXT_PROUD)]
    stair = staircase(d, left, base - cap23)
    return out + ([stair] if stair else [])


def staircase(d, left, top):
    """The Card Cascade logo: `RisingSliders` steps descending to the right,
    filling `#LogoWidth` by `#SlopeHeight` — which is not a number of its own,
    but the run from the pusher sockets' front edge up to `#LogoHeight23`
    below `ProductName`'s baseline. **Suppressed on an XS lid**, which carries
    the word alone — inferred, not read off a sketch."""
    if d.HorizontalSlots <= 2:
        return None
    y0 = socket_span(d)[0]
    sw, sh = logo_width(d) / d.RisingSliders, (top - y0) / d.RisingSliders
    pts = [(left, y0), (left + logo_width(d), y0)]
    for k in range(1, d.RisingSliders + 1):
        pts.append((left + logo_width(d) - (k - 1) * sw, y0 + k * sh))
        pts.append((left + logo_width(d) - k * sw, y0 + k * sh))
    with BuildPart() as part:
        with BuildSketch(Plane.XY.offset(WALL)):
            Polygon(*pts, align=None)
        extrude(amount=LOGO_PROUD)
    return part.part


def floor_text(d, part, variant=TB.LID_OWN):
    return part.fuse(*(text_block(d, variant) + logo_block(d)))


# --- the logo pattern ------------------------------------------------------
#
# The game's logo, in the UNDERSIDE of the floor, printed in the second
# filament: the artwork is extruded PATTERN_DEPTH into the floor and the same
# regions fill the pocket, standing PATTERN_PROUD below the underside so the
# slicer has an unambiguous boundary. The inlays are separate SOLIDS, not part
# of the lid, and `cad.build` writes them as their own 3MF objects.
PATTERN_DEPTH = 0.810
PATTERN_PROUD = 0.010


# How the mark is SIZED — `cad/` policy, not Onshape's (spec/LID.md, "Sizing
# the mark"). "As big as fits" is NOT the rule: the mark takes a PROPORTION of
# the lid, with the flat floor as a hard limit underneath it:
#
#     want = min(WIDTH_FRACTION * W / w,  DEPTH_FRACTION * D / h)
#     hard = min((W - 2*ROUND) / w,       (D - 2*ROUND) / h)
#     scale = min(max(want, 1.0), hard)
#
# A mark is never taken BELOW its drawn size to satisfy a proportion, but it
# IS taken below to satisfy `hard`: a pocket that runs into a round is a
# defect. The fractions, `LOGO_CLEAR` and `tables.LID_LOGO_EDITION` are
# Allan's to set.
LOGO_WIDTH_FRACTION = 0.600
LOGO_DEPTH_FRACTION = 0.850

# What the mark keeps clear of the outer rounds, on top of the rounds
# themselves: clamped to the flat floor exactly, the inlay stops sitting flush
# where the floor starts to curve away.
LOGO_CLEAR = 0.500


def logo_room(d):
    """(width, depth) of FLAT outer floor — where the outer rounds start to
    curve away from it."""
    return (lid_width(d) - 2 * OUTER_ROUND,
            lid_depth(d) - 2 * OUTER_ROUND)


def logo_limit(d):
    """(half width, half depth) the mark's INK must stay inside: the flat
    floor less `LOGO_CLEAR`, from the lid's centre. Half-extents, NOT a size —
    comparing `logo_room` against a mark's size says the same thing only for a
    mark centred on the lid, and a drawing is not (`marks.reach`)."""
    rw, rd = logo_room(d)
    return (rw / 2 - LOGO_CLEAR, rd / 2 - LOGO_CLEAR)


def logo_target(d):
    """(width, depth) the mark is sized to — the proportion of the lid it
    should take."""
    return (lid_width(d) * LOGO_WIDTH_FRACTION,
            lid_depth(d) * LOGO_DEPTH_FRACTION)


def logo_edition(d, variant=TB.LID_OWN):
    """Which of the game's marks this lid carries, or None for its default.
    Keyed on the BASE MODEL, because it is a question about which sets the box
    holds (`TB.lid_editions`). `LID_ALTERNATE` asks for the SECOND edition
    such a cascade ships from 7.1d; asking a cascade that has no alternate is
    a bug in the caller, and `build.lid_variants_built` is the gate."""
    editions = TB.lid_editions(d.GameName, d.calModelName)
    if variant != TB.LID_ALTERNATE:
        return editions[0]
    if len(editions) < 2:
        refuse(f"{d.calModelName} carries its game's only lid mark; there is "
               f"no alternate edition to build (cad/tables.lid_editions)")
    return editions[1]



def logo_scale(d, name):
    """The nominal factor this lid sizes `name` to — see above. A mark's size
    is AFFINE in it, `a*n + b`, because a generated mark's letters scale and
    its strokes do not (`cad/marks.growth`); a drawing has `b = 0`."""
    (tw, td) = logo_target(d)
    (aw, bw), (ah, bh) = MK.growth(d.GameName, name)
    want = min((tw - bw) / aw, (td - bh) / ah)
    # The hard clamp is per SIDE, against where the ink may REACH — not the
    # mark's size against the flat floor (`marks.reach`, `logo_limit`).
    lw, ld = logo_limit(d)
    hard = min((lim - b) / a
               for lim, (a, b) in zip((lw, lw, ld, ld), MK.reach(d.GameName, name))
               if a > 0)
    return min(max(want, 1.0), hard)


def logo_choice(d, variant=TB.LID_OWN):
    """(mark, nominal factor) — which of the game's marks this lid gets and how
    far it is sized; (None, 0.0) for a game with no artwork and for the
    unmarked lid, which takes the same path: no pocket, no inlays, one body.
    The marks are listed LARGEST FIRST, so the first that fits `logo_limit` as
    drawn is the biggest that fits; if none does, the smallest is shrunk."""
    if variant not in TB.LID_VARIANTS:
        refuse(f"unknown lid variant {variant!r}; one of {TB.LID_VARIANTS} (cad/parts/lid.py)")
    if variant == TB.LID_UNMARKED:
        return None, 0.0
    names = (TB.LID_LOGO.get(d.GameName) or {}).get(logo_edition(d, variant))
    if not names:
        return None, 0.0
    chosen = None
    for name in names:
        if MK.growth(d.GameName, name) is None:
            continue
        chosen = name
        if logo_scale(d, name) >= 1.0:
            break
    if chosen is None:
        return None, 0.0
    return chosen, logo_scale(d, chosen)


def logo_art(d, variant=TB.LID_OWN):
    """The game's mark as filled faces in the lid's frame; [] for a lid that
    carries none. A drawing is already in that frame, so `cad.marks` sizes it
    about its OWN centre; a generated mark is built centred. A game in
    `TB.LID_LOGO_TURNED` is turned a half turn about the lid's centre here,
    AFTER it is sized — which the fit need not know."""
    name, n = logo_choice(d, variant)
    if not name:
        return []
    faces = MK.faces(d.GameName, name, n)
    if d.GameName in TB.LID_LOGO_TURNED:
        faces = [f.rotate(Axis.Z, 180) for f in faces]
    return faces


def _prisms(d, variant=TB.LID_OWN):
    """The mark's regions extruded `PATTERN_DEPTH` up from the underside —
    both the pocket and, moved down, the inlays."""
    # `dir` explicitly, NOT the face's own normal: a DXF's loops wind however
    # they were drawn, so some regions come back facing -Z and extruding
    # along their normals sends them DOWN — cutting nothing and leaving their
    # inlays floating below the lid.
    return [extrude(f, PATTERN_DEPTH, dir=(0, 0, 1))
            for f in logo_art(d, variant)]


def logo_pattern(d, part, variant=TB.LID_OWN):
    """(the body with its pocket cut, the inlay solids) — one set of regions
    at two Z ranges, so the inlay cannot drift out of the pocket."""
    prisms = _prisms(d, variant)
    if not prisms:
        return part, []
    # ONE cut with every region, into the BARE SHELL: the regions are
    # disjoint, nothing later touches the pocket, and a ten-face body cuts far
    # faster than the finished lid's hundreds. The prisms start ON the
    # underside, which is fine HERE — the Topper's identical cut is not
    # (`topper.ENGRAVE_OVERSHOOT`).
    part = part.cut(*prisms)
    return part, [q.moved(Location((0, 0, -PATTERN_PROUD))) for q in prisms]


def inlays(d):
    """The logo's inlay solids alone, without building the lid."""
    return [q.moved(Location((0, 0, -PATTERN_PROUD))) for q in _prisms(d)]


def outer_edges(d, part):
    """The twelve edges of the outer envelope. Stated rather than picked: an
    edge qualifies when its midpoint lies on two of the six outer faces, and
    nothing else on the lid is within reach of them."""
    half_w, half_d, H = lid_width(d) / 2, lid_depth(d) / 2, d.LidHeight
    tol = 1e-6
    out = []
    for e in part.edges():
        m = e @ 0.5
        on = ((abs(abs(m.X) - half_w) < tol) + (abs(abs(m.Y) - half_d) < tol)
              + (abs(m.Z) < tol) + (abs(m.Z - H) < tol))
        if on >= 2:
            out.append(e)
    return out


def build_all(d, variant=TB.LID_OWN):
    """(the Lid BODY, its logo inlays) — both from ONE extrusion of the mark,
    so pocket and inlays always agree. `variant` is one of `TB.LID_VARIANTS`.
    The pocket goes into the bare shell first: nothing else reaches it, so the
    order is free and the cheap one is taken."""
    part = shell(d)
    part, inlays = logo_pattern(d, part, variant)
    part = sockets(d, part)
    part = closing_grooves(d, part)
    part = floor_text(d, part, variant)
    # The outer rounds stay LAST, as the tree has them: rounding the bare
    # shell first saves nothing and CHANGES a mark that sits at the hard limit
    # against the rounds, so the order is not free after all.
    return fillet(outer_edges(d, part), OUTER_ROUND), inlays


def build(d, variant=TB.LID_OWN):
    """The Lid BODY as a build123d Part, from a `derive.Derived`."""
    return build_all(d, variant)[0]
