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
# everything: all names in NAMES x all 5 widths, plus a blank label
.venv/bin/python dominion_labels.py

# specific sets / widths
.venv/bin/python dominion_labels.py --names "Seaside,Renaissance" --widths 20,53

# also write STEP files (e.g. to re-import into Onshape)
.venv/bin/python dominion_labels.py --step

# skip the blank label
.venv/bin/python dominion_labels.py --no-blank

# vanilla 3MF without the Bambu Studio filament metadata
.venv/bin/python dominion_labels.py --plain
```

Output lands in `labels_out/` as `<Name>_<width>mm.3mf`.

Edit the `NAMES` list at the top of `dominion_labels.py` to set your
expansion list (spaces are fine: `"Base Set 1"`, `"Dark Ages"`, ...).

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
| `RAISE_TEXT` / `RAISE_LOGO` | 0.6 | height of the black features above the plate |
| `TAPER` | 45° | chamfer around the base |
| `MARGIN` | 3.6 | logo / "cc" inset from the label edge |
| `LOGO_SIZE` | 4.5 | staircase bounding square (3 steps) |
| `CAP_HEIGHT` | 4.175 | name text capital height |
| `BASELINE_Y` | 10.1 | text baseline, measured from the bottom edge |
| `TEXT_SIDE_MARGIN` | 2.5 | min side gap; long names shrink to fit |
| `CC_XHEIGHT` | 2.5 | height of the "cc" mark |

Values were measured from the original Onshape STEP export. Two
deliberate deviations from that export, chosen per your spec — flip them
back if the original was intentional:

- The STEP measures **22.1** mm tall; the script uses your stated 22.2.
- In the STEP the logo and "cc" are raised only **0.4** mm (text 0.6);
  the script raises everything 0.6 (`RAISE_LOGO = 0.4` restores it).

The name text is set in Orbitron **Bold** (weight 700 matches the
original's stroke widths exactly), horizontally centred, on a fixed
baseline. Names too wide for a label shrink uniformly to fit.
