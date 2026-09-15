"""Marks that are GENERATED rather than imported.

`cad/art.py` loads a drawing someone else made. This BUILDS one, from the font
it was set in and the geometry drawn around it — the only way a mark keeps its
**stroke weight** when the Lid's fit sizes it. `#LineWidth` is absolute in
Onshape's sketch and it is absolute here.

Two marks, both Innovation: the plain one and Ultimate. Every number is read
off Allan's own drawings and his `Logo Flourishes` sketch, each fit recorded
in `spec/LID.md`. Ultimate is registered TWICE in `GENERATED`, at the two
sizes the sketch shipped at, so the lid's ladder keeps the big mark where a
lid carried it.
"""
import math
from functools import lru_cache
from pathlib import Path

from build123d import (Align, Axis, Box, Compound, Cylinder, Location, Mode,
                       Plane, Text)

from . import art

FONT_DIR = Path(__file__).resolve().parent.parent / "fonts"
NOTO_SERIF = str(FONT_DIR / "NotoSerif-Regular.ttf")

# `#LineWidth`, ABSOLUTE at every size — the one number here that does not
# scale.
LINE_WIDTH = 0.600

# Each star arm's offset off the centre, a slight pinwheel. ABSOLUTE, like the
# line width: Allan's `5x at 270` pattern seed misses its own centre by this.
TWIST = 0.1041

# The font size the SMALL Innovation drawing is set at. The big drawing is
# 33.3466 = this x 1.59999, which is `#LogoScaleFactor`.
NOMINAL_SIZE = 20.8416

# Everything below is in font units per 1000 em, so it scales with the size.
SERIF_MID = 693.0            # middle of the I's top serif slab (672..714)
ARM = 119.952                # star arm, centre to tip
# The first arm of the run, in the READING frame the mark is built in BEFORE
# it is mirrored into the lid; the mirror maps each arm to 180 - x.
ARM0 = -46.1442
ARM_STEP = 67.5              # 5 arms at 270 degrees


def _units(size):
    return size / 1000.0                    # mm per font unit


@lru_cache(maxsize=8)
def innovation_plain(size):
    """The plain Innovation mark at `size`, in the lid's frame: faces on the
    origin (its box in X, its WORD in Y — `_centre`) and MIRRORED in X, the
    pattern being cut into the far side of the lid's floor. Which way up it
    reads on a PRINTED lid is `tables.LID_LOGO_TURNED`'s question."""
    faces, base, letter_I = _wordmark(size)
    shape = _centre(faces, word=(base, letter_I.bounding_box().max.Y))
    return tuple(f.mirror(Plane.YZ) for f in shape)


def _wordmark(size):
    """`Innovation` at `size` with the ring fused into its `I` and the star
    into its `i`'s tittle: (faces, baseline, the `I`)."""
    u = _units(size)
    word = Text("Innovation", font_size=size, font_path=NOTO_SERIF,
                align=(Align.CENTER, Align.MIN))
    faces = list(word.faces())
    # The tittle is the one face clear of the x-height. Aligned MIN in Y, so
    # the baseline is the o's and a's 10-unit overshoot above the bottom.
    base = word.bounding_box().min.Y + 10 * u
    tittle = max(faces, key=lambda f: f.bounding_box().min.Y)
    letter_I = min(faces, key=lambda f: f.bounding_box().min.X)

    ring = _ring(letter_I, base, u)
    star = _star(tittle, u)

    out = []
    for f in faces:
        if f is letter_I:
            f = f.fuse(ring).clean().faces()[0]
        elif f is tittle:
            f = f.fuse(*star).clean().faces()[0]
        out.append(f)
    return out, base, letter_I


def _flat(solid):
    f = solid.faces().sort_by(lambda f: f.center().Z)[-1]   # -> a face at Z 0
    return f.moved(Location((0, 0, -f.center().Z)))


def _ring(letter_I, base, u):
    bb = letter_I.bounding_box()
    r = (bb.max.X - bb.min.X) / 2
    at = Location(((bb.min.X + bb.max.X) / 2, base + SERIF_MID * u, 0))
    return (_disc(r + LINE_WIDTH, (0, 0)) - _disc(r, (0, 0))).moved(at)


def _star(tittle, u):
    bb = tittle.bounding_box()
    cx, cy = (bb.min.X + bb.max.X) / 2, (bb.min.Y + bb.max.Y) / 2
    L, d = ARM * u, TWIST
    arms = []
    for k in range(5):
        th = math.radians(ARM0 + k * ARM_STEP)
        c, s = math.cos(th), math.sin(th)
        # the arm's own centre: L/2 along the bearing, d off it
        mx, my = cx + L / 2 * c - d * s, cy + L / 2 * s + d * c
        bar = _flat(Box(L, LINE_WIDTH, 1, mode=Mode.PRIVATE))
        arms.append(bar.rotate(Axis.Z, ARM0 + k * ARM_STEP)
                    .moved(Location((mx, my, 0))))
    return arms


