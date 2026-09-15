"""Text on the parts.

Two typefaces, bundled from Google Fonts under the OFL and identified against
the reference STEPs rather than assumed: **Orbitron Bold** for the brand lines
and **Open Sans Bold** for the detail line.

SIZING IS A RULE, NOT A REPRODUCTION. Onshape can constrain sketch text in one
dimension only, so this module states the intent and fits BOTH. Two rules that
ARE the CAD's are kept: the version baseline sits one cap height below the
product line's, at half its cap. `spec/PUSHER.md`, "Text sizing is a rule".
"""
from functools import lru_cache
from pathlib import Path

from build123d import Text, Align

FONT_DIR = Path(__file__).resolve().parent.parent / "fonts"
LOGO_FONT = str(FONT_DIR / "Orbitron-Bold.ttf")
DETAIL_FONT = str(FONT_DIR / "OpenSans-Bold.ttf")

# Orbitron Bold's left side bearing on "C", per em. Both logo lines begin with
# C, so it is what turns their shared text origin into an ink position.
_LSB_C = 0.056

# Fraction of the space left clear around a line of text.
LOGO_MARGIN = 0.12

# The detail line's baseline, measured at exactly 7.000 on BOTH references —
# one of the few placements here that is a constant rather than a fitted box.
DETAIL_BASELINE_X = 7.000

_PROBE = 10.0


@lru_cache(maxsize=8)
def _metrics(font_path):
    """(cap, ascender) per unit font size, MEASURED by rendering so a font swap
    leaves no stale constant."""
    def h(ch):
        return Text(ch, font_size=_PROBE, font_path=font_path,
                    align=(Align.MIN, Align.MIN)).bounding_box().size.Y
    return h("C") / _PROBE, h("d") / _PROBE


def font_size_for_cap(cap, font_path=LOGO_FONT):
    return cap / _metrics(font_path)[0]


# Every sizing rule FITS text to a box, and a small box would otherwise shrink
# a line without limit. A floor applies at EVERY placement: text CUT into a
# part may not go below FLOOR_CUT of stroke, text that stands PROUD not below
# FLOOR_PROUD. A line under its floor is raised to it, its margins giving way;
# where even the floor does not fit, the placement RAISES. The stroke is each
# face's THINNEST, in em.
STROKE = {                        # em, thinnest stroke
    "Orbitron-Bold.ttf": 0.118,
    "OpenSans-Bold.ttf": 0.100,
    "NotoSerif-Bold.ttf": 0.054,
}
FLOOR_CUT = 0.200                 # mm, engraved into the part
FLOOR_PROUD = 0.250               # mm, embossed or a second-filament inlay


def floor_size(font=LOGO_FONT, proud=False):
    return (FLOOR_PROUD if proud else FLOOR_CUT) / STROKE[Path(font).name]


def floored(size, font=LOGO_FONT, proud=False):
    return max(size, floor_size(font, proud))


class DoesNotFit(ValueError):
    """A line at its floor overruns the part. Raised, never written."""


@lru_cache(maxsize=64)
def _width_per_cap(txt, font_path=LOGO_FONT):
    t = Text(txt, font_size=_PROBE, font_path=font_path,
             align=(Align.MIN, Align.MIN))
    return t.bounding_box().size.X / (_PROBE * _metrics(font_path)[0])


def logo_lines(d, chamfer=2.0):
    """[(text, font_size, x_ink, baseline)] for the two Orbitron lines: along
    the rise near the front edge, left-anchored at the first step. The product
    line's ascender must clear the strip spanning the whole length
    (`calSliderDistance`) and its ink stop short of the end chamfer."""
    cap_em, asc_em = _metrics(LOGO_FONT)
    asc_per_cap = asc_em / cap_em
    strip = d.calSliderDistance
    x0 = d.calHeightIncrement
    x_end = d.calPusherTotalHeight - chamfer
    margin = LOGO_MARGIN * strip
    # The length budget is measured from the INK, one C side bearing right of
    # the anchor; the bearing scales with the size, so it belongs INSIDE the
    # division.
    cap = min((strip - 2 * margin) / asc_per_cap,
              (x_end - x0) / (_width_per_cap(d.ProductName, LOGO_FONT)
                              + _LSB_C / cap_em))
    size = floored(font_size_for_cap(cap, LOGO_FONT), LOGO_FONT)
    cap = size * cap_em
    if cap * asc_per_cap > strip + 1e-9 or \
            x0 + (_width_per_cap(d.ProductName, LOGO_FONT) * cap
                  + _LSB_C * size) > x_end + 1e-9:
        raise DoesNotFit(f"{d.ProductName!r} at its floor ({size:.3f} em) "
                         f"overruns the pusher's front strip")
    # The version line is half the product's, and no smaller than the floor.
    # It never grows past the product's own cap, whose band below the baseline
    # is where it sits.
    lines = [(d.ProductName, size, -(margin + cap * asc_per_cap)),
             (d.calVersion, min(size, floored(size / 2, LOGO_FONT)),
              -(margin + cap * asc_per_cap + cap))]
    out = []
    for txt, sz, base in lines:
        if not txt.startswith("C"):
            raise ValueError(f"{txt!r} does not start with C; _LSB_C does not "
                             f"apply and the left anchor would be wrong")
        out.append((txt, sz, x0 + _LSB_C * sz, base))
    return out


