"""Text on the parts.

Two of the Pusher's three lines are Orbitron Bold — the same file
`labelmaker.py` uses — confirmed against the STEP to under 0.001 mm on every
glyph width and to 0.023 mm on the advance across 48.7 mm of text.

**The third line is not Orbitron** and its font is not yet known; see
spec/PUSHER.md. `detail_line()` returns the string, but nothing cuts it until
the font is settled — cutting it in the wrong face would look like a
reproduction and not be one.

## Sizing, and why LogoTextHeight goes away

Onshape sizes sketch text by dragging a bounding box, so the design carries
`#LogoTextHeight` — the *measured* cap height of the C in "Card Cascade" — as a
workaround for not being able to state a cap height directly. It is then used
as a real dimension: the version line's baseline sits exactly one
`LogoTextHeight` below the product line's (4.4682 measured, 4.4682 apart).

build123d can be told a cap height, so here `LOGO_CAP` is the input and the
font size is derived from the font's own metrics. The workaround does not need
reproducing, only its consequences.
"""
from pathlib import Path

from build123d import Text, Align

FONT_DIR = Path(__file__).resolve().parent.parent / "fonts"
LOGO_FONT = str(FONT_DIR / "Orbitron-Bold.ttf")

# Orbitron Bold, measured from the file: cap height and the left side bearing
# of "C", as fractions of the font size. Both logo lines begin with C
# (ProductName is "Card Cascade" or "Craft Cascade"; calVersion is "CC <v>"),
# so the bearing turns the shared text origin into an ink position.
_CAP_PER_EM = 0.720
_LSB_C = 0.056


def font_size_for_cap(cap):
    return cap / _CAP_PER_EM


# Orbitron Bold, from the file: the ascender of "d" as a multiple of the cap
# height of "C". The product line's tallest ink is an ascender, so this is what
# has to clear the strip it runs along.
_ASC_PER_CAP = 4.7785 / 4.4684

# Fraction of the strip left clear above the text and below it.
LOGO_MARGIN = 0.12


def _width_per_cap(txt, font_path=LOGO_FONT):
    """Rendered width of `txt` per unit of cap height. A property of the string
    and the font, so it survives any change of scale."""
    probe = 10.0
    t = Text(txt, font_size=probe, font_path=font_path, align=(Align.MIN, Align.MIN))
    return t.bounding_box().size.X / (probe * _CAP_PER_EM)


def logo_lines(p, d, chamfer=2.0):
    """[(text, font_size, x_ink, baseline)] for the two Orbitron lines.

    **This is a rule, not a reproduction.** The Onshape sketch sizes these by
    fitting a text box, and the result does not follow from the derived
    variables: the same string comes out at a cap of 4.4684 on Compile 105 Sl
    and 1.1611 on Dominion 246 Sl, a factor of 3.85, where nothing derived
    moves by more than 2.55 and most by under 1.3. Allan's note on the second
    export -- "the text is too small here, but it's hard to make this work
    better in Onshape" -- is that artefact. So the rebuild states the intent
    instead of copying the outcome.

    Two things ARE the CAD's, confirmed on both parts and kept:
      * the version line's baseline sits exactly one cap height below the
        product line's (#LogoTextHeight is measured back out of Onshape for
        precisely this), and
      * it is set at half the product line's cap.

    The size is then the largest that fits the space the line actually has:
    the product line runs along the rise near the front edge, so its ascender
    must clear the strip that spans the whole length -- which is the last
    step's drop, `calSliderDistance` -- and it must stop short of the end
    chamfer. Both lines are left-anchored at the first step.
    """
    strip = d.calSliderDistance
    x0 = d.calHeightIncrement
    x_end = d.calPusherTotalHeight - chamfer
    margin = LOGO_MARGIN * strip
    # The length budget is measured from the INK, which starts one C side
    # bearing right of the anchor, and the bearing scales with the size — so it
    # belongs inside the division, not outside it.
    cap = min((strip - 2 * margin) / _ASC_PER_CAP,
              (x_end - x0) / (_width_per_cap(d.ProductName)
                              + _LSB_C / _CAP_PER_EM))
    size = font_size_for_cap(cap)
    lines = [(d.ProductName, size, -(margin + cap * _ASC_PER_CAP)),
             (d.calVersion, size / 2, -(margin + cap * _ASC_PER_CAP + cap))]
    out = []
    for txt, sz, base in lines:
        if not txt.startswith("C"):
            raise ValueError(f"{txt!r} does not start with C; _LSB_C does not "
                             f"apply and the left anchor would be wrong")
        out.append((txt, sz, x0 + _LSB_C * sz, base))
    return out


def detail_line(p):
    """The rotated line down the leading edge: "<cards per slot> <sleeving>".

    NOT CUT — font unknown. Confirmed as the string from the STEP's glyph
    pattern (word space after the first glyph, the narrow `l` third, and the
    three `e`s fourth, fifth and seventh) and from Allan's screenshots, which
    show "12 Unsleeved" and "12 Sleeved" on other parts.
    """
    return f"{p.CardsPerSlidingSlot} {'Sleeved' if p.isSleeved else 'Unsleeved'}"


def cap_height(txt, font_size, font_path=LOGO_FONT):
    """Measured cap height of `txt` as rendered — the check that _CAP_PER_EM
    still describes the font file."""
    t = Text(txt, font_size=font_size, font_path=font_path,
             align=(Align.MIN, Align.MIN))
    return t.bounding_box().size.Y
