# The Box, measured

Allan supplied the part studio's feature tree and the two sketch variables on
2026-09-01, plus five hand-exported STEPs in `spec/reference/` (0 API calls). This
file records the transcription and what it has been checked against; it is the
Box's counterpart to `spec/PUSHER.md`, and is incomplete until `cad/parts/box.py`
exists.

---

## The envelope, exact on all 48 boxes

```
#BoxWidth = #WallThickness*2 + 11.1mm + #calSlotwidth*#HorizontalSlots
#BoxDepth = (6mm + (#RisingSliders-1)*#calSliderDistance
             + #calFirstSliderDistance) + #calFrontPocketDepth
```

Height is `BoxHeight`, `105.00` throughout.

The sketch box is **centred on the origin**: on `Box Compile 105S` the outer
walls are planar faces at `x = ±112.150`, which is `#BoxWidth / 2` for
`224.300`, and the inner walls at `±110.550` — `WallThickness 1.600`, confirmed
rather than assumed.

Both formulas reproduce every one of the 48 boxes in `individual/` exactly, once
two constants are added for the features that stand proud of the sketch box:

| | | over 48 boxes |
|---|---|---|
| measured width | `#BoxWidth + 2.600` | constant |
| measured depth | `#BoxDepth + 6.100` | constant |

Neither offset is symmetric. On `Box Compile 105S` the width runs
`-113.750 .. +113.150` about a box of `±112.150` — `1.600` proud on one side and
`1.000` on the other — and the depth `-23.400 .. +26.300` about `±21.800`, so
`1.600` and `4.500`. Those are the label holders, the closing bumps and the rear
storage; which feature owns which number is still to be measured.

**`#BoxDepth` and `calLidDepth` are the same expression.** `calLidDepth` adds
`8.5` where this adds `6.0`, and then `WallThickness + PusherThickness + 1.0`:

```
calLidDepth - #BoxDepth = 8.5 + 1.6 + 3.0 + 1.0 - 6.0 = 8.100   (exactly, all 48)
```

So the `2.00 mm` in CLAUDE.md's "the box is lid − 2.00 mm on both axes" is the
*measured envelope* — `8.100 - 6.100` — not the sketch, and the two are not
independent formulas that happen to agree.

## The reference STEPs

Hand-exported from the Onshape UI, 0 API calls, in `spec/reference/`.

| file | cascade | envelope | faces | what it splits |
|---|---|---|---|---|
| `Box Compile 105S.step` | Compile 105 Card Sl `S4.7.7.32-Sl` | `226.900 × 49.700` | 1672 | S: 3 slots, 2 pusher slots. Same cascade as the Pusher STEP, so the rim cutouts can be checked against that pusher's tabs |
| `Box Dominion 244S.step` | Dominion 244 Card Sl `M4.21.10.45-Sl` | `276.900 × 58.300` | 1832 | M: 4 slots, 3 pusher slots |
| `Box Dominion 202S Merged.step` | Dominion 202 Card (Mat) Sl, same model code | `276.900 × 58.300` | 1879 | the SAME box with `MatPocket = 1`. Volume `147581.786` against `148340.743` — the merge removes `758.957 mm³` and adds 47 faces |
| `Box Dominion 650S.step` | Dominion 650 Card Sl `L8.50.10.62-Sl` | `341.900 × 109.300` | 2146 | L: 5 slots, deepest box in the catalogue |
| `Box FCM 72S.step` | **not in parts.csv** — see below | `211.900 × 33.700` | 1586 | the smallest box |
| `Box Dominion 246S.step` | Dominion 246 Card Sl `S2.40.12/30.45-Sl` | `211.900 × 66.100` | 1818 | the ONLY reference with a first-riser override — `calFirstSliderDistance 20.400` against `calSliderDistance 9.600` |
| `Box Dominion 246S without final fillet.step` | the same box, `Smooth box edges` suppressed | identical | 1774 | **the build target** — see below |
| `Box Dominion 244U.step` | Dominion 244 Card Un `M4.21.10.32-Un` | `268.900 × 44.880` | 1828 | UNSLEEVED, and 244S's pair-mate, so the diff between them isolates sleeving alone. Every earlier reference was sleeved and half the catalogue had nothing behind it |
| `Box Dominion 244U without final fillet.step` | the same box, fillet suppressed | identical | 1763 | one of the two twins that settled `Lower the front` — see below |
| `Box Innovation 130U.step` | Innovation 130 Card Un `XS5.15.10.32-Un` | `150.900 × 50.100` | 1625 | Innovation, XS and unsleeved at once: the only game with no reference, the only size, and the exception that takes 2 pusher slots where its size would otherwise take 3. It caught the front label holder |
| `Box Innovation 130U without final fillet.step` | the same box, fillet suppressed | identical | 1555 | the second twin |
| `Box Dominion 333S.step` | Dominion 333 Card Sl `S9.21.10.62-Sl` | `211.900 × 100.300` | 1944 | nine risers: the `RisingSliders > 8` logo margin, the lowest rise in the catalogue, and the pusher rest at its floor |

**`Box FCM 72S` is a row parts.csv does not have.** Its envelope solves uniquely
to FCM, sleeved, `HorizontalSlots 3, RisingSliders 3, FrontPocketCardCapacity 6,
CardsPerSlidingSlot 6` — `calModelName` `S3.6.6.20.Sl`, `calCapacityLabel`
`72 Cards/S`, which is where the filename's "72S" comes from. The formulas hit
`211.900 × 33.700` on the nose. Treated as a reference, not as a catalogue row,
until parts.csv says otherwise.

~~No unsleeved and no Innovation box among the five, and neither is needed:
sleeving moves `calCardwidth` and `calCardThickness` only, which reach the box
through `calSlotwidth` and `calSliderDistance` and add no topology; and
Innovation's `isOnlyTwoPusherSlots` M box is topologically the Compile/FCM S
case, which two of the five cover.~~ **Half right, and the wrong half was
expensive.** Unsleeved really does add no topology — `Box Dominion 244U` and
`Box Dominion 333S` both passed every check unchanged the moment they landed.
But the reasoning did not cover XS, and `Box Innovation 130U` found a real
defect on its first run: a box `150.900` wide carrying a `160.000` front label
holder. See "The label holders" below.

## The feature tree, transcribed

In studio order. Sketches are italic in Onshape's tree and marked *(sk)* here;
`(n)` is the feature count Onshape shows for a folder.

