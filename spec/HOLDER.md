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

| `Holder M5.10.10.45-Sl.step` | Innovation `4 Later Ages` | 4 | 5 | yes | 8.900 | 17.400 |
| `Holder M5.10.10.32-Un.step` | the same row, unsleeved | 4 | 5 | no | 6.400 | 17.400 |

The 246 pair is the useful one for `first`: it is ONE configuration exported
twice, so the two differ only in what `first` changes, and its
`calSliderDistance` and `calFirstSliderDistance` differ by more than a factor of
two. The 333 holder is the same cascade whose Box and Pusher are already
references, and its rise is the catalogue's shallowest.

The **Innovation pair is what makes the rest general**. Everything measured on
the Dominion three was confirmed at `calSlotwidth 65.000` and three compartments
only; these are a SPANNING game at `69.000` and `67.000` with FOUR, and the
whole suite reproduces them with no change to any rule. So the width formula,
the slant, the pocket, the lattice at two more slot widths, the scallop with its
modelled fillet, and the side slot are all confirmed across two games, four slot
widths and both compartment counts. Whatever distinguishes a spanning game, it
is not any of these.

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

`44.250` is exactly half the `88.500` pocket, so the upper slant meets the rear
face at the top of the card pocket. Both intercepts are the same numbers on
every holder whatever the slope, which is what makes them a datum rather than a
coincidence.

The `2.000` separation is **`#LipHeight`** (Allan). It was measured here as the
gap between the two planes before the variable was known, and the two agree —
which is the only confirmation either has. Its whole purpose is the rear lip,
whose section is the band between them. Note this is NOT the lip's `2.100`
reach along the slant, which remains an unnamed constant.

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

### The lattice column is a FIXED `10.000`, and the mullion absorbs the rest

`#LipLength` is a constant `10 mm` (Allan), and `Vertical slits in holder` uses
it for the window width. The three STEPs cannot show this on their own — all
three are Dominion sleeved at `calSlotwidth 65.000` — so it was checked against
the corpus instead, probing the front wall's own plane at a rail's Z, where the
only vertices are the window corners:

| game | `calSlotwidth` | pitch `(W+2)/5` | measured gaps |
|---|---|---|---|
| Dominion Sl | 65.00 | 12.2 | `10.0 2.2 10.0 2.2 10.0 2.2 10.0 2.2 10.0` |
| Innovation Un | 67.00 | 12.6 | `10.0 2.6 ...` |
| Compile Un | 68.00 | 12.8 | `10.0 2.8 ...` |
| Innovation Sl | 69.00 | 13.0 | `10.0 3.0 ...` |
| Compile Sl | 70.00 | 13.2 | `10.0 3.2 ...` |

Five slot widths, three games, and the window is `10.000` every time. So the
mullion is `pitch - 10.000` and is **not** the rows' `2.000` rail.

The pattern is LEFT-ALIGNED on the outline. Five windows and four mullions come
to `4 * pitch + 10`, against an outline of `5 * pitch - 2`, so `pitch - 12.000`
is left over on the right — `0.2` on Dominion, `1.2` on Compile sleeved. That
asymmetry is the reference's and is reproduced, not corrected.

## `Finger Cutouts` is a `12.000` circle on the slant top

One per compartment, on its centre, and its centre sits exactly on the UPPER
slant plane at the front face — so its lowest point is

    slant_top - 12.000 = 32.250

which is one of the constant Z-planes on all three references whatever the depth
or the rise.

**The radius is `12.000` and not the `12.400` the circular edges report.** This
is the Box's thumb trap again, and for the same reason: `Fillet 1` puts `0.400`
on each face, the wall is `0.800`, so the two fillets meet in the middle and
consume the cylindrical face entirely. Every scallop surface in the STEP is a
TORUS — a scan for cylinders above `Z 20` finds none — and the only circular
edges are the fillets' outer boundaries at `12.400`.

