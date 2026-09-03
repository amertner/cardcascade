# The Holder, measured

The card tray that rides the box's slider ribs. One per riser; a cascade's
holders form a staircase, and their sloped tops make one continuous diagonal
when the cascade is open. `automation/plan_exports.holder` is the design record
for WHY it is keyed the way it is; this file is the geometry.

## The ten references

Hand-exported from the Onshape UI, so 0 API calls, in `spec/reference/`, and
all ten are asserted against. Nothing is held out any more — see "`210 Card`
disagreed with its own sibling" below for the one that was.

| file | row | n | risers | sleeved | `calSlotwidth` | `calSliderDistance` | `calHeightIncrement` |
|---|---|---|---|---|---|---|---|
| `Holder S2.40.12-30.45-Sl.step` | Dominion `246 Card` | 3 | 2 | yes | 65.000 | 9.600 | 16.000 |
| `FirstHolder S2.40.12-30.45-Sl.step` | the same row's first riser | 3 | 2 | yes | 65.000 | **20.400** | 16.000 |
| `Holder S9.21.10.62-Sl.step` | Dominion `333 Card` | 3 | 9 | yes | 65.000 | 8.400 | 9.667 |
| `Holder M5.10.10.45-Sl.step` | Innovation `4 Later Ages` | 4 | 5 | yes | 69.000 | 8.900 | 17.400 |
| `Holder M5.10.10.32-Un.step` | the same row, unsleeved | 4 | 5 | no | 67.000 | 6.400 | 17.400 |
| `Holder XS5.15.10.45-Sl.step` | Innovation `Single Mini` | **2** | 5 | yes | 69.000 | 8.900 | 17.400 |
| `Holder S4.7.7.32-Sl.step` | Compile `105 Card` | 3 | 4 | yes | 70.000 | 8.000 | 18.000 |
| `Holder S4.18.12.32-Un.step` | FCM `198 Card` | 3 | 4 | no | 63.000 | 6.960 | 20.000 |
| `Holder L5.7.7.45-Sl.step` | Compile `210 Card` — RE-EXPORTED | **5** | 5 | yes | 70.000 | 8.000 | 17.400 |
| `Holder L5.7.7.20-Un.step` | the same row, unsleeved — RE-EXPORTED | **5** | 5 | no | 68.000 | 5.200 | 17.400 |

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

The **last five close the parameter space**. Between them they add every
remaining slot width (`63`, `68`, `70`), both remaining compartment counts (`2`
and `5`), and the two games that had no reference at all — and the one thing
that looked like a broken rule turned out to be a pair of mis-configured
exports. Every rule in this file is now checked at 2, 3, 4 AND 5 compartments,
at all five slot widths, in all four games, both sleevings, and against both
slider distances.

## The frame

    X   0 at the centre of the FIRST compartment, +k * calSlotwidth for the rest
    Y   0 at the REAR face, NEGATIVE going forward
    Z   0 is a datum inside the card pocket; the base sits at -45.250 on every
        reference, whatever the parameters

The sense of `Y` is fixed by `Rear lip`, below: Onshape calls that group the
REAR lip and its tabs stand at `Y > 0`, so `Y = 0` is the rear face and the
slant descends toward the front. (An earlier revision of this file had it the
other way round in this block and the right way round everywhere else.)

## What is settled

### The overall envelope

    width  = calSlotwidth * HorizontalSlots + 9.800
    depth  = sliderDistance - 0.400
    base   = Z -45.250

`9.800` is `2 * 4.900`: each end stands `4.900` beyond the outer slot edge, of
which `4.000` is the end block that carries the side slot and `0.900` closes the
gap to the first compartment wall. Exact on all ten references, and on the 20
cached components exported since the studio trimmed it — see "`individual/` is a
mixed catalogue" for the 30 that still say `5.000`.

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

## `Card holder bottom`: what a 1.000-spaced probe could not see

**Superseded — see "`Card holder bottom` drops the floor `0.200`" below.** Kept
because the reasoning is the instructive part: the reading was not careless, it
was made with a probe too coarse to see the feature, and it looked like proof.

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

## `210 Card` disagreed with its own sibling — RESOLVED, it was the export

**The row holds 7 cards per rising slot (Allan), and BOTH holders have been
re-exported.** They measure `7.600` sleeved and `4.800` unsleeved — the plain
rule under each card thickness, exactly:

