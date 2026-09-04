"""Text on the parts.

Two typefaces, both bundled from Google Fonts under the OFL:

* **Orbitron Bold** (`fonts/Orbitron-Bold.ttf`, the file `labelmaker.py` also
  uses) for the product name and the version — the brand lines.
* **Open Sans Bold** (`fonts/OpenSans-Bold.ttf`) for the detail line. Allan
  chose it because it fits more text in the same space than Orbitron, which is
  a wide geometric face; measured on "12 Sleeved" it needs 7.14 cap-widths
  against Orbitron's 10.9 for a string of that length.

Both were identified against the reference STEPs rather than assumed. Orbitron
Bold matches every logo glyph to under 0.001 mm. For the detail line every
Open Sans weight was tried: Bold lands at 0.0006 mm on the Compile reference
and 0.0004 mm on the Dominion one, where SemiBold is out by 0.17 and Regular
by 0.34 — the thin `l` is what separates them.

## Sizing is a rule, not a reproduction

Onshape can constrain sketch text in only one dimension, so a box that suits
one parameter set does not suit another. Measured on the two references, the
same string in the same font comes out at a cap of 4.4684 on Compile 105 Sl
and 1.1611 on Dominion 246 Sl -- a factor of 3.85, where nothing in the derived
set moves by more than 2.55 and most by under 1.3. The detail line does the
same thing, 3.686 against 1.314.

So this module states the intent and fits **both** dimensions, which is what
Onshape cannot do. Two rules that ARE the CAD's are kept, confirmed on both
references: the version baseline sits exactly one cap height below the product
line's (`#LogoTextHeight` is measured back out of Onshape for precisely that),
and it is set at half the product line's cap.
"""
from functools import lru_cache
from pathlib import Path

from build123d import Text, Align

FONT_DIR = Path(__file__).resolve().parent.parent / "fonts"
LOGO_FONT = str(FONT_DIR / "Orbitron-Bold.ttf")
DETAIL_FONT = str(FONT_DIR / "OpenSans-Bold.ttf")

# Orbitron Bold's left side bearing on "C", as a fraction of the font size,
# measured from the file (56/1000). Both logo lines begin with C (ProductName
# is "Card Cascade" or "Craft Cascade"; calVersion is "CC <v>"), so the bearing
# is what turns their shared text origin into an ink position.
_LSB_C = 0.056

# Fraction of the space left clear around a line of text.
LOGO_MARGIN = 0.12

# The detail line's baseline, measured at exactly 7.000 on BOTH references —
# one of the few placements in the CAD that is a constant rather than a fitted
# box. It clears the notch, which is 5.200 deep, and the tabs, which are 5.000
# long, by a comfortable margin.
DETAIL_BASELINE_X = 7.000

_PROBE = 10.0


@lru_cache(maxsize=8)
def _metrics(font_path):
    """(cap height, ascender height) per unit font size, from the font file.

    Measured by rendering rather than hardcoded, so a font swap cannot leave a
    stale constant behind. "C" is the cap reference and "d" the ascender.
    """
    def h(ch):
        return Text(ch, font_size=_PROBE, font_path=font_path,
                    align=(Align.MIN, Align.MIN)).bounding_box().size.Y
    return h("C") / _PROBE, h("d") / _PROBE


def font_size_for_cap(cap, font_path=LOGO_FONT):
    return cap / _metrics(font_path)[0]


