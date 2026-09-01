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

**`Box FCM 72S` is a row parts.csv does not have.** Its envelope solves uniquely
to FCM, sleeved, `HorizontalSlots 3, RisingSliders 3, FrontPocketCardCapacity 6,
CardsPerSlidingSlot 6` — `calModelName` `S3.6.6.20.Sl`, `calCapacityLabel`
`72 Cards/S`, which is where the filename's "72S" comes from. The formulas hit
`211.900 × 33.700` on the nose. Treated as a reference, not as a catalogue row,
until parts.csv says otherwise.

No unsleeved and no Innovation box among the five, and neither is needed:
sleeving moves `calCardwidth` and `calCardThickness` only, which reach the box
through `calSlotwidth` and `calSliderDistance` and add no topology; and
Innovation's `isOnlyTwoPusherSlots` M box is topologically the Compile/FCM S
case, which two of the five cover.

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
| `Remove material, don't let pushers drop through` | the slot's floor is at `z = 3.000` | a stored pusher rests there, not on the box floor |
| `Divider` / `Repeat Divider` | `1.600` wide, `z` up to `85.000` | **`n` dividers for `n` slots** — at every boundary except the left inner wall, the last one CLOSING the run on the right |

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

A related trap inside `box.py` itself: composing the negative first (empty the
slot band, then subtract the rest and the dividers back out of it) produces a
tool that cannot be subtracted with. Every cut here is a plain rectangular box,
and they are disjoint because the cavities are already separated by their
dividers.

## Still open

- **The `Rev` line.** Allan: it should read `Rev 7.0` or `CC 7.0`, i.e. it
  tracks the version — so the `Rev 1.8` in the feature-tree screenshot is stale
  in the CAD. The glyphs still need measuring off the STEPs, as the Pusher's
  fonts were, and the STEP will say what it currently reads.
- **`isLabelHoldersOnBox` is to become a real option.** Always `1` today, but
  Allan wants it usable — users have asked for a box without label holders. So
  the `Front Label Holder` / `Side Label Holder` groups are built behind the
  flag rather than unconditionally, even though the catalogue cannot exercise
  the `0` branch.
- The `2.600` width offset: `1.600` on `-X` and `1.000` on `+X`, owner not yet
  identified. It is NOT symmetric, which is odd given both label-holder groups
  mirror.
- **The rear storage's last ~2 %**: a shelf in the slot band at `z 23.833..25.000`
  that the reference keeps and this does not, worth `1776` mm³ on Compile 105 and
  `4103` on Dominion 650 — and `0` on FCM 72, which is exact. Plus
  `Make rightmost pocket deeper` and the rear thumb cutout at
  `#calFingerHoleOffset`, neither yet built.
- Still to build: the sliders (4.000 deep x 1.500 wide vertical ribs on both
  end walls, `RisingSliders` of them at a `calSliderDistance` pitch in Y — the
  diff finds all 8 on `Box Compile 105S`), the front pocket, the bottom pusher
  slots, `Lower the front`, the thumb and lip, the closing bumps, the label
  holders, and the text.