| holder | `calCardThickness` | `calSliderDistance` | rule | measured | cards |
|---|---|---|---|---|---|
| `210 Card` Sl | 0.800 | 8.000 | 7.600 | **7.600** | **7.00** |
| `210 Card` Un | 0.400 | 5.200 | 4.800 | **4.800** | **7.00** |

So both original exports were configured with a `Cards/Riser slot` of 12, and
the depth formula never had an exception in it. That is the outcome the
`105 Card` export had already argued for by satisfying the rule when its sibling
did not, and it is why no override was written for the row while the question
was open.

The pair also earns its place beyond settling this. Five compartments is a count
nothing else in the reference set reaches, and the unsleeved one is the only
reference at `calSlotwidth 68.000`. Every rule in this file is now checked at 2,
3, 4 AND 5 compartments and at all five slot widths.

Both files are the re-exports; the old 12-card exports are in git history, not
on disk. The reasoning that got here is kept below, because what it rules out is
the useful part: the readings that FIT `210` all predicted the wrong answer for
`105`, and that is what said the fault was in the files rather than in the rule.

### How it was read while it was open

The table below is the FIRST exports. Both have since been replaced on disk by
re-exports that land on the rule.

Adding Innovation XS (2 compartments), FCM (`calSlotwidth 63.000`, rise
`20.000`) and Compile (`68.000` and `70.000`, 3 and 5 compartments) closed every
axis of the parameter space. All of them pass on the standard rule — **including
Compile's `105 Card`**, whose slider distance is `8.000` and depth `7.600`,
exactly `CardsPerSlidingSlot = 7` cards.

`210 Card` does not:

| holder | `n` | `calCardThickness` | depth | implied cards | row says |
|---|---|---|---|---|---|
| `105 Card` Sl | 3 | 0.800 | **7.600** | **7.00** | 7 |
| `210 Card` Sl — superseded | 5 | 0.800 | 11.600 | **12.00** | 7 |
| `210 Card` Un — superseded | 5 | 0.400 | 6.800 | **12.00** | 7 |
| `210 Card` Sl — RE-EXPORTED | 5 | 0.800 | **7.600** | **7.00** | 7 |
| `210 Card` Un — RE-EXPORTED | 5 | 0.400 | **4.800** | **7.00** | 7 |

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

**So this is a question about one row, not about the formula**, and nothing was
special-cased for it. An earlier revision of this file recorded a
`COMPILE_DEPTH_CARDS = 12` override; the `105 Card` export killed it, which is
exactly what it was requested for. The likeliest explanation was that the `210`
export had been configured with a `Cards/Riser slot` other than the `7` in
parts.csv — the corpus agreed, since the old `Holder 5x7-r5-Sl.3mf` measures
`8.404`, which is the 7-card rule plus its lip.

That is what it turned out to be, on both files. The lesson to keep: a reference
that fails a rule every other reference satisfies is a question about that
reference first, and holding it out — rather than fitting the rule to it — is
what made the re-exports worth asking for. `tests/test_holder.py` keeps the
`HELD_OUT` list, now empty, for the next time.

## `Bottom Text`, and where it is a DELIBERATE DIVERGENCE

Two blocks engraved `0.200` into the underside, in **two faces**, as the Pusher
has: the name in Orbitron Bold and the capacity in Open Sans Bold. Calculated
ink width against measured, on every reference:

| holder | name | calc / meas | capacity | calc / meas |
|---|---|---|---|---|
| 246 Sl | `CC 7.0 - Dominion` | 97.230 / 97.231 | `12 Sleeved` | 50.967 / 50.947 |
| 333 Sl | `CC 7.0 - Dominion` | 81.025 / 81.026 | `10 Sleeved` | 42.472 / 42.456 |
| Inno M Sl | `CC 7.0 - Innovation` | 94.981 / 94.982 | `10 Sleeved` | 46.012 / 45.994 |
| Compile 105 | `CC 7.0 - Compile` | 70.684 / 70.685 | `7 Sleeved` | 35.444 / 35.436 |
| FCM 198 Un | `CC 7.0 - FCM` | 45.328 / 45.328 | `12 Unsleeved` | 40.888 / 40.876 |

