"""The Topper.

The cap that closes the top of a card slot. **Innovation only.** Six per
parameter set — one per expansion plus a `Blank` — one shape with different
lettering. Measured in `spec/TOPPER.md`.

Local frame — the part studio's, which is also the assembly's:

    X   0 at the CENTRE OF THE FIRST SLOT, exactly as the Holder's is, so the
        part runs -calSlotwidth/2 .. calSlotwidth*(HorizontalSlots - 0.5)
    Y   NEGATIVE throughout: the front face at -depth and the rear at -2*depth,
        so the topper sits one full depth back from the origin
    Z   the base at Z_BASE, a measured constant, and the tabs' tops
        45.200 above it

It does NOT import the Holder: every feature Onshape derives from
`Import Holder` is a named function here, and `TriangleMatch` binds to
`holder.slant_slope` rather than to a body. What that costs is the mate
Onshape got for free, so `tests/test_topper.py` asserts the tabs against
`holder` independently."""
import math

from build123d import (
    Align, Box, BuildLine, BuildPart, BuildSketch, Circle, Line, Location,
    Mode, Plane, Polyline, Pos, Text, ThreePointArc, chamfer, extrude, fillet,
    make_face,
)

from .. import derive as D
from .. import tables as TB
from .. import text as TX
from . import holder as H

# Where the base sits in assembly. There is no mate: the topper RESTS on the
# holder, logo up, diagonal meeting diagonal, its fins in the holder's lip
# rooms, so its base is `z_base` below. This constant is the catalogue's
# value, and `tests/test_topper.py` holds the two to each other.
Z_BASE = 48.450


def z_base(d):
    """Where the topper's base sits: the holder's slant top plus the topper's
    own rear thickness."""
    return H.slant_top(d) + topper_height(d)

FRONT_WALL = 0.800         # the front wall, and the flat left along the top
FLOOR = 1.200              # floor thickness
FRONT_WALL_RISE = 1.400    # how far the front wall stands above the floor's top

# At each slot boundary the part carries a RIB the full depth, and a wider
# BAND of front wall around it — a T in plan, NOT a solid post; a plan section
# alone reads as one block (spec/TOPPER.md, "Ribs and front bands").
RIB_W = D.WallThickness             # 1.600, the rib through the depth
# BAND_HALF is DERIVED below, and the sketch states it two ways that must
# agree — see the assert. Neither is `#FootDistanceFromWall`.
FRONT_MARGIN = 6.000

# `Inner Hole Outline` is sketched IN THE SLANT PLANE, so INNER_INSET is
# measured ALONG the slant and NOT in Y: a plain Y-offset would be wrong by
# the slope, and wrong differently on every row (`slant_cos`).
INNER_INSET = 0.800        # from the slant's rear edge, ALONG the slant
INNER_END_INSET = 1.400    # from each end of the part, in X
BAND_HALF = FRONT_MARGIN + INNER_END_INSET   # 7.400: the front band is 14.800
assert abs(BAND_HALF - (FRONT_MARGIN + 0.6 + RIB_W / 2)) < 1e-9, \
    "the sketch's two readings of the band, 6 + 1.4 and 6.6 + 0.8, disagree"

TAB_W = D.WallThickness    # 1.600
TAB_INSET = 1.300          # from each end of the part
TAB_RISE = 44.000          # "extruded to 44 mm blind", off the FLOOR
# How far the tab stops short of the pocket's rear wall. Taken off the
# POCKET's own rear face, not the part's rear FACE, where it is not constant.
TAB_REAR_GAP = 1.200
TAB_CHAMFER = 0.500        # the top all round, and the two REAR vertical edges

# The tabs' tops, above Z_BASE: the tab starts on the floor and is 44 blind.
TOTAL_HEIGHT = FLOOR + TAB_RISE                                       # 45.200

# `Room for Lips` — the notch each Holder rear lip needs in the topper's rear
# wall. Its X extent is NOT a number of the topper's own: it is
# `holder.lip_plan`, with no clearance at all, and the notch floor is likewise
# bound to `holder.SLANT_STEP` (spec/TOPPER.md, "The lip notches are the
# HOLDER's lip base").
LIP_ROOM_RISE = H.SLANT_STEP   # the notch floor, above the topper's floor top

