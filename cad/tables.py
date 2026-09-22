"""Per-game lookups, keyed by GameName.

The first block is transcribed verbatim from the Onshape variable studio, the
variable each came from named above it; `Colours` is kept so the transcription
can be diffed without a mental exclusion. The lid-mark and topper tables after
it are `cad/`'s own policy (`spec/LID.md`, `spec/TOPPER.md`).
**`CraftGutermann` is deliberately absent** — deprecated, and the one place
these tables knowingly differ from Onshape.
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

# cad/'s own games, which the studio never had: MiniCards, a GENERIC game of
# 41 x 63 mm cards (any game with that card), its thicknesses typical ones.
UNSLEEVED_CARD_WIDTH["MiniCards"] = 41
TEN_UNSLEEVED_THICKNESS["MiniCards"] = 3.5
TEN_SLEEVED_THICKNESS["MiniCards"] = 6.0
DESIRED_HEIGHT_INCREMENT["MiniCards"] = 14
GAME_SHORT_NAME["MiniCards"] = "Min"

# The first release that builds each of cad/'s own games: no row of one is
# on the catalogue before it (`params.load_rows`), so the 7.0 corpus and every
# older release's catalogue are what they were.
GAME_SINCE = {"MiniCards": "8.0"}

# GENERIC games are no game at all: cascades for any game with that size of
# card, to show what is possible. Where a game's name would be engraved they
# carry CREDIT, and they ship only the unmarked lid (`build.lid_variants_built`).
GENERIC_GAMES = frozenset({"MiniCards"})
# "(C)" spelled out: Orbitron Bold has no `©`, and the full name is too wide
# to clear the lid's sockets and staircase.
CREDIT = "(C) Mertner"

# CardHeight is the GAME's: its card plus 3.000 of envelope, as 92 is for an
# 88-89 card. The studio's 92 wherever a game is not listed.
CARD_HEIGHT = {"MiniCards": 66.0}

# The BOX is a HEIGHT CLASS's, so one class is one look for every game in it:
# box height and label height, the lid and the lowered front following from
# them (`derive`, `spec/BOX.md`, "Shorter cards"). A game not in a class has
# the studio's 105 box and 22.2 label. "mini" is sized for 63..68 mm cards
# (mini American to mini Euro, sleeved): 13.000 over the tallest's CardHeight,
# as 105 is over 92.
HEIGHT_CLASS = {"MiniCards": "mini"}
CLASS_BOX_HEIGHT = {"mini": 86.0}
CLASS_LABEL_HEIGHT = {"mini": 12.0}
# The studio's own exceptions, a game and not a class.
BOX_HEIGHT = {"Colours": 115.0}
LID_HEIGHT = {"Colours": 55.0}

# calSizeLetter — from HorizontalSlots
SIZE_LETTER = {2: "XS", 3: "S", 4: "M", 5: "L"}

# Each game's logo is one sketch in the Lid studio, extruded twice: a pocket
# cut and a second-filament fill; the artwork is in `logos/<Game>/`
# (`spec/LID.md`). Per game and per edition, the drawn VARIANTS largest first:
# `lid.logo_choice` takes the first that fits `lid.logo_limit` and scales it
# to fill, so a second file is needed only where the two are not a scale.
LID_LOGO = {
    "Compile": {None: ("lid_logo.dxf",)},
    "Dominion": {None: ("lid_logo.dxf",)},
    "FCM": {None: ("lid_logo.dxf",)},
    # Both Innovation marks are GENERATED, not drawn (`cad/marks.py`), so
    # their strokes hold at every size. The drawings in `logos/Innovation/`
    # are what they are CHECKED against, not what is used.
    "Innovation": {None: ("@innovation-ultimate-big", "@innovation-ultimate"),
                   "plain": ("@innovation-plain",)},
}

# The games whose mark goes into the lid TURNED a half turn about the lid's
# centre (`lid.logo_art`), every edition and size — settled by a PRINTED lid,
# never by a render (`spec/LID.md`). A set and not a turned file because
# Innovation's marks are GENERATED. About the LID's centre and not the mark's
# own box, the origin being the placement datum.
LID_LOGO_TURNED = frozenset({"Innovation"})

# Which EDITION of a game's mark a cascade carries — keyed on `calModelName`
# up to its third dot, this being a question about which SETS the box holds
# and not about any dimension. Anything not listed gets the default, `None`.
LID_LOGO_EDITION = {
    "Innovation": {"S3.15.10": "plain", "XS5.15.10": "plain"},
}

# The VARIANTS of a lid a cascade can ship (`cad/parts/lid.py`). Here and not
# in the part because `build.py` and `project.py` name one without loading
# build123d.
LID_OWN = "own"              # the cascade's mark and its game's name
LID_ALTERNATE = "alternate"  # the game's other edition, from 7.1d
LID_UNMARKED = "unmarked"    # no mark, `lid.CREDIT` for the game's name, 7.2b
LID_VARIANTS = (LID_OWN, LID_ALTERNATE, LID_UNMARKED)

# The VARIANTS of a BACK a box can be built with (`box.storage_slot_count`),
# from 7.2g (`rev.back_pocket_variants`). Here for the reason the lid's are.
BACK_STANDARD = ""         # one cavity per pusher shipped; the rest is pocket
BACK_OPEN = "open"         # no dividers or cutouts: the pocket is the full
#                            inner width
BACK_NOTCHES = "notches"   # as many cavities as the width takes, no pocket
#                            and so no thumb cutout
BACK_POCKET_VARIANTS = (BACK_STANDARD, BACK_OPEN, BACK_NOTCHES)

# What an edition is CALLED, where a name has to tell two lids apart: the
# suffix on the alternate lid's file and object. A game's DEFAULT edition is
# the `None` key here as it is above.
LID_EDITION_NAME = {
    "Innovation": {None: "Ultimate", "plain": "Innovation"},
}

# And the word for the lid that carries NO mark (7.2b): the same suffix rule,
# one word for every game, because the lid says nothing about one.
LID_UNMARKED_NAME = "Unmarked"


def lid_editions(game, model):
    """The editions of `game`'s mark a cascade of this model ships, the one it
    CARRIES first. A cascade carrying its game's default mark ships that
    alone; one carrying another edition ships the default TOO, for its owner
    to choose. The second is what `rev.both_lid_editions` admits — the FLAG,
    not this function, is what a release turns on."""
    own = (LID_LOGO_EDITION.get(game) or {}).get(".".join(model.split(".")[:3]))
    return (own,) if own is None else (own, None)


def has_lid_alternate(game, model):
    """Is there a SECOND edition for this cascade to ship? Only a cascade
    whose mark is not its game's default has one; WHETHER it ships is the
    release's question, asked in `cad/build.py`."""
    return len(lid_editions(game, model)) > 1


def lid_edition_name(game, edition):
    """The word that names an edition in a file or an object name. A REFUSAL
    rather than a `None` to concatenate, which would write `Lid <model>
    None.3mf` and be found on the shelf, not here."""
    name = (LID_EDITION_NAME.get(game) or {}).get(edition)
    if name is None:
        refuse(f"{game}'s {edition!r} lid edition has no name to put in a "
               f"file (cad/tables.LID_EDITION_NAME)")
    return name


# The five Innovation expansions whose topper mark `cad/parts/topper.MARKS`
# draws, in catalogue order. Data here rather than read off `MARKS` so the
# catalogue paths need no build123d; `topper.py` asserts the two agree.
TOPPER_EXPANSIONS = ("Artifacts", "Cities", "Echoes", "Figures", "Unseen")
# The six toppers a cascade ships, in catalogue order: the Blank and the five.
TOPPERS = ("Blank",) + TOPPER_EXPANSIONS
