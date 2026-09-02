"""Per-game lookups, transcribed verbatim from the Onshape variable studio.

Every table here is keyed by GameName and is a straight transcription — the
Onshape variable each came from is named above it. Games Onshape knows about
that `automation/components.py` does not (Colours, CraftGutermann) are kept, so
the transcription can be diffed against the studio without a mental exclusion.
"""

# gameUnsleevedCardWidth — "The unsleeved width of a card" (mm)
UNSLEEVED_CARD_WIDTH = {
    "Dominion": 60, "FCM": 60, "Compile": 65,
    "Colours": 64, "Innovation": 64, "CraftGutermann": 24 * 2,
}

# game10UnsleevedCardThickness — "How thick are 10 unsleeved cards?" (mm)
TEN_UNSLEEVED_THICKNESS = {
    "Dominion": 3.8, "FCM": 3.8, "Compile": 4.0,
    "Colours": 6.0, "Innovation": 4, "CraftGutermann": 240,
}

# game10SleevedCardThickness — "How thick are 10 sleeved cards?" (mm)
# NB no CraftGutermann entry in the studio; a sleeved CraftGutermann cascade
# would fail the lookup in Onshape too, so it fails here rather than defaulting.
TEN_SLEEVED_THICKNESS = {
    "Dominion": 6, "FCM": 6, "Compile": 8, "Colours": 9, "Innovation": 6.5,
}

# calDesiredHeightIncrement — "how much of the top of the card must be visible?"
DESIRED_HEIGHT_INCREMENT = {
    "Dominion": 16, "FCM": 20, "Compile": 18,
    "Colours": 16, "Innovation": 22, "CraftGutermann": 20,
}

# gameShortName
GAME_SHORT_NAME = {
    "Dominion": "Dom", "FCM": "FCM", "Compile": "Cmp",
    "Colours": "Col", "Innovation": "Inn", "CraftGutermann": "CGM",
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
# Compile and FCM have no file yet — their lids build without a pattern rather
# than with a guessed one, and `cad.build` says so.
LID_LOGO = {
    "Dominion": "lid_logo.dxf",
    "Innovation": "lid_logo.dxf",
}

# `#LogoScaleFactor` — Innovation's logo sketch alone carries one (Allan):
#
#     #LogoScaleFactor = (#LidWidth < 70mm ? 1.6 : 1)
#
# and `#LidWidth` there is the lid's DEPTH, `calLidDepth`, not its width. Every
# dimension in that sketch is DIVIDED by the factor, so 1.6 draws the SMALL
# logo and 1 the big one — the sense is the opposite way round from what the
# name suggests, and it is why a shallow lid gets the small mark.
#
# Games with no factor draw one size.
LID_LOGO_FACTOR = {"Innovation": lambda d: 1.6 if d.calLidDepth < 70.0 else 1.0}

# Which artwork file serves which factor. `lid_logo.dxf` is the 1.6 drawing —
# it was lifted from `Lid Innovation 130U`, a 52.100-deep lid — and the 1.0
# drawing is NOT it scaled: `#LineWidth` (0.600) and the flourish dashes'
# 1.500 are absolute, so they stay the same size while the letters grow. A lid
# that needs a factor with no file builds without its pattern rather than with
# a wrong one.
LID_LOGO_BY_FACTOR = {"Innovation": {1.6: "lid_logo.dxf"}}