```
Create box shape (6)
    #BoxWidth, #BoxDepth
    Top of box (sk) / Extrude solid box / Hollow out box
    Center of box                       (mate connector)
Model name (2)
    Model name (sk) / Model Name        (extrude — text)
Hole in bottom of box (2)
    Bottom slots for pushers (sk) / Remove material for bottom slots
Pusher holder & Rear Storage (19)
    #dBackSlotWidth, #calPusherSlots
    Add depth to back
    Top hole for pusher storage (sk) / Remove material, don't let pushers dr...
    Cut out top of back (sk) / Top of back
    Cover slot (sk) / Divider / Repeat Divider
    Hanging holes (sk) / Extrude 3 / Repeat Hanging Holes
    Make rightmost pocket deeper
    #calFingerHoleOffset
    Thumb Cutout in back (sk) / Remove thumb hole in back / Fillet rear thumb hole
    Pusher Storage                      (mate connector)
Lower the front (2)
    Sketch 1 / Extrude 2
Round top box corners
Sliders (10)
    Slider (sk) / Slider tilt (sk) / Extrude slider / Round top of. slider
    Mirror slider / Replicate sliders
    First Slider (sk) / First Slider / Fillet 1 / Mirror First Slider
Front pocket (13)
    Front divider (sk) / Extrude front divider
    Divider for front pocket (sk) / Divider for front pocket / Additional dividers
    Pad outermost slots (2): Padding on the side of outer slots (sk) / Outermost padding
    #HoleAreaHeight
    Slits in front pocket (sk) / Make holes / Holes in remaining slots
    Angled cutout of front holder (2)
Thumb and Lip (8)
    Import Holder patterns              (derived)
    Thumb (sk) / Remove thumb hole / Fillet thumb hole
    Lip (sk) / Lip (extrude) / Lip (fillet) / Repeat thumb and lips
TokenHolder (0)                         (empty folder)
Logo (5)
    Logo (sk) / #LogoHeight / Capacity (sk) / Rev (sk) / Logo text (extrude)
Closing mechanism (4)
    Side bump (sk) / Extrude 1 / Chamfer 1 / Mirror 1
Tittles (4)                             SUPPRESSED
Front Label Holder (10)
    Name tag left (sk) / Fastener (sk) / Tag holder left / Chamfer 2
    Fastener / Round Fastener / Mirror 2 / Cutout (sk) / Sweep 1
    CentreBottom of Label               (mate connector)
Side Label Holder (6)
    Side Label Holder (sk) / Extrude 7 / Chamfer 3 / Mirror 3
    Side Cutout (sk) / Sweep 2
#SharpEdges                             (query)
Smooth box edges                        (fillet)
```

Every feature in `Front Label Holder` and `Side Label Holder` carries Onshape's
`fx` marker, which the other groups do not — almost certainly conditional
suppression on `isLabelHoldersOnBox`. **Untestable from the catalogue**: that
variable is `0` only for Colours or `HorizontalSlots <= 1`, and no parts.csv row
is either, so every box on disk has both holders. Built always-on unless Allan
says otherwise.

## Variables the tree names that the studio transcription does not

| variable | seen as | reading |
|---|---|---|
| `#dBackSlotWidth` | `37.6 mm` on `M4.21.10.45-Sl` | **`= calPusherTotalDepth + 4.000`, confirmed** — the stored pusher's own depth plus 2.00 of clearance a side. It is the PITCH between rear storage slots; see below |
| `#calPusherSlots` | `3` on the same box | 2 for S and for all Innovation, 3 for M and L. Counted independently off all 48 boxes' rim cutouts (`2 × slots + 1` section loops) and it agrees everywhere — see below |
| `#calFingerHoleOffset` | `162.5 mm` on the same box | **`= (calPusherSlots - 1 + (HorizontalSlots - calPusherSlots)/2) * calSlotwidth`** (Allan). Step right one slot width per pusher slot after the first, then centre the remainder. `cad/parts/box.py` |
| `#HoleAreaHeight` | `68.5 mm` | front-pocket slit height |
| `#LogoHeight` | `2.74 mm` | the Logo text's cap height, as `#LogoTextHeight` is the Pusher's |
| `#SharpEdges` | query | the edge set `Smooth box edges` fillets |

## `components.pushers_for` disagreed with the CAD on Innovation XS — fixed

Counting rim cutouts on all 48 boxes matched `components.pushers_for` everywhere
except `XS5.15.10-Un/Sl`: Innovation's map was `{"S": 2, "M": 2, "L": 3}`, `XS`
was not a key, so it fell through to the default `3` — but the box has **2**
slots, and both built Single Mini projects carry 2 pushers.

**It was latent, not live.** `ctx["pushers"]` reaches only a planner total and
`count` in `manifest.json`, which `make_cascade --count` consumes on a FIRST
build. `refresh_cascades` never sees it: `build_swap` pairs template objects to
files by NAME, and `assemble_one` emits `--part` args only, under
`--keep-layout`. On a first build from an Innovation donor (2 pushers) it would
have failed loudly — `make_cascade` refuses `--count` above the instances it
has; from a 3-pusher donor it would have quietly printed a spare.

Fixed by giving Innovation a flat `"pushers": 2`, which is the shape
`isOnlyTwoPusherSlots` actually has — closing the `XS` hole and the unreachable
`L` entry together. `plan_exports` also learned that `XS` is a two-letter size
(`size = base[0]` made it `"X"`); that renames nothing today, because Innovation's
holders span and `Single Mini` carries no toppers, but `"X"` was a trap for any
future XS file.

**`verify.py --boxes` is the guard.** It counts each box's rim cutouts and
compares with the table — 48 boxes checked, 0 disagree now, and exactly the two
XS boxes flagged when the old map is restored. The table and the CAD are two
copies of one fact; this is what keeps them together.

## The rear pusher storage, and the lock it carries

Read off the rim cutouts of all five STEPs, which span 2 and 3 slots and the
C2, C3 and C5 lock classes. `tests/test_box.py` holds the rule to them.

```
#dBackSlotWidth = calPusherTotalDepth + 4.000          the pitch
slot k centreline = -#BoxWidth/2 + WallThickness + (k + 0.5) * #dBackSlotWidth
```

The slots pack from the **left inner wall**, each centred in its own cell, so
the first sits half a pitch in. Every one of the 14 slot centrelines across the
five references lands on it exactly.

Each slot's two rim cutouts sit at that centreline `± s`, `4.500` wide — the
7.0 catalogue, already in `cad/lock.py` as `BOX_CUTOUT_W`. Measured `4.500` on
all 28 cutouts, and the pairs `2s` apart to `0.00`: `17.00` on the two C3 boxes,
`48.00` on the C5, `10.20` on the C2.

**Probe the back wall, not a plain section.** The end walls and the label
holders run the full depth, so at the cutouts' height a plain `z` section reads
their edges as rim pieces: that is what made the leftmost FCM cutout measure
`4.15` instead of `4.500`. `tests/test_box.py` intersects a thin bar through the
back wall instead.

## The back, in section

Constant on all five references, as offsets from `#BoxDepth/2`:

| from | to | | |
|---|---|---|---|
| `-1.600` | `-0.300` | `1.300` | the back wall — a `1.600` wall with `0.300` eaten by the slot |
| `-0.300` | `+2.900` | **`3.200`** | the pusher slot — `LOCK_STANDARD.md`'s box slot depth, exactly |
| `+2.900` | `+4.500` | `1.600` | the outer back wall |

So **`Add depth to back` adds exactly `4.500` behind the sketch box**, and that
is one half of the `6.100` depth offset. The other `1.600` is at the front, and
the `Front Label Holder` sweep is what stands there — on `Box Compile 105S` it
is a face at `y = -23.400`, `160.000` wide, `z 40.500..64.500`.

The back wall is a **lattice**, not a panel: openings `10.000` wide at a
`13.600` pitch horizontally and `20.833` tall at a `22.833` pitch vertically,
with `2.000` bands between the rows and `3.600` piers between the columns. Three
rows on `Box Compile 105S` (`z 3.000..23.833`, `25.833..46.667`,
`48.667..69.500`), then solid from `69.500` to the rim. The front pocket's back
wall carries the same pattern in a `1.000` panel at `y = -14.600..-13.600`.

## The text is engraved in the FLOOR

Not on a wall. `Model Name` and the `Logo` group cut `0.400` deep into the top
of the `1.600` floor — glyph faces at `z = 1.200` against a floor face at
`1.600` — the same `ENGRAVE` depth the Pusher uses. They sit at the two ends,
outboard of the card slots.