LIP_FILLET = 1.400         # `Fillet Lip Room`
FRONT_FILLET = 2.000       # `Fillet front holes`
EDGE_ROUND = 0.800         # `Top and front edges`


def width(d):
    """`calSlotwidth * HorizontalSlots` — the Holder less its two end blocks."""
    return d.calSlotwidth * d.HorizontalSlots


def depth(d):
    """The Holder's own depth."""
    return H.holder_depth(d, first=False)


def topper_height(d):
    """`#TopperHeight`, the REAR thickness — constant on every Innovation row,
    but the expression is real."""
    return (d.BoxHeight - D.WallThickness * 2 - D.PusherFootThickness
            - d.calPocketHeight - 4.0 - 3.5)


def x_span(d):
    """(x0, x1). X = 0 is the centre of the FIRST slot, as the Holder's."""
    x0 = -d.calSlotwidth / 2
    return x0, x0 + width(d)


def y_span(d):
    """(front, rear), both negative — the topper sits one depth back."""
    dp = depth(d)
    return -dp, -2 * dp


def slant_slope(d):
    """The Holder's `Top slant angle`, and not a second transcription of it.
    This IS `TriangleMatch`."""
    return H.slant_slope(d, first=False)


def slant_z(d, y):
    """Z of the slant plane at a given Y, anchored at the REAR, where the
    section is `#TopperHeight` thick — the one place the slant's height is
    stated rather than inferred."""
    _, rear = y_span(d)
    return Z_BASE + topper_height(d) + slant_slope(d) * (y - rear)


def post_x(d):
    """Centre X of each full post — the slot boundaries. The two ends carry
    HALF a post each, `Remove Inner Hole` stopping INNER_END_INSET short."""
    return [d.calSlotwidth * (k + 0.5) for k in range(d.HorizontalSlots - 1)]


def band_x(d):
    """(x0, x1) of each front-wall band, and the half-bands at the ends. A
    band is centred on a slot boundary and the part stops half a slot out."""
    x0, x1 = x_span(d)
    out = [(x0, x0 + BAND_HALF)]
    out += [(c - BAND_HALF, c + BAND_HALF) for c in post_x(d)]
    out.append((x1 - BAND_HALF, x1))
    return out


def rib_x(d):
    """(x0, x1) of each rib — RIB_W wide, centred on a slot boundary."""
    return [(c - RIB_W / 2, c + RIB_W / 2) for c in post_x(d)]


def wedge_profile(d):
    """The section `TriangleMatch` + `CardHeight` make, as (Y, Z) points:
    base, front face, the FRONT_WALL flat on top, the slant, and the rear at
    `#TopperHeight` (spec/TOPPER.md, "The section")."""
    front, rear = y_span(d)
    # The front is the LESS negative edge, so going into the part subtracts.
    z_front = slant_z(d, front - FRONT_WALL)
    z_rear = Z_BASE + topper_height(d)
    return [(rear, Z_BASE), (front, Z_BASE), (front, z_front),
            (front - FRONT_WALL, z_front), (rear, z_rear)]


def wedge(d):
    """The base solid: the profile swept the full width."""
    x0, x1 = x_span(d)
    with BuildPart() as part:
        with BuildSketch(Plane.YZ):
            with BuildLine():
                pts = wedge_profile(d)
                Polyline(*pts, close=True)
            make_face()
        extrude(amount=x1 - x0)
    return part.part.moved(Location((x0, 0, 0)))


def slant_cos(d):
    """cos of the slant's angle to Y: what turns a distance ALONG the slant
    into a Y thickness."""
    m = slant_slope(d)
    return 1.0 / math.sqrt(1.0 + m * m)


def inner_hole(d):
    """`Remove Inner Hole` — the pocket, as the solid to subtract: ONE prism
    of six faces swept along X, whose top IS the wedge's own slant plane, so
    the cut runs out through the slant rather than needing a top. Its
    floor is `Z_BASE + FLOOR`, its front FRONT_WALL in, its rear INNER_INSET
    along the slant, and its ends INNER_END_INSET in."""
    x0, x1 = x_span(d)
    front, rear = y_span(d)
    y_front = front - FRONT_WALL
    y_rear = rear + INNER_INSET * slant_cos(d)
    z_floor = Z_BASE + FLOOR
    with BuildPart() as part:
        with BuildSketch(Plane.YZ):
            with BuildLine():
                Polyline((y_front, z_floor), (y_front, slant_z(d, y_front)),
                         (y_rear, slant_z(d, y_rear)), (y_rear, z_floor),
                         close=True)
            make_face()
        extrude(amount=(x1 - x0) - 2 * INNER_END_INSET)
    return part.part.moved(Location((x0 + INNER_END_INSET, 0, 0)))