# --- floors: no stroke thinner than the printer can lay down --------------
#
# Every sizing rule in the catalogue FITS text to a box, and a small box
# used to shrink a line without limit — a pusher's version line reached a
# 0.10 mm stroke, a box's model line 0.12. A floor is applied at every
# placement (Allan, 2026-09-04): text CUT into a part may not go below
# FLOOR_CUT of stroke, and text that STANDS PROUD — embossed, or laid in the
# second filament — not below FLOOR_PROUD, the slicer laying a proud line
# thinner than its nozzle dynamically but not indefinitely. A line whose
# fitted size is under its floor is raised to it, its margins giving way;
# where even the floor does not physically fit the part the placement
# RAISES rather than write something illegible or something that overruns.
#
# The stroke is each face's THINNEST, in em, measured off a 1000 px/em
# raster of the strings the catalogue sets (distance transform along the
# medial axis, first percentile — the corner pixels excluded). Orbitron and
# Open Sans are near-monoline; Noto Serif's number is its hairline.
STROKE = {                        # em, thinnest stroke
    "Orbitron-Bold.ttf": 0.118,
    "OpenSans-Bold.ttf": 0.100,
    "NotoSerif-Bold.ttf": 0.054,
}
FLOOR_CUT = 0.200                 # mm, engraved into the part
FLOOR_PROUD = 0.250               # mm, embossed or a second-filament inlay
SERIF_FONT = str(FONT_DIR / "NotoSerif-Bold.ttf")   # the Topper's


def floor_size(font=LOGO_FONT, proud=False):
    """The smallest em `font` may be set at, cut or proud."""
    return (FLOOR_PROUD if proud else FLOOR_CUT) / STROKE[Path(font).name]


def floored(size, font=LOGO_FONT, proud=False):
    """`size`, or the floor if that is larger."""
    return max(size, floor_size(font, proud))


class DoesNotFit(ValueError):
    """A line at its floor overruns the part. Raised, never written."""


@lru_cache(maxsize=64)
def _width_per_cap(txt, font_path=LOGO_FONT):
    """Rendered ink width of `txt` per unit of cap height. A property of the
    string and the font and nothing else, so it survives any change of scale."""
    t = Text(txt, font_size=_PROBE, font_path=font_path,
             align=(Align.MIN, Align.MIN))
    return t.bounding_box().size.X / (_PROBE * _metrics(font_path)[0])


def logo_lines(p, d, chamfer=2.0):
    """[(text, font_size, x_ink, baseline)] for the two Orbitron lines.

    They run along the rise near the front edge, left-anchored at the first
    step. The product line's ascender must clear the strip that spans the whole
    length -- the last step's drop, `calSliderDistance` -- and its ink must
    stop short of the end chamfer, whichever binds first.
    """
    cap_em, asc_em = _metrics(LOGO_FONT)
    asc_per_cap = asc_em / cap_em
    strip = d.calSliderDistance
    x0 = d.calHeightIncrement
    x_end = d.calPusherTotalHeight - chamfer
    margin = LOGO_MARGIN * strip
    # The length budget is measured from the INK, which starts one C side
    # bearing right of the anchor, and the bearing scales with the size — so it
    # belongs inside the division, not outside it.
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
    # The version line is half the product's — and no smaller than the floor,
    # which the four 2-riser Dominion pushers reach (0.885 em fitted against
    # 1.695). It never grows past the product's own cap, whose band below the
    # baseline is where it sits, and the floor is always under that.
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


def detail_line(p):
    """The rotated line along the leading edge: "<cards per slot> <sleeving>".

    Confirmed from the STEP's glyph pattern -- a word space after the first
    glyph, the narrow `l` third, and the three `e`s fourth, fifth and seventh --
    and from Allan's screenshots, which show "12 Unsleeved" and "12 Sleeved".
    """
    return f"{p.CardsPerSlidingSlot} {'Sleeved' if p.isSleeved else 'Unsleeved'}"


