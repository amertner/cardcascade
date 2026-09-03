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

The BLANK is complete: `build()` reproduces all three rolled-back exports and
the unfilleted one with zero symmetric difference in both directions, on two
parameter sets, and the filleted `Unseen` body holds nothing it lacks.

INCOMPLETE only in that the `Expansion Name` group — the mark and the
expansion's name, 19 features — is not written, so the other five of the six
are not buildable yet. `spec/TOPPER.md` records every rule they will need.
"""
import math

from build123d import (
    Align, Axis, Box, BuildLine, BuildPart, BuildSketch, GeomType, Line,
    Location, Mode, Plane, Polyline, Pos, Rot, Text, ThreePointArc, chamfer,
    extrude, fillet, make_face, mirror,
)

from .. import derive as D
from .. import text as TX
from . import holder as H

# Where the base sits in assembly. Constant on all 48 cached components and on
# every reference, whatever the capacity, size or sleeving. It is PLACEMENT —
# where the assembly mate lands the part — not a formula, and Allan has said it
# does not matter. Nothing derives it and nothing should.
Z_BASE = 48.450

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
# `Face of TriangleMatch` — so its two dimensions are measured there, not in Y.
# The 0.800 is the inset from the slant's REAR edge and the 1.400 the inset
# from each END. Differencing the wedge against the `to Remove Inner Hole`
# rollback gives the tool exactly: a 6-face prism, and its rear face lands at
# 0.800 * cos(theta) in Y — 0.444 on M15-Sl at slope 1.4977, 0.242 on M10-Un at
# 3.1538. A plain Y-offset would be wrong by the slope, and wrong differently
# on every row, because the slope moves with calSlotDepth.
INNER_INSET = 0.800        # from the slant's rear edge, ALONG the slant
INNER_END_INSET = 1.400    # from each end of the part, in X

TAB_W = D.WallThickness    # 1.600
TAB_INSET = 1.300          # from each end of the part
TAB_RISE = 44.000          # "extruded to 44 mm blind" (Allan), off the FLOOR
# How far the tab stops short of the pocket's rear wall. NOT a constant offset
# from the rear FACE: measured 1.442 in on M10-Un and 1.644 on M15-Sl, and the
# difference is exactly INNER_INSET * (cos 0.55529 - cos 0.30224). Taken off the
# pocket's own rear face it is 1.200 on both, to six decimals.
TAB_REAR_GAP = 1.200
TAB_CHAMFER = 0.500        # the top all round, and the two REAR vertical edges

# The tabs' tops, above Z_BASE. Constant on all 48 — and now derived: the tab
# starts on the floor and is 44 mm blind.
TOTAL_HEIGHT = FLOOR + TAB_RISE                                       # 45.200

# `Room for Lips` — the notch each Holder rear lip needs in the topper's rear
# wall. Its X extent is not a number of the topper's own: it is the HOLDER's
# lip base, `holder.lip_plan`, with NO clearance at all — |x| 14.200..26.600
# from the slot centre on both parameter sets, against a lip base that measures
# 14.200..26.600. That is the same relationship `spec/HOLDER.md` records for
# `Lip Rest`, and it is why this binds to holder.lip_plan rather than to
# 20.400 +- 6.200.
#
# LIP_ROOM_RISE is 2.000 on both sets, which is `#LipHeight`. Two constants
# cannot tell a constant from a variable, so it is written here as its own
# number and NOT bound to holder.SLANT_STEP.
LIP_ROOM_RISE = 2.000      # the notch floor, above the topper's floor top

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


def slant_cos(p, d):
    """cos of the slant's angle to Y — how a distance ALONG the slant projects.

    `1/sqrt(1 + m^2)`. This is the factor that turns `Inner Hole Outline`'s
    0.800, which is measured in the slant plane, into the rear wall's Y
    thickness: 0.4442 at slope 1.4977 and 0.2418 at 3.1538, against 0.444 and
    0.242 measured.
    """
    m = slant_slope(p, d)
    return 1.0 / math.sqrt(1.0 + m * m)


def inner_hole(p, d):
    """`Remove Inner Hole` — the pocket, as the solid to subtract.

    Differencing `wedge()` against the `to Remove Inner Hole` rollback gives
    this exactly: ONE prism of SIX faces, swept along X, whose top is the
    wedge's own slant plane. So it needs no separate top — the cut simply runs
    out through the slant.

        floor   Z_BASE + FLOOR
        front   FRONT_WALL in from the front face
        rear    INNER_INSET along the slant from the rear edge
        ends    INNER_END_INSET in from each end
    """
    x0, x1 = x_span(p, d)
    front, rear = y_span(p, d)
    y_front = front - FRONT_WALL
    y_rear = rear + INNER_INSET * slant_cos(p, d)
    z_floor = Z_BASE + FLOOR
    with BuildPart() as part:
        with BuildSketch(Plane.YZ):
            with BuildLine():
                Polyline((y_front, z_floor), (y_front, slant_z(p, d, y_front)),
                         (y_rear, slant_z(p, d, y_rear)), (y_rear, z_floor),
                         close=True)
            make_face()
        extrude(amount=(x1 - x0) - 2 * INNER_END_INSET)
    return part.part.moved(Location((x0 + INNER_END_INSET, 0, 0)))


def slot_x(p, d):
    """Centre X of each SLOT — `calSlotwidth * k`, one per HorizontalSlots.

    The front-wall removal is centred on these, where the ribs and bands are
    centred on the BOUNDARIES between them.
    """
    return [d.calSlotwidth * k for k in range(p.HorizontalSlots)]


def _arc(bl, a, c, b):
    """A quarter arc from `a` to `b` about centre `c`, as a ThreePointArc.

    Given explicitly rather than with a signed RadiusArc: which side a radius
    arc takes is exactly the thing that would silently invert a fillet.
    """
    import math as _m
    ux, uz = (a[0] - c[0]) + (b[0] - c[0]), (a[1] - c[1]) + (b[1] - c[1])
    n = _m.hypot(ux, uz)
    r = _m.hypot(a[0] - c[0], a[1] - c[1])
    mid = (c[0] + r * ux / n, c[1] + r * uz / n)
    return ThreePointArc(a, mid, b)


def front_removal(p, d):
    """`Remove most of front` .. `Fillet front holes`, as the solid to subtract.

    The front wall is taken away above the floor's `FRONT_WALL_RISE`, over
    `calSlotwidth - 2*BAND_HALF` centred on each SLOT CENTRE — which is what
    leaves the 14.800 band at each boundary — and then `Fillet front holes`
    rounds all four corners of every opening at `FRONT_FILLET`.

    That fillet is built INTO THE TOOL rather than run on the body, because
    OCCT will not put a 2.000 round on an 0.800 wall and Onshape's "allow edge
    overflow" is precisely the permission to do it anyway. The reference says
    what the answer is: 16 quarter-cylinders of `r 2.000`, each spanning the
    wall's own 0.800, four per opening.

    The two kinds go opposite ways, which is the whole subtlety:

        BOTTOM corners  the opening's side meets its own floor, a notch in the
                        material, so the round ADDS material inside the opening
                        and the tool's corner is cut away
        TOP corners     the opening's side meets the WALL'S TOP FACE, so the
                        round REMOVES material and the tool grows FRONT_FILLET
                        into the band on each side

    They are equal and opposite: `(4 - pi) * FRONT_FILLET**2 * FRONT_WALL` is
    `0.6867` mm3 a corner, 8 of each, so the volume balances exactly and volume
    alone would pass a tool with neither. The symmetric difference is what
    catches it — `tests/test_topper.py` asserts both directions separately.
    """
    front, rear = y_span(p, d)
    z0 = Z_BASE + FLOOR + FRONT_WALL_RISE
    z1 = slant_z(p, d, front - FRONT_WALL)
    r = FRONT_FILLET
    hw = (d.calSlotwidth - 2 * BAND_HALF) / 2
    out = None
    for c in slot_x(p, d):
        xl, xr = c - hw, c + hw
        with BuildPart() as part:
            with BuildSketch(Plane.XZ) as sk:
                with BuildLine():
                    _arc(None, (xl + r, z0), (xl + r, z0 + r), (xl, z0 + r))
                    Line((xl, z0 + r), (xl, z1 - r))
                    _arc(None, (xl, z1 - r), (xl - r, z1 - r), (xl - r, z1))
                    # up and over the wall's top, so the tool's top face is not
                    # coincident with it; there is nothing above z1 at this Y.
                    Polyline((xl - r, z1), (xl - r, z1 + 1.0),
                             (xr + r, z1 + 1.0), (xr + r, z1))
                    _arc(None, (xr + r, z1), (xr + r, z1 - r), (xr, z1 - r))
                    Line((xr, z1 - r), (xr, z0 + r))
                    _arc(None, (xr, z0 + r), (xr - r, z0 + r), (xr - r, z0))
                    Line((xr - r, z0), (xl + r, z0))
                make_face()
            extrude(amount=FRONT_WALL)
        b = part.part.moved(Location((0, front, 0)))
        out = b if out is None else out + b
    return out


def holder_tabs(p, d):
    """`Tab-to-attach` — two plates that clip the topper onto the Holder.

    One at each end, `TAB_W` thick and `TAB_INSET` in, standing off the FLOOR
    and `TAB_RISE` tall. In Y they fill the pocket's own footprint less
    `TAB_REAR_GAP` at the rear. `TAB_CHAMFER` runs all round the top and down
    the two REAR vertical edges — the front edges are square, because the tab
    merges into the front wall there.
    """
    x0, x1 = x_span(p, d)
    front, rear = y_span(p, d)
    y_front = front - FRONT_WALL
    y_rear = rear + INNER_INSET * slant_cos(p, d) + TAB_REAR_GAP
    z0 = Z_BASE + FLOOR
    z1 = z0 + TAB_RISE
    out = None
    for xc in (x0 + TAB_INSET + TAB_W / 2, x1 - TAB_INSET - TAB_W / 2):
        b = (Pos(xc, (y_front + y_rear) / 2, (z0 + z1) / 2)
             * Box(TAB_W, y_front - y_rear, z1 - z0))
        es = [e for e in b.edges()
              if abs(e.center().Z - z1) < 1e-6
              or (abs(e.center().Y - y_rear) < 1e-6
                  and abs(e.length - (z1 - z0)) < 1e-6)]
        b = chamfer(es, TAB_CHAMFER)
        out = b if out is None else out + b
    return out


def lip_room_x(p, d):
    """(x0, x1) of every lip notch — the HOLDER's lip base, not a number here.

    Two per slot, mirrored about the slot centre, `HorizontalSlots` times over:
    that is `Remove Lip Room` + `Other side` + `Linear pattern 1`, and it gives
    the 8 notches and 16 `r 1.400` cylinders the M15-Sl rollback carries.
    """
    xs = [x for x, _y in H.lip_plan(p, d, first=False)]
    lo, hi = min(xs), max(xs)
    return sorted((c - hi, c - lo) if s < 0 else (c + lo, c + hi)
                  for c in slot_x(p, d) for s in (+1, -1))


def lip_rooms(p, d):
    """`Room for Lips` .. `Linear pattern 1`, as the solid to subtract.

    A notch through the rear wall, floor at `LIP_ROOM_RISE` above the topper's
    own floor and open upward through the slant, with `LIP_FILLET` on its two
    bottom corners. The tool runs a little past the wall both ways: behind it
    is outside the part and in front of it is the pocket, so the extra is air
    either way and no face of the cut is coincident with a face of the body.
    """
    front, rear = y_span(p, d)
    z0 = Z_BASE + FLOOR + LIP_ROOM_RISE
    z1 = Z_BASE + TOTAL_HEIGHT + 1.0
    r = LIP_FILLET
    depth_y = INNER_INSET * slant_cos(p, d) + 2.0
    out = None
    for xl, xr in lip_room_x(p, d):
        with BuildPart() as part:
            with BuildSketch(Plane.XZ):
                with BuildLine():
                    _arc(None, (xl + r, z0), (xl + r, z0 + r), (xl, z0 + r))
                    Polyline((xl, z0 + r), (xl, z1), (xr, z1), (xr, z0 + r))
                    _arc(None, (xr, z0 + r), (xr - r, z0 + r), (xr - r, z0))
                    Line((xr - r, z0), (xl + r, z0))
                make_face()
            extrude(amount=depth_y)
        b = part.part.moved(Location((0, rear - 1.0 + depth_y, 0)))
        out = b if out is None else out + b
    return out


def dividers(p, d):
    """`Divider` and `More Dividers` — the ribs, as the solid to ADD.

    Each is the inner hole's own profile, `RIB_W` wide, centred on a slot
    boundary: differencing the rollbacks gives three solids of six faces whose
    YZ section is identical to the pocket's, to four decimal places. So a rib
    is the pocket filled back in over 1.600, not a shape of its own.
    """
    out = None
    for c in post_x(p, d):
        strip = Pos(c, 0, 0) * Box(RIB_W, 1000, 1000)
        r = inner_hole(p, d) & strip
        out = r if out is None else out + r
    return out

def top_and_front_edges(p, d, part):
    """`Top and front edges` — the last feature of the blank, `r EDGE_ROUND`.

    Named for the SKETCH's orientation; `Upside Down` sits between, so the
    sketch's top and front are the assembly's BOTTOM and ends. The filleted
    `M10-Un` reference says exactly which edges, and there are only eight
    cylinders and no tori:

        the bottom face's whole perimeter   4, of `width - 2r` and `depth - 2r`
        the ends' FRONT vertical edges      2, `Z_BASE + r` up to the wall top
        the ends' REAR vertical edges       2, trimmed by the SLANT, which is
                                            why they reach `55.173` on M10-Un
                                            and not the rear's own `52.650`

    That last one is the tell that this is one fillet on a connected chain and
    not four separate ones: the rear edge stops where the slant begins, and the
    fillet surface runs past it until the slant face cuts it off — `slant_z` at
    `rear + r`, to three decimals on both parameter sets.

    It has to be built BEFORE the lettering (Allan): the logo and the name are
    offset from the edge of these fillets, so `Expansion Name` does not work
    without it.
    """
    x0, x1 = x_span(p, d)
    front, rear = y_span(p, d)
    es = []
    for e in part.edges():
        a, b = e.start_point(), e.end_point()
        if abs(a.Z - Z_BASE) < 1e-6 and abs(b.Z - Z_BASE) < 1e-6:
            es.append(e)
        elif (abs(a.X - b.X) < 1e-6 and abs(a.Y - b.Y) < 1e-6
              and min(abs(a.X - x0), abs(a.X - x1)) < 1e-6
              and min(abs(a.Y - front), abs(a.Y - rear)) < 1e-6):
            es.append(e)
    return fillet(es, EDGE_ROUND)


def build(p, d=None):
    """The blank Topper, in the Onshape tree's own order.

    INCOMPLETE: `Expansion Name` — the mark and the expansion's name — is not
    written, so this is the `Blank` of the six. `spec/TOPPER.md` records every
    rule the other five will need.
    """
    if p.GameName != "Innovation":
        raise ValueError(f"the Topper is Innovation-only, not {p.GameName!r}")
    if d is None:
        d = D.derive(p)
    part = wedge(p, d) - inner_hole(p, d)                 # Main topper
    part = part - front_removal(p, d)                     # Remove .. front
    part = part + dividers(p, d)                          # Divider, More
    part = part + holder_tabs(p, d)                       # Tab-to-attach
    part = part - lip_rooms(p, d)                         # Room for Lips ..
    return top_and_front_edges(p, d, part)                # Top and front edges

# ---------------------------------------------------------------------------
# `Expansion Name` — the mark and the expansion's name, engraved in the
# UNDERSIDE. Placement is solved; the five marks' own outlines are not written
# yet. See spec/TOPPER.md.

FONT = str(TX.FONT_DIR / "NotoSerif-Bold.ttf")   # Noto Serif Bold (Allan)

# The cap band as a fraction of the em. Measured 0.72025 / 0.72030 / 0.72016 /
# 0.72016 on four different words, agreeing to 1.5e-4, and NOT the face's own
# sCapHeight of 0.714 — which suggests Onshape constrains a nominal 0.72 em box
# rather than the cap height. That last part is an inference; 0.7202 is the
# measurement. See spec/TOPPER.md, "The typeface".
BAND_EM = 0.7202

ENGRAVE = 0.800            # how deep the mark and the name are cut
MARK_GAP = 1.000           # the mark box's left edge, past calLogoSidelength/2
TEXT_GAP = 3.000           # the sketch's `+3mm`, past calLogoSidelength*3/2


def logo_edge_dist(p, d):
    """`#LogoEdgeDist` — a PART-STUDIO variable, so it lives here and not in
    `derive.py`, which is the variable studio's transcription."""
    if p.CardsPerSlidingSlot > 10:
        return 1.2 if p.isSleeved else 0.8
    return 1.0 if p.isSleeved else 0.6