def _arc(start, centre, end):
    """A quarter arc from `start` to `end` about `centre`, as a ThreePointArc
    through the arc's midpoint — explicit rather than a signed RadiusArc,
    whose choice of side would silently invert a fillet."""
    ux, uz = ((start[0] - centre[0]) + (end[0] - centre[0]),
              (start[1] - centre[1]) + (end[1] - centre[1]))
    n = math.hypot(ux, uz)
    r = math.hypot(start[0] - centre[0], start[1] - centre[1])
    mid = (centre[0] + r * ux / n, centre[1] + r * uz / n)
    return ThreePointArc(start, mid, end)


def front_removal(d):
    """`Remove most of front` .. `Fillet front holes`, as the solid to
    subtract: the front wall taken away above `FRONT_WALL_RISE` over
    `calSlotwidth - 2*BAND_HALF` centred on each SLOT CENTRE, all four corners
    of every opening rounded at `FRONT_FILLET`.

    That fillet is built INTO THE TOOL, because OCCT will not put a 2.000
    round on an 0.800 wall. The two kinds go OPPOSITE ways: at a BOTTOM corner
    the round ADDS material inside the opening, so the tool's corner is cut
    away; at a TOP corner it REMOVES material, so the tool grows into the
    band. Equal and opposite, so only the symmetric difference catches a tool
    with neither.
    """
    front, _rear = y_span(d)
    z0 = Z_BASE + FLOOR + FRONT_WALL_RISE
    z1 = slant_z(d, front - FRONT_WALL)
    r = FRONT_FILLET
    hw = (d.calSlotwidth - 2 * BAND_HALF) / 2
    out = None
    # Centred on the SLOT centres (the holder's compartments), where the ribs
    # and bands are centred on the BOUNDARIES between them.
    for c in H.compartment_x(d):
        xl, xr = c - hw, c + hw
        with BuildPart() as part:
            with BuildSketch(Plane.XZ):
                with BuildLine():
                    _arc((xl + r, z0), (xl + r, z0 + r), (xl, z0 + r))
                    Line((xl, z0 + r), (xl, z1 - r))
                    _arc((xl, z1 - r), (xl - r, z1 - r), (xl - r, z1))
                    # up and over the wall's top, so the tool's top face is not
                    # coincident with it; there is nothing above z1 at this Y.
                    Polyline((xl - r, z1), (xl - r, z1 + 1.0),
                             (xr + r, z1 + 1.0), (xr + r, z1))
                    _arc((xr + r, z1), (xr + r, z1 - r), (xr, z1 - r))
                    Line((xr, z1 - r), (xr, z0 + r))
                    _arc((xr, z0 + r), (xr - r, z0 + r), (xr - r, z0))
                    Line((xr - r, z0), (xl + r, z0))
                make_face()
            extrude(amount=FRONT_WALL)
        b = part.part.moved(Location((0, front, 0)))
        out = b if out is None else out + b
    return out


def holder_tabs(d):
    """`Tab-to-attach` — two plates that clip the topper onto the Holder, one
    at each end, filling the pocket's footprint less `TAB_REAR_GAP`.
    `TAB_CHAMFER` runs round the top and down the two REAR vertical edges
    only; the front edges are square, where the tab merges into the wall."""
    x0, x1 = x_span(d)
    front, rear = y_span(d)
    y_front = front - FRONT_WALL
    y_rear = rear + INNER_INSET * slant_cos(d) + TAB_REAR_GAP
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


def lip_room_x(d):
    """(x0, x1) of every lip notch — the HOLDER's lip base, not a number here.
    Two per slot, mirrored about the slot centre."""
    xs = [x for x, _y in H.lip_plan(d, first=False)]
    lo, hi = min(xs), max(xs)
    return sorted((c - hi, c - lo) if s < 0 else (c + lo, c + hi)
                  for c in H.compartment_x(d) for s in (+1, -1))


