#!/usr/bin/env python3
"""Test: set the Primary Variable Studio for one cascade via the Onshape API.

Builds the FULL set of Primary input variables for a chosen cascade (default:
Innovation "270 Card", sleeved) from parts.csv and POSTs them in ONE call. This
is the Stage-2 variable step: because we specify every primary input, no GET of
current state is needed. Inputs not distinguished by parts.csv (Version) get
sensible defaults.

NOTE: the POST replaces the studio's variable set, so this assumes the 10
Primary inputs below are the COMPLETE set (as seen in the screenshots). If the
studio has more, they would be dropped — recoverable via Onshape version
history. Run --dry-run first to review the exact body; it makes 0 API calls.

Usage:
    set_variables.py "<Primary variable-studio URL>" --dry-run   # 0 calls; prints body
    set_variables.py "<url>"                                     # 1 POST call (270 Sl Innovation)
    set_variables.py "<url>" --game Dominion --name "560 Card" --unsleeved
"""
import argparse
import csv
import json
import sys
from pathlib import Path

import onshape as O

HERE = Path(__file__).parent


def col(row, name):
    return (row.get(name) or "").strip()


def var(name, vtype, expression, description):
    return {"name": name, "type": vtype, "expression": expression,
            "description": description}


def build_primary(row, sleeved, game_name=None):
    """The full Primary variable set for one cascade (parts.csv row + sleeving).
    Numbers are unitless expressions; GameName/Version are quoted strings.

    game_name overrides the GameName variable sent to Onshape (the model expects
    the short code, e.g. "FCM", not the parts.csv "Game" full name "Food Chain
    Magnate"). Defaults to the row's Game column when not given."""
    first = col(row, "Cards/First Riser")
    slot = col(row, "Cards/Riser slot")
    override = 1 if first else 0
    merged = 1 if col(row, "Merged-slot").upper() == "TRUE" else 0
    return [
        var("HorizontalSlots", "NUMBER", col(row, "Horizontal"),
            "Number of horizontal card slots in a row"),
        var("RisingSliders", "NUMBER", col(row, "Risers"),
            "Number of rising rows of cards"),
        var("FrontPocketCardCapacity", "NUMBER", col(row, "Front capacity"),
            "How many cards should fit in front pocket"),
        var("CardsPerSlidingSlot", "NUMBER", slot,
            "Number of cards in each sliding slot"),
        var("isFirstSlidingSlotOverride", "NUMBER", str(override),
            "1, if the first sliding slot is different from the rest"),
        var("FirstSlidingSlotCards", "NUMBER", first or slot,
            "If isFirstSlidingSlotOverride, capacity of that slot"),
        var("isSleeved", "NUMBER", "1" if sleeved else "0",
            "0 or 1, indicating unsleeved or sleeved"),
        var("MatPocket", "NUMBER", str(merged),
            "1, if two front pockets should merge"),
        var("GameName", "ANY", f'"{game_name or col(row, "Game")}"',
            "Changes logo, height increment and card size"),
        var("Version", "ANY", '"6.5"',                  # current CC design
            "Version number to be printed on box and lid"),
    ]


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("url")
    ap.add_argument("--game", default="Innovation")
    ap.add_argument("--name", default="270 Card",
                    help="Short name in parts.csv (default '270 Card')")
    ap.add_argument("--unsleeved", action="store_true",
                    help="build the unsleeved variant (default: sleeved)")
    ap.add_argument("--csv", default=str(HERE / "parts.csv"))
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    sleeved = not args.unsleeved

    with open(args.csv, newline="") as f:
        rows = [r for r in csv.DictReader(f)
                if col(r, "Game") == args.game
                and col(r, "Short name") == args.name]
    if len(rows) != 1:
        sys.exit(f"{len(rows)} rows match game={args.game!r} name={args.name!r} "
                 f"in {args.csv} (need exactly 1)")
    body = build_primary(rows[0], sleeved)
    label = f"{args.name} {'Sl' if sleeved else 'Un'} {args.game}"

    if args.dry_run:
        ytd = O.read_cumulative()
        print(f"DRY RUN — would POST {len(body)} Primary variables for "
              f"[{label}] in ONE call:\n")
        print(json.dumps(body, indent=2))
        print(f"\nExpected: 1 call. Year-to-date {ytd}/{O.ANNUAL_LIMIT} "
              f"({O.ANNUAL_LIMIT - ytd} left).")
        return

    did, wtype, wid, eid = O.parse_url(args.url)
    stem = f"/d/{did}/{wtype}/{wid}/e/{eid}"
    O.begin()
    auth = O.creds()
    O.api(auth, "POST", f"/api/variables{stem}/variables", "set-primary",
          json=body)
    print(f"Set Primary variables for [{label}] ({len(body)} variables).")
    print(O.budget_line())


if __name__ == "__main__":
    main()