Sectioning at the wall's mid-depth recovers the true circle. Fitting one from
the near-face profile does not, and drifts: `R` reads `11.71` at `x = 3` and
`11.93` at `x = 10`. At mid-depth the residual against `R = 12.000` centred on
`44.250` is `0.010 / 0.023 / 0.060 / 0.093` at `x = 3 / 6 / 10 / 11`, which is
exactly the probe window's `0.080` times the local slope `x / sqrt(R^2 - x^2)` —
an artefact of the measurement, not of the model. The test therefore compares
the STEP and the build as PROFILES sampled the same way, rather than fitting a
radius at all.

### `Fillet 1` is MODELLED, because no kernel will compute it

There is exactly **one torus face per scallop**, centred at `y = -0.400` — the
front wall's mid-depth — and nothing on the back wall. So `Fillet 1` rounds the
FRONT wall's scallop edges only, and because that wall is `2 * 0.400` thick the
rounds from its two faces merge into that single torus.

`fillet(..., 0.400)` fails on all three references. That is not a build123d
quirk: a fillet whose two sides meet exactly is degenerate for any kernel. So
the rounding is built INTO the cut instead — the bead is the annulus between
`12.000` and `12.400` across the front wall, less the torus the fillet rolls. At
the face the torus reduces to a point so the hole is the full `12.400`; at
mid-wall it fills the annulus so the hole necks to `12.000`.

Checked by sampling ACROSS the wall rather than by a bounding box, which is
where a wrong bead would show and an envelope would not:

| y | x = 0 | x = 6 | x = 11 |
|---|---|---|---|
| `-0.05` | 32.090 | 33.696 | 39.153 |
| `-0.15` | 32.184 | 33.805 | 39.381 |
| `-0.40` | 32.250 | 33.881 | 39.547 |

STEP and build agree at every one, on both holders, and the built torus count
matches the reference's.

## The side slot is the BOX's rib, and the two parts agree

`Side slot solid` / `Side slot` / `Side slot hole` / `Mirror Side`. Measured on
the holder alone: `1.900` wide, centred on the holder's **mid-depth**, `4.000`
deep from each end, full height — the slant is what stops it, and it already
has. Identical on all three references whatever the depth (`-5.550..-3.650` at
`9.200`, `-10.950..-9.050` at `20.000`, `-4.950..-3.050` at `8.000`).

Set against `cad/parts/box.py`, measured independently on the other part:

| box | | holder | |
|---|---|---|---|
| `SLIDER_W` | `1.500` | `SLOT_W` | `1.900` → `0.200` clearance a side |
| `SLIDER_PROUD` | `4.000` | `END_BLOCK` | `4.000` → the same |

Neither was fitted to the other, so this is a real cross-part check and the test
asserts it as one.

## `Card holder bottom` needs no code

The base is already right. Probing a compartment's centre finds material at
`-44.750` and `-43.750` and none at `-42.750` or `-41.750` on all three
references — exactly the `2.000` left between the base at `-45.250` and the card
pocket's bottom at `-43.250`, which `shell` and `card_pockets` already produce.
Whatever the feature does in the studio's own order, the final solid matches.

The `Z -41.250` plane is NOT a floor, which is what it looked like at first: its
area is exactly `240.00` on every holder, and that is the bottom face of the
first window row — `10.000 x 0.800` per window, five columns, two walls, three
compartments.

## `Rear lip`, and what the second slant plane is for

Two tabs per compartment, standing proud of the `Y = 0` face — which is what
fixes the frame's sense: Onshape calls this group the REAR lip, so `Y = 0` is
the REAR face and the slant descends toward the front.

**In section they are the band between the two slant planes.** That is the only
thing the lower plane does, and it is why it exists. Their top rides the upper
plane extended past `Y = 0`, so the whole holder's `Z` maximum is
`slant_top + slope * reach` rather than `slant_top`.

**They reach `LIP_REACH = 2.100` ALONG the slant**, not in `Y`. Measured `Y`
against `Y * sqrt(1 + slope^2)`:

| holder | slope | `Y` reach | along the slant |
|---|---|---|---|
| 246 Default | 1.7857 | 1.026 | **2.100** |
| 246 First | 0.7812 | 1.655 | **2.100** |
| 333 Default | 1.2037 | 1.342 | **2.100** |
| Innovation Sl | 2.1299 | 0.892 | **2.100** |
| Innovation Un | 3.1538 | 0.635 | **2.101** |