def lip_rooms(d):
    """`Room for Lips` .. `Linear pattern 1`, as the solid to subtract.

    A notch through the rear wall, floor at `LIP_ROOM_RISE` above the
    topper's own and open upward through the slant, with `LIP_FILLET` on its
    two bottom corners. The tool runs past the wall both ways — air either
    way — so no face of the cut is coincident with the body's.
    """
    _front, rear = y_span(d)
    z0 = Z_BASE + FLOOR + LIP_ROOM_RISE
    z1 = Z_BASE + TOTAL_HEIGHT + 1.0
    r = LIP_FILLET
    depth_y = INNER_INSET * slant_cos(d) + 2.0
    out = None
    for xl, xr in lip_room_x(d):
        with BuildPart() as part:
            with BuildSketch(Plane.XZ):
                with BuildLine():
                    _arc((xl + r, z0), (xl + r, z0 + r), (xl, z0 + r))
                    Polyline((xl, z0 + r), (xl, z1), (xr, z1), (xr, z0 + r))
                    _arc((xr, z0 + r), (xr - r, z0 + r), (xr - r, z0))
                    Line((xr - r, z0), (xl + r, z0))
                make_face()
            extrude(amount=depth_y)
        b = part.part.moved(Location((0, rear - 1.0 + depth_y, 0)))
        out = b if out is None else out + b
    return out


def dividers(d):
    """`Divider` and `More Dividers` — the ribs, as the solid to ADD. Each is
    the inner hole's OWN profile, `RIB_W` wide, centred on a slot boundary: a
    rib is the pocket filled back in, not a shape of its own."""
    out = None
    hole = inner_hole(d)                 # the same prism under every rib
    for c in post_x(d):
        strip = Pos(c, 0, 0) * Box(RIB_W, 1000, 1000)
        r = hole & strip
        out = r if out is None else out + r
    return out

def top_and_front_edges(d, part):
    """`Top and front edges` — the last feature of the blank, `r EDGE_ROUND`.

    Named for the SKETCH's orientation; `Upside Down` sits between, so the
    sketch's top and front are the assembly's BOTTOM and ends. The edges are
    the bottom face's whole perimeter and the ends' four vertical edges — ONE
    fillet on a connected chain, which is why the rear ones run past where the
    slant trims them. Built BEFORE the lettering, which is offset from these
    fillets' edge.
    """
    x0, x1 = x_span(d)
    front, rear = y_span(d)

    def on_side(pt):
        return (min(abs(pt.X - x0), abs(pt.X - x1)) < 1e-6
                or min(abs(pt.Y - front), abs(pt.Y - rear)) < 1e-6)

    es = []
    for e in part.edges():
        a, b = e.start_point(), e.end_point()
        # The bottom PERIMETER, not "everything in the bottom plane": the
        # glyph outlines lie in this plane too, so the loose form is one
        # reordering away from rounding the lettering.
        if (abs(a.Z - Z_BASE) < 1e-6 and abs(b.Z - Z_BASE) < 1e-6
                and on_side(a) and on_side(b)):
            es.append(e)
        elif (abs(a.X - b.X) < 1e-6 and abs(a.Y - b.Y) < 1e-6
              and min(abs(a.X - x0), abs(a.X - x1)) < 1e-6
              and min(abs(a.Y - front), abs(a.Y - rear)) < 1e-6):
            es.append(e)
    return fillet(es, EDGE_ROUND)


# --- the marks ------------------------------------------------------------
# Each is drawn in the READING frame — x right, y up, origin at the centre of
# `mark_box` — and sized entirely by `calLogoSidelength`. Nothing here is a
# traced outline: every number below is a fraction of L (spec/TOPPER.md, "All
# five marks are SOLVED").


