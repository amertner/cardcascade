"""Three shapes the parts kept drawing for themselves.

Each was written out in full in two to four part modules — the box twice
over — and they had drifted only in their argument order, which is the kind
of duplication that hides a real difference when one does appear. They are
plain build123d and know nothing about a cascade.

  * `slab` — an axis-aligned box from its EXTENTS, which is how every cut and
    pad in the parts is stated (`x from a to b`), where `Box` wants a centre
    and a size.
  * `tray` — a rectangle extruded up from Z = 0 and hollowed to a wall with
    the top face removed: the Box and the Lid are both one of these before
    anything is cut into them.
  * `text_solid` — one line of text as a solid, placed by its PEN ORIGIN.
    `Text` aligns on its ink, and `cad.text.metrics` reads the bearings out
    of the font file to put the pen back on (0, 0); see the note in the body
    for the two traps this pays for once.
"""
from build123d import (Align, Box, BuildPart, BuildSketch, Kind, Location, Mode,
                       Plane, Pos, Rectangle, Text, add, extrude, offset)

from . import text as T


def slab(x0, x1, y0, y1, z0, z1):
    """An axis-aligned box spanning [x0, x1] x [y0, y1] x [z0, z1]."""
    return Box(x1 - x0, y1 - y0, z1 - z0).moved(
        Location(((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2)))


def tray(width, depth, height, wall):
    """A `width` x `depth` rectangle centred on the origin, extruded `height`
    up from Z = 0 and hollowed to `wall` with the TOP face removed, so the
    floor and the four walls are all `wall` thick."""
    with BuildPart() as part:
        with BuildSketch(Plane.XY):
            Rectangle(width, depth)
        extrude(amount=height)
        top = part.faces().sort_by(lambda f: f.center().Z)[-1]
        offset(amount=-wall, openings=top, kind=Kind.INTERSECTION,
               mode=Mode.REPLACE)
    return part.part


def text_solid(txt, font, size, depth, z=0.0):
    """`txt` at `size` in `font`, extruded `depth` up from the plane Z = `z`,
    with the pen origin at (0, 0) and the baseline on Y = 0.

    `Text` with `align=MIN` puts the INK's corner on the origin, which leaves
    the pen origin at -lsb and the baseline at -lo; shifting by +lsb, +lo
    brings both to zero. The shift has to be applied to a `Mode.PRIVATE`
    `Text`, or `Text` adds itself to the sketch where it stands AND the
    shifted copy lands on top of it.
    """
    _adv, lsb, lo, _hi = T.metrics(txt, font)
    with BuildPart() as part:
        with BuildSketch(Plane.XY.offset(z)):
            glyphs = Text(txt, font_size=size, font_path=font,
                          align=(Align.MIN, Align.MIN), mode=Mode.PRIVATE)
            add(Pos(lsb * size, lo * size) * glyphs)
        extrude(amount=depth)
    return part.part
