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
# like the line width: fitted at -0.1039 on both drawings, where the arm length
# scales by 1.6002 between them. With it the five tips land to 0.0005 and
# 0.0003; without it they are 0.10 out.
TWIST = 0.1039

# The font size the SMALL Innovation drawing is set at, fitted over its nine
# clean glyphs to 0.016 mm. The big drawing is 33.3466 = this x 1.59999.
NOMINAL_SIZE = 20.8416

# Everything below is in font units per 1000 em, so it scales with the size.
CAP = 714.0                  # the I's cap height
SERIF_MID = 693.0            # middle of the I's top serif slab (672..714)
I_INK = 291.0                # the I's ink width; the annulus bore is half it
ARM = 119.952                # star arm, centre to tip: 2.500 at NOMINAL_SIZE,
#                              and 4.0002 measured on the big drawing - x1.6002
ARM0 = -46.14                # the first arm of the run, reading orientation
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
    star = _star(tittle, size, u)

    out = []
    for f in faces:
        if f is letter_I:
            f = f.fuse(ring).clean().faces()[0]
        elif f is tittle:
            f = f.fuse(*star).clean().faces()[0]
        out.append(f)
    shape = _centre(out)
    return tuple(f.mirror(Plane.YZ) for f in shape)


def _ring(letter_I, base, u):
    """The annulus round the `I`: bore = the letter's ink width, wall
    `LINE_WIDTH`, centred on the middle of its top serif."""
    bb = letter_I.bounding_box()
    r = (bb.max.X - bb.min.X) / 2
    at = Location(((bb.min.X + bb.max.X) / 2, base + SERIF_MID * u, 0))
    disc = Cylinder(r + LINE_WIDTH, 1, mode=Mode.PRIVATE).faces() \
        .sort_by(lambda f: f.center().Z)[-1]
    bore = Cylinder(r, 1, mode=Mode.PRIVATE).faces() \
        .sort_by(lambda f: f.center().Z)[-1]
    return (disc - bore).moved(at).moved(Location((0, 0, -disc.center().Z)))


def _star(tittle, size, u):
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
        bar = Box(L, LINE_WIDTH, 1, mode=Mode.PRIVATE).faces() \
            .sort_by(lambda f: f.center().Z)[-1]
        bar = bar.moved(Location((0, 0, -bar.center().Z)))
        arms.append(bar.rotate(Axis.Z, ARM0 + k * ARM_STEP)
                    .moved(Location((mx, my, 0))))
    return arms


def _centre(faces):
    """Put a mark's bounding box on the origin."""
    xs = [f.bounding_box() for f in faces]
    cx = (min(b.min.X for b in xs) + max(b.max.X for b in xs)) / 2
    cy = (min(b.min.Y for b in xs) + max(b.max.Y for b in xs)) / 2
    return [f.moved(Location((-cx, -cy, 0))) for f in faces]


# name -> (builder, the size that is n = 1.0). A generated mark is named with
# a leading `@` so that `cad/tables.LID_LOGO` can list it beside a filename and
# nothing has to ask which kind it is.
GENERATED = {
    "@innovation-plain": (innovation_plain, NOMINAL_SIZE),
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
