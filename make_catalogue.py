"""Write CATALOGUE.md: every cascade in one place, for a reader who has a game
that is NOT one of ours and wants to know whether a cascade fits it.

Every number is the CAD's: the rows are parts.csv through `cad.derive`, the
external sizes the same formulas the posters print (`make_posters.values`),
the model codes `calModelName`. `catalogue.json` holds the words around them
and the links out (MakerWorld, one per game or per cascade).

    .venv/bin/python make_catalogue.py            # writes CATALOGUE.md
    .venv/bin/python make_catalogue.py --check    # exits 1 if it is stale
    .venv/bin/python make_catalogue.py --reddit   # outreach/catalogue-reddit.md too

The Reddit version is the pinned r/cardcascade post, for a game that is NOT
one of the four (Allan, 2026-09-26): every project a row, grouped by slot
width, the pocket and slot DEPTHS in mm (a capacity is a depth divided by
one game's card thickness); no code spans, no GitHub link. Its prose is
Allan's, written in the file: the generator owns what follows the
`REDDIT_MARK` heading, and `--check` compares only that.
"""

import argparse
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from cad import assembly as A, derive as D, params, tables as T   # noqa: E402
from cad.parts import lid as LID                                    # noqa: E402
from cad.revisions import CURRENT                                   # noqa: E402

CSV = ROOT / "automation" / "parts.csv"
SPEC = ROOT / "catalogue.json"
OUT = ROOT / "CATALOGUE.md"
REDDIT = ROOT / "outreach" / "catalogue-reddit.md"
REDDIT_MARK = "## Complete configuration catalogue"


def fmt(x, decimals=0):
    """A size, rounded UP: a reader wants to know that it fits."""
    q = 10 ** decimals
    v = math.ceil(round(x * q, 6)) / q
    return f"{v:.{decimals}f}"


def model_code(d):
    """`calModelName` spelled the way the shipped file names spell it:
    `M4.21.10.32-M-Un`, hyphens before the flags and none of the studio's `/`."""
    m = d.calModelName
    m = m.replace("/", "-")
    for tail in (".Un", ".Sl"):
        if m.endswith(tail):
            m = m[:-3] + "-" + tail[1:]
    return m


def per_slot(d):
    riser = (f"{d.CardsPerSlidingSlot}/{d.FirstSlidingSlotCards}"
             if d.isFirstSlidingSlotOverride else str(d.CardsPerSlidingSlot))
    return f"{d.FrontPocketCardCapacity} / {riser}"


def height(d):
    return fmt(D.WallThickness + d.BoxHeight)


def footprint(d):
    return f"{fmt(d.BoxWidth + LID.WIDTH_OVER_BOX)} x {fmt(d.calLidDepth, 1)}"


def size(d):
    return f"{footprint(d)} x {height(d)}"


def model_url(spec, game, short):
    """The family's MakerWorld model page, a row's own if it has one; None
    where the family is not on MakerWorld yet, "" for the collection."""
    urls = spec["makerworld"]
    return urls.get(f"{game}/{short}", urls.get(game))


def link(spec, game, short):
    url = model_url(spec, game, short)
    if url is None:
        return "_not on MakerWorld yet_"
    if url:
        return f"[MakerWorld]({url})"
    return f"[MakerWorld collection]({spec['makerworld_collection']})"


def profile_links(spec, game, short):
    """One link per sleeving: the print profile where `profiles` names one,
    the model page otherwise."""
    url = model_url(spec, game, short)
    if url is None:
        return "_not on MakerWorld yet_"
    base = url or spec["makerworld_collection"]
    prof = spec.get("profiles", {}).get(f"{game}/{short}", {})
    out = []
    for slv, word in (("Un", "unsleeved"), ("Sl", "sleeved")):
        pid = str(prof.get(slv) or "").strip()
        if pid.startswith("http"):
            out.append(f"[{word}]({pid})")
        elif pid:
            out.append(f"[{word}]({base}#profileId-{pid})")
        else:
            out.append(f"[{word}]({base})")
    return " / ".join(out)


def load():
    """[(game code, row, derived unsleeved, derived sleeved)] in parts.csv order."""
    spec = json.loads(SPEC.read_text())
    pairs = {}
    order = []
    hidden = set(spec.get("hidden", []))
    for row, p in params.cascades(str(CSV), version=CURRENT):
        d = D.derive(p)
        if d.GameName in hidden:
            continue
        key = (d.GameName, row["Short name"])
        if key not in pairs:
            pairs[key] = [row, None, None]
            order.append(key)
        pairs[key][2 if d.isSleeved else 1] = d
    return spec, [(k[0], *pairs[k]) for k in order]