In plan the flat runs `|x| 15.400 .. 25.400` from the compartment's centre —
`#LipLength` long, starting `#LipDistanceFromFingerHole` out from the scallop's
own filleted edge at `FINGER_R + FINGER_FILLET = 12.400`. Both of Allan's sketch
numbers land exactly. `Chamfer lip` then widens the base by `1.200` a side at 45
degrees in `Y`.

**The chamfer is not truncated at the base.** Where the lip is shorter in `Y`
than `1.200` the chamfer plane simply runs out of lip; it does not start closer
in. The base is `12.400` on all five references whatever the reach. Modelling it
the other way leaves the base `12.052` and is invisible to the bounding box, the
reach AND the tip width — all three stay right — and shows up only in the lip
volume. So the test compares per-solid volumes, not envelopes.

## `210 Card` disagrees with its own sibling, and the rule stands

Adding Innovation XS (2 compartments), FCM (`calSlotwidth 63.000`, rise
`20.000`) and Compile (`68.000` and `70.000`, 3 and 5 compartments) closed every
axis of the parameter space. All of them pass on the standard rule — **including
Compile's `105 Card`**, whose slider distance is `8.000` and depth `7.600`,
exactly `CardsPerSlidingSlot = 7` cards.

`210 Card` does not:

| holder | `n` | `calCardThickness` | depth | implied cards | row says |
|---|---|---|---|---|---|
| `105 Card` Sl | 3 | 0.800 | **7.600** | **7.00** | 7 |
| `210 Card` Sl | 5 | 0.800 | 11.600 | **12.00** | 7 |
| `210 Card` Un | 5 | 0.400 | 6.800 | **12.00** | 7 |

Both `210` holders are `12.00` cards deep in a game whose other row is exactly
`7.00`, and `12` is a whole number under both thicknesses, so it is a CARD COUNT
and not an offset. The files are the rows they claim: widths of `359.800`,
`349.800` and `219.800` are `calSlotwidth * n + 9.800` for 5, 5 and 3
compartments at `70.000`, `68.000` and `70.000`, and `210`'s rise of `17.400` is
`(105 - 18)/5`, so its `HorizontalSlots` and `RisingSliders` are both confirmed
as `5` independently of the depth.

Three readings were tried and all three are dead. A flat `12`, and
`CardsPerSlidingSlot` plus either `HorizontalSlots` or `RisingSliders`, all fit
`210` — `7 + 5` twice over — and all three predict `12`, `10` and `11` for
`105`, which measures `7`.

**So this is a question about one row, not about the formula**, and nothing is
special-cased for it. An earlier revision of this file recorded a
`COMPILE_DEPTH_CARDS = 12` override; the `105 Card` export killed it, which is
exactly what it was requested for. The likeliest explanation is that the `210`
export was configured with a `Cards/Riser slot` other than the `7` in parts.csv
— the corpus agrees the geometry changed, since the old `Holder 5x7-r5-Sl.3mf`
measures `8.404`, which is the 7-card rule plus its lip.

The two `210` references are held out in `tests/test_holder.py`, not deleted,
and the suite prints their measured depth against the rule on every run.

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
- The tabs between the scallops.
- `Lip Rest` and `Chamfer lip rest`: a REMOVE, extruding the lip's own faces
  through all along `LipPlane` from a starting offset of `#calSlotDepth * 2`.
  Measured on the references but not yet built.
- `Leftmost Pusher Pos` — what it positions.
- Whether the row rail stays `2.000` at other card heights; only `CardHeight
  92.0` has a reference.
- `Remove little front lip`, `Remove Slant Angle`, `Middle`.
- **`210 Card`'s depth**: 12 cards where the row says 7 and its sibling
  measures 7. See above. Needs the row's real `Cards/Riser slot`, or a
  re-export.
- The row rail's `2.000` at another `CardHeight`. Every reference is `92.0`,
  and only `Colours` is not.