The second font is what the ink width identifies: the capacity block is `42.456`
wide on `333`, which is `10 Sleeved` in Open Sans (`42.472`) and nothing like it
in Orbitron (`51.342`).

The name is `CC <version> - <GameName>` — `GameName`, so FCM engraves its short
form. The capacity is the holder's OWN card count, so the first-riser holder
shows `FirstSlidingSlotCards`. Both are inset `10.000` past the end blocks, the
name left-aligned and the capacity right, matching Allan's sketch dimension.

### The size

Onshape's rule is **cap height = `depth - 2.000`**, and it reproduces every
reference to a thousandth. It also takes no account of how long the strings are,
and Onshape can constrain a text box in one dimension only, so on a short or a
deep holder the two blocks run into each other:

| holder | Onshape size | blocks' ink | room | |
|---|---|---|---|---|
| 246 Sl | 10.000 | 148.2 | 176.8 | fits |
| 333 Sl | 8.333 | 123.5 | 176.8 | fits |
| **FirstHolder 246** | **25.000** | **370.5** | **176.8** | **2.1x over** |
| **Innovation XS** | **9.028** | **141.0** | **119.8** | **1.2x over** |

`FirstHolder 246` is the one Allan flagged: 7 runs of ink against a legible
holder's 23, two of them `46.3` and `62.3` wide — whole words fused into bars —
and `5.8x` the ink volume.

So the size is the **lesser** of Onshape's and one that makes both blocks fit.
That changes only what was broken: on all five references whose text does not
collide, the depth term is the smaller and the result is Onshape's size exactly,
to `1e-4`. On the two that do, the build's blocks are separated where the STEP's
overlap — and the test asserts both directions, so a future Onshape fix would
fail here rather than converging silently.

The baseline is CENTRED on the cap band. The reference's moves with each
string's own ink extents — `0.598` to `1.353` above the back face across the
five — and lands within `0.4` of centre; with the size already a divergence,
centring is the rule that stays sensible when it binds.

## `individual/` is a mixed catalogue, and its own provenance cannot say so

Overall width is `calSlotwidth * n` plus a constant, and the 50 corpus holders
that map to a parts.csv row split cleanly:

     +9.800  x20
    +10.000  x30

All ten STEPs are `+9.800`, including `Holder S9.21.10.62-Sl` whose corpus twin
`Holder S-21-r9-Sl.3mf` is `+10.000` and otherwise identical to the micron. So
`+9.800` is current and the 30 are stale — the same shape of problem as the
pushers' 18/14, and `tests/test_holder_corpus.py` reproduces the 20 and MOVES
the 30.

**The split is exactly the export DATE**, from `automation/state/<Game>.csv`:

    ..2026-08-20 18:47   +10.000  x30
      2026-08-24 12:55.. +9.800   x20

and every one of the 50 is recorded at studio version **6.6**. This is the
unversioned change `automation/PIPELINE.md` already records under "An
unversioned CAD change is invisible to provenance": Allan's fix for holders that
users reported sticking, rolled out deliberately without a `VERSIONS["Holder"]`
bump so that it folds into whatever gets re-exported next. Holders of both
lengths coexisting is intended, and `PROV.is_current` cannot tell them apart —
`--changed Holder` is the lever, when someone wants them swept.

PIPELINE.md dated it off the SPANNING holders' `X-min` alone (`-38.5000` ->
`-38.4000`, five files). It is the same `0.100` a side on all 50, per-slot games
included, and the width constant is the whole of it.

For `cad/` this decides only which number to build: `4.900` is what all ten
STEPs measure and what the studio has now.

The engraved version is a SEPARATE axis, and the two must not be conflated.
Every cached holder engraves `CC 6.6` — measured as ink width against
`cad/text.py`, exact to a thousandth on all five sampled, including the ones
exported on 2026-08-31 — while every hand-exported STEP engraves `CC 7.0`. So
the studio's version variable moved after the last of these exports.

**Everything is 7.0 now, and on the Holder the bump changed NOTHING but the
embossed number (Allan).** That is what licenses the corpus regression to build
at `Version="6.6"` and compare like for like: the only thing 7.0 moves on this
part is the string, exactly as it is for the TokenHolder
(`spec/TOKENHOLDER.md`).

