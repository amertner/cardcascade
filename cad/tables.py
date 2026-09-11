"""Per-game lookups, transcribed verbatim from the Onshape variable studio.

Every table here is keyed by GameName and is a straight transcription — the
Onshape variable each came from is named above it. `Colours`, which Onshape
knows about and `automation/components.py` does not, is kept so the
transcription can be diffed against the studio without a mental exclusion.

**`CraftGutermann` is deliberately absent.** The studio still has it; the design
is deprecated and Allan asked for it to go. It is the one place these tables
knowingly differ from Onshape, so do not add it back when diffing.
"""

from .refuse import refuse

# gameUnsleevedCardWidth — "The unsleeved width of a card" (mm)
UNSLEEVED_CARD_WIDTH = {
    "Dominion": 60, "FCM": 60, "Compile": 65,
    "Colours": 64, "Innovation": 64,
}

# game10UnsleevedCardThickness — "How thick are 10 unsleeved cards?" (mm)
TEN_UNSLEEVED_THICKNESS = {
    "Dominion": 3.8, "FCM": 3.8, "Compile": 4.0,
    "Colours": 6.0, "Innovation": 4,
}

# game10SleevedCardThickness — "How thick are 10 sleeved cards?" (mm)
TEN_SLEEVED_THICKNESS = {
    "Dominion": 6, "FCM": 6, "Compile": 8, "Colours": 9, "Innovation": 6.5,
}

# calDesiredHeightIncrement — "how much of the top of the card must be visible?"
DESIRED_HEIGHT_INCREMENT = {
    "Dominion": 16, "FCM": 20, "Compile": 18,
    "Colours": 16, "Innovation": 22,
}

# gameShortName
GAME_SHORT_NAME = {
    "Dominion": "Dom", "FCM": "FCM", "Compile": "Cmp",
    "Colours": "Col", "Innovation": "Inn",
}

# calSizeLetter — from HorizontalSlots
SIZE_LETTER = {2: "XS", 3: "S", 4: "M", 5: "L"}

# --- the Lid's logo pattern ------------------------------------------------
#
# Each game's logo is one sketch in the Lid studio, extruded twice: `Remove
# logo` cuts the pocket and `Add Logo Material` fills it with the second
# filament. The artwork lives in `logos/<Game>/`; `spec/LID.md` records where
# each file came from and what it was checked against.
#
# Per game, and per edition of a game's mark, the drawn VARIANTS of it, largest
# first. `lid.logo_art` takes the first that fits the lid's flat floor and then
# scales it to fill — so a game needs a second file only where its two sizes
# are not a scale of each other. Compile's are (its small mark is the big one
# at 1/1.25297, line weights and all, which is why one file serves its six
# lids); Innovation's are not, because `#LineWidth` and the flourish dashes are
# absolute in that sketch, so its letters grow between the two drawings and its
# strokes do not.
LID_LOGO = {
    "Compile": {None: ("lid_logo.dxf",)},
    "Dominion": {None: ("lid_logo.dxf",)},
    "FCM": {None: ("lid_logo.dxf",)},
    # Both Innovation marks are GENERATED, not drawn — `cad/marks.py` builds
    # them from Noto Serif and the Logo Flourishes sketch, so their 0.600
    # strokes hold at every size the fit picks. The drawings beside them in
    # `logos/Innovation/` — `lid_logo.dxf` and `lid_logo_big.brep` for the
    # Ultimate mark, `lid_logo_plain*.dxf` for the plain one — are what they
    # are CHECKED against, not what is used.
    "Innovation": {None: ("@innovation-ultimate-big", "@innovation-ultimate"),
                   "plain": ("@innovation-plain",)},
}

# The games whose mark goes into the lid TURNED a half turn about the lid's
# centre (`lid.logo_art`), every edition and size of it. Innovation, because a
# printed 7.1 lid read upside down (Allan, 2026-09-11) — the same finding that
# turned Dominion's drawing back the same day (`spec/LID.md`).
#
# A set here and not a turned file because Innovation's marks are GENERATED:
# there is no drawing to turn, and `cad/marks.py` stays in the frame of the
# drawings it is checked against, so those comparisons do not move. About the
# LID's centre and not the mark's own box, because the origin is the
# placement datum — the plain mark centres its WORD there (`marks._centre`),
# and a turn about its box would undo that.
LID_LOGO_TURNED = frozenset({"Innovation"})

# Which EDITION of a game's mark a cascade carries — keyed on the base model,
# `calModelName` up to its third dot, because this is a question about which
# sets the box holds and not about any dimension.
#
# Innovation is the one game with two: the Ultimate mark says "Innovation
# Ultimate", and the two cascades that hold a single set say just "Innovation"
# (Allan). Anything not listed gets the game's default mark, `None`.
LID_LOGO_EDITION = {
    "Innovation": {"S3.15.10": "plain", "XS5.15.10": "plain"},
}

# What an edition is CALLED, where a name has to tell two lids apart: the
# suffix on the alternate lid's file and on its object in the project, from
# 7.1d. A game's DEFAULT edition is the `None` key here as it is above, and
# Innovation's default is the mark that says Ultimate.
LID_EDITION_NAME = {
    "Innovation": {None: "Ultimate", "plain": "Innovation"},
}


def lid_editions(game, model):
    """The editions of `game`'s mark a cascade of this model ships, the one it
    CARRIES first.

    A cascade that carries its game's default mark ships that alone, and that
    is 46 of the 50. One that carries another edition ships the default TOO,
    on a plate of its own, so its owner prints whichever the shelf should read
    (Allan, 2026-09-10): Innovation's two single-set cascades say just
    `Innovation` and get an `Innovation Ultimate` lid beside it.

    `model` is `calModelName`, keyed on up to its third dot exactly as
    `LID_LOGO_EDITION` is — this is a question about which SETS the box holds
    and not about any dimension.

    The second is what `rev.both_lid_editions` admits, and it is the flag and
    not this function that a release turns on: every caller before 7.1d takes
    `[0]` alone.
    """
    own = (LID_LOGO_EDITION.get(game) or {}).get(".".join(model.split(".")[:3]))
    return (own,) if own is None else (own, None)


def has_lid_alternate(game, model):
    """Is there a SECOND edition for this cascade to ship?

    Only a cascade whose mark is not its game's default has one. WHETHER it
    ships is the release's question and not this one's — `cad/build.py` asks
    both, `rev.both_lid_editions` first.
    """
    return len(lid_editions(game, model)) > 1


def lid_edition_name(game, edition):
    """The word that names an edition in a file or an object name.

    A refusal rather than a `None` to concatenate: a second edition with no
    name would otherwise write `Lid <model> None.3mf` and be found on the
    shelf, not here.
    """
    name = (LID_EDITION_NAME.get(game) or {}).get(edition)
    if name is None:
        refuse(f"{game}'s {edition!r} lid edition has no name to put in a "
               f"file (cad/tables.LID_EDITION_NAME)")
    return name


# The five Innovation expansions whose topper mark `cad/parts/topper.MARKS`
# draws, in catalogue order. Data here rather than read off `MARKS` so that
# `cad.build --list` and `cad.promote` can name the toppers without importing
# build123d; `topper.py` asserts the two agree.
TOPPER_EXPANSIONS = ("Artifacts", "Cities", "Echoes", "Figures", "Unseen")
# The six toppers a cascade ships, in catalogue order: the Blank and the five.
TOPPERS = ("Blank",) + TOPPER_EXPANSIONS
