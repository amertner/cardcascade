"""Marks that are GENERATED rather than imported.

`cad/art.py` loads a drawing someone else made. This builds one, from the font
it was set in and the geometry that was drawn around it — which is the only way
a mark keeps its **stroke weight** when the Lid's fit sizes it. Scale an
outline and its 0.600 strokes scale with it: at the 1.436 the fit gives
`S5.10.10.32-Un`, a 0.600 line becomes 0.862. Onshape's sketch does not do
that, because `#LineWidth` is absolute there, and neither does this.

## Innovation, the plain mark

Allan: "one that is just Innovation, and one that is Innovation Ultimate. The
two single-set boxes would be the Innovation version." This is that one, and
every number in it was measured off the two drawings Allan has already made —
`spec/LID.md`, "The Innovation mark, rebuilt" records the fit:

* the word is **Noto Serif Regular** at default advances with no kerning,
  which `build123d`'s own `Text` reproduces to `0.019` over 109 mm of
  wordmark. `NOMINAL_SIZE` is the size the SMALL drawing is set at; the big
  one is that x 1.6, to five figures, which is `#LogoScaleFactor` exactly.
* the **circle** round the `I` is an annulus on the middle of that letter's
  top serif, its bore the letter's own ink width and its wall `LINE_WIDTH`.
  Measured `r 3.0306 / 3.6306` against `3.0325` for the letter's half-width
  and a wall of `0.6000`.
* the **star** over the `i` is the letter's own tittle with five arms through
  it — `LINE_WIDTH` wide, `ARM` long, `67.5` apart, which is the `5x at 270`
  circular pattern Allan's Logo Flourishes sketch holds. Each arm is offset
  `TWIST` off the centre, a slight pinwheel; with it the five arm tips land on
  the drawing to `0.0005`, and the "disc" they seemed to stand on turned out
  to be the tittle itself.

The letters and the geometry hung off them scale with the size; `LINE_WIDTH`
does not. That is the whole point of building it rather than scaling it.

## Innovation Ultimate

The same wordmark, ring and star, with `Ultimate` under it in Noto Serif Bold
Italic and its three flourishes: a lead-in of five dashes, a ring with a bar
and an upright at the end, and a fan of five boxes under the `U`. Every
number is read off Allan's own `Logo Flourishes` sketch, exported 2026-09-04
at `#LogoScaleFactor 1` (`logos/Innovation/sketch/Logo Flourishes.dxf`), or
off the two Ultimate drawings where the sketch does not carry the element (the
words, the end flourish). What scales and what does not is settled by the two
drawings — 1.6 apart — agreeing on it: the dashes are `1.500 x 0.600` and the
ring `r 1.400 / 2.000` at both sizes, the fan's boxes are `0.625 x 1.250` and
`1.000 x 2.000`. Two positions carry an absolute term as well as a scaled one,
and the sketch alone cannot separate them; both are stated as `a*n + b`, with
the `b` a round number of the geometry it sits on. `tests/test_lid.py` holds
the result to the sketch export region for region.

It is registered TWICE in `GENERATED`, at the two sizes the sketch shipped
at, so that the lid's ladder keeps the big mark where a lid carried it.
"""
import math
from functools import lru_cache
from pathlib import Path

from build123d import (Align, Axis, Box, Compound, Cylinder, Location, Mode,
                       Plane, Text)

from . import art

FONT_DIR = Path(__file__).resolve().parent.parent / "fonts"
NOTO_SERIF = str(FONT_DIR / "NotoSerif-Regular.ttf")

# `#LineWidth`, absolute at every size — the one number here that does not
# scale. Confirmed on the small drawing's annulus at 0.6000.
LINE_WIDTH = 0.600

# Each star arm is offset this far off the centre, a slight pinwheel. ABSOLUTE,
# like the line width. It is where Allan drew the seed of the `5x at 270`
# circular pattern — a rectangle whose axis misses the pattern's centre by this
# much, so every copy misses it by the same. Read off the Logo Flourishes
# sketch (2026-09-04): one offset fits all five arms' twenty corners to an rms
# of 0.00002 mm. The mesh fit before it said 0.1039.
TWIST = 0.1041

# The font size the SMALL Innovation drawing is set at, fitted over its nine
# clean glyphs to 0.016 mm. The big drawing is 33.3466 = this x 1.59999. The
# sketch's annulus agrees: its bore of 4.848958 at the big size is the I's
# half ink width (291 font units) at 33.326, which is this x 1.6 to 0.06 % —
# one radius read to 0.003 mm is the coarser instrument, so the letters' fit
# stands and the sketch confirms it rather than replacing it.
NOMINAL_SIZE = 20.8416

