"""Primary — the ten Onshape variable-studio inputs, and how a parts.csv row
becomes them.

Exactly the variables `automation/set_variables.build_primary` POSTs, plus the
few `cad/` adds that Onshape has no input for (each marked below). Everything
else is computed in `derive.py`.
"""
from dataclasses import dataclass
import csv

from .refuse import refuse
from .revisions import CURRENT

# parts.csv "Game" -> the GameName the Onshape model expects. FCM is the one
# that differs; the rest are identical.
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
    # The RELEASE this part is built to. It picks the GEOMETRY (through
    # `derive` -> `d.rev`) as well as the `CC <v>` stamp, so anything compared
    # against `individual/` or a reference STEP must pass "7.0".
    Version: str = CURRENT
    # cad/ only — see the module docstring. 1 is what every shipped box has;
    # 0 leaves the front and side label holders off (`box.label_holders`).
    LabelHolders: int = 1
    # cad/ only. parts.csv's `Sleeved card width`: the width a SLEEVED card of
    # this row is given, where the studio adds 2.000. 0 is the studio's rule.
    SleevedCardWidth: float = 0.0
    # cad/ only, the mirror of the above (`rev.unsleeved_card_width`).
    # parts.csv's `Unsleeved card width`: the width an UNSLEEVED card of this
    # row is given, where the studio takes the game's own.
    UnsleevedCardWidth: float = 0.0
    # cad/ only. Which back the Box is built with, and NOT read from a row:
    # `build.back_pocket_twin` sets it, as `LabelHolders` is set for the plain
    # box twin. "" is the studio's rear storage.
    BackPocket: str = ""
    # cad/ only. parts.csv's `Deep slot` column: `back` puts the deeper
    # first-riser slot at the BACK instead of the studio's front. Meaningless
    # without an override; blank (or `front`) is the studio's own.
    DeepSlotAtBack: int = 0


def _int(row, col, default=0):
    v = (row.get(col) or "").strip()
    return int(v) if v else default


def from_row(row, sleeved, version=CURRENT):
    """One parts.csv row + a sleeving -> Primary. Mirrors build_primary(). A
    malformed row NAMES itself: the ValueError carries its Short name."""
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
    with open(path, newline="") as f:
        return [r for r in csv.DictReader(f)
                if (r.get("Status") or "").strip() != "Parked"]


def game_code(name):
    """The GameName a `--game` argument means, however it is spelt: the
    parts.csv name or the code, any case."""
    for csv_name, code in GAME_NAME.items():
        if name.lower() in (csv_name.lower(), code.lower()):
            return code
    refuse(f"unknown game {name!r}; one of {sorted(GAME_NAME.values())}")


def cascades(csv_path, game=None, version=CURRENT):
    """[(row, Primary)] for every row at both sleevings, `game` filtered — the
    one row selector every CLI's --game goes through."""
    code = game_code(game) if game else None
    out = []
    for row in load_rows(csv_path):
        for sleeved in (0, 1):
            p = from_row(row, sleeved, version)
            if code and p.GameName != code:
                continue
            out.append((row, p))
    return out
