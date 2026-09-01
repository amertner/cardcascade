"""Primary — the ten Onshape variable-studio inputs, and how a parts.csv row
becomes them.

These are exactly the variables `automation/set_variables.build_primary` POSTs.
Nothing else is an input; everything else is computed in `derive.py`.
"""
from dataclasses import dataclass
import csv

# parts.csv "Game" -> the GameName the Onshape model expects. FCM is the one
# that differs (set_variables.py passes the short code, not "Food Chain
# Magnate"); the rest are identical.
GAME_NAME = {
    "Compile": "Compile",
    "Dominion": "Dominion",
    "Food Chain Magnate": "FCM",
    "Innovation": "Innovation",
}


@dataclass(frozen=True)
class Primary:
    HorizontalSlots: int
    RisingSliders: int
    FrontPocketCardCapacity: int
    CardsPerSlidingSlot: int
    isFirstSlidingSlotOverride: int
    FirstSlidingSlotCards: int
    isSleeved: int
    MatPocket: int
    GameName: str
    Version: str = "7.0"


def _int(row, col, default=0):
    v = (row.get(col) or "").strip()
    return int(v) if v else default


def from_row(row, sleeved, version="7.0"):
    """One parts.csv row + a sleeving -> Primary. Mirrors build_primary()."""
    first = _int(row, "Cards/First Riser")
    slot = _int(row, "Cards/Riser slot")
    game = (row.get("Game") or "").strip()
    return Primary(
        HorizontalSlots=_int(row, "Horizontal"),
        RisingSliders=_int(row, "Risers"),
        FrontPocketCardCapacity=_int(row, "Front capacity"),
        CardsPerSlidingSlot=slot,
        isFirstSlidingSlotOverride=1 if first else 0,
        FirstSlidingSlotCards=first or slot,
        isSleeved=1 if sleeved else 0,
        MatPocket=1 if (row.get("Merged-slot") or "").strip().upper() == "TRUE" else 0,
        GameName=GAME_NAME.get(game, game),
        Version=version,
    )


def load_rows(path):
    with open(path, newline="") as f:
        return [r for r in csv.DictReader(f)
                if (r.get("Status") or "").strip() != "Parked"]