It also means the end-block trim is not the version bump wearing a disguise.
Two changes happened in sequence and only one of them was versioned:

    unversioned, ~2026-08-22   END_EXTRA 5.000 -> 4.900   GEOMETRY
    the 6.6 -> 7.0 bump        `CC 6.6` -> `CC 7.0`       the embossed string

A cached holder can therefore be old in one sense and current in the other, and
30 of the 50 are: they carry the 6.6 string like all the rest, and the 5.000 end
block that only the pre-trim ones have.

**One consequence is still open, and it is `automation/`'s, not this part's.**
`onshape_config.GENERATIONS["7.0"]` still reads `"Holder": "6.6"`. Moving it to
`"7.0"` would be correct about the studio AND would make `PROV.is_current` call
all 50 cached holders stale at once — which is the sweep deferred above, arriving
by a side door. The same applies to `TokenHolder` and `Topper`, both also pinned
at `6.6` in that table. Whoever bumps them should mean to.

**The difference is the end block and nothing else.** Set the 30 against the
build and every other coordinate agrees to the micron — depth, height, the lip's
reach, where the part sits — with X in by `0.100` at each end and the volume
down by `0.25%` to `1.10%`, which is what those two slivers of end block weigh.
The test asserts that, rather than a width: a stale file that had also moved its
lattice or its lip would pass a width check and fail this one.

## Where it stands

`python -m cad.build --part holder` writes all 56, about three seconds each,
and every one of them is a closed, manifold mesh. Against all ten references the
geometry is **+257.5 mm³ on 261,657**, `+0.098%`, and all but a few cubic
millimetres of that is the DELIBERATE text divergence on the two holders whose
Onshape text collides with itself:

| | mm3 |
|---|---|
| text, on the two holders Onshape engraves too big | **+253.40** |
| `Chamfer lip rest`, shape error | +17.56 |
| everything else, over all ten | +0.01 |
| boolean loss in the measurement itself | -13.50 |
| net | **+257.47** |

Set the text aside and the whole of the rest is `+17.6 mm³` — `+0.007%`, spread
over ten holders, and per holder it is the same order as the arithmetic's own
noise. `tests/holder_diff.py` is the dev loop that prints this band by band, the
last column included.

## The four features a volume diff found, in the order it found them

Each of these was invisible to the check that had been made of it, and each was
found by taking the difference against a reference rather than by probing where
the feature was expected to be. That is the transferable part.

### `Card holder bottom` drops the floor `0.200`

An earlier revision of this file said the feature needed no code. That was wrong,
and wrong for an instructive reason: the check probed at `-43.750` and `-42.750`,
which straddle a step at `-43.450`, so a `1.000`-spaced probe could not see a
`0.200` feature. The diff found it at once — one lump per compartment, exactly
the pocket's footprint by `0.200`, `63.400 * 7.600 * 0.200 = 96.368` on `246`.

`pocket_z` still returns the UNDROPPED datum, because that is what the `Hole
outline` sketch's `2.000` inset is measured from.

### The scallop stops at the back wall

The reference keeps the back wall whole behind the finger hole — it is what
holds the cards in. Sampling only the front wall cannot see this, and on a steep
holder like `246` the slant has already removed the back wall at the scallop's
height, so even a volume diff stays silent. `333`, the shallowest rise in the
catalogue, is the only reference where that wall still reaches up there.

### `Lip Rest` is an OBLIQUE prism

A REMOVE: the lip's face, extruded along `LipPlane` "through all" from a start
of `#calSlotDepth * 2`. Three things about it are measured rather than assumed.

**The direction is along the slant.** On `333` the cut first meets material at
`Y -7.668`, and `2 * calSlotDepth = 12.000` taken along the slant from `Y = 0`
lands at `-7.673`.

**It is oblique, not a right prism.** The lip's face lies in the plane `Y = 0`
and is swept along a direction that is not its normal, so every cross-section at
constant `Y` is that same upright rectangle translated. Building it as a rotated
box puts the near face `0.769` further forward in `Y` and `0.6` low in `Z` —
both visible on `333`, and the difference between an over-cut of `103` and one
of `14`.

**"Through all" is literal.** The removed volume stops changing once the sweep
passes about `20`, and every longer value gives the same solid.

### `Chamfer lip rest` is `1.500` at 45 degrees, on the LOWER pair

