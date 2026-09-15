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
    # `tests/test_holder_corpus.py` prices its engraving at an explicit
    # `Version="6.6"`.
    Version: str = CURRENT
    # cad/ only — see the module docstring. 1 is what every shipped box has;
    # 0 leaves the front and side label holders off (`box.label_holders`).
    LabelHolders: int = 1
    # cad/ only. parts.csv's `Sleeved card width` column: the width a SLEEVED
    # card of this row is given, in mm, where the studio adds 2.000 to the
    # game's unsleeved width. 0 is the studio's rule. One row uses it:
    # `Three Expansions` at 64, so its sleeved twin is as wide as its
    # unsleeved one and still lies flat in the Innovation box.
    SleevedCardWidth: float = 0.0
    # cad/ only, and the mirror of the above (`rev.unsleeved_card_width`).
    # parts.csv's `Unsleeved card width` column: the width an UNSLEEVED card
    # of this row is given, in mm, where the studio takes the game's own. 0 is
    # the studio's rule. One row uses it: `Single Mini` at 66, the sleeved
    # width, so its unsleeved twin is as wide as its sleeved one — which is
    # what makes four pushers fit the back, and what makes the pair's two lids
    # interchangeable.
    UnsleevedCardWidth: float = 0.0
    # cad/ only. Which back the Box is built with, and NOT read from a row:
    # `build.back_pocket_variants_built` says which variants a row ships and
    # `build.back_pocket_twin` sets this, as `LabelHolders` is set for the
    # plain box twin. "" is the studio's rear storage; see
    # `tables.BACK_POCKET_VARIANTS` and `box.storage_slot_count`.
    BackPocket: str = ""
    # cad/ only. parts.csv's `Deep slot` column: `back` puts the deeper
    # first-riser slot (`Cards/First Riser`) at the BACK of the cascade
    # instead of the studio's front. On Innovation it holds the expansion's
    # achievements and player aids, wanted once at setup, so the least stable
    # riser is the one used least. Meaningless without an override, and blank
    # (or `front`) is the studio's own.
    DeepSlotAtBack: int = 0


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
        SleevedCardWidth=_float(row, "Sleeved card width"),
        UnsleevedCardWidth=_float(row, "Unsleeved card width"),
        DeepSlotAtBack=_deep_slot(row),
    )


def _deep_slot(row):
    v = (row.get("Deep slot") or "").strip().lower()
    if v in ("", "front"):
        return 0
    if v == "back":
        return 1
    short = (row.get("Short name") or "?").strip()
    raise ValueError(f"parts.csv row {short!r}: Deep slot {v!r} is not front, "
                     f"back or blank")


def _float(row, col, default=0.0):
    v = (row.get(col) or "").strip()
    return float(v) if v else default


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