def _unseen_mark(L):
    """A shield, and five rays on an arc below it. The shield is TWO arcs: a
    semicircle of radius L/2 about C = (0, 5L/14), and an arc across the same
    chord peaking at (0, L/2). The rays are L/5 by L/10 rectangles at 0 and
    +-25 and +-50 degrees, pivoting about **C itself**, not the box
    centre."""
    c = 5 * L / 14
    r = L / 2
    with BuildSketch() as sk:
        with BuildLine():
            _arc((-r, c), (0.0, c), (0.0, c - r))
            _arc((0.0, c - r), (0.0, c), (r, c))
            # the upper arc, by its three points: the two shoulders and the apex
            ThreePointArc((r, c), (0.0, r), (-r, c))
        make_face()
    out = sk.sketch
    # from C: the semicircle's own rim, L/12 of clearance, then half the ray
    r_mid = r + L / 12 + L / 10
    for phi in (-50.0, -25.0, 0.0, 25.0, 50.0):
        a = math.radians(phi)
        # `long` points outward along the ray, `wide` across it
        lx, ly = math.sin(a), -math.cos(a)
        wx, wy = math.cos(a), math.sin(a)
        mx, my = lx * r_mid, c + ly * r_mid
        hl, hw = L / 5 / 2, L / 10 / 2
        pts = [(mx + sx * hl * lx + sy * hw * wx, my + sx * hl * ly + sy * hw * wy)
               for sx, sy in ((-1, -1), (-1, +1), (+1, +1), (+1, -1))]
        with BuildSketch() as ray:
            with BuildLine():
                Polyline(*pts, close=True)
            make_face()
        out = out + ray.sketch
    return out


def _cities_mark(L):
    """An eight-pointed star: EIGHT triangles through the centre, not a traced
    outline — four on the axes (apex L/2 out, base L/5) and four on the
    diagonals (apex (L/4, L/4), base L/8). The star's 16 vertices are where
    adjacent triangles' edges cross; nothing places them directly."""
    out = None
    for k in range(8):
        a = math.radians(45.0 * k)
        dx, dy = math.cos(a), math.sin(a)
        if k % 2 == 0:
            apex, half = L / 2, L / 10
        else:
            apex, half = L / (2 * math.sqrt(2.0)), L / 16
        with BuildSketch() as tri:
            with BuildLine():
                Polyline((apex * dx, apex * dy),
                         (-half * dy, half * dx),
                         (half * dy, -half * dx), close=True)
            make_face()
        out = tri.sketch if out is None else out + tri.sketch
    return out


def _echoes_mark(L):
    """A diamond: a square turned 45 degrees, its four vertices on the box's
    edge midpoints."""
    r = L / 2
    with BuildSketch() as sk:
        with BuildLine():
            Polyline((0.0, r), (-r, 0.0), (0.0, -r), (r, 0.0), close=True)
        make_face()
    return sk.sketch


def _artifacts_mark(L):
    """Two tall triangles that OVERLAP, and the overlap is the whole point:
    each has its base on the box's bottom edge and its apex `L/4` in from a
    top corner, the bases crossing the centre line by `L/8`. Their union has
    FIVE edges, not six."""
    r = L / 2
    out = None
    for sgn in (-1.0, +1.0):
        with BuildSketch() as tri:
            with BuildLine():
                Polyline((sgn * r, -r), (-sgn * L / 8, -r),
                         (sgn * L / 4, r), close=True)
            make_face()
        out = tri.sketch if out is None else out + tri.sketch
    return out


def _figures_mark(L):
    """An ANNULUS — the ring alone, not a disc with a ring round it: the mark
    is ONE solid with TWO wires. Outer radius `L/2`, inner `L/2 - L/5`."""
    with BuildSketch() as sk:
        Circle(L / 2)
        Circle(L / 2 - L / 5, mode=Mode.SUBTRACT)
    return sk.sketch


MARKS = {"Artifacts": _artifacts_mark, "Cities": _cities_mark,
         "Echoes": _echoes_mark, "Figures": _figures_mark,
         "Unseen": _unseen_mark}
assert tuple(sorted(MARKS)) == TB.TOPPER_EXPANSIONS, \
    "cad/tables.TOPPER_EXPANSIONS is the catalogue's copy of MARKS' keys"


# ---------------------------------------------------------------------------
# `Expansion Name` — the mark and the expansion's name, engraved in the
# UNDERSIDE. The placement and all five marks; see spec/TOPPER.md.

FONT = str(TX.FONT_DIR / "NotoSerif-Bold.ttf")

# The cap band as a fraction of the em — NOT the face's own sCapHeight of
# 0.714 (spec/TOPPER.md, "The typeface").
BAND_EM = 0.7202