## `Smooth box edges` is a `0.600` fillet, and there is a ground truth for it

Allan exported `Box Dominion 246S` twice, once with the final fillet suppressed.
Diffing the pair settles the one step that could not be reverse-engineered from
a finished solid, because an Onshape edge QUERY has no counterpart in build123d:

| | |
|---|---|
| volume removed | `129.190 mm³` — **0.094 %** of the box |
| faces added | 44 (1774 → 1818) |
| radius | **`0.600`**, from three independent offsets: `105.000-104.400`, `33.500-32.900`, `103.650-103.050` |
| where | 13 sliver chains: the top rim, the `z = 85.000` ledge, and vertical edges on the end walls |

So the build target is the **unfilleted** STEP, and the filleted one validates the
last step on its own. That removes what was the plan's biggest fidelity risk: the
diff against the target is no longer polluted by a fillet, and the fillet is
checked as a `0.600` radius over a named edge set rather than chased as a query.

## `MatPocket` is confined to the front pocket

Allan: it changes the front pocket and the TokenHolder entity, and nothing else.
Consistent with the measurement — `Box Dominion 202S Merged` differs from
`Box Dominion 244S` by `758.957 mm³` and 47 faces, all inside the front pocket.
So the Box's Mat branch is one feature group deep, and `plan_exports`' note that
the merge "resizes the box" is about the pocket, not the envelope: the two share
an envelope to `0.000`.

## `Hole in bottom of box` — one rectangle, and two SIDE FLOORS

Despite the plural in the feature name, the floor carries a single rectangular
through-cut. Measured by subtracting each STEP from the floor slab: on all six
references the removed lump's volume equals its own bounding box **to the last
decimal**, so there is no chamfer, draft or second pocket inside it.

**State it by what is LEFT, not by what goes.** A strip of floor
`calSlotwidth / 2` wide survives at each end — the **side floor** — and it is
there for a reason: the holders rest on it when the box is not in use (Allan).
The cut is everything between the two.

```
side floor = calSlotwidth / 2                             at each end
width      = #BoxWidth - 2*WallThickness - 2*side_floor
           = 11.1 + calSlotwidth * (HorizontalSlots - 1)   centred on X = 0
depth      = from -#BoxDepth/2 + WallThickness + calFrontPocketDepth + 1.000
             to   +#BoxDepth/2 - WallThickness
```

In depth it runs from the back of the front pocket's divider to the inner face
of the back wall, i.e. exactly the sliding card area. It is NOT aligned with the
rear pusher slots, which sit at their own pitch.

| box | width | depth | volume |
|---|---|---|---|
| Compile 105 Sl | `151.100` | `33.800` | `8171.488` |
| Dominion 244 / 202 Sl | `206.100` | `35.400` | `11673.504` |
| Dominion 650 Sl | `271.100` | `69.000` | `29929.440` |
| Dominion 246 Sl | `141.100` | `31.800` | `7179.168` |
| FCM 72 Sl | `141.100` | `19.800` | `4470.048` |

The `1.000` is the front pocket's back wall, measured as a panel at
`y = -#BoxDepth/2 + WallThickness + calFrontPocketDepth` and `1.000` thick. It
lives in `box.FRONT_DIVIDER` until the Front pocket group is written and can own
it.

## `Pusher holder & Rear Storage`, measured

Constant on every reference unless stated. Offsets from `#BoxDepth/2`:

| feature | value | |
|---|---|---|
| `Add depth to back` | `+4.500` | one half of the 6.100 depth offset |
| back wall | `-1.600 .. -0.300`, so `1.300` | a `1.600` wall with `0.300` eaten by the slot |
| pusher slot | `-0.300 .. +2.900`, so **`3.200`** | `LOCK_STANDARD.md`'s box slot depth exactly |
| outer back wall | `+2.900 .. +4.500`, `1.600` | |
| `Top of back` | the storage is capped at `z = 85.000` | only the END WALLS carry on to `BoxHeight` |
| `Remove material, don't let pushers drop through` | the cavity floor — see below | a stored pusher rests there, not on the box floor |
| `Divider` / `Repeat Divider` | `1.600` wide, `z` up to `85.000` | **`n` dividers for `n` slots** — at every boundary except the left inner wall, the last one CLOSING the run on the right |

### The hanging holes do NOT cut the dividers — a deliberate divergence

Onshape cuts each hanging hole as one prism from the card side through to the
outer wall, so it takes the storage dividers with it. Measured, that is not a
near miss:

| | dividers pierced | width lost |
|---|---|---|
| `Box Dominion 244S` | 3 of 3, all **full width** | `4.800` |
| `Box Compile 105S` | 2 of 2 | `2.300` |
| `Box Dominion 246S` | 2 of 2 | `2.300` |
| `Box FCM 72S` | 1 of 2 | `1.600` |
| `Box Dominion 650S` | 1 of 3 | `1.600` |

A fully-pierced divider is severed at every hole row — three cuts through the
`1.600` wall that holds a stored pusher. The holes themselves are wanted; that
is not.

**So `cad/` stops them at the slot band.** The back wall keeps the complete
lattice, and so does the fill below the pusher rest; the dividers stay solid
from the floor to `Top of back`. `box.storage_dividers` names the ranges and
`box._except` takes them out of each hole. On `Box Dominion 244S` it adds
`960 mm³` — `0.6 %`.

This is the **first place `cad/` is knowingly not the reference**, so it is
asserted in both directions: `tests/test_box.py` checks every divider is whole
on the build AND that the STEP pierces at least one, which is what would catch
a future change quietly re-converging on Onshape. `tests/box_diff.py` will show
it as EXTRA, and it is expected there.

### The pusher rest is a formula, and it is NOT `3.000`

```
rest = min(25.000, BoxHeight - calPusherTotalHeight - 0.500)
```

A pusher is stored **on edge and upright**. `#dBackSlotWidth` is its own
`calPusherTotalDepth` plus clearance measured along the box's WIDTH — that is
what makes the slot pitch what it is — so the pusher's *staircase height* stands
vertically. The rest is then placed to bring the top of that staircase to
`0.500` below the rim, where its tabs meet the box rim cutouts, until the
`25.000` cap takes over for a short pusher.

Read off **all 44 canonical Boxes in `individual/`** by ray-probing the meshes
(0 API calls, `verify._meshes` does the loading). Three distinct values, two of
them below the cap, so the formula is pinned and not just fitted:

| `calPusherTotalHeight` | rest | boxes |
|---|---|---|
| `60.000 .. 72.000` | `25.000` | every `R <= 4` box, and `L3.18.6` |
| `80.000` | `24.500` | `S5.40.12`, `M4.18.12`, `S4.18.12` |
| `87.000` | `17.500` | every box where `calHeightIncrement` is clamped |

`87.000` is the ceiling `calHeightIncrement = min(desired, (BoxHeight-18)/R)`
imposes, so `17.500` is the lowest rest any cascade can have.

**This file recorded `3.000` for two stages, and it was a misread.** The probe
went down a hanging hole and found solid from `0.000` to `3.000` — which is real,
but it is the material below the first hole ROW, not the rest. Below the rest
the slot band is a **lattice, not a plug**: the hanging holes cut through it
exactly as they cut the back wall, which is why a hole reads `3.000` and a pier
reads the rest. Probe the strip before the first hole (`HOLE_INSET/2` from the
left inner wall) — always inside the first cavity and never pierced. The
"shelf at `z 23.833..25.000`" this file listed as an open residual was the top
of that lattice all along.

