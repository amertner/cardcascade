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