def family_table(spec, rows):
    out = ["| Family | Unsleeved card, up to | Sleeved card, up to | Card thickness the capacities assume | Box height | Designed for | Files |",
           "|---|---|---|---|---|---|---|"]
    for game, fam in spec["families"].items():
        firsts = [(r, u, s) for g, r, u, s in rows if g == game]
        if not firsts:
            continue
        r, u, s = firsts[0]
        un = f"{fmt(u.calCardwidth)} x {fmt(A.card_height(u))} mm"
        sl = f"{fmt(s.calCardwidth)} x {fmt(A.card_height(s))} mm"
        thick = (f"{T.TEN_UNSLEEVED_THICKNESS[game] / 10:.2f} mm unsleeved, "
                 f"{T.TEN_SLEEVED_THICKNESS[game] / 10:.2f} mm sleeved")
        out.append(f"| **{fam['title']}** | {un} | {sl} | {thick} | {fmt(u.BoxHeight)} mm "
                   f"| {fam['games']} | {link(spec, game, '')} |")
    return "\n".join(out)


def cascade_table(spec, game, rows):
    out = ["| Cascade | Cards | Slots (across x deep) | Cards per slot (pocket / sliding) | Unsleeved: W x D x H mm | Model | Sleeved: W x D x H mm | Model | Printer | Made for | Print profile |",
           "|---|---|---|---|---|---|---|---|---|---|---|"]
    for g, row, u, s in rows:
        if g != game:
            continue
        short = row["Short name"].strip()
        slots = f"{u.HorizontalSlots} x {u.RisingSliders + 1}"
        printer = spec["printers"][(row.get("3D printer") or "").strip()]
        made_for = (spec.get("made_for", {}).get(f"{game}/{short}")
                    or (row.get("Set/Extension") or "").strip())
        label = (row.get("Project label") or "").strip()
        name = f"{short} ({label})" if label else short
        out.append(f"| **{name}** | {u.calTotalCards} | {slots} | {per_slot(u)} "
                   f"| {size(u)} | `{model_code(u)}` | {size(s)} | `{model_code(s)}` "
                   f"| {printer} | {made_for} | {profile_links(spec, game, short)} |")
    return "\n".join(out)


def guide_table(guide, sleeving):
    cols = guide["columns"]
    out = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    for r in guide[sleeving]:
        out.append("| " + " | ".join(r) + " |")
    return "\n".join(out)


def render():
    spec, rows = load()
    games = [g for g in spec["families"] if any(r[0] == g for r in rows)]
    n = len(rows)
    parts = [f"""# Card Cascade catalogue

Every Card Cascade there is, at release **{CURRENT}**: {n} designs, each in an
unsleeved and a sleeved version. This page is generated from the CAD
(`make_catalogue.py`), so the sizes and capacities are the ones the parts are
built to.

A Card Cascade is a 3D-printed **store-and-play** box for a card game. Closed,
it is a labelled box on a shelf. Open, its sliding card holders rise in a
staircase so that every pile shows its top card, ready to play, with the big
piles in front pockets. Each cascade is a complete Bambu Studio project: box
and pushers, lid with the game's logo, sliding holders, an optional token
holder, and slide-in labels as a separate project.

## Does one fit your game?

The cascades were designed for four card sizes, one family each. A cascade
fits a game it was never designed for when:

1. **The card is no bigger than the family's card.** The slots are cut for the
   card sizes below (the slot is 3 mm wider than the card, so a card up to
   about 1 mm wider still slides). Cards may be smaller; they just sit lower
   in the slot.
2. **The cards are no thicker.** Capacities are counted at the thickness
   below. Thicker cards mean fewer per slot, not a jam: a slot holding 10
   cards at 0.38 mm holds about 7 at 0.55 mm.
3. **The pile count fits the slots.** One pile per slot, a big pile per front
   pocket: pick a cascade with at least as many slots as you have piles.
4. **It fits your printer.** Every project is laid out for a named bed; a
   cascade for a 256 mm bed prints on anything larger.

## Families by card size

{family_table(spec, rows)}

"""]
    for game in games:
        fam = spec["families"][game]
        parts.append(f"## {fam['title']}\n\n{fam['blurb']}\n\n{cascade_table(spec, game, rows)}\n")
    g = spec["dominion_guide"]
    parts.append(f"""## Dominion: which cascade for which expansion

Every Dominion expansion has a cascade, or a pair of cascades on a printer with
a 256 mm bed. Sleeved cards are thicker, so more sets split on a standard
printer.

### Unsleeved

{guide_table(g, "Un")}

### Sleeved

{guide_table(g, "Sl")}

The Base Set has 60 Copper, and a front pocket takes 40: split the Copper
across two pockets. The 12-card sliding slots of the Base Set cascades are
for Duchy and Province (12 each) and for the 24 Estates across two slots.
Randomiser cards fit in every cascade.

## Reading a model code

`L8.50.10.62-Sl` says everything about a cascade:

| Part | Meaning |
|---|---|
| `L` | Width in slots across: `XS` 2, `S` 3, `M` 4, `L` 5 |
| `8` | Sliding card holders (rows behind the front pockets) |
| `50` | Cards per front pocket |
| `10` | Cards per sliding slot; `12-30` when the first row behind the pockets is deeper |
| `62` | Width of the side label, mm |
| `-M` | Two front pockets merged for player mats |
| `Sl` / `Un` | Sleeved or unsleeved cards |
| `86-` | A height-class prefix: the box is 86 mm tall instead of 105 |

The same code is on every part, engraved in the box floor and on the lid, so
boxes, lids, holders and pushers always match.

All the listings: the [Card Cascades collection]({spec["makerworld_collection"]}) on
MakerWorld. Questions, requests for another game, and prints:
[r/cardcascade]({spec["reddit"]}). Source and CAD: [{spec["github"]}]({spec["github"]}).
""")
    return "\n".join(parts)