def face_datum(p, d):
    """Where every `Expansion Name` offset is measured from: the FLAT part of
    the underside, i.e. inside `Top and front edges`.

    Returns `(x, y_rear, y_front)`. This is the whole reason the fillet has to
    be built before the lettering (Allan) — an offset taken from the part's own
    edge instead is wrong by EDGE_ROUND, on every one of the six.
    """
    x0, _x1 = x_span(p, d)
    front, rear = y_span(p, d)
    return x0 + EDGE_ROUND, rear + EDGE_ROUND, front - EDGE_ROUND


def cap_band(p, d):
    """The band the lettering's CAP HEIGHT fills.

        depth - 2 * EDGE_ROUND - 3 * LogoEdgeDist

    The `2 * EDGE_ROUND` is the two `Top and front edges` fillets, NOT the two
    walls: the front wall is 0.800 but the rear one is 0.242 on M10-Un, so a
    rule written off the walls happens to be right on one term and would be
    wrong the moment either moved. `3 *` is the two margins, LogoEdgeDist at
    the top and twice that at the bottom.
    """
    return depth(p, d) - 2 * EDGE_ROUND - 3 * logo_edge_dist(p, d)


def font_size(p, d):
    """The em that puts `cap_band` at BAND_EM of it."""
    return cap_band(p, d) / BAND_EM