### `Hanging holes` — the lattice through the back

Five per horizontal slot, `10.000` wide, at a pitch of `(calSlotwidth - 2.000)/5`
within a slot; the groups repeat at `calSlotwidth`, so the pier between two slots
is `2.000` wider than the piers inside one. The first hole is `8.300` from the
left inner wall — a constant. They cut through the back wall AND the dividers,
reaching from the card side to the outer wall.

Three rows, also constant (**not** a function of riser count): `z 3.000..23.833`,
`25.833..46.667`, `48.667..69.500` — `20.833` tall with `2.000` between, and the
back solid from `69.500` to the rim.

`tests/test_box.py` reproduces every hole position exactly on all six
references — 15 holes at `HorizontalSlots 3`, 20 at 4, 25 at 5.

**Probe the lattice through a HOLE, not the slot centreline.** On an M box the
pusher slot's centreline lands on a pier, where material runs past the rest and
a vertical profile says nothing about it. That cost a false failure.

### `Thumb Cutout in back` — and what `#calFingerHoleOffset` is measured from

A `ThumbCutoutRadius = 12.000` hole through the **outer back wall only**,
centred on `REAR_TOP` so `Top of back` takes its upper half away, filleted
`0.600` into both faces — not the front thumb's `0.400`, and the wall it cuts
is `1.600` rather than `1.000`.

```
centre X = -#BoxWidth/2 + WallThickness + #calFingerHoleOffset
           + #dBackSlotWidth + 1.600
centre Z = 85.000
```

So **`calFingerHoleOffset` is not measured from the left inner wall** but from
the left edge of the SECOND storage cavity — one slot pitch and one divider in.
Exact on all five references, whose pitches run `22.000` to `71.200`, which is
what separates that reading from a plain offset: a constant would not track the
pitch.

It lands in the empty run to the right of the last divider on every reference,
so it never meets a pusher slot, and it does not touch the `1.300` inner back
wall — that reads as one unbroken piece at this height on all five, in the STEP
and in the build.

**Watch the cutting tool's over-run.** `box.round_hole` runs past each face at
the flared radius so the cut is not coincident with it. The default `5.000`
reached back through the empty slot band and bored a `12.600` hole in the inner
back wall — about `630 mm³` the STEP does not remove. The rear thumb passes
`over=2.000`, which clears the `1.600` wall and stops inside the `3.200` band.

## `Closing mechanism` — a chamfered pad, at a CONSTANT position

```
proud    ClosingBumpDepth = 1.000
Y        -1.750 .. 6.250      8.000 long
Z        87.000 .. 90.000     3.000 tall
chamfer  0.500 on the OUTER face's four edges
```

One on each end wall (`Mirror 1`), identical on every reference.

**Its position is a constant in the box frame**, not measured from either face:
the same `Y` and `Z` on references whose `#BoxDepth` runs `27.600` to
`103.200`.

The chamfer is on the outer face only, so the pad's sides rise square for the
first `0.500` and are cut back over the last `0.500`. That is what makes the
volume `21.4167 mm³` rather than the `24.000` of a plain pad — and the diff had
already measured `21.417` before the feature was written, which is how the
chamfer was identified without a section.

`Make rightmost pocket deeper` needs nothing further: it is the cut this file
already records as "right of the pusher slots the slot band is empty from the
floor up", found empirically at stage 2 before the feature had a name.

## `Lower the front`, and the rim cutouts

The front wall stops at **`z = 68.600`** instead of `BoxHeight`, over the whole
inner width — above it only the two end walls remain, `WallThickness` each.
Measured at exactly `68.600` on all six references.

It is treated as a **constant**, and cannot be shown to be anything else: every
catalogue box has `calPocketHeight 88.5` and `calPocketDrop 8.0`
(`calMaxPocketHeight` is `CardHeight - 3.5 = 88.5` for every game but Colours and
CraftGutermann), so nothing in the derived set varies here and a formula could
not be distinguished from a number.

**The rim cutouts are `5.000` tall, not the `5.25` `LOCK_STANDARD.md` records.**
That file says "box rim cutout `4.50` wide, `5.25` deep (`z 99.75 -> 105.00`)".
On the unfilleted reference they run `z 100.000..105.000`, and a cutout's volume
is exactly `4.500 x 1.300 x 5.000 = 29.250` — the `1.300` being the back wall,
which is all they cut. The width `4.50` is right; the depth is `5.00`. Worth
reconciling with the standard.

They also close the loop on the lock: `tests/test_box.py` now measures the rim
cutouts on the BUILD as well as on the STEP, and they agree exactly on all six —
position, `4.500` width, and the back wall stopping at `100.000` inside a cutout
while reaching the rim beside it.

**Probe the cutout's z-profile at its TOP only.** Whether the profile below is
one interval or several depends on whether that cutout's centre happens to land
on a hanging hole or on a pier, which varies by box. That cost a second false
failure, after the same trap in the rear storage.

## build123d cannot subtract two boxes that share an outer envelope

Worth knowing before the next part. Once the rear storage landed, `cad`'s box and
the STEP shared their **entire** outer envelope — same walls, same `105.000`
height, same `4.500` of added depth — and OCCT's boolean then returns an EMPTY
intersection for two solids that plainly overlap:

* both shapes pass `BRepCheck_Analyzer`;
* each intersects a large box correctly;
* a fuzzy tolerance from `1e-7` to `1e-3` changes nothing;
* `ref - mine` comes back as `ref`, and `ref & mine` as zero volume.

`tests/box_diff.py` slices both shapes into slabs along X and diffs slab by slab,
which works and reconciles with the plain volume difference. A feature straddling
a slab boundary is then reported as two lumps — the cost of the workaround.

**Lump sizes there are indicative; positions are what the tool is for.** A slab
whose boolean half-fails reports the same lump in BOTH directions, inflating both
totals while leaving their difference nearly right, and the totals move by over a
thousand mm³ between `--slabs 8` and `--slabs 11`. The tool now checks
`missing - extra` against the plain volume gap, which needs no boolean at all,
and says so when they disagree. Anything that matters is confirmed by a direct
probe in `tests/test_box.py`, not by a lump size.

A related trap inside `box.py` itself: composing the negative first (empty the
slot band, then subtract the rest and the dividers back out of it) produces a
tool that cannot be subtracted with. Every cut here is a plain rectangular box,
and they are disjoint because the cavities are already separated by their
dividers.

## `Round top box corners` — a `4.600` round, front and back

Above `Lower the front` only the two **end walls** reach the rim: the front is
down at `68.600` and the rear storage is capped at `85.000`. So the "top box
corners" are the four corners of those two walls seen from the side, and each
carries a big round.

| | |
|---|---|
| radius | **`4.600`**, identical front and back on all six references |
| starts at | `z = 105.000 - 4.600 = 100.400` |
| the edges | the top-front edge at `y = -#BoxDepth/2` and the top-back edge at `y = #BoxDepth/2 + 4.500` — the outer face of the added depth, not the sketch box |

Fitted from the end wall's `y` extent at three heights, which pins the radius
three times over: an arc of radius `r` has eaten `r - sqrt(2ru - u²)` at depth
`u`, and `u = 3.01 / 2.01 / 1.01` give `4.602 / 4.599 / 4.600`.

