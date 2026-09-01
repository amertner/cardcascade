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


def logo_lines(p, d):
    """[(text, font_size, x_origin, baseline)] for the Orbitron lines.

    MEASURED, NOT DERIVED. The anchors below come from the one STEP we have;
    the Onshape sketch drives them from #StepHypotenuse and #calSliderDistance
    (see the Detail text sketch), but its dimensions land on the text BOX and
    Onshape fits the glyphs inside that box by its own rule, which one sample
    cannot recover. `LOGO_BASELINE` is 0.0236 mm off `StepHypotenuse/4`
    (4.9244) for exactly that reason. A second STEP at a different parameter
    set settles whether these scale.
    """
    LOGO_CAP = 4.4682              # #LogoTextHeight
    LOGO_X = 16.7176               # both lines share this left origin
    LOGO_BASELINE = -4.9008        # ~= -StepHypotenuse/4; see above
    size = font_size_for_cap(LOGO_CAP)
    lines = [(d.ProductName, size, LOGO_BASELINE),
             # one LogoTextHeight below, at half the cap height
             (d.calVersion, size / 2, LOGO_BASELINE - LOGO_CAP)]
    out = []
    for txt, sz, base in lines:
        if not txt.startswith("C"):
            raise ValueError(f"{txt!r} does not start with C; _LSB_C does not "
                             f"apply and the left anchor would be wrong")
        out.append((txt, sz, LOGO_X + _LSB_C * sz, base))
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