def baseline_y(p, d):
    """Y of the lettering's baseline: `LogoEdgeDist * 2` in from the flat
    face's FRONT edge. Exact on all three filleted references — -8.000,
    -10.400, -14.950 — against ink that overshoots it by a round letter's
    0.036, 0.055 and 0.090."""
    _x, _rear, y_front = face_datum(p, d)
    return y_front - 2 * logo_edge_dist(p, d)


def text_origin_x(p, d):
    """The PEN's start, `calLogoSidelength*3/2 + 3` past the flat face's end.

    Not the ink's start: what is left over is the first glyph's own left
    bearing, and it reads 0.01609 em and 0.01610 em for `U` on two parameter
    sets whose sizes differ by 54%. That agreement is what says the rule places
    the pen and the font does the rest.
    """
    x, _rear, _front = face_datum(p, d)
    return x + 1.5 * d.calLogoSidelength + TEXT_GAP


def mark_box(p, d):
    """(x0, y0, x1, y1) of the `calLogoSidelength` square the mark fills.

    Left edge at `calLogoSidelength/2 + MARK_GAP` past the flat face's end —
    which puts its RIGHT edge at `calLogoSidelength*3/2 + 1`, exactly 2.000
    before the pen. Centred in the depth: the two fillets cancel, so the box's
    centre is the face's own centre and not something that moves with
    EDGE_ROUND.

    Predicted box tops -11.1125 / -14.8625 / -21.89375 against measured
    -11.112 / -14.862 / -21.894, for calLogoSidelength 4.225 / 5.725 / 8.5375.
    Cities fills the square exactly; Unseen's shield fills its width and its
    top edge, and its rays hang below.
    """
    x, _rear, _front = face_datum(p, d)
    front, rear = y_span(p, d)
    L = d.calLogoSidelength
    x0 = x + L / 2 + MARK_GAP
    cy = (front + rear) / 2
    return x0, cy - L / 2, x0 + L, cy + L / 2


def engrave(p, d, sketch):
    """Cut a sketch that is drawn in the READING frame into the underside.

    The face is read from BELOW, so the drawing's +y is the part's -Y: the
    sketch is mirrored about the X axis before it is sunk. Getting that
    backwards leaves a part whose name is legible only in a mirror, which is
    the same trap the TokenHolder's underside engraving sat in.
    """
    tool = extrude(mirror(sketch, about=Plane.XZ), amount=ENGRAVE)
    return Pos(0, 0, Z_BASE) * tool


def name_sketch(p, d, word):
    """The expansion's name, as a sketch in the reading frame with the pen's
    origin at (0, 0) — so the caller places it by `text_origin_x` and
    `baseline_y` and nothing here has to know where the part is."""
    size = font_size(p, d)
    _adv, lsb, lo, _hi = TX.metrics(word, FONT)
    with BuildSketch() as sk:
        Text(word, font_size=size, font_path=FONT, align=(Align.MIN, Align.MIN))
    return sk.sketch.moved(Location((lsb * size, lo * size, 0)))