# Everything below is in font units per 1000 em, so it scales with the size.
SERIF_MID = 693.0            # middle of the I's top serif slab (672..714)
ARM = 119.952                # star arm, centre to tip: 2.500 at NOMINAL_SIZE,
#                              and 4.0002 measured on the big drawing - x1.6002
# The first arm of the run, in the READING frame the mark is built in before
# it is mirrored into the lid. The sketch draws the lid's frame directly, so
# there its arms read -43.8558, 23.6442, 91.1442, 158.6442 and 226.1442; the
# mirror maps each to 180 - x, and the run starts at -46.1442. The mesh fit
# before the sketch said -46.14.
ARM0 = -46.1442
ARM_STEP = 67.5              # 5 arms at 270 degrees


def _units(size):
    """mm per font unit."""
    return size / 1000.0


@lru_cache(maxsize=8)
def innovation_plain(size):
    """The plain Innovation mark at `size`, in the lid's frame.

    Returned as a tuple of faces, bbox-centred on the origin, and MIRRORED in
    X: the pattern is cut into the far side of the lid's floor, and Compile's,
    FCM's and Innovation's marks all read the right way round from there.
    """
    faces, _base, _letter_I = _wordmark(size)
    shape = _centre(faces)
    return tuple(f.mirror(Plane.YZ) for f in shape)


def _wordmark(size):
    """`Innovation` at `size` with the ring fused into its `I` and the star
    into its `i`'s tittle: (faces, baseline, the `I`). The plain mark whole,
    and the first half of the Ultimate one."""
    u = _units(size)
    word = Text("Innovation", font_size=size, font_path=NOTO_SERIF,
                align=(Align.CENTER, Align.MIN))
    faces = list(word.faces())
    # The tittle is the one face clear of the x-height; every letter reaches
    # the baseline. The text is aligned MIN in Y, so the baseline is the o's
    # and a's 10-unit overshoot above the bottom.
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
    """The top face of a unit-tall PRIVATE solid, brought down to Z = 0 —
    a filled outline, which is what a mark is made of."""
    f = solid.faces().sort_by(lambda f: f.center().Z)[-1]
    return f.moved(Location((0, 0, -f.center().Z)))


def _ring(letter_I, base, u):
    """The annulus round the `I`: bore = the letter's ink width, wall
    `LINE_WIDTH`, centred on the middle of its top serif."""
    bb = letter_I.bounding_box()
    r = (bb.max.X - bb.min.X) / 2
    at = Location(((bb.min.X + bb.max.X) / 2, base + SERIF_MID * u, 0))
    return (_disc(r + LINE_WIDTH, (0, 0)) - _disc(r, (0, 0))).moved(at)


def _star(tittle, u):
    """Five arms through the tittle — `LINE_WIDTH` wide, `ARM` long, `ARM_STEP`
    apart, each `TWIST` off the centre."""
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


def _centre(faces):
    """Put a mark's bounding box on the origin."""
    xs = [f.bounding_box() for f in faces]
    cx = (min(b.min.X for b in xs) + max(b.max.X for b in xs)) / 2
    cy = (min(b.min.Y for b in xs) + max(b.max.Y for b in xs)) / 2
    return [f.moved(Location((-cx, -cy, 0))) for f in faces]



# --- Innovation Ultimate, generated -----------------------------------------
#
# Everything is in the READING frame relative to the wordmark's anchor — the
# `I`'s centre in X and the baseline in Y — and in units of `n`, the nominal
# factor (size / NOMINAL_SIZE), unless marked ABSOLUTE. Read off the sketch
# export `logos/Innovation/sketch/Logo Flourishes.dxf` (the flourishes, exact,
# at n = 1.6) and the two Ultimate drawings (the words, both scales).

NOTO_SERIF_BI = str(FONT_DIR / "NotoSerif-BoldItalic.ttf")

# `Ultimate` is Noto Serif Bold Italic at this fraction of the wordmark's size
# (12.1539 on the small drawing): its ink runs 84.666 on the big drawing and
# `Text` at this ratio gives 84.669. Placed by its INK's corner, which lands
# at the same n-multiple on both drawings to 0.0001.
ULT_RATIO = 0.58316
ULT_INK_LEFT = 25.2114        # n, right of the I's centre
ULT_INK_BOTTOM = -12.6196     # n, below the baseline (the baseline is 12.620 n)

