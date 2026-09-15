"""Three shapes the parts kept drawing for themselves.

Plain build123d; they know nothing about a cascade. `slab` is an axis-aligned
box from its EXTENTS, which is how every cut and pad in the parts is stated,
where `Box` wants a centre and a size; `tray` a rectangle extruded from Z = 0
and hollowed to a wall, top face removed; `text_solid` one line of text as a
solid, placed by its PEN ORIGIN.
"""
from build123d import (Align, Box, BuildPart, BuildSketch, Kind, Location, Mode,
                       Plane, Pos, Rectangle, Text, add, extrude, offset)

from . import text as T


def slab(x0, x1, y0, y1, z0, z1):
    return Box(x1 - x0, y1 - y0, z1 - z0).moved(
        Location(((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2)))


def tray(width, depth, height, wall):
    """A `width` x `depth` rectangle on the origin, extruded `height` up from
    Z = 0 and hollowed to `wall`, TOP face removed."""
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

    `Text` with `align=MIN` puts the INK's corner on the origin, so a shift of
    +lsb, +lo brings both to zero. It MUST go on a `Mode.PRIVATE` `Text`.
    """
    _adv, lsb, lo, _hi = T.metrics(txt, font)
    with BuildPart() as part:
        with BuildSketch(Plane.XY.offset(z)):
            glyphs = Text(txt, font_size=size, font_path=font,
                          align=(Align.MIN, Align.MIN), mode=Mode.PRIVATE)
            add(Pos(lsb * size, lo * size) * glyphs)
        extrude(amount=depth)
    return part.part
