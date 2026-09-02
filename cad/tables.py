"""Per-game lookups, transcribed verbatim from the Onshape variable studio.

Every table here is keyed by GameName and is a straight transcription — the
Onshape variable each came from is named above it. `Colours`, which Onshape
knows about and `automation/components.py` does not, is kept so the
transcription can be diffed against the studio without a mental exclusion.

**`CraftGutermann` is deliberately absent.** The studio still has it; the design
is deprecated and Allan asked for it to go. It is the one place these tables
knowingly differ from Onshape, so do not add it back when diffing.
"""

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