Allan's dialog gives the size; which two edges it takes, and whether the rest
carries any clearance, are measured. The section is a HEXAGON, not a rectangle —
`width` at the top and `width - 2 * 1.500` at the bottom — and the rest is
EXACTLY the lip's own base width with no clearance at all:

| model | residual in that band |
|---|---|
| plain rectangle, `0.300` clearance a side | `-66.32` |
| chamfered on the UPPER pair, `0.300` clearance | `-25.59` |
| chamfered on the LOWER pair, `0.300` clearance | `-14.66` |
| **chamfered on the LOWER pair, NO clearance** | **`-4.88`** |

The same dialog confirms `Chamfer lip` at `1.200`, which was already measured
off the lip's own taper.

Three earlier readings of this chamfer were tried and rejected before the
dialog arrived, and are recorded so they are not tried again: a constant width
(the slivers are four different widths), a constant taper along the sweep (the
width falls with depth but not linearly in either the sweep or `Y`), and the
lip's TIP width rather than its base — which predicts the sliver widths well,
`1.026 / 0.892 / 0.635 / 0.610` against `0.977 / 0.850 / 0.600 / 0.580`
measured, and was tempting enough to build, but made every measurable case
worse.

A residual of about `+/-5 mm3` per holder remains in that band, mixed in sign
where it was uniformly negative before — roughly a tenth of what it was, and
smaller than the unexplained term already carried. It is not zero and is not
claimed to be.

## Completeness, band by band

Volume alone can hide errors that cancel, and once the text is built the
boolean diff is unreliable — OCCT fails to clean it on five of the eight and
returns the whole solid. Comparing INTERSECTIONS band by band does work
(`tests/holder_diff.py`), and gives this, in mm³, positive meaning the build has
more material there:

| holder | total | text | base | body | rests | lips | residual |
|---|---|---|---|---|---|---|---|
| 246 Sl | -0.006% | +0.48 | -0.00 | -0.00 | -0.02 | +0.00 | -1.91 |
| 246 1st | +0.559% | **+230.73** | +0.00 | +0.07 | -5.73 | -0.00 | -2.10 |
| 333 Sl | -0.005% | +0.90 | -0.00 | +0.01 | -1.21 | +0.00 | -0.82 |
| Inno M Sl | -0.007% | +1.55 | +0.00 | -0.01 | +1.60 | -0.00 | -5.28 |
| Inno M Un | +0.011% | +0.75 | -0.00 | +0.00 | +4.74 | -0.00 | -2.76 |
| Inno XS | +0.093% | **+15.99** | -0.00 | -0.00 | +0.80 | -0.00 | -0.20 |
| Compile 105 | +0.005% | +0.72 | -0.00 | -0.02 | +2.23 | +0.00 | -1.69 |
| FCM 198 Un | +0.052% | +0.28 | -0.00 | +0.00 | +3.79 | -0.00 | +5.48 |
| Compile 210 Sl | +0.007% | +1.49 | -0.00 | -0.02 | +3.34 | -0.00 | -2.43 |
| Compile 210 Un | +0.024% | +0.51 | -0.00 | -0.02 | +8.02 | -0.00 | -1.80 |

The base, the body and the lips are exact on all ten — the `body` column is
hundredths of a cubic millimetre across a part of twenty thousand. The `text`
column is exact on the six holders whose text fits, and carries the deliberate
divergence on the two that do not.

**`residual` is the method's own error, and it is why `rests` is not quoted as
a measurement.** The five bands tile the part, so they have to add up to the
whole difference; what is left over is volume the intersections lost. It is not
symmetric — cut a single shape into the same bands and the BUILD loses `0.27`
every time while the imported STEP loses between `1.1` and `5.5`, which is where
almost all of it comes from. So this table resolves the `+230` and the `+16` in
the `text` column, and it does not resolve `rests`. The honest statement about
`Chamfer lip rest` is that its shape error is of the order of a few cubic
millimetres a holder, mixed in sign — the same conclusion the chamfer's own
section reaches by a different route, which is the only reason to believe it.

**Every feature in the tree is built, and the part is printable.** What is left
is a few cubic millimetres of shape error in the lip rest, and the text
divergence, which is intended.

## The mesh, and one thing OCCT gets wrong at a tangency

A valid solid is not yet a printable file. Two of the 56 written holders — FCM's
`M5.6.6.20-Un` and `L3.18.6.20-Un`, the two shallowest in the catalogue — came
out with 64 and 80 NON-MANIFOLD edges, while Onshape's own 850 cached bodies
have none anywhere.