def _centre(faces, word=None):
    """Put a mark on the origin: its bounding box, or — where `word` is a
    `(baseline, cap height)` pair — its box in X and that band's middle in Y.

    A box is the right datum for a COMPOSITION but the wrong one for a single
    line of type carrying ornaments on ONE side: box-centred, the plain
    Innovation mark's WORD sits low on the lid. So it is centred on its
    BASELINE-to-CAP band, and Ultimate keeps its box. `cad/` policy, not a
    transcription (`spec/LID.md`).
    """
    xs = [f.bounding_box() for f in faces]
    cx = (min(b.min.X for b in xs) + max(b.max.X for b in xs)) / 2
    cy = ((word[0] + word[1]) / 2 if word else
          (min(b.min.Y for b in xs) + max(b.max.Y for b in xs)) / 2)
    return [f.moved(Location((-cx, -cy, 0))) for f in faces]


# Everything is in the READING frame relative to the wordmark's anchor — the
# `I`'s centre in X, the baseline in Y — and in units of `n`, the nominal
# factor (size / NOMINAL_SIZE), unless marked ABSOLUTE (`spec/LID.md`).

NOTO_SERIF_BI = str(FONT_DIR / "NotoSerif-BoldItalic.ttf")

# `Ultimate` is Noto Serif Bold Italic at this fraction of the wordmark's
# size, placed by its INK's corner.
ULT_RATIO = 0.58316
ULT_INK_LEFT = 25.2114        # n, right of the I's centre
ULT_INK_BOTTOM = -12.6196     # n, below the baseline (the baseline is 12.620 n)

# The lead-in: five dashes, ABSOLUTE, their top edge on the bar line below the
# baseline. The run's inner end carries an absolute term two drawings alone
# could not separate from the scaled one.
DASH_LEN = 1.500
DASH_PITCH = 2.8125
BAR_LINE = -7.500             # n: the dashes' top edge and the bar's
DASH_INNER = (24.0078, -1.000)   # a*n + b

# The end flourish: a ring of bore RING_R and wall LINE_WIDTH, both ABSOLUTE,
# a bar back toward the word, and an upright from its bottom tangent; the bore
# is cut out of all three. Its FAR edge is the scaled position.
RING_R = 1.400
RING_X = (87.6654, RING_R + LINE_WIDTH)
BAR_BACK = 8.750              # n
UPRIGHT_TOP = -3.750          # n

# The fan under the U: five SCALED boxes, hand-placed — not on one arc — the
# outer ones leaning outward. Centres relative to the I's centre and the
# ULTIMATE baseline, from the sketch.
FAN_BOX = (0.625, 1.250)      # n
ULT_BASELINE = -12.620        # n
FAN = ((28.1492, -2.1871, 0.0),
       (26.1269, -1.8826, +18.0), (30.1714, -1.8826, -18.0),
       (24.6009, -1.2408, +37.0), (31.6974, -1.2408, -37.0))


def _rect(x0, x1, y0, y1):
    return _flat(Box(x1 - x0, y1 - y0, 1, mode=Mode.PRIVATE)).moved(
        Location(((x0 + x1) / 2, (y0 + y1) / 2, 0)))


def _disc(r, at):
    return _flat(Cylinder(r, 1, mode=Mode.PRIVATE)).moved(Location((at[0], at[1], 0)))


@lru_cache(maxsize=8)
def innovation_ultimate(size):
    """The Innovation Ultimate mark at `size`: the plain mark's wordmark, ring
    and star plus `Ultimate`, its lead-in, its end flourish and the fan under
    its U. Same frame and conventions as `innovation_plain`."""
    n = size / NOMINAL_SIZE
    u = _units(size)
    out, base, letter_I = _wordmark(size)
    bbI = letter_I.bounding_box()
    ix = (bbI.min.X + bbI.max.X) / 2

    # `Ultimate`, by its ink corner.
    ult = Text("Ultimate", font_size=ULT_RATIO * size, font_path=NOTO_SERIF_BI,
               align=(Align.MIN, Align.MIN))
    bb = ult.bounding_box()
    at = Location((ix + ULT_INK_LEFT * n - bb.min.X,
                   base + ULT_INK_BOTTOM * n - bb.min.Y, 0))
    out += [f.moved(at) for f in ult.faces()]

    # The lead-in, from its inner end outward (toward the I).
    inner = ix + DASH_INNER[0] * n + DASH_INNER[1]
    top = base + BAR_LINE * n
    for k in range(5):
        x1 = inner - k * DASH_PITCH * n
        out.append(_rect(x1 - DASH_LEN, x1, top - LINE_WIDTH, top))

    # The end flourish.
    cx = ix + RING_X[0] * n + RING_X[1]
    cy = top - LINE_WIDTH / 2
    r_out = RING_R + LINE_WIDTH
    ring = _disc(r_out, (cx, cy))
    bar = _rect(cx - BAR_BACK * n, cx, cy - LINE_WIDTH / 2, cy + LINE_WIDTH / 2)
    upright = _rect(cx - LINE_WIDTH / 2, cx + LINE_WIDTH / 2, cy - r_out,
                    base + UPRIGHT_TOP * n)
    flourish = ring.fuse(bar, upright).clean().faces()[0]
    out.append((flourish - _disc(RING_R, (cx, cy))).faces()[0])

    # The fan.
    base_u = base + ULT_BASELINE * n
    for dx, dy, ang in FAN:
        box = _rect(-FAN_BOX[0] * n / 2, FAN_BOX[0] * n / 2,
                    -FAN_BOX[1] * n / 2, FAN_BOX[1] * n / 2)
        out.append(box.rotate(Axis.Z, ang).moved(Location((ix + dx * n, base_u + dy * n, 0))))

    shape = _centre(out)
    return tuple(f.mirror(Plane.YZ) for f in shape)