# The lead-in: five dashes, ABSOLUTE 1.500 x LINE_WIDTH, their top edge on the
# bar line 7.500 n below the baseline, at a pitch of 2.8125 n. The run's inner
# end — the edge nearest the U — sits at 24.0078 n LESS 1.000 from the I's
# centre; the 1.000 is absolute, and it is what two drawings alone could not
# separate from the scaled part (spec/LID.md, "measured, not yet built").
DASH_LEN = 1.500
DASH_PITCH = 2.8125
BAR_LINE = -7.500             # n: the dashes' top edge and the bar's
DASH_INNER = (24.0078, -1.000)   # a*n + b

# The end flourish: a ring of bore RING_R and wall LINE_WIDTH, both ABSOLUTE,
# a bar from its centre 8.750 n back toward the word on the bar line, and an
# upright from its bottom tangent up to 3.750 n below the baseline. The bore
# is cut out of all three — the cross does not reach into it. The ring's
# centre is 87.6654 n plus one outer radius from the I's centre: its FAR edge
# is the scaled position, which is how the mark's extent is dimensioned.
RING_R = 1.400
RING_X = (87.6654, RING_R + LINE_WIDTH)
BAR_BACK = 8.750              # n
UPRIGHT_TOP = -3.750          # n

# The fan under the U: five 0.625 n x 1.250 n boxes, SCALED (1.000 x 2.000
# on the sketch at n = 1.6), hand-placed — not on one arc — at +-18 and +-37 degrees
# off the vertical, the outer ones leaning outward. Centres relative to the
# I's centre and the ULTIMATE baseline, from the sketch at n = 1.6, where
# Allan fixed their positions (2026-09-04); the cached small drawing has them
# where the OLD sketch put them.
FAN_BOX = (0.625, 1.250)      # n
ULT_BASELINE = -12.620        # n
FAN = ((28.1492, -2.1871, 0.0),
       (26.1269, -1.8826, +18.0), (30.1714, -1.8826, -18.0),
       (24.6009, -1.2408, +37.0), (31.6974, -1.2408, -37.0))


def _rect(x0, x1, y0, y1):
    """A rectangle as a face on Z = 0."""
    return _flat(Box(x1 - x0, y1 - y0, 1, mode=Mode.PRIVATE)).moved(
        Location(((x0 + x1) / 2, (y0 + y1) / 2, 0)))


def _disc(r, at):
    """A disc of radius `r` as a face on Z = 0, centred at `at`."""
    return _flat(Cylinder(r, 1, mode=Mode.PRIVATE)).moved(Location((at[0], at[1], 0)))


@lru_cache(maxsize=8)
def innovation_ultimate(size):
    """The Innovation Ultimate mark at `size`: the plain mark's wordmark, ring
    and star, with `Ultimate`, its lead-in, its end flourish and the fan
    under its U. Same frame and conventions as `innovation_plain`."""
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
# a leading `@` so that `cad/tables.LID_LOGO` can list it beside a filename and
# nothing has to ask which kind it is.
GENERATED = {
    "@innovation-plain": (innovation_plain, NOMINAL_SIZE),
    # The Ultimate mark at its two PUBLISHED sizes — the small drawing's and
    # the big one's, `#LogoScaleFactor` 1.6 and 1. Two entries rather than one
    # so that `lid.logo_choice` keeps the ladder the drawings had: a lid that
    # carried the big mark at its drawn size keeps it, instead of having the
    # width fraction size the small one up to three quarters of it.
    "@innovation-ultimate-big": (innovation_ultimate, NOMINAL_SIZE * 1.6),
    "@innovation-ultimate": (innovation_ultimate, NOMINAL_SIZE),
}


# --- one interface over both kinds of mark ---------------------------------
#
# `n` is the NOMINAL FACTOR: 1.0 is the mark at the size it was drawn, which is
# what the Lid's fit clamps against. For a drawing that is a plain scale; for a
# generated mark it scales the font size, and the strokes stay put.


def faces(game, name, n=1.0):
    """The mark's filled faces at nominal factor `n`, in the lid's frame."""
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
def growth(game, name):
    """((aw, bw), (ah, bh)) with `size(n) = a*n + b`, or None for no such mark.

    Affine and not proportional, and that is the whole point of a generated
    mark: its letters scale with `n` and its strokes do not, so its width is
    `a*n + b` with `b` the strokes. A drawing has `b = 0`. Two probes fix it
    exactly, and they are cached because the Lid's fit asks this of every lid.
    """
    one, two = _extent_at(game, name, 1.0), _extent_at(game, name, 2.0)
    if one is None:
        return None
    return ((two[0] - one[0], 2 * one[0] - two[0]),
            (two[1] - one[1], 2 * one[1] - two[1]))


def extent(game, name, n=1.0):
    """(width, height) of the mark at nominal factor `n`."""
    g = growth(game, name)
    return None if g is None else (g[0][0] * n + g[0][1], g[1][0] * n + g[1][1])
