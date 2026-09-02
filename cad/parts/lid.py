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

Complete: shell, sockets, closing grooves, the outer rounds, the floor's
engraving, and the logo pattern in the underside — every game has artwork now
(`cad/tables.LID_LOGO`). The pattern is where `cad/` first parts company with
Onshape on purpose: the mark is FITTED to the lid rather than drawn at one or
two fixed sizes. See `spec/LID.md`, "Sizing the mark".
"""
from build123d import (
    Align, Axis, Box, BuildPart, BuildSketch, Kind, Location, Mode, Plane,
    Polygon, Pos, Rectangle, Text, add, chamfer, extrude, fillet, offset,
)

from . import box as box_part
from .. import art as A
from .. import derive as D
from .. import lock as L
from .. import tables as TB
from .. import text as T

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
SOCKET_BACK = D.FootDistanceFromWall + WALL   # 9.000 from the lid's BACK FACE,
#                              i.e. #FootDistanceFromWall in from its inner one
KEY_RIB_LEN = 5.000          # along the channel, on the centreline

# A socket block is `#calFootTotalWidth` wide — the pusher's own foot, plate
# and both feet — with the channel down the middle of it, so its two walls are
# what is left. Nothing here is a number of its own.


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

    The FIRST one is placed and the rest step off it, which is the sketch's own
    shape (Allan):

        first block's left edge = the left inner wall
                                  + #calSlotwidth/2 + #calSliderSpaceLeftRight/2

    and the set then spans `(HorizontalSlots - 1) * calSlotwidth`, the card
    slots' own span. `35.45` in on a `calSlotwidth 65` lid.

    That anchor is why the set is NOT centred on the lid: it leaves `35.450` at
    the left and `36.050` at the right, so its centre lands `0.300` to the left
    of the lid's. This file carried that `-0.300` as a measured constant until
    the sketch turned up — see spec/LID.md, "What the fit got wrong".
    """
    n = socket_count(p)
    span = (p.HorizontalSlots - 1) * d.calSlotwidth
    first = (-(lid_width(p, d) / 2 - WALL) + d.calSlotwidth / 2
             + d.calSliderSpaceLeftRight / 2 + d.calFootTotalWidth / 2)
    return [first + k * span / (n - 1) for k in range(n)]


def socket_span(p, d):
    """(y0, y1) of a socket. Its length is the standard's `D - 0.400` and its
    BACK edge sits `SOCKET_BACK` in from the lid's back face — constant on all
    46 lids, whose depths run 34.98 to 111.30."""
    y1 = lid_depth(d) / 2 - SOCKET_BACK
    return y1 - (d.calPusherTotalDepth - L.LID_SOCKET_CLEARANCE), y1