`cad/parts/box.py` cuts it with a tool (a block minus a cylinder) rather than
`fillet()` on picked edges. Both edges are trivially described but awkward to
select stably, and a cut also keeps the tree order honest: whatever the later
groups ADD near the rim is untouched by a round that has already happened.

## `Sliders` — one rib per riser, and where they sit

Vertical ribs on both end walls, which the holders ride on. The section is
constant on every reference: **`1.500` wide in Y, standing `4.000` proud of the
inner end wall**, running the full height from the floor to the rim.

**A rib's BACK FACE sits on the centre of its card slot**, and the slots are
measured from the inner back wall — `calSliderDistance` each, except the last
(frontmost), which is `calFirstSliderDistance`:

```
rib j back face = #BoxDepth/2 - WallThickness - (j*calSliderDistance
                                                + calSliderDistance/2)
first slider    = #BoxDepth/2 - WallThickness - ((R-1)*calSliderDistance
                                                 + calFirstSliderDistance/2)
```

which is the feature tree's own split: `Replicate sliders` lays down the `R-1`
plain ones at a `calSliderDistance` pitch, and `First Slider` places the odd one
out. Exact on all six references — 25 ribs in all, from FCM 72's three to
Dominion 650's eight.

**`Box Dominion 246S` is what settles it.** Everywhere else
`calFirstSliderDistance == calSliderDistance`, so the frontmost rib is where a
plain pitch would put it anyway and the two readings cannot be told apart. On
`246S` they are `20.400` against `9.600`, and the measured rib pitch is
`15.000` — neither distance, but exactly their average, which is what
"back face on the slot centre" predicts and a constant pitch does not.

### `Round top of slider` rounds ACROSS the rib, not along it

**Radius `0.700`** on the two top edges parallel to X, leaving a `0.100` flat
between the two arcs. The rib's front face stays square to the rim — the third
top edge is NOT rounded, which is what says this is a two-edge fillet rather
than a domed end.

Same fit as the corners, at four depths: `u = 0.11 / 0.21 / 0.31 / 0.51` all
give `0.700` to four decimals.

### Watch which reference you fit a rim radius on

`Box Compile 105S` narrows by `0.254` at `0.11` below the rim where
`Box Dominion 246S without final fillet` does not narrow at all. That is not a
difference between the boxes: it is `Smooth box edges`, present in one export
and suppressed in the other, and `0.6 - sqrt(2·0.6·0.11 - 0.11²) = 0.254`
exactly. A useful independent confirmation of the `0.600` final fillet — and a
trap for anything else measured near `z = 105`.

## `Front pocket` — five features, and one plane over the top of them

Everything here is exact on all six references.

```
divider panel   y = -#BoxDepth/2 + WallThickness + calFrontPocketDepth,
                1.000 thick, the full inner width
dividers        right edge at -#BoxWidth/2 + WallThickness
                              + #calFirstLeftFrontDividerDist + k*calSlotwidth
                0.800 wide, k = 0 .. HorizontalSlots-2
padding         FrontPocketSidePaddingWidth = 5.800 against each end wall,
                filling the pocket front to back
slits           the SAME openings as the back's hanging holes — same X, same
                three rows
angled cutout   the plane through (y = front wall inner face, z = 68.600) and
                (y = panel BACK face, z = 87.500)
```

`#calFirstLeftFrontDividerDist` is the studio's own
`calSlotwidth + calFrontDividerLeftSpacing`, so the leftmost compartment is one
slot wide plus the side spacing and the rest are a slot each.

**The angled cutout is one plane and it shapes the whole group.** The padding's
top, each divider's top and the panel's top are not three separate numbers —
they are wherever that plane crosses each solid, which is why they all differ
per box and per X. Both endpoints hold to `0.001` on all six references while
the slope ranges from `0.349` to `1.323`, purely because `calFrontPocketDepth`
does. It starts exactly at the top of the lowered front wall, so `Lower the
front` and this are one continuous surface.

**`MatPocket` drops the RIGHTMOST divider**, merging the last two compartments
into the wide slot the mat needs — which is what
`calFrontSlotsForCards = HorizontalSlots - 2` counts.
`Box Dominion 244S` and `Box Dominion 202S Merged` are the same box with the
same envelope, and across a mid-pocket section the only difference is that one
divider: `3` against `2`.

### Shape the group before fusing it

Every piece reaches `WallThickness/2` into the wall it stands on, to keep the
fuse off a coincident face. The angled cut therefore has to reach those
overlaps too — clipped to the inner width it leaves a sliver of padding
standing to the rim inside each end wall, `1.816 mm³` a side. So the pocket is
built as one composite, cut, and only then fused, which also lets the cut run
the full width without touching the end walls (the STEP leaves those square to
the rim).

The corner-round probe is what caught it: `4.600` measured `4.800` of eaten
material on the build and `4.795` on the STEP, because the probe column sits in
the end wall and the sliver was in it.

## `Thumb and Lip`

### `Thumb`

A finger hole through the divider panel, **one per horizontal slot**:

```
centre X = -#BoxWidth/2 + WallThickness + calSliderSpaceLeftRight - 0.800
           + calSlotwidth/2 + k*calSlotwidth
centre Z = 87.500          the same height the angled cutout reaches
radius   = ThumbCutoutRadius = 12.000
fillet   = 0.400 into BOTH panel faces (`Fillet thumb hole`)
```

Exact on all six references, at `HorizontalSlots` 3, 4 and 5, and `MatPocket`
does not move them even though it drops a divider. The radius never reaches a
pad (`5.800` in) or a divider, so the thumb only ever meets the panel.

The fillet was read off the hole's profile through the panel — the radius at
eight depths, fitting `r - sqrt(2rt - t²)` to four decimals at every one. Note
the trap: a thin probe slab reports the section at the depth where the hole is
NARROWEST, which is the far side of the slab, so the whole profile reads one
slab-thickness shallow. Correct for that and `0.400` falls out; do not, and it
looks like a `0.275` fillet that fits nothing.

`box.thumb_tool` revolves the profile rather than cutting a cylinder and
calling `fillet()`, because the angled cutout takes the top off the hole — its
edge is an arc, not a circle. Use `ThreePointArc`, not `RadiusArc`: two points
and a radius admit four arcs and the one chosen left the hole a plain `12.400`
cylinder, which the STEP's own profile caught immediately.

### `Lip` — and where its angle comes from

Two per thumb, symmetric about it, standing proud of the panel's BACK face for
the front holder to catch on.

```
centre X   thumb centre +- 20.400
section    a PARALLELOGRAM: from the panel's back face at z = 85.500,
           LipDepth = 2.100 along the ramp, LipHeight = 2.000 tall in Z
plan       LipLength = 10.000 with a LipChamfer = 1.200 45-degree chamfer at
           each end, so the base measures 12.400
angle      tan = (calFirstSliderDistance - 1.200) / (calHeightIncrement - 1.000)
```

**The angle is the HOLDER's diagonal cutout angle** (Allan) — the group opens
with `Import Holder patterns`, and that is what comes across. It is the one
thing here that could not be reached from the Box alone, and the reason is
worth recording: `Box Dominion 244S` and `Box Dominion 650S` have identical
slot, slider and holder DEPTH — `calSliderDistance 8.400`, `calHolderDepth
7.900` — and different lip angles, `0.480` against `0.729`. What separates them
is `calHeightIncrement`, `16.000` against `10.875`, which is a riser-count term
and has no business in a front-pocket feature until you know the angle is
imported from a part that does care about it.

