# Dominion Expansion Box Labels

Generates the expansion-name labels as **two-colour 3MF files** (white
chamfered base plate + black raised name/logo/"cc"), replicating the
original Onshape design. One command produces every name in every size.

## Setup (macOS)

```bash
cd cardcascade
python3 -m venv .venv
.venv/bin/pip install build123d
```

That's it — `Orbitron-Bold.ttf` is bundled (Google Fonts, OFL licence).

> Note: use this bundled *static* Bold TTF. The variable-weight
> `Orbitron[wght].ttf` that Google Fonts' "Download family" button gives
> you crashes the OpenCascade text engine that build123d uses.

## Usage

```bash
# individual label files for every NAMES entry of the default game (Dominion)
.venv/bin/python dominion_labels.py

# multi-plate Bambu project 3MFs (whole sets + split-box labels)
.venv/bin/python dominion_labels.py --plates

# one 3MF per set (default / split boxes / spares plates) in labels_out/sets/
.venv/bin/python dominion_labels.py --sets

# another game (its own NAMES entries and width lists)
.venv/bin/python dominion_labels.py --game FCM --plates

# specific sets / widths
.venv/bin/python dominion_labels.py --names "Seaside,Renaissance" --widths 32,53

# also write STEP files (e.g. to re-import into Onshape)
.venv/bin/python dominion_labels.py --step

# skip the blank label
.venv/bin/python dominion_labels.py --no-blank

# vanilla 3MF without the Bambu Studio filament metadata
.venv/bin/python dominion_labels.py --plain
```

Output lands in `labels_out/` as `<Name>_<width>mm.3mf`, or as
`<game>_plates.3mf` with `--plates`.

Each game in the `GAMES` dict at the top of the script defines the
label widths for a set (`widths`), for split-box `<name> 1/2` labels
(`split_widths`), and the standard text size per width (`caps`,
capital height in mm). Dominion: 156.4 (front), 80, 53, 32 for sets
(splits skip the 80) at 6.5/5.0/4.5/3.5 mm caps; FCM: 45, 30, 20 at
4.5/3.5/2.8 mm.

## The NAMES file

When `--names` is not given, the script reads the set list from a
`NAMES` file (looked up in the current directory, then next to the
script). One set per line as `<game>,<set name>[,<key>=V]...`, where
every value `V` is `<unsleeved>[/<sleeved>][@<box name>:<box model>]`
— label widths per sleeving (one value = both) plus the optional
recommended-box identity, which appears in the `--sets` plate titles
(e.g. `Base Set, Sleeved (560 Card, L6.12.40-Sl)`). Only lines
matching `--game` are used:

| Field | Meaning |
|---|---|
| `box=V` | the whole set's box; presence means the set gets whole-box labels |
| `split=V` | both split half-boxes; presence means the set gets `<name> 1/2` labels |
| `split1=V`, `split2=V` | like `split=` but for half-boxes of different sizes (must appear together) |
| none | line is skipped |

Widths are validated against the game's standard width lists — a
non-standard width is an error. (Rule of thumb: the label must be at
least 14 mm narrower than the box lid's depth; pick the largest
standard width that fits.) The special name `(BLANK)` stands for the
blank label (logo + "cc", no text). Blank lines and lines starting
with `#` are ignored:

```
Dominion,Base Set,box=53/80@560 Card:L6.12.40,split=53@300 Card:S5.12.40
Dominion,Alchemy,box=32@168 Card:S4.10.16
FCM,Occupations,split1=30/45@264 Card:M4.12.18,split2=20@180 Card:L3.6.18
FCM,Milestones,box=20/30@144 Card:M5.6.6
```

If there is no NAMES file either, the built-in `NAMES` list at the top
of `dominion_labels.py` is used.

## Per-set project files (`--sets`)

`--sets` writes one Bambu project per set into `<out>/sets/`, using
the recommendations from the NAMES file. Labels are stacked one above
the other, centred on the plate. Each file has up to five plates:

1. **single cascade (unsleeved)** — box front (156.4 for Dominion)
   plus the unsleeved `box=` side label
2. **single cascade (sleeved)** — the same with the sleeved width
3. **split cascade (unsleeved)** — front + side for `<name> 1` and
   `<name> 2` (always two fronts and two sides)
4. **split cascade (sleeved)** — the same with the sleeved widths
5. **"... spares"** — every other label from the full width matrix

Sleeved/unsleeved plates that would be identical are collapsed into
one, so a set like Alchemy (`box=32`) has just two plates.

## The multi-plate project files (`--plates`)

`--plates` writes the game's labels into two Bambu Studio projects
spread across 256x256 P1S plates: `<game>_sets_plates.3mf` with every
whole-set label, and `<game>_splits_plates.3mf` with the `<name> 1/2`
split-box labels. Every set gets an identical block of label rows
(widest row on top, e.g. front+80 over 53+32 for Dominion sets), with
a vertical gap between sets, flowing bottom-up through the plates in
NAMES order. Blocks avoid the P1's no-print corner and the top strip
of each plate is left free for the wipe tower. Plates are named after
the full list of sets they carry. The
files embed `bambu_project_settings.config` (printer/filament profile,
prime tower enabled, one wipe tower position per plate), so they open
ready to slice with black in slot 1 and white in slot 2. To refresh
that profile, save any project from your own Bambu Studio and copy its
`Metadata/project_settings.config` over `bambu_project_settings.config`.

## Slicing

Each 3MF contains one object with two parts: `base` (white) and
`raised` (black). The file embeds Bambu Studio / OrcaSlicer project
metadata assigning `raised` to filament 1 and `base` to filament 2, so
it opens two-coloured — just load black in slot 1 and white in slot 2.
(Bambu ignores standard 3MF colours; without this metadata everything
lands on filament 1, which is why the file used to open single-colour.)

For other slicers, `--plain` writes a vanilla 3MF instead: the two
parts import as one object and you assign a filament to each part by
hand. On a single-extruder printer, add a filament change at
z = 0.6 mm — all black geometry is above that height.

## Parameters (top of the script, all in mm)

| Parameter | Value | Meaning |
|---|---|---|
| `LABEL_HEIGHT` | 22.2 | overall label height |
| `WIDTHS` | 20, 32, 53, 80, 156.4 | the five label widths |
| `BASE_THICKNESS` | 0.6 | white plate thickness |
| `RAISE_TEXT` | 0.6 | height of the name text above the plate |
| `RAISE_LOGO` | 0.4 | height of the logo and "cc" above the plate |
| `TAPER` | 45° | chamfer around the base |
| `MARGIN` | 3.6 | logo / "cc" inset from the label edge |
| `LOGO_SIZE` | 4.5 | staircase bounding square (3 steps) |
| `TEXT_GAP_ABOVE_LOGO` | 2 | gap between the logo top and the text bottom |
| `TEXT_TOP_MARGIN` | 3 | min gap between the text top and the label top edge |
| `CC_XHEIGHT` | 2.5 | height of the "cc" mark |

Values were measured from the original Onshape STEP export (which is
22.1 mm tall; the script uses the specified 22.2).

The name text is set in Orbitron **Bold** (weight 700 matches the
original's stroke widths exactly) at the game's standard capital
height for the label's width (`caps`), so same-width labels look
uniform. Names too long for their box — flush with the logo's left
edge and the "cc"'s right edge, 2 mm above the logo, at least 3 mm
below the top edge — shrink to fit. Text is centred horizontally and
bottom-anchored.