def socket(p, d, x):
    """One socket, centred on channel X `x`.

    The block is `#calFootTotalWidth` x span x `SOCKET_H` and everything else
    is taken out of it:

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

    block = slab(x - d.calFootTotalWidth / 2, x + d.calFootTotalWidth / 2,
                 y0, y1)
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


# --- the floor's engraving -------------------------------------------------
#
# Two blocks, both EMBOSSED — where the Box's floor text is engraved. On the
# +X side three right-aligned lines reading up in Y; on the -X side the
# `Card Cascade` logo, its version, and the staircase. Every expression below
# is the part studio's own, from Allan's sketches (2026-09-02); `spec/LID.md`
# records them and what each was checked against.
TEXT_PROUD = 0.400           # calModelName, GameName, calCapacityLabel, version
LOGO_PROUD = 0.600           # ProductName and its staircase
CAP_MODEL = 3.000            # calModelName's cap height
CAP_LINE = 3.500             # GameName's and calCapacityLabel's
LINE_GAP = 2.000             # a line's cap top to the baseline above it
VERSION_DROP = 2.000         # ProductName's baseline to the version's cap top
LOGO_DROP = 1.000            # + FootDistanceFromWall, to ProductName's cap top


def text_offset(d):
    """How far the +X text block's right edge sits in from the right inner wall.

        #calLidTextOffset + 2*#calSlotwidth/3 + #calFootTotalWidth + 2mm

    Allan's sketch, verbatim — `60.43` on a `calSlotwidth 65` lid. It carries
    no conditional, unlike the logo block's, which is what puts an XS lid's two
    blocks on top of each other rather than side by side.
    """
    return (d.calLidTextOffset + 2 * d.calSlotwidth / 3
            + d.calFootTotalWidth + 2.0)


def logo_offset(p, d):
    """The same, for the -X logo block's left edge from the left inner wall.

        #calLidTextOffset + 2*#calSlotwidth/3
        + (#HorizontalSlots > 2 ? #calFootTotalWidth + 2mm : 0)

    So on every lid but an XS one the two blocks are mirror images; on an XS
    lid the logo keeps the bare offset and the text block moves DOWN instead —
    see `text_block`. Exact on all 44 cached lids.
    """
    extra = d.calFootTotalWidth + 2.0 if p.HorizontalSlots > 2 else 0.0
    return d.calLidTextOffset + 2 * d.calSlotwidth / 3 + extra


def logo_width(d):
    """`#LogoWidth = #calSlotwidth - 12mm - #calFootTotalWidth`.

    The box `ProductName` is fitted to, and the staircase's own width. `43.800`
    at `calSlotwidth 65`, and it is what makes the logo's size a pure function
    of the slot width across the whole catalogue.
    """
    return d.calSlotwidth - 12.0 - d.calFootTotalWidth


def logo_size(d):
    """`ProductName`'s font size, and with it `#LogoHeight` (its cap) and
    `#LogoHeight23` (two thirds of that, the version's cap).

    Fitted to `#LogoWidth` by ADVANCE. Onshape's own advance for this string
    runs `0.31 %` wider than the font file's, so this comes out `0.31 %` larger
    than the reference — the identical residual `spec/BOX.md` records for the
    Box's `ProductName`, and the same cause. See `cad/README.md`, "Text sizing
    is a rule, not a transcription".
    """
    return T.fit_size(d.ProductName, logo_width(d))


def emboss(txt, size, x_pen, baseline, proud):
    """One line of embossed text, as a solid to fuse.

    `x_pen` is where the pen starts and `baseline` the baseline. The glyphs are
    placed by the PEN ORIGIN, which no measurement of rendered ink recovers —
    `cad.text.metrics` reads the bearings out of the font file. Two traps, both
    already paid for in `box.engrave_line`: `Text` adds ITSELF to the sketch as
    well as the shifted copy unless it is `Mode.PRIVATE`, and `align=MIN` leaves
    the pen at `-lsb`, so the shift is `+lsb, +lo`.
    """
    _adv, lsb, lo, _hi = T.metrics(txt)
    with BuildPart() as part:
        with BuildSketch(Plane.XY.offset(WALL)):
            glyphs = Text(txt, font_size=size, font_path=T.LOGO_FONT,
                          align=(Align.MIN, Align.MIN), mode=Mode.PRIVATE)
            add(Pos(lsb * size, lo * size) * glyphs)
        extrude(amount=proud)
    return part.part.moved(Location((x_pen, baseline, 0)))


def right_aligned(txt, size, right, baseline, proud):
    """A line whose text box ENDS at `right` — the three +X lines and the
    version, which are all right-aligned on their block's edge."""
    adv = T.metrics(txt)[0]
    return emboss(txt, size, right - adv * size, baseline, proud)


def text_block(p, d):
    """`calCapacityLabel`, `GameName`, `calModelName` — the +X block.

    Right-aligned on `text_offset` in from the right inner wall, reading UP in
    Y at `CAP_LINE / CAP_LINE / CAP_MODEL`, each line's cap top `LINE_GAP`
    below the baseline above it.

    The block hangs off the pusher socket line: the capacity line's cap top is
    `#HorizontalSlots > 2 ? 2mm : 15mm` below the socket's back edge. The 15 is
    the whole of why an XS lid's text sits lower — see `spec/LID.md`.
    """
    right = lid_width(p, d) / 2 - WALL - text_offset(d)
    gap = 2.0 if p.HorizontalSlots > 2 else 15.0
    base = (lid_depth(d) / 2 - WALL - D.FootDistanceFromWall - gap) - CAP_LINE
    out = []
    lines = ((d.calCapacityLabel, CAP_LINE), (p.GameName, CAP_LINE),
             (d.calModelName, CAP_MODEL))
    for i, (txt, cap) in enumerate(lines):
        out.append(right_aligned(txt, cap / T.CAP, right, base, TEXT_PROUD))
        if i + 1 < len(lines):
            # The NEXT line's cap, not this one's: the gap is measured to that
            # line's cap TOP, so a 3.000 line follows 2.000 + 3.000 below.
            base = base - LINE_GAP - lines[i + 1][1]
    return out


def logo_block(p, d):
    """`ProductName`, `calVersion` and the staircase — the -X block.

    `ProductName`'s cap top is `#FootDistanceFromWall + 1mm` below the lid's
    inner back face, its box `text_offset` in from the left inner wall and
    `logo_width` long. The version is right-aligned on the same box, its cap
    top `VERSION_DROP` below `ProductName`'s baseline.
    """
    left = -(lid_width(p, d) / 2 - WALL) + logo_offset(p, d)
    size = logo_size(d)
    cap = T.CAP * size                       # #LogoHeight
    cap23 = 2 * cap / 3                      # #LogoHeight23
    base = (lid_depth(d) / 2 - WALL
            - (D.FootDistanceFromWall + LOGO_DROP)) - cap
    out = [emboss(d.ProductName, size, left, base, LOGO_PROUD),
           right_aligned(d.calVersion, cap23 / T.CAP, left + logo_width(d),
                         base - VERSION_DROP - cap23, TEXT_PROUD)]
    stair = staircase(p, d, left, base - cap23)
    return out + ([stair] if stair else [])


def staircase(p, d, left, top):
    """The Card Cascade logo: `RisingSliders` steps descending to the right,
    filling `#LogoWidth` by `#SlopeHeight`.

        #LogoStepWidth  = #LogoWidth / #RisingSliders
        #LogoStepHeight = #SlopeHeight / #RisingSliders

    `#SlopeHeight` is not a number of its own: the slope runs from the pusher
    sockets' own front edge up to `#LogoHeight23` below `ProductName`'s
    baseline, so it is `67.620` on the nine-riser lid and `22.018` on the
    two-riser one by the same rule.

    **Suppressed on an XS lid**, which carries the word alone. That is inferred
    rather than read off a sketch — it is the third feature to branch on
    `#HorizontalSlots > 2`, and both XS lids in `individual/` agree.
    """
    if p.HorizontalSlots <= 2:
        return None
    y0 = socket_span(p, d)[0]
    sw, sh = logo_width(d) / p.RisingSliders, (top - y0) / p.RisingSliders
    pts = [(left, y0), (left + logo_width(d), y0)]
    for k in range(1, p.RisingSliders + 1):
        pts.append((left + logo_width(d) - (k - 1) * sw, y0 + k * sh))
        pts.append((left + logo_width(d) - k * sw, y0 + k * sh))
    with BuildPart() as part:
        with BuildSketch(Plane.XY.offset(WALL)):
            Polygon(*pts, align=None)
        extrude(amount=LOGO_PROUD)
    return part.part


def floor_text(p, d, part):
    """Both blocks, fused to the floor."""
    for solid in text_block(p, d) + logo_block(p, d):
        part = part + solid
    return part


# --- the logo pattern ------------------------------------------------------
#
# The game's logo, in the UNDERSIDE of the floor, printed in the second
# filament. In Onshape it is one sketch and two features, and this is both of
# them: `Remove logo` blind-extrudes the artwork `0.810` into the floor, and
# `Add Logo Material` extrudes the same regions `0.810` from a starting offset
# of `-0.800` — so the inlay fills the pocket and stands `PATTERN_PROUD` below
# the lid's own underside, which is what gives the slicer an unambiguous
# boundary between the two filaments.
#
# The inlays are separate SOLIDS, not part of the lid: `cad.build` writes them
# as their own objects in the 3MF, exactly as Onshape's export does.
PATTERN_DEPTH = 0.810
PATTERN_PROUD = 0.010


# How the mark is SIZED
# ---------------------
# Onshape draws each mark at one size and, on Innovation alone, at a second one
# through `#LogoScaleFactor = (#LidWidth < 70mm ? 1.6 : 1)`. That rule is a
# blunt instrument, and Allan has asked for the mark to follow the box instead:
# take the biggest drawing that fits, then size it to the lid.
#
# "As big as fits" on its own is not the rule, though. The floor a lid can
# spare grows much faster than the mark should: fitted to the flat, Dominion's
# mark would be 199 x 69 on its deepest lid and Innovation's plain one 218 mm
# across a 220 mm lid, edge to edge. What the catalogue actually holds to is a
# PROPORTION — the marks Allan has drawn sit at 22..79 % of their tightest
# lid's width — so that is the rule here, with the floor as a hard limit
# underneath it:
#
#     want = min(WIDTH_FRACTION * W / w,  DEPTH_FRACTION * D / h)
#     hard = min((W - 2*ROUND) / w,       (D - 2*ROUND) / h)
#     scale = min(max(want, 1.0), hard)
#
# The two clamps are what keep it honest at the ends. A mark is never taken
# BELOW its drawn size to satisfy a proportion — that would shrink marks Allan
# has already published, and he asked for bigger, not smaller — but it is taken
# below to satisfy `hard`, because a pocket that runs into a round is a defect.
# Compile's smallest lid is the one that needs it: its mark is 39.333 deep on a
# 37.700 lid and has to come down to 0.908 (Onshape draws that lid at 0.798).
#
# WIDTH_FRACTION 0.600 is Dominion's own — its mark is 124.693 on a 207.900
# lid — and it is the constant that does the work, because depth is otherwise
# slack on every deep lid. DEPTH_FRACTION 0.850 is Innovation's big mark on the
# 62.100 lid it was drawn for. Between them they leave 20 of the catalogue's 50
# lids exactly as they are today and grow the rest.
#
# Both are Allan's to set, and so is `LID_LOGO_EDITION` beside them.
LOGO_WIDTH_FRACTION = 0.600
LOGO_DEPTH_FRACTION = 0.850


def logo_room(p, d):
    """(width, depth) of FLAT outer floor — the hard limit, past which the
    pocket would run into an outer round."""
    return (lid_width(p, d) - 2 * OUTER_ROUND,
            lid_depth(d) - 2 * OUTER_ROUND)


def logo_target(p, d):
    """(width, depth) the mark is sized to — the proportion of the lid it
    should take, which is a smaller rectangle than `logo_room` on all but the
    shallowest lids."""
    return (lid_width(p, d) * LOGO_WIDTH_FRACTION,
            lid_depth(d) * LOGO_DEPTH_FRACTION)


def logo_edition(p, d):
    """Which of the game's marks this cascade carries, or None for its default.

    Keyed on the base model — `calModelName` up to its third dot — because it
    is a question about which sets the box holds. Innovation's two single-set
    cascades say just "Innovation" where the other four say "Innovation
    Ultimate" (`TB.LID_LOGO_EDITION`).
    """
    rule = TB.LID_LOGO_EDITION.get(p.GameName)
    if not rule:
        return None
    return rule.get(".".join(d.calModelName.split(".")[:3]))


def logo_scale(p, d, size):
    """How far a drawing of `size` is scaled on this lid — see above."""
    (rw, rd), (tw, td) = logo_room(p, d), logo_target(p, d)
    hard = min(rw / size[0], rd / size[1])
    want = min(tw / size[0], td / size[1])
    return min(max(want, 1.0), hard)


def logo_choice(p, d):
    """(filename, scale) — which drawing of the game's mark this lid gets and
    how far it is scaled, or (None, 0.0) for a game with no artwork on file.

    The drawings are listed largest first, so the first one that fits the flat
    floor as drawn is the biggest that fits. If none does — the lid is smaller
    than every drawing — the last, smallest one is taken and shrunk to fit.
    """
    names = (TB.LID_LOGO.get(p.GameName) or {}).get(logo_edition(p, d))
    if not names:
        return None, 0.0
    chosen = None
    for name in names:
        size = A.extent(p.GameName, name)
        if size is None:
            continue
        chosen = name
        if logo_scale(p, d, size) >= 1.0:
            break
    if chosen is None:
        return None, 0.0
    return chosen, logo_scale(p, d, A.extent(p.GameName, chosen))


def logo_art(p, d):
    """The game's mark as filled faces in the lid's frame, or None.

    The DXF is drawn in that frame already — lifted from, or exported beside, a
    reference lid — so the fit is applied about the drawing's OWN centre, not
    the lid's. At scale 1 that leaves the artwork exactly where Onshape put it.
    """
    name, scale = logo_choice(p, d)
    if not name:
        return None
    faces = A.logo(p.GameName, name)
    if not faces:
        return None
    if abs(scale - 1.0) < 1e-9:
        return list(faces)
    cx, cy = A.centre(p.GameName, name)
    return [f.moved(Location((-cx, -cy, 0))).scale(scale)
             .moved(Location((cx, cy, 0))) for f in faces]


def logo_pattern(p, d, part):
    """(the body with its pocket cut, the inlay solids).

    Both come from one set of regions, so the inlay cannot drift out of the
    pocket: they are the same extrusion at two Z ranges.
    """
    faces = logo_art(p, d)
    if not faces:
        return part, []
    inlays = []
    for f in faces:
        # `dir` explicitly, NOT the face's own normal: a DXF's loops wind
        # whichever way they were drawn, and six of the Innovation logo's 31
        # regions come back facing -Z. Extruded along their normals those six
        # went DOWN — cutting nothing and leaving their inlays floating below
        # the lid, which cost exactly their 134.484 mm2 x 0.810.
        prism = extrude(f, PATTERN_DEPTH, dir=(0, 0, 1))
        part = part - prism
        inlays.append(prism.moved(Location((0, 0, -PATTERN_PROUD))))
    return part, inlays


def inlays(p):
    """Just the logo's inlay solids — what `build` cuts the pocket for."""
    d = D.derive(p)
    faces = logo_art(p, d)
    return [extrude(f, PATTERN_DEPTH, dir=(0, 0, 1))
            .moved(Location((0, 0, -PATTERN_PROUD)))
            for f in (faces or [])]


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
    """`p` is a params.Primary. Returns the Lid BODY as a build123d Part.

    The logo pattern's inlays are separate solids — `inlays(p)` — because they
    print in the second filament and Onshape exports them as their own bodies.
    The pocket for them is cut here, so the two always agree.
    """
    d = D.derive(p)
    part = shell(p, d)
    part = sockets(p, d, part)
    part = closing_grooves(p, d, part)
    part = floor_text(p, d, part)
    part, _inlays = logo_pattern(p, d, part)
    return fillet(outer_edges(p, d, part), OUTER_ROUND)