# How deep the mark and the name are cut: 0.810, NOT the 0.800 the wall and
# the fillet make it tempting to assume. The inlays are 0.810 tall too but sit
# INLAY_PROUD lower, leaving that much clear at the pocket's top — the same
# trick the Lid's logo inlays use.
ENGRAVE = 0.810
ENGRAVE_OVERSHOOT = 0.500   # below the face, so the cut has no coincident face
INLAY_PROUD = 0.010         # the inlays stand this far below the underside
MARK_GAP = 1.000           # the mark box's left edge, past calLogoSidelength/2
TEXT_GAP = 3.000           # the sketch's `+3mm`, past calLogoSidelength*3/2


def logo_edge_dist(d):
    """`#LogoEdgeDist` — a PART-STUDIO variable, so it lives here and not in
    `derive.py`, which transcribes the variable studio."""
    if d.CardsPerSlidingSlot > 10:
        return 1.2 if d.isSleeved else 0.8
    return 1.0 if d.isSleeved else 0.6


def face_datum(d):
    """Where every `Expansion Name` offset is measured from: `(x, y_rear,
    y_front)` of the FLAT part of the underside, inside `Top and front edges`.
    This is why the fillet is built first — an offset taken from the part's
    own edge instead is wrong by EDGE_ROUND."""
    x0, _x1 = x_span(d)
    front, rear = y_span(d)
    return x0 + EDGE_ROUND, rear + EDGE_ROUND, front - EDGE_ROUND


def cap_band(d):
    """The band the lettering's CAP HEIGHT fills: `depth - 2 * EDGE_ROUND -
    3 * LogoEdgeDist`. The `2 * EDGE_ROUND` is the two `Top and front edges`
    fillets, NOT the two walls — a rule written off the walls is right on one
    term by coincidence. `3 *` is the two margins, LogoEdgeDist at the top and
    twice at the bottom."""
    return depth(d) - 2 * EDGE_ROUND - 3 * logo_edge_dist(d)


# The deepest descender any expansion name has: `Figures`' `g`, and Onshape's
# `g`, which reaches 0.00459 em deeper than the vendored font's
# (spec/TOPPER.md, "The vendored Noto Serif Bold").
DESCENDER_EM = -(TX.metrics("Figures", FONT)[2] - 0.00459)


def font_size(d):
    """The em that puts `cap_band` at BAND_EM of it — or the CUT floor
    (`cad/text.py`, "floors") where that is larger. CUT, not proud, although
    the sketch stands the inlay INLAY_PROUD proud: the topper prints face down
    and the lettering is a second-filament fill in a pocket. Only the two
    10-card unsleeved rows fall under the floor; `baseline_y` then shares what
    the flat has left in the sketch's 1:2 margins, and a floor the flat could
    not hold raises `DoesNotFit` rather than putting the `g` into the
    round."""
    fitted = cap_band(d) / BAND_EM
    floor = TX.floor_size(FONT)
    if fitted >= floor:
        return fitted
    _x, rear, front = face_datum(d)
    flat = front - rear
    # The largest em whose band AND deepest descender fit with the 1:2 split:
    #   2/3 (flat - BAND_EM s) >= DESCENDER_EM s
    holds = 2 * flat / (3 * DESCENDER_EM + 2 * BAND_EM)
    if holds < floor:
        raise TX.DoesNotFit(f"topper lettering at its floor ({floor:.3f} em) "
                            f"does not fit the {flat:.2f} flat with `Figures`' "
                            f"g; it holds {holds:.3f}")
    return floor


def baseline_y(d):
    """Y of the lettering's baseline: `LogoEdgeDist * 2` in from the flat
    face's FRONT edge."""
    _x, y_rear, y_front = face_datum(d)
    # `2 * LogoEdgeDist` is two thirds of what the flat has left once the cap
    # band is out of it, and it is written that way so a band raised to its
    # floor (`font_size`) keeps the sketch's 1:2 split of the margins instead
    # of walking off the rear round.
    left = (y_front - y_rear) - font_size(d) * BAND_EM
    return y_front - 2 * left / 3


def text_origin_x(d):
    """The PEN's start, past the flat face's end — NOT the ink's start, which
    is one left bearing later."""
    x, _rear, _front = face_datum(d)
    return x + 1.5 * d.calLogoSidelength + TEXT_GAP