def detail_placement(p, d, notch_depth=5.2):
    """(text, font_size, baseline_x, start_y) for the detail line.

    It reads down the depth near the leading edge, so it is bounded by the band
    between its baseline and the first step in one direction and by the pusher's
    depth in the other, and is centred along that depth. Rotated 90 degrees when
    cut: baseline along -Y, glyphs standing up +X.

    The lowest ink sits on `DETAIL_BASELINE_X` rather than the true baseline, so
    a round letter's undershoot is inside the line rather than below it. On the
    references that undershoot is 0.05 mm at the Compile size and 0.02 at the
    Dominion one.
    """
    cap_em, asc_em = _metrics(DETAIL_FONT)
    txt = detail_line(p)
    band = d.calHeightIncrement - DETAIL_BASELINE_X
    depth = d.calPusherTotalDepth
    wpc = _width_per_cap(txt, DETAIL_FONT)
    cap = min((band - LOGO_MARGIN * band) / (asc_em / cap_em),
              (depth - 2 * LOGO_MARGIN * depth) / wpc)
    # FCM's `Pusher 3x6-Un` fits at 1.806 em and is raised to the 2.000 floor;
    # its ink then runs 11.82 of the 14.04 depth, inside the 12 % margins'
    # hard limit.
    size = floored(font_size_for_cap(cap, DETAIL_FONT), DETAIL_FONT)
    cap = size * cap_em
    if cap * asc_em / cap_em > band + 1e-9 or wpc * cap > depth + 1e-9:
        raise DoesNotFit(f"{txt!r} at its floor ({size:.3f} em) overruns the "
                         f"pusher's leading edge")
    return (txt, size, DETAIL_BASELINE_X, -(depth - wpc * cap) / 2)

# --- metrics -------------------------------------------------------------
CAP = 0.720          # Orbitron Bold's OS/2 capHeight, 720/1000


@lru_cache(maxsize=4)
def _ttf(font):
    from fontTools.ttLib import TTFont
    return TTFont(font)


@lru_cache(maxsize=512)
def metrics(txt, font=LOGO_FONT):
    """`(advance, left bearing, ink bottom, ink top)` for `txt`, per em and
    measured from the BASELINE.

    Read out of the font file rather than inferred from rendered ink. Bearings
    cancel from every ink measurement, so recovering them by arithmetic needs a
    glyph assumed symmetric — and picking `|` for that put the left bearing of
    "Card Cascade" at `0.0435` against its true `0.0560`.
    """
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
    """`(width, height)` of the inked extent of `txt` — no bearings. Rendered
    rather than computed, so it reflects what actually gets cut."""
    from build123d import BuildSketch
    with BuildSketch() as sk:
        Text(txt, font_size=size, font_path=font, align=(Align.MIN, Align.MIN))
    bb = sk.sketch.bounding_box()
    return bb.size.X, bb.size.Y


def fit_size(txt, box_len, font=LOGO_FONT):
    """The font size whose ADVANCE across `txt` fills `box_len` — which is the
    dimension an Onshape text box actually constrains."""
    return box_len / metrics(txt, font)[0]


@lru_cache(maxsize=8)
def box_trail(font=LOGO_FONT):
    """How far short of an Onshape text box's RIGHT edge the ink stops, per em:
    a quarter of the font's space advance.

    Read off Allan's right-aligned samples (`spec/reference/Text right-aligned
    sample*.step`, 2026-09-04): four lines in three fonts, boxes 10 tall, one
    shared right edge at x 110.135. Open Sans Bold ends its ink 0.0646 em short
    of it and Orbitron Bold 0.0761, each ±0.0004 from the dimension's rounding,
    whatever the last glyph — and a quarter of the space advance is 0.0649 and
    0.0765. The two parts had carried these as fitted constants: the holder's
    0.0646 exactly, the tray's 0.0754 (±0.002 once the cap-band reading it
    rests on is propagated; the 18 cached trays read 0.0764 ± 0.001). One rule
    for both is what the sample was asked for, and this is it. Why Onshape
    pads a text box by a quarter space is not known; that it does is.
    """
    f = _ttf(font)
    return f["hmtx"][f.getBestCmap()[ord(" ")]][0] / f["head"].unitsPerEm / 4


@lru_cache(maxsize=256)
def right_bearing(txt, font=LOGO_FONT):
    """The LAST glyph's right side bearing, per em — its advance less its ink.

    The counterpart of `metrics`' left bearing, and needed for the same reason:
    a rule that places the end of the ink cannot be checked without it, and
    recovering it from rendered ink needs a glyph assumed symmetric. The
    TokenHolder's engraving is the caller — `parts/token_holder.TRAIL`.
    """
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
