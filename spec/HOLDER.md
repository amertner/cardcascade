# The Holder, measured

The card tray that rides the box's slider ribs. One per riser; a cascade's
holders form a staircase, and their sloped tops make one continuous diagonal
when the cascade is open. `automation/plan_exports.holder` is the design record
for WHY it is keyed the way it is; this file is the geometry.

## The three references

Hand-exported from the Onshape UI, so 0 API calls, in `spec/reference/`:

| file | row | n | risers | sleeved | `calSliderDistance` | `calHeightIncrement` |
|---|---|---|---|---|---|---|
| `Holder S2.40.12-30.45-Sl.step` | Dominion `246 Card` | 3 | 2 | yes | 9.600 | 16.000 |
| `FirstHolder S2.40.12-30.45-Sl.step` | the same row's first riser | 3 | 2 | yes | **20.400** | 16.000 |
| `Holder S9.21.10.62-Sl.step` | Dominion `333 Card` | 3 | 9 | yes | 8.400 | 9.667 |

The 246 pair is the useful one: it is ONE configuration exported twice, so the
two differ only in what `first` changes, and its `calSliderDistance` and
`calFirstSliderDistance` differ by more than a factor of two. The 333 holder is
the same cascade whose Box and Pusher are already references, and its rise is
the catalogue's shallowest.

## The frame

    X   0 at the centre of the FIRST compartment, +k * calSlotwidth for the rest
    Y   0 at the front face, NEGATIVE going back
    Z   0 is a datum inside the card pocket; the base sits at -45.250 on every
        reference, whatever the parameters

## What is settled

### The overall envelope

    width  = calSlotwidth * HorizontalSlots + 9.800
    depth  = sliderDistance - 0.400
    base   = Z -45.250

`9.800` is `2 * 4.900`: each end stands `4.900` beyond the outer slot edge, of
which `4.000` is the end block that carries the side slot and `0.900` closes the
gap to the first compartment wall. Measured on all three, exact.

**`sliderDistance` here means the holder's OWN**: `calSliderDistance` for the
standard holder and `calFirstSliderDistance` for the first-riser one. The 246
pair settles it — `9.600 - 0.400 = 9.200` and `20.400 - 0.400 = 20.000`, both
exact — and no other row could, because everywhere else the two are equal.

### `Top slant angle` is the Box's lip angle

Read off the slant face's normal, so there is no probe to get wrong:

| holder | measured `dZ/dY` | `(HInc-1)/(calSlider-1.2)` | `(HInc-1)/(calFirst-1.2)` |
|---|---|---|---|
| 246 Default | **1.7857** | **1.7857** | 0.7812 |
| 246 First | **0.7812** | 1.7857 | **0.7812** |
| 333 Default | **1.2037** | 1.2037 | 1.2037 (equal) |

So the rise is always `calHeightIncrement - 1.000` and the run is the holder's
own `sliderDistance - 1.200`. The two candidates are 2.3x apart on the 246 pair;
there is nothing marginal in it.

`cad/parts/box.lip_slope` is the reciprocal of this — `0.8308` against the 333
holder's `1.2037` — which is what Allan meant by "the same angle as the diagonal
holder cutout". Note the Box uses `calFirstSliderDistance` unconditionally and
is right to: the box's lip sits against the FIRST holder.

**There are TWO parallel slant planes, `2.000` apart.** Aggregating the sloped
faces by (slope, intercept) finds both on every reference:

| holder | `dZ/dY` | Z at `Y = 0` | area | Z at `Y = 0` | area |
|---|---|---|---|---|---|
| 246 Default | 1.7857 | **44.250** | 763.8 | **42.250** | 251.8 |
| 246 First | 0.7812 | **44.250** | 721.6 | **42.250** | 197.9 |
| 333 Default | 1.2037 | **44.250** | 643.6 | **42.250** | 172.1 |