def detail_line(d):
    return f"{d.CardsPerSlidingSlot} {'Sleeved' if d.isSleeved else 'Unsleeved'}"


def detail_placement(d):
    """(text, font_size, baseline_x, start_y) for the detail line.

    It reads down the depth near the leading edge, bounded by the band between
    its baseline and the first step and by the pusher's depth, and centred
    along it. Rotated 90 degrees when cut: baseline along -Y, glyphs up +X.
    The lowest INK sits on `DETAIL_BASELINE_X` rather than the true baseline,
    so a round letter's undershoot stays inside the line.
    """
    cap_em, asc_em = _metrics(DETAIL_FONT)
    txt = detail_line(d)
    band = d.calHeightIncrement - DETAIL_BASELINE_X
    depth = d.calPusherTotalDepth
    wpc = _width_per_cap(txt, DETAIL_FONT)
    cap = min((band - LOGO_MARGIN * band) / (asc_em / cap_em),
              (depth - 2 * LOGO_MARGIN * depth) / wpc)
    # The smallest pusher fits under the floor and is raised to it; its ink
    # then still runs inside the 12 % margins' hard limit.
    size = floored(font_size_for_cap(cap, DETAIL_FONT), DETAIL_FONT)
    cap = size * cap_em
    if cap * asc_em / cap_em > band + 1e-9 or wpc * cap > depth + 1e-9:
        raise DoesNotFit(f"{txt!r} at its floor ({size:.3f} em) overruns the "
                         f"pusher's leading edge")
    return (txt, size, DETAIL_BASELINE_X, -(depth - wpc * cap) / 2)

CAP = 0.720          # Orbitron Bold's OS/2 capHeight, 720/1000


@lru_cache(maxsize=4)
def _ttf(font):
    from fontTools.ttLib import TTFont
    return TTFont(font)


@lru_cache(maxsize=512)
def metrics(txt, font=LOGO_FONT):
    """`(advance, left bearing, ink bottom, ink top)` for `txt`, per em and
    measured from the BASELINE. Read out of the FONT FILE, NEVER inferred from
    rendered ink: bearings cancel from every ink measurement, so recovering
    them by arithmetic needs a glyph assumed symmetric and gets it wrong."""
    f = _ttf(font)
    upm = f["head"].unitsPerEm
    hmtx, cmap, glyf = f["hmtx"], f.getBestCmap(), f["glyf"]
    adv, lsb, lo, hi = 0.0, None, 0.0, 0.0
    for ch in txt:
        g = cmap.get(ord(ch))
        if g is None:
            continue
        a, l = hmtx[g]
        if lsb is None:
            lsb = l / upm
        shape = glyf[g]
        if shape.numberOfContours:
            lo, hi = min(lo, shape.yMin / upm), max(hi, shape.yMax / upm)
        adv += a / upm
    return adv, (lsb or 0.0), lo, hi


@lru_cache(maxsize=256)
def ink(txt, font=LOGO_FONT, size=10.0):
    """`(width, height)` of `txt`'s INK — no bearings, and rendered, so it is
    what actually gets cut."""
    from build123d import BuildSketch
    with BuildSketch() as sk:
        Text(txt, font_size=size, font_path=font, align=(Align.MIN, Align.MIN))
    bb = sk.sketch.bounding_box()
    return bb.size.X, bb.size.Y


def fit_size(txt, box_len, font=LOGO_FONT):
    """The font size whose ADVANCE across `txt` fills `box_len` — the
    dimension an Onshape text box actually constrains."""
    return box_len / metrics(txt, font)[0]


@lru_cache(maxsize=8)
def box_trail(font=LOGO_FONT):
    """How far short of an Onshape text box's RIGHT edge the ink stops, per em:
    a quarter of the font's space advance. Read off Allan's right-aligned
    samples (`spec/reference/Text right-aligned sample*.step`), replacing a
    fitted constant in each of two parts. Why Onshape pads a text box by a
    quarter space is not known; that it does is."""
    f = _ttf(font)
    return f["hmtx"][f.getBestCmap()[ord(" ")]][0] / f["head"].unitsPerEm / 4


def box_run(txt, font=LOGO_FONT):
    """How far the RIGHT edge of an Onshape text box sits from the pen origin,
    per em: the advance less the last glyph's right bearing, plus `box_trail`.
    The Holder's capacity line and the TokenHolder's engraving are
    right-aligned on it."""
    return metrics(txt, font)[0] - right_bearing(txt, font) + box_trail(font)


@lru_cache(maxsize=256)
def right_bearing(txt, font=LOGO_FONT):
    """The LAST glyph's right side bearing, per em — its advance less its ink,
    the counterpart of `metrics`' left bearing. `box_run` is the caller."""
    f = _ttf(font)
    upm = f["head"].unitsPerEm
    hmtx, cmap, glyf = f["hmtx"], f.getBestCmap(), f["glyf"]
    for ch in reversed(txt):
        g = cmap.get(ord(ch))
        if g is None:
            continue
        shape = glyf[g]
        if not shape.numberOfContours:
            continue
        return (hmtx[g][0] - shape.xMax) / upm
    return 0.0
