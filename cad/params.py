"""Primary — the ten Onshape variable-studio inputs, and how a parts.csv row
becomes them.

These are exactly the variables `automation/set_variables.build_primary` POSTs,
plus ONE that Onshape has no input for: `LabelHolders`, the parts.csv `Label
holders` column, which `derive.py` folds into `isLabelHoldersOnBox` where the
studio computes that flag from the game and the slot count alone. Nothing else
is an input; everything else is computed in `derive.py`.
"""
from dataclasses import dataclass
import csv

from .refuse import refuse
from .revisions import CURRENT

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
    # The RELEASE this part is built to. It picks the geometry (through
    # `derive` -> `d.rev`, `cad/revisions.py`) as well as the `CC <v>` stamp,
    # so a caller that means an older release must SAY so: everything that
    # compares against `individual/` or a reference STEP passes "7.0", and
    # `tests/test_holder_corpus.py` has priced its engraving at an explicit
    # `Version="6.6"` since long before this default moved.
    Version: str = CURRENT
    # cad/ only — see the module docstring. 1 is what every shipped box has;
    # 0 leaves the front and side label holders off (`box.label_holders`).
    LabelHolders: int = 1


def _int(row, col, default=0):
    v = (row.get(col) or "").strip()
    return int(v) if v else default


def from_row(row, sleeved, version=CURRENT):
    """One parts.csv row + a sleeving -> Primary. Mirrors build_primary().

    A malformed row names itself: a number that will not parse or a Game the
    studio does not know raises a ValueError carrying the row's Short name,
    rather than an `int()` traceback with no row in it or a KeyError from
    deep in `derive`.
    """
    short = (row.get("Short name") or "?").strip()
    try:
        first = _int(row, "Cards/First Riser")
        slot = _int(row, "Cards/Riser slot")
    except ValueError as e:
        raise ValueError(f"parts.csv row {short!r}: {e}") from None
    game = (row.get("Game") or "").strip()
    if GAME_NAME.get(game, game) not in GAME_NAME.values():
        raise ValueError(f"parts.csv row {short!r}: unknown Game {game!r}; "
                         f"known: {sorted(GAME_NAME)}")
    try:
        return _primary(row, sleeved, version, first, slot, game)
    except ValueError as e:
        raise ValueError(f"parts.csv row {short!r}: {e}") from None


def _primary(row, sleeved, version, first, slot, game):
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
        LabelHolders=0 if (row.get("Label holders") or "").strip().upper()
        in ("FALSE", "0", "NO", "OFF") else 1,
    )


def load_rows(path):
    """Every parts.csv row but the Parked ones — the one place that status is read."""
    with open(path, newline="") as f:
        return [r for r in csv.DictReader(f)
                if (r.get("Status") or "").strip() != "Parked"]


def game_code(name):
    """The GameName a `--game` argument means, however it is spelt: the
    parts.csv name (`Food Chain Magnate`) or the code (`FCM`), any case."""
    for csv_name, code in GAME_NAME.items():
        if name.lower() in (csv_name.lower(), code.lower()):
            return code
    refuse(f"unknown game {name!r}; one of {sorted(GAME_NAME.values())}")


def cascades(csv_path, game=None, version=CURRENT):
    """[(row, Primary)] for every row at both sleevings, `game` filtered —
    the one row selector every CLI's --game goes through."""
    code = game_code(game) if game else None
    out = []
    for row in load_rows(csv_path):
        for sleeved in (0, 1):
            p = from_row(row, sleeved, version)
            if code and p.GameName != code:
                continue
            out.append((row, p))
    return out