The solids were valid (`BRepCheck_Analyzer`, one solid, one shell). The fault
was in the meshing, and specifically in the weld: OCCT triangulates each face
separately, `Fillet 1`'s torus is TANGENT to the rear face, and where the slant
passes through that tangent point as well the two faces' triangulations land
within the `1e-6` weld key. The same three vertices then come out twice, wound
opposite ways — a zero-thickness flap, which is exactly the thing a slicer calls
non-manifold.

`cad/mesh3mf._drop_flaps` removes both members of such a pair. They enclose
nothing, so the volume is unchanged to `1e-11`, and the surface closes. All 56
written holders are now closed and manifold, which
`tests/test_holder_corpus.py` asserts on every run.

### Two faults it does NOT fix, found by the same scan

Sweeping all 800 written bodies for the same thing turns up two more, both
outside the Holder and neither of them a flap. **They are recorded here because
this is where the scan was written, not because they belong to this part.**

| what | where | reading |
|---|---|---|
| six edges with FOUR triangles on them | `Box M5.10.10.45-Sl`, `S5.10.10.45-Sl`, `XS5.15.10.45-Sl` — Innovation, sleeved, and only these three | a line contact: two surfaces meeting along `x -95.050, y 28.200` rather than crossing. Not a hole |
| 24 UNPAIRED edges, i.e. an open boundary | `Part 2`, `Part 3` and `Part 4` of `Lid S3.15.10.20-Un`, `S3.15.10.32-Sl`, `XS5.15.10.32-Un`, `XS5.15.10.45-Sl` — 12 inlay bodies | a missing face: a closed loop of boundary edges on the flat at `z 0.800`. A real hole in a printed body |

Onshape's own 850 cached bodies have neither, so both are the writer's or the
solid's and not the design's. The lid one is the more serious — an open
boundary is a hole a slicer has to guess at, where a line contact usually
prints.

## The feature names that carry no geometry

Allan on each, and what the rebuild does about it — nothing, in every case, and
that is now a statement rather than an absence of evidence:

- **`Leftmost Pusher Pos`** is roughly where the pusher touches the holder when
  it is in use, and has no other use. A reference position, not a feature: it
  removes and adds nothing, so `cad/parts/holder.py` has no counterpart and
  should not grow one.
- **`Remove Slant Angle`** is what makes the top of the holder diagonal rather
  than flat. `shell` builds that slant into the section it sweeps, rather than
  cutting a flat top and then removing a wedge — same solid, one operation
  instead of two, and it is why `slant_z` appears as two corner heights.
- **`Remove little front lip`** is Allan's hack for making the WHOLE top
  diagonal: the top used to carry a `1.000` flat lip at the front, and this
  removes it. So the current part has no flat there at all, which is what
  `shell` builds — the slant runs to the front face. Worth knowing if an older
  export ever turns up with a `1 mm` flat at the front: that is a pre-hack
  holder, not a defect.
**`Middle`** was not asked about and is not explained. It sits next to `Mid
plane` and `Mirror Side` in the tree, which makes a construction plane for the
mirrors the obvious guess — but that is a guess, and it is written here as one.
The rebuild mirrors about `Plane.YZ` directly.

The band-by-band table is the check on all of them: within what it resolves, a
feature of more than a few cubic millimetres has nowhere left to hide.

## Still open

- **Nothing about the geometry, and nothing about the references.** All ten are
  asserted against, the parameter space is closed on every axis, and every
  feature in the tree is built.
- Whether the 30 pre-2026-08-24 cached holders should be swept onto `4.900`.
  **Left as they are for now (Allan).**
  Not a rebuild question — the rebuild already builds `4.900` — but the two
  lengths do coexist in shipped cascades, and PIPELINE.md says that is
  deliberate. `--changed Holder` is what sweeps them if that ever changes.
- Whether the row rail stays `2.000` at another `CardHeight`. Not answerable and
  not a risk: `derive` gives `CardHeight = 92.0` for EVERY game, and the only
  other value the studio ever had was CraftGutermann's `58.0`, which is
  deprecated and gone. (An earlier revision of this file said `Colours` was the
  exception. `Colours` differs in `BoxHeight` and `LidHeight`, not in the card.)