**Confirmed on all 46 canonical Holders in `individual/`** (0 API calls). Their
diagonal cutout's face normal gives the angle directly, and the formula
reproduces every one across four games, both sleevings, rises from `9.667` to
`22.000` and slider distances from `4.800` to `20.400`.

It is the FIRST slider distance because the lip meets the FRONT holder.
`Box Dominion 246S` is the only reference that can tell the two apart —
`20.400` against `9.600` — and it reads `1.280`, not `0.560`.

A shallow lip truncates its own chamfer, so the top face measures
`LipLength + 2*(LipChamfer - protrusion)` until the protrusion passes `1.200`:
`11.371` on FCM 72, `10.840` on Compile 105, and exactly `10.000` on Dominion
650 and 246. Both the STEP and the build show it.

The lip goes into the pocket composite BEFORE the angled cutout, and reaches
`0.800` into the panel so the fuse is not across a coincident face. That tab is
then trimmed with the panel by the same cut, which is what makes the order
work: after the cut, the tab would stand where the STEP has nothing.

## The label holders — one section, two lengths

`Front Label Holder` and `Side Label Holder` are the same shape. Measured off
the STEPs' own faces, which give round numbers throughout:

```
proud       1.600
z           40.500 .. 64.500
chamfer     1.600 on the outer face's bottom and two ends — NOT its top,
            which is the side the label slides in from
slot        0.800 deep, its rim 2.100 in, its own chamfer starting 1.300 in
opening     4.000 in, cut clean through
front       the label plus 3.600 — 156.400 wide, or 62.000 where the wide
            one will not fit, which is the XS box alone
side        calSideLabelWidth + 3.800, centred on y = 2.250
```

The side holder is on the **-X end only**, and that is the whole of the box's
asymmetric `2.600` width offset: `1.600` here against the closing bump's
`1.000` at the other end. With both holders built, the build's envelope matches
the STEP's exactly — `#BoxWidth + 2.600` by `#BoxDepth + 6.100` — which is the
first time the two agree on the outside.

The chamfer is measured **from the outer face**, so it reaches the wall exactly
and `chamfer()` on a plain pad reproduces it without any construction geometry.
The slot is chamfered the same way off its own deep face.

### The front holder is NOT one size — the XS box takes a 62

`Box Innovation 130U` measures its front holder's outer face at `62.400`, where
every other reference measures `156.800`. The section is identical; only the
length changes, and the groove (`L - 4.200`) and opening (`L - 8.000`) both
follow it.

**`cc.cfg` has known this all along, from the labels' side:** "The XS box is
only 150.9 mm wide, too narrow for the 156.4 front label, so the 62 is a FRONT
there (its pocket is cut for it at 62.4 mm outer)." So the front holder is the
label plus `3.600`, and the XS box's front takes what is elsewhere a large SIDE
label — `62` is `calSideLabelWidth`'s widest rung.

`cad/` keys it on whether the wide holder fits rather than on the size letter,
because that is the reason cc.cfg gives. XS is the only row it catches: every S
box is at least `209.300` wide.

**And the narrow holder carries no fasteners** — at `65.600` long there is
nothing above its frame but the two post tops.

This was a real defect, not a missing detail: the wide holder is `160.000` on a
box `148.300` across, so it stood proud of both ends. The build's envelope came
out `160.000` where the STEP's is `150.900`, which is exactly what the
envelope assertion caught the moment the reference arrived.

### The fastener is three cylinders, and its section is a LENS

`Fastener` / `Round Fastener`, on the front holder only, two of them at the
thirds of its length. A section through the middle looks exactly like a
triangular ridge with 60-degree flanks — and it is not.

Every one of its four faces is `GeomType.CYLINDER` of radius **exactly
1.000**, and every axis lies **in the wall face**:

| face | axis |
|---|---|
| lower flank | along X at `z = 64.500` |
| upper flank | along X at `z = 65.500` |
| each end | along Z, at `x = centre ± 4.000` |

So the ridge is the intersection of three unit cylinders: the two along X give
a lens section peaking `0.866025` proud halfway up and meeting the wall over
exactly `1.000` of height, and the third — a stadium prism, an `8.000` segment
dilated by `1.000` — rounds the ends. The flanks are arcs and the peak is an
EDGE, which is why there are two faces along X and not one.

**A straight-line fit through the three extremes is wrong and looks right.** A
circle through `(0, 64.500)`, `(0.866, 65.000)` and `(0, 65.500)` exists — it
has radius `0.577350` — and reproduces all three points while being half again
too fat in between. What settled it was reading the radius off the surface
(`BRepAdaptor_Surface(...).Cylinder().Radius()`) rather than fitting probes.

### The XS box gets ONE fastener — a deliberate divergence

`Box Innovation 130U`'s narrow front holder has **no fastener at all**: at
`65.600` overall there is nothing above its frame but the two post tops, so its
label's top edge is gripped by nothing. Allan wants one there, centred.

One and not two, because two at the thirds would sit `10.933` out from centre
and each ridge is `10.000` long end to end — they would run into the posts,
which stand at `|x| >= 28.800`. `fastener_centres` returns `(0.0,)` for the
narrow holder and `(-L/6, +L/6)` for the wide one; `label_holder` takes
absolute X positions rather than a bool, so the two cases are one code path.

Measured on the build:

```
Inno130U XS  holder  65.6  fasteners at (0.0,)
     x  -32.750.. -28.800  proud 1.600     post
     x   -4.999..   4.999  proud 0.866     the new ridge
     x   28.800..  32.750  proud 1.600     post
Dom244U   M  holder 160.0  fasteners at (-26.667, +26.667)   unchanged
```

Asserted from both ends, as every divergence is: a `10.5 x 1.8 x 2.2` cell
centred on the holder — clear of the posts — must hold **one** solid in the
build and **none** in the STEP. If Onshape ever grows the fastener, that check
fails rather than passing quietly.

## The engraved text, measured

Five lines, `0.400` into the top of the `1.600` floor (glyph faces at
`z = 1.200`), on the two **side floors** — the strips the holders rest on.
Read off the STEPs by subtracting them from a floor slab and identifying each
glyph by its ink box.

| side | line | source |
|---|---|---|
| `-X`, reading DOWN in Y | 1 | `calModelName` |
| | 2 | **`GameName`** — the primary, not `gameShortName`: `Box Dominion 244S` reads "Dominion" where the short name is "Dom" |
| `+X`, reading UP in Y | 1 | `ProductName` |
| | 2 | `calCapacityLabel` |
| | 3 | **`Rev <Version>`** |

**The `Rev` line reads `Rev 7.0`.** That closes the question this file has been
carrying: not `calVersion` ("CC 7.0"), and not the stale "Rev 1.8" of the
feature-tree screenshot. It is the literal word `Rev`, a space, and the version.

### Every line is Orbitron Bold

Identified by each line's ink-length-to-tallest-glyph ratio, which is a pure
property of the string and the face:

| line | measured | Orbitron Bold | Open Sans Bold |
|---|---|---|---|
| `Dominion` | `6.836` | **`6.8347`** | `6.6122` |
| `S2.40.12-30.45.Sl` | `13.187` | **`13.1855`** | `10.3862` |
| `Card Cascade` | `10.200` | **`10.1987`** | `8.5336` |
| `246 Cards/S` | `9.498` | **`9.4987`** | `7.3896` |
| `Rev 7.0` | `5.844` | **`5.8447`** | `4.6020` |

So the Box uses ONE face where the Pusher uses two — there is no Open Sans on it.