# name -> (builder, the size that is n = 1.0). A generated mark is named with
# a leading `@` so `cad/tables.LID_LOGO` can list it beside a filename.
GENERATED = {
    "@innovation-plain": (innovation_plain, NOMINAL_SIZE),
    # Ultimate at its two PUBLISHED sizes, so `lid.logo_choice` keeps the
    # ladder the drawings had.
    "@innovation-ultimate-big": (innovation_ultimate, NOMINAL_SIZE * 1.6),
    "@innovation-ultimate": (innovation_ultimate, NOMINAL_SIZE),
}


#
# `n` is the NOMINAL FACTOR: 1.0 is the mark at the size it was DRAWN, which
# is what the Lid's fit clamps against. A plain scale for a drawing; for a
# generated mark it scales the font size and the strokes stay put.


def faces(game, name, n=1.0):
    if name in GENERATED:
        build, nominal = GENERATED[name]
        return list(build(round(nominal * n, 6)))
    drawn = art.logo(game, name)
    if not drawn:
        return []
    if abs(n - 1.0) < 1e-9:
        return list(drawn)
    # about the drawing's OWN centre, so a mark drawn off-centre stays put
    cx, cy = art.centre(game, name)
    return [f.moved(Location((-cx, -cy, 0))).scale(n)
             .moved(Location((cx, cy, 0))) for f in drawn]


@lru_cache(maxsize=32)
def _extent_at(game, name, n):
    if name not in GENERATED:
        size = art.extent(game, name)
        return None if size is None else (size[0] * n, size[1] * n)
    bb = Compound(children=faces(game, name, n)).bounding_box()
    return bb.size.X, bb.size.Y


@lru_cache(maxsize=32)
def _bbox_at(game, name, n):
    fs = faces(game, name, n)
    if not fs:
        return None
    bb = Compound(children=list(fs)).bounding_box()
    return bb.min.X, bb.max.X, bb.min.Y, bb.max.Y


@lru_cache(maxsize=32)
def reach(game, name):
    """How far the mark's ink stands from the LID'S CENTRE on each of its four
    sides — `((a, b), ...)` for right, left, top and bottom, each a positive
    distance `a*n + b`. None for no such mark.

    `growth` answers a question about SIZE; this answers one about PLACE, and
    the two stop being the same the moment a mark is not centred on the lid.
    Affine for the reason `growth` is and read the same way, by two PROBES.
    The four sides are kept apart: a mark can be off centre in one only.
    """
    one, two = _bbox_at(game, name, 1.0), _bbox_at(game, name, 2.0)
    if one is None:
        return None
    d1 = (one[1], -one[0], one[3], -one[2])
    d2 = (two[1], -two[0], two[3], -two[2])
    return tuple((v2 - v1, 2 * v1 - v2) for v1, v2 in zip(d1, d2))


@lru_cache(maxsize=32)
def growth(game, name):
    """((aw, bw), (ah, bh)) with `size(n) = a*n + b`, or None for no such mark.
    AFFINE and not proportional, which is the whole point of a generated mark:
    its letters scale with `n` and its strokes do not, so `b` is the strokes
    and a drawing has `b = 0`. Two probes fix it exactly."""
    one, two = _extent_at(game, name, 1.0), _extent_at(game, name, 2.0)
    if one is None:
        return None
    return ((two[0] - one[0], 2 * one[0] - two[0]),
            (two[1] - one[1], 2 * one[1] - two[1]))


def extent(game, name, n=1.0):
    g = growth(game, name)
    return None if g is None else (g[0][0] * n + g[0][1], g[1][0] * n + g[1][1])