`44.250` is exactly half the `88.500` pocket, so the upper slant meets the front
face at the top of the card pocket, and `Z = 0` is the pocket's centre. Both
intercepts are the same three numbers on all three holders whatever the slope,
which is what makes them a datum rather than a coincidence.

This is the trap in measuring the slant from wall tops: the front wall's top is
on the `44.250` plane on all three, but which plane the BACK wall's top lands on
differs, so a front-minus-back reading gives the right ratio on the 333 holder
and a wrong one on both 246 holders. Aggregate the face normals; do not subtract
wall tops.

### The card pocket and the lattice

The `Hole outline` sketch sits on the face of `Hole for cards`, inset `3` each
side, `2` from the bottom and `#calHeightIncrement + 10mm` from the top. That
makes the pocket face

    88.500 = CardHeight - 3.5

on every holder — `calMaxPocketHeight`'s first term, and constant because the
`calHeightIncrement` in the top inset cancels the one in the height:

    HoleOutlineHeight = 76.500 - calHeightIncrement
    HoleOutlineWidth  = calSlotwidth - 6.000

The outline's bottom is the top of the floor, `Z -41.250`. `Vertical slits in
holder` then divides it into **three window rows** of `(H - 6)/3`, separated and
topped by `2.000` rails, and **five columns** at `(W + 2)/5` pitch. Predicted
against measured, all five rail faces, both rises:

    246  H = 60.500  window 18.167   rails -23.083 -21.083 -2.917 -0.917 17.250
    333  H = 66.833  window 20.278   rails -20.972 -18.972  1.306  3.306 23.583

exact in both.

## The engraved text is a DELIBERATE DIVERGENCE

Onshape can constrain a text box in one dimension only — the same limitation
`spec/PUSHER.md` records — and on the deep first-riser holder it fails outright.
Measured as the void in a `1.200` slab above the base:

| holder | lumps | runs of ink | volume | widest run |
|---|---|---|---|---|
| 333 Default | 25 | 23 | `59.0 mm3` | `6.0` |
| 246 Default | 25 | 23 | `84.3 mm3` | `5.7` |
| **246 First** | **8** | **7** | **`340.4 mm3`** | **`62.3`** |

Two of the First holder's runs are `46.3` and `62.3` wide: whole words fused
into solid bars, `5.8x` the ink of the others. The cause is in the numbers — the
glyph size tracks the bar's depth, `20.000` against `9.200`, a `2.17x` jump, and
ink area goes as the square. The string is scaled up until it overruns its own
length and the letters collide.

Allan: "hopefully we can make this work better out of Onshape." So the rebuild
sizes the text by rule from real glyph metrics (`cad/text.py`, already doing
this for the Pusher and the Box) rather than reproducing the collision, and the
tests assert it from both ends so it cannot silently converge back.

Engraving depth is `0.200` on all three.

## `individual/` is a mixed catalogue, again

Overall width is `calSlotwidth * n` plus a constant, and the 38 corpus holders
that map to a parts.csv row split cleanly:

     +9.800  x20
    +10.000  x18

All three STEPs are `+9.800`, including `Holder S9.21.10.62-Sl` whose corpus
twin `Holder S-21-r9-Sl.3mf` is `+10.000` and otherwise identical to the micron.
So `+9.800` is current and the 18 are stale — the same shape of problem as the
pushers' 18/14, and the regression should reproduce the 20 and MOVE the 18.

## Still open

- Where the slant plane sits, not just its slope.
- The scalloped top: `Finger Cutouts`, and the tabs between the scallops.
- `Side slot solid` / `Side slot` / `Side slot hole` — the `1.900` slot in the
  `4.000` end block that takes the box's `1.500` rib.
- The whole `Rear lip` group (12 features), including `#LipLength = 10`.
- `Leftmost Pusher Pos` and `Horizontal capacity` — the compartment pattern.
- `Remove little front lip`, `Remove Slant Angle`, `Middle`.
- Whether any of this differs for the spanning games (Compile, Innovation),
  which have no reference yet.