### The placement, from Allan's four sketches

Every number below is one of the sketch's own dimensions, and each is confirmed
on all five references.

```
                     both blocks
cap top              TEXT_INSET = 3.000 in from the side floor's INNER edge
                     — `#calSlotwidth/2 - 3mm` on the -X sketch, and measured
                     3.000, 3.000, 3.001, 2.996, 3.004 on the +X one
engraving            0.400 into the floor's top, so z 1.200..1.600

                     -X, reading DOWN in Y
lines                calModelName, then GameName, at ONE size — which is why
                     `Model name` is a single feature
pen start            3.000 from the back of the sliding-card area
line gap             3.000, baseline to the next line's cap top

                     +X, reading UP in Y
pen start            2.500 from the front of the sliding-card area, on all
                     three lines
ProductName          fitted to the card area less 2 x 2.500. #LogoHeight is
                     its cap height
calCapacityLabel     fitted to the same length; its cap top sits
                     2 x #LogoHeight/3 below the ProductName baseline
version              cap = 3 x #LogoHeight/4; cap top sits #LogoHeight/2 below
                     the calCapacityLabel baseline
```

The `2.500` was the one that had fooled me. I had measured the ink starting
`2.700` from the front and called it a fitted number; it is `2.500` to the TEXT
BOX plus the first glyph's left side bearing, `0.056` of the font size for
Orbitron's `C`. That reproduces the ink position to three decimals on every
reference — `2.702`, `2.713`, `2.949`, `2.604`, `2.688`.

Fitting `ProductName` to `card area - 5.000` then predicts its size to a
**constant `0.31 %`** across all five. Constant, so the residual is in how the
advance is being measured, not in the rule.

**The `-X` block does not fill its box.** Its sketch bounds it the same way —
`3.000` at the back, `#calFrontPocketDepth + #WallThickness + 3mm` at the front,
which is `card area - 5.000` again — but the text measures `card area - 6.900`
(`6.74` to `7.18` across the five). Allan: the size "is a bit arbitrary, I just
wanted to make it fit", so `cad/` uses the measured `6.900` rather than the
sketch's bound, which lands within a few tenths of every reference.

**The `RisingSliders` conditional**, in full (Allan):

```
#RisingSliders <= 8 ? 2.5 mm : 2.5mm + (#RisingSliders-8)*#calSliderDistance
```

It applies to the BACK of the `+X` box only; the front stays `2.500`. Past eight
risers the extra term is exactly the depth those risers add to the card area, so
the logo block **stops growing** and keeps the size it had at eight — `64.000`
long at `R = 8, 9, 10, 12` alike. Allan experimented with ten and twelve; one
catalogue row reaches it, Dominion's `333 Card` at `S9.21.10`.

No reference STEP is past eight risers, so `tests/test_box.py` checks the branch
by that property rather than against a measurement. Both `S9.21.10` variants
build, and the sleeved one's envelope is `211.900 x 100.300` against parts.csv's
`214 x 102.3` lid — the documented lid less `2.00`.

### The version line is a DELIBERATE DIVERGENCE

The sketches still read `Rev <version>`; Allan: it should say `CC`, as the Lid
does, i.e. `calVersion`. So the build engraves `CC 7.0` where every reference
engraves `Rev 7.0`.

This is the **second** intentional difference, after the whole dividers, and it
is asserted the same way — from both ends. The two are told apart by the line's
ink-length-to-cap ratio, which is a property of the string and the face alone:
`5.84` for `Rev 7.0` against `4.93` for `CC 7.0`. `tests/test_box.py` checks the
STEP still reads the first and the build reads the second, so a re-export that
converged would fail rather than pass quietly.

### Placing glyphs by the pen, not by their ink

`build123d`'s `Text` aligns to the INK or centres it, never to the pen origin,
and the bearings are exactly what turns a sketch dimension into an ink position.
`cad/text.metrics` reads them out of the font file with `fontTools` — advance,
left bearing, and the ink's extent above and below the baseline, per em.

The arithmetic alternative does not survive contact: bearings cancel from every
ink measurement, so recovering them needs a glyph assumed symmetric, and `|`
put the left bearing of `Card Cascade` at `0.0435` against its true `0.0560`.

Two traps in the build itself, both caught by the ink landing in the wrong
place: `Text` inside a `BuildSketch` adds ITSELF as well as the shifted copy
unless it is `Mode.PRIVATE`, and the shift to bring the pen to the origin is
`+lsb, +lo` — `align=MIN` leaves the pen at `-lsb`, not at `+lsb`.

## `Smooth box edges` — which edges, measured

The filleted / unfilleted pair settles the radius at `0.600` and the cost at
`129.406 mm³` over `44` new faces. What it also settles, now, is the EDGE SET.

An edge survives the fillet if the filleted solid still has one with the same
midpoint, which needs no booleans — comparing the two references that way finds
**80 of the unfilleted solid's 5052 edges gone**, `2704 mm` of them:

| count | where |
|---|---|
| 22 | horizontal at `z = 105.000` — the top rim |
| 14 | horizontal at `z = 85.000` — the `Top of back` ledge |
| 10 | vertical at `x = ±103.050` — the inner end walls |
| 8 + 8 | curved at `z = 103.650` and `104.790` — the rounded top corners' arcs |
| 4 | vertical at `x = ±104.650` — the outer end walls |
| 4 | horizontal at `z = 0.000` — the bottom perimeter |
| 4 | curved at `z = 84.800` |
| 2 | horizontal at `z = 68.600` — the lowered front's top edge |
| 4 | vertical on the storage DIVIDERS, at `x = ±69.050, ±67.450, ±35.050, ±33.450` |

Read as one thing: **every edge a finger meets.** The top rim, the rear
storage's cap, the lowered front, the bottom of the box, and the vertical
arrises of the end walls and the dividers. Nothing inside the card slots, the
lattice or the label holders is touched.

### `#SharpEdges` is a rule

Allan's query: **edge convexity CONVEX on the Box**, intersected with **"created
by"** a short list of features — `Extrude solid box`, `Add depth to back`,
`Top of back`, `Lower the front` and the rest of the shell-level ones.

That corrects a reading in an earlier revision of this file. It said "a good
part of the set is CONCAVE", inferred from a plain convex fillet over `2704 mm`
removing about `209 mm³` where the pair measures `129.4`. The inference assumed
a 90-degree dihedral at every edge, and the rounded top corners and the 45-degree
chamfers are nothing like that.

Measured properly — what fraction of a small cube at each midpoint lies inside
the solid, `0.25` convex against `0.75` concave — the 80 edges split **60 convex
and 20 concave**. The concave twenty are not filleted at all: they are CONSUMED,
short edges that vanish when their neighbours are rounded. The query is
convex-only and the geometry agrees.

### Two attempts that did not work, and why

**A convexity test from face normals needs calibrating, not deriving.**
`(n1 x n2) . t` separates convex from concave, but which sign is which depends
on the STEP's face orientation: taken one way it selects exactly the 20 concave
edges of the 80. Calibrate it against the reference pair.

**Midpoint diffing is NOT "created by".** The obvious way to reproduce the
feature filter without Onshape's history is to record the edges after each named
feature and keep what the previous state did not have. It does not work: every
boolean re-splits the edges it passes through, so an edge that merely gets cut
in two comes back with new midpoints and reads as newly created. Wired up that
way the filter selected `434` edges where Onshape's picks about `60`, the fillet
removed `312 mm³` against the reference's `129.4`, and one box took `162`
seconds instead of six.