def depths(d):
    """The front pocket's and a sliding slot's stack room, mm, and the first
    sliding row's where it is deeper: the CAD's, thickness x count."""
    pocket = fmt(d.calFrontPocketDepth, 1)
    slot = fmt(d.calSlotDepth, 1)
    if d.isFirstSlidingSlotOverride:
        slot = f"{slot} ({fmt(d.calFirstSlotDepth, 1)} first row)"
    return pocket, slot


def one_profile_link(spec, game, short, d):
    url = model_url(spec, game, short) or spec["makerworld_collection"]
    pid = str(spec.get("profiles", {}).get(f"{game}/{short}", {}).get(
        "Sl" if d.isSleeved else "Un") or "").strip()
    if pid.startswith("http"):
        return pid
    return f"{url}#profileId-{pid}" if pid else url


def reddit_width_tables(spec, rows):
    """One table per slot width, every project a row, widest last. The bed is
    its size and the Bambu range that has it, the height is stated
    once per width, and the thickness is per TEN cards, the stack a reader
    measures with a ruler."""
    bed = {"Standard": "256/P1", "Large": "325/H2", "Mixed": None, "Mini": "180/A1 mini",
           "": "256/P1"}
    by_width = {}
    for g, row, u, s in rows:
        for d in (u, s):
            by_width.setdefault(d.calCardwidth, []).append((g, row, d))
    out = []
    for w in sorted(by_width):
        entries = by_width[w]
        entries.sort(key=lambda e: (e[2].HorizontalSlots * (e[2].RisingSliders + 1),
                                    e[2].calFrontPocketDepth, e[2].calSlotDepth))
        games = sorted({spec["families"][g]["title"] for g, _, _ in entries})
        heights = sorted({height(d) for _, _, d in entries}, key=float)
        tall = (f"All Cascades are {heights[0]} mm tall." if len(heights) == 1
                else f"Cascades are {' or '.join(heights)} mm tall.")
        out.append(f"### Cards up to {fmt(w)} mm wide\n")
        out.append(f"The slot is {fmt(w + 3)} mm; designed for {', '.join(games)}. {tall}\n")
        out.append("| Slots across x deep | Front pocket depth/mm | Sliding slot depth/mm "
                   "| Closed W × D (mm) | 3D Printer bed width / model | Design thickness: mm/10 cards (capacity) | Cascade download link |")
        out.append("|---|---|---|---|---|---|---|")
        for g, row, d in entries:
            short = row["Short name"].strip()
            label = (row.get("Project label") or "").strip()
            name = f"{spec['families'][g]['title']} {short}" + (f" ({label})" if label else "")
            kind = (row.get("3D printer") or "").strip()
            printer = bed[kind] or ("325/H2" if d.isSleeved else "256/P1")
            pocket, slot = depths(d)
            out.append(f"| {d.HorizontalSlots} x {d.RisingSliders + 1} | {pocket} | {slot} "
                       f"| {footprint(d)} | {printer} "
                       f"| {10 * d.calCardThickness:.1f} ({d.calTotalCards} cards) "
                       f"| [{name}]({one_profile_link(spec, g, short, d)}) |")
        out.append("")
    return "\n".join(out)


def reddit_prose():
    """Everything above `REDDIT_MARK` in the file as it stands, heading
    included: hand-written, never generated."""
    if not REDDIT.exists():
        sys.exit(f"{REDDIT.relative_to(ROOT)} is missing: its prose is written by hand")
    head, mark, _ = REDDIT.read_text().partition(REDDIT_MARK + "\n")
    if not mark:
        sys.exit(f"{REDDIT.relative_to(ROOT)}: no '{REDDIT_MARK}' heading; the tables go under it")
    return head + mark


def render_reddit():
    spec, rows = load()
    return reddit_prose() + "\n" + reddit_width_tables(spec, rows)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--check", action="store_true",
                    help="exit 1 if CATALOGUE.md or the Reddit version differs from what would be written")
    ap.add_argument("--reddit", action="store_true", help="also write the Reddit version")
    args = ap.parse_args()
    targets = [(OUT, render())]
    if args.reddit or args.check:
        targets.append((REDDIT, render_reddit()))
    if args.check:
        stale = [p.name for p, text in targets if not p.exists() or p.read_text() != text]
        if stale:
            print(f"stale: {', '.join(stale)}: run make_catalogue.py --reddit")
            return 1
        print("CATALOGUE.md and the Reddit version are current")
        return 0
    for p, text in targets:
        p.write_text(text)
        print(f"wrote {p.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