def mark_box(d):
    """(x0, y0, x1, y1) of the `calLogoSidelength` square the mark fills, its
    left edge `calLogoSidelength/2 + MARK_GAP` past the flat face's end.
    Centred in the depth: the two fillets cancel, so the box's centre is the
    face's own and does not move with EDGE_ROUND."""
    x, _rear, _front = face_datum(d)
    front, rear = y_span(d)
    L = d.calLogoSidelength
    x0 = x + L / 2 + MARK_GAP
    cy = (front + rear) / 2
    return x0, cy - L / 2, x0 + L, cy + L / 2


def name_sketch(d, word):
    """The expansion's name, as a sketch in the reading frame with the pen's
    origin at (0, 0), so nothing here has to know where the part is."""
    size = font_size(d)
    _adv, lsb, lo, _hi = TX.metrics(word, FONT)
    with BuildSketch() as sk:
        Text(word, font_size=size, font_path=FONT, align=(Align.MIN, Align.MIN))
    return sk.sketch.moved(Location((lsb * size, lo * size, 0)))


def name_and_mark(d, expansion):
    """`Expansion Name`'s sketch, in the reading frame — what the cut and the
    inlays are both extruded from."""
    def place(sketch, x, y):
        """Reading frame at the origin -> the underside, at (x, y)."""
        return Pos(x, y, 0) * sketch.mirror(Plane.XZ)

    mx0, my0, mx1, my1 = mark_box(d)
    sk = place(name_sketch(d, expansion),
               text_origin_x(d), baseline_y(d))
    mark = MARKS.get(expansion)
    if mark is not None:
        sk = sk + place(mark(d.calLogoSidelength),
                        (mx0 + mx1) / 2, (my0 + my1) / 2)
    return sk


def expansion_name(d, expansion):
    """`Expansion Name` — the mark and the word, as the solid to subtract."""
    # Dropped OVERSHOOT below the underside so no face of the tool is
    # coincident with the face it cuts. Without it OCCT quietly leaves part of
    # the cut behind, warning only "Boolean operation unable to clean".
    return Pos(0, 0, Z_BASE - ENGRAVE_OVERSHOOT) * extrude(
        name_and_mark(d, expansion), amount=ENGRAVE + ENGRAVE_OVERSHOOT)


def inlays(d, expansion):
    """The lettering as the SECOND-FILAMENT solids a print needs, ENGRAVE tall
    and standing INLAY_PROUD below the underside. A topper written without
    them prints its name as an empty pocket."""
    if expansion == "Blank":
        return []
    solid = Pos(0, 0, Z_BASE - INLAY_PROUD) * extrude(name_and_mark(d, expansion),
                                                    amount=ENGRAVE)
    return sorted(solid.solids(), key=lambda q: (q.bounding_box().min.X, q.bounding_box().min.Y))


EXPANSIONS = TB.TOPPERS


def build(d, expansion="Blank"):
    """One Topper, in the Onshape tree's own order. `Blank` carries no name
    or logo; the other five are the same body with `Expansion Name` engraved.
    An expansion `MARKS` does not know RAISES rather than writing a topper
    with a name and no mark."""
    if d.GameName != "Innovation":
        raise ValueError(f"the Topper is Innovation-only, not {d.GameName!r}")
    if expansion not in EXPANSIONS:
        raise ValueError(f"no such Innovation expansion: {expansion!r}")
    part = wedge(d) - inner_hole(d)                 # Main topper
    part = part - front_removal(d)                     # Remove .. front
    part = part + dividers(d)                          # Divider, More
    part = part + holder_tabs(d)                       # Tab-to-attach
    part = part - lip_rooms(d)                         # Room for Lips ..
    part = top_and_front_edges(d, part)                # Top and front edges
    if expansion == "Blank":
        return part
    return part - expansion_name(d, expansion)         # Expansion Name


def build_all(d, expansion="Blank"):
    """(the Topper BODY, its lettering inlays) — what a topper file carries."""
    return build(d, expansion), inlays(d, expansion)


# NB `Solid.volume` is NOT the metric to check a NAMED topper with: OCCT's
# GProp over-reports a body carrying this many small BSpline faces, and the
# hand-exported STEP has the same kind of error in it. Use the tessellated
# volume or the engraving differenced back out, as `tests/test_topper.py`
# does. `spec/TOPPER.md`, "`Solid.volume` is the wrong metric".