### A third attempt: the skeleton, and why it also misses

Build the named features ON THEIR OWN — shell, rear block, `Top of back`,
dividers, `Lower the front`, `Round top box corners` — take that solid's convex
edges, and select the finished part's edges that lie on the same pair of
SURFACES. Matching by surface rather than by midpoint is the right idea and
solves the splitting problem: the skeleton's rim is one edge where the finished
box's is twenty-two pieces, and every piece lies on the same two planes.

It is fast (`0.2 s`) and deterministic. It is also wrong: 52 edges selected, 38
of them right, 14 false and about 18 missed.

The reason is that the skeleton is NOT the solid those features produced:

* **The dividers do not exist in it.** A divider is what is LEFT after the
  cavities are cut, and the cavities are not shell-level features. Adding
  divider-shaped boxes into a region that is still solid contributes nothing.
* **The `z = 85.000` ledge has 4 edges where the real box has 14**, for the
  same reason — the storage behind it is not hollow yet.
* **Conversely the skeleton's back rim is unbroken**, so every piece of the real
  rim BETWEEN the pusher cutouts lies on it and gets selected. The reference
  leaves those alone.

And the deeper point: Onshape's filter is per-feature PROVENANCE, not a snapshot.
It cannot be had by building up to a point in the tree either, because
`Round top box corners` comes after the rear storage — a snapshot there would
contain the lattice and the cutouts, which the query excludes.

### So the edge set has to be STATED

Not recovered. Everything needed is a model constant: the horizontal levels are
`0`, `FRONT_TOP`, `REAR_TOP` and `BoxHeight`, the verticals are the wall and
divider positions, and the arcs are `Round top box corners`. Written that way it
is fast, deterministic and generalises across the catalogue.

One caveat found the hard way: the rim cutouts also reach `z = 105.000`, and the
reference does NOT fillet the rim pieces between them. So a plain "every
horizontal edge at these levels" rule over-selects, and the statement needs to
exclude the back wall's own rim.

### What `sharp_edges` states, and what a second pass added

Written that way it is four clauses, and the second pass over it — diffing each
of the three UNFILLETED twins against its filleted self, which is a much
sharper instrument than one box's edge census — showed the first version
reached about 16 of the 30-odd edges. The families it was missing were the same
three on every box, no exceptions:

| family | per box | where |
|---|---|---|
| inner vertical corners | 4 | the end wall's INNER face, front `FRONT_TOP..100.400` and back `REAR_TOP..100.400` |
| corner-round arcs | 8 | `Round top box corners` leaves one on EACH face of each end wall |
| inner rim | 6–12 | the rim on the inner face, in the segments the ribs break it into |

Read together with what was already there, it is one thing: **the perimeter of
an end wall, on both of its faces** — along the bed, up the front and back
corners, round the arcs, along the rim. The arcs matter because they are what
makes it a CHAIN: the arc's tangent where it leaves `z = BoxHeight - CORNER_R`
is vertical, so it runs straight into the corner below it, and at the top it
runs into the rim.

### Two of those families are a KERNEL LIMIT, and stay sharp

Onshape rounds them; OCCT will not, and the reason is measurable.

**The inner rim.** A slider rib runs the full height of the wall and is
`SLIDER_W` wide with a `SLIDER_TOP_R` round on each flank, so where it meets
the rim it presents a flat only

    1.500 - 2 * 0.700 = 0.100

wide. A `0.600` fillet on either neighbouring segment has to die into a `0.700`
cylinder across that. OCCT refuses, and refuses in every order tried: the whole
family at once, after everything else, before everything else, one segment at a
time.

**The inner face's FRONT corner and the arc above it** — one tangent chain.
Fine on `246S`, `244U` and `130U`; on `S9.21.10`, the nine-riser Dominion,
refused. Given the whole chain, given one link, given the link reversed, before
or after the rest: refused.

That neither is about the SHAPE is plain from the symmetry. In both cases the
`+X` wall takes the edges and the `-X` wall, its exact mirror, does not — the
two differ in edge ORIENTATION and in nothing else. Parasolid manages both. A
per-edge `try/except` would recover them, and is exactly what Allan ruled out:
generation is to be fast and deterministic. So the rule keeps the back inner
corner and its arc, all four outer corners, both outer arcs, the outer rim, the
footprint and the ledge — and leaves the inner rim and the front inner chain
sharp. **Everything a hand touches is rounded**; what is given up is a `0.600`
round on interior edges no finger reaches.

Proven by building the whole catalogue: **50 of 50 boxes, 0 failures, 370 s**.
`tests/test_box.py` probes twelve rounded corners per reference with a `0.240`
cube — at a right convex corner a quarter of it is material while the corner is
sharp, and a `0.600` round takes all of it, because the far corner of that
quarter is `sqrt(2) * (0.600 - 0.120) = 0.679` from the fillet cylinder's
centre and the cylinder is only `0.600`. So "rounded" is exactly zero and
"sharp" is about `0.0035 mm³`, with no tolerance to tune. The four sharp ones
are asserted from BOTH ends — rounded on the STEP, sharp on the build — so a
future kernel that manages them fails the suite rather than passing quietly.

## Still open

- **`isLabelHoldersOnBox` is to become a real option.** Always `1` today, but
  Allan wants it usable — users have asked for a box without label holders. So
  the `Front Label Holder` / `Side Label Holder` groups are built behind the
  flag rather than unconditionally, even though the catalogue cannot exercise
  the `0` branch.
- The `2.600` width offset: `1.600` on `-X` and `1.000` on `+X`, owner not yet
  identified. It is NOT symmetric, which is odd given both label-holder groups
  mirror.
- **The rear storage's last two features**: `Make rightmost pocket deeper` and
  the rear thumb cutout at `#calFingerHoleOffset`. The latter shows in the diff
  as a `ThumbCutoutRadius`-sized arc through the outer back wall, `z 72.9..85.0`
  on `Box Dominion 246S`. (The "shelf" that used to be listed here was the top
  of the pusher rest's lattice — see above; it is built now.)
- `Smooth box edges` is built and the rule is stated, but it is NOT complete:
  the inner rim and the inner face's front corner-and-arc chain stay sharp
  because OCCT refuses them. See "Two of those families are a KERNEL LIMIT"
  above. Worth revisiting if OCCT's filleting improves.
- **The `RisingSliders > 8` branch** of the `Card Cascade` sketch's margin —
  see above. `S9.21.10` is the row that needs it. Nothing else — `box_diff` on `Dom246S_raw` now shows
  MISSING of `0.000` and an EXTRA that is exactly the deliberate whole-divider
  divergence (`460.0 mm³`) plus the text. The diff isolates each of them cleanly now — the thumb as
  `115 mm³` of panel I still carry at `z 75.1..87.5`, the lip as five `35.977`
  lumps at `z 85.5..88.8`, the front label holder as a `1.600` sweep at
  `y = -#BoxDepth/2 - 1.600` over `z 40.500..64.500`, and the side label holder
- **`isLabelHoldersOnBox` is built behind the flag** but no catalogue row can
  exercise the `0` branch, so that path is written and unexercised.
- **Probe hygiene.** Four probe bugs so far have been caught only because the
  STEP failed the same check as the build — a bar too narrow to contain what it
  measured, a cap a millimetre low, a cell that clipped a slice of wall, and a
  rebound loop variable. Assert on BOTH shapes; a check that only reads the
  build cannot tell a wrong probe from a wrong model.
