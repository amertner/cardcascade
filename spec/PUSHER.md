# The Pusher, measured

From a hand-exported STEP of `Compile 105 Card Sleeved` (`S4.7.7.32-Sl`), 0 API
calls, plus the Onshape feature tree and the Primary values that produced it:
`HorizontalSlots 3, RisingSliders 4, FrontPocketCardCapacity 7,
CardsPerSlidingSlot 7, isFirstSlidingSlotOverride 0, FirstSlidingSlotCards 7,
isSleeved 1, MatPocket 0, GameName Compile, Version 7.0`.

Derived for those: `calPusherTotalDepth 32.00`, `calPusherTotalHeight 72.00`,
`calHeightIncrement 18.00`, `calSliderDistance 8.00`,
`calTabCentreDistance 8.50` (C3).

The STEP is one solid, 531 faces, volume `4214.001`. Its bounding box is
`72.000 × 32.000 × 4.500` — `calPusherTotalHeight` × `calPusherTotalDepth` ×
(`PusherThickness 3.000` + tab proudness `1.500`), all three exact.

**Coordinates below are the STEP's**, which is assembly position, not the part
studio's origin: X (rise) runs `3.000 .. 75.000`, Y (depth) `0.000 .. -32.000`,
Z (thickness) `-18.000 .. -13.500`. The `Lay down` / `Fix to lid` mate
connectors in the feature tree put it there. Build at the origin and transform.

## The outline — 16 straight segments, no arcs in plane

Sectioned at mid-plate (`z = -16.500`), traversed in order. Every number is
either a constant or a derived variable; none had to be fitted.

| from | to | length | what it is |
|---|---|---|---|
| `(3.000, 0.000)` | `(3.000, -13.300)` | 13.300 | leading edge, first half |
| `(3.000, -13.300)` | `(8.200, -13.300)` | 5.200 | notch side — `NOTCH_D` |
| `(8.200, -13.300)` | `(8.200, -18.700)` | 5.400 | notch end — `NOTCH_W` |
| `(8.200, -18.700)` | `(3.000, -18.700)` | 5.200 | notch side |
| `(3.000, -18.700)` | `(3.000, -32.000)` | 13.300 | leading edge, second half |
| `(3.000, -32.000)` | `(19.000, -32.000)` | 16.000 | back edge |
| `(19.000, -32.000)` | `(21.000, -30.000)` | 2.828 | **chamfer, 2.000 × 2.000** |
| `(21.000, -30.000)` | `(21.000, -24.000)` | 6.000 | step 1 riser |
| `(21.000, -24.000)` | `(39.000, -24.000)` | 18.000 | tread = `calHeightIncrement` |
| `(39.000, -24.000)` | `(39.000, -16.000)` | 8.000 | riser = `calSliderDistance` |
| `(57.000, -16.000)` | `(57.000, -8.000)` | 8.000 | riser |
| `(57.000, -8.000)` | `(75.000, -8.000)` | 18.000 | tread |
| `(75.000, -8.000)` | `(75.000, -2.000)` | 6.000 | last riser |
| `(75.000, -2.000)` | `(73.000, 0.000)` | 2.828 | **chamfer, 2.000 × 2.000** |
| `(73.000, 0.000)` | `(3.000, 0.000)` | 70.000 | front edge |

The staircase is exactly `x = 3 + k·calHeightIncrement`, `y = -k·calSliderDistance`
— which is why `#StepHypotenuse = 19.7 mm` in the feature tree is
`sqrt(18² + 8²) = 19.698`, the diagonal `Replicate steps` steps along. With a
first-riser override the first drop becomes `calFirstSliderDistance`, so the
hypotenuse for step 1 differs from the rest — which is the same asymmetry that
makes `calPusherTotalDepth` depend on `FirstSlidingSlotCards`.

The two `6.000` risers at the ends are the `2.000` chamfer taken off an
`8.000` riser.

## Rounds — this is what the two `Round` features are for

Cylindrical, axis along Y, on **both** Z faces, rounding the top edge of each
step riser. They do not appear in the mid-plate section.

| feature | radius | at |
|---|---|---|
| `Round step 1` | **1.000** | `x = 21` (the first step) |
| `Round top of step` | **0.800** | `x = 39`, `57`, `75` (replicated) |

The first step having its own radius is why `First Step` / `Round step 1` are
separate features from `Single step` / `Round top of step`.

## Lock features — exactly `LOCK_STANDARD.md`

| | measured | standard |
|---|---|---|
| tab, 2 off | `3.800` wide × `5.000` long, `1.500` proud | `3.80 × 5.00`, `1.500` |
| tab position | Y centres `-7.500` and `-24.500`; centreline `-16.000` | **`±8.500` = C3** |
| tab X | `3.000 .. 8.000` — flush with the leading edge | flush |
| notch | `5.400` wide × `5.200` deep, through the `3.000` plate | `5.400 × 5.200` |
| notch position | Y `-13.300 .. -18.700`, centre `-16.000` | on the centreline |

`calTabCentreDistance` for `D = 32.00` is `8.5`, and the part measures `8.500`.
The v7 standard is in the CAD as specified.

## Text — engraved `0.400` deep

Glyph faces sit at `z = -15.400` against a front face at `z = -15.000`. The
arithmetic confirms engraving rather than a raised inlay: front face `1200.436`
+ glyphs `144.964` + tab bases `38.000` = `1383.400`, against a back face of
`1383.500`.

| line | glyphs | placement | cap height |
|---|---|---|---|
| `Card Cascade` (`ProductName`) | 11 | along X, baseline `y = -4.900`, `x 20.07..68.80` | `3.60`, ascenders `4.78` |
| `CC 7.0` (`calVersion`) | 5 | along X, baseline `y = -9.370`, `x 19.89..30.91` | `2.24` |
| *unidentified* | 8 | rotated 90°, reading down −Y, `x ≈ 9.95..13.92` | `2.92` |

`Card Cascade` is confirmed by its ascenders: the two glyphs reaching `4.78`
are at word positions 4 and 10, which are exactly the two `d`s. `CC 7.0` by its
period, glyph 4 of 5 at `0.41 × 0.41`.

**`#LogoTextHeight = 4.47 mm`** is the `C` of `Card Cascade`, which measures
`4.470` including its round overshoot.

## Fonts — two, both identified against the STEPs

| line | typeface | worst glyph error |
|---|---|---|
| `Card Cascade` (`ProductName`) | **Orbitron Bold** | `0.0008 mm` Compile, `0.0002` Dominion |
| `CC 7.0` (`calVersion`) | **Orbitron Bold** | as above |
| `7 Sleeved` / `12 Sleeved` | **Open Sans Bold** | `0.0043 mm` Compile, `0.0004` Dominion |

Orbitron Bold is the file `labelmaker.py` already uses. Open Sans is Allan's
choice for the detail line because Orbitron is a wide geometric face and Open
Sans fits more text in the same space — `"12 Sleeved"` needs `7.14` cap-widths
in Open Sans against about `10.9` in Orbitron.

**The weight was tested, not assumed.** Every Open Sans weight from Light to
ExtraBold was fitted to the STEP glyphs:

| weight | Compile: height / width error | Dominion |
|---|---|---|
| **Bold (700)** | **`0.0043` / `0.0006`** | **`0.0003` / `0.0004`** |
| SemiBold (600) | `0.0221` / `0.1711` | `0.0060` / `0.0830` |
| Regular (400) | `0.0415` / `0.3436` | `0.0125` / `0.1673` |

Two orders of magnitude between Bold and its neighbours. The thin `l` is what
separates them: it measures `0.7689` where Regular predicts `0.4253`.
`fonts/OpenSans-Bold.ttf` is bundled, Google Fonts under the OFL like Orbitron.

## Text sizing is a rule, not a reproduction

Onshape can constrain sketch text in only one dimension, so a text box that is
right for one parameter set is wrong for another. Measured on the two
references, same strings and same fonts:

| | strip depth | part length | logo cap | detail cap |
|---|---|---|---|---|
| Compile 105 Sl | `8.00` | `72` | `4.4684` | `3.686` |
| Dominion 246 Sl | `9.60` | `32` | `1.1611` | `1.314` |

A factor of `3.85` on the logo and `2.81` on the detail, where nothing in the
derived set moves by more than `2.55` and most by under `1.3`. There is no
formula on the derived variables behind it. So `cad/text.py` states the intent
and fits **both** dimensions, which is the thing Onshape cannot do.

**Logo lines**, along the rise near the front edge, left-anchored at the first
step:

```
cap = min( (strip - 2·margin) / ASC_PER_CAP,            # ascender clears the strip
           (x_end - x0) / (width_per_cap + LSB/CAP) )   # ink stops before the chamfer
```

`strip` is `calSliderDistance`, the depth of the region that spans the whole
rise. The side bearing is inside the division because the ink starts one
bearing right of the anchor and that bearing scales with the size.

**Detail line**, reading down the depth near the leading edge, rotated 90°:

```
cap = min( (band - margin) / ASC_PER_CAP,               # ascender clears the first step
           (depth - 2·margin) / width_per_cap )         # ink fits the depth
```

`band` runs from the baseline to the first step. The baseline is
`DETAIL_BASELINE_X = 7.000` — measured at exactly that on **both** references,
one of the few placements in the CAD that is a constant rather than a fitted
box. It clears the `5.200` notch and the `5.000` tabs comfortably. The line is
centred along the depth.

**Two rules of the CAD's are kept**, confirmed on both parts: the version
line's baseline sits exactly one cap height below the product line's — what
`#LogoTextHeight` is measured back out of Onshape for — and it is set at half
the product line's cap.

### What the rule gives

Across all 34 pushers, logo caps run `1.27 .. 6.42` and detail caps
`1.33 .. 6.65`. On the two references:

| | Onshape logo | rule | Onshape detail | rule |
|---|---|---|---|---|
| Compile 105 Sl | `4.468` | `4.734` | `3.686` | `3.917` |
| Dominion 246 Sl | `1.161` | `1.274` | `1.314` | **`3.283`** |

The Dominion detail line — the one Allan flagged as too small — comes out
**2.5× larger**, because its box was fitted in the wrong direction and the
depth it runs along was almost entirely unused.

**The logo on short pushers is a real limit, not a fitting failure.** The four
2-riser Dominion pushers are `H = 32`, the shortest in the catalogue, and
`Card Cascade` needs about `10.9` cap widths, so along the rise it cannot
exceed `1.27` there. Making those legible needs a layout change — running the
logo along the depth of the large lower panel (`16 × 30` on that part) would
allow roughly `2.4`, or the string could shorten. That is a design call, not a
fitting one. The same applies to `FCM 3x6-Un`'s detail line at `1.33`: that
pusher is only `14.04` deep and the string is 10 glyphs.

## What the rebuild reproduces

`cad/parts/pusher.py`, checked by `tests/test_pusher.py` against **both**
STEPs. Every X-normal face area, the full mid-plate outline, the tab tops and
the volume match exactly:

| | Compile 105 Sl | Dominion 246 Sl |
|---|---|---|
| bounding box | `72.000 × 32.000 × 4.500` | `32.000 × 30.000 × 4.500` |
| mid-plate outline | 16 vertices, area `1407.920` | 12 vertices, area `601.520` |
| volume | `4271.997` vs `4271.986` | `1851.430` vs `1851.435` |
| riser faces | `6.0 / 11.2 / 11.2 / 8.4` | `18.4 / 10.64` |
| tab tops | `38.000` | `38.000` |

All **34** distinct pushers build and export, spanning `C1..C5` — including
`FCM 3x6-Un` at `D = 14.04`, the only C1 and the tightest geometry in the
catalogue. 34 rather than 32 because the two the Pusher key's missing
first-riser axis hides (see `spec/DERIVED.md`) are separate geometry.

## What the written 3MFs reproduce

`tests/test_pusher_regression.py` reads the 34 files `cad.build` writes back
through `automation/verify.py` — the same code the Onshape pipeline is checked
with — and compares each against the file in `individual/` it replaces. It
passes.

Against **all 32** canonical pushers, exactly (1e-3 mm): height, depth, the
`4.500` total thickness, and all three assembly coordinates. Every built pusher
carries two `3.800` tabs, fully backed, with the full `5.00` mm of root, and its
notch exactly where `verify.target_lock` puts it — which is the C1–C5 re-cut,
delivered without spending it in Onshape.

The lock itself splits, and the split is not noise:

| | pushers | what the rebuild does |
|---|---|---|
| already 7.0 in `individual/` | 18 | reproduces the lock exactly |
| still 6.6 | 14 | moves it onto the catalogue |

**The split matches parts.csv's `Build` column on every row it can name.** Read
the generation off each canonical pusher's lock — `6.6` if the tab centres are
`D - 12.00` apart, `7.0` if they sit at `D/2 ± s` — and it agrees with the
pinning for 30 of 32, including the per-sleeving pins (`Dominion 168/202/244
Card` are `Sl:6.6`, and their `Pusher 4x10-Un` reads 7.0 while `-Sl` reads 6.6;
`Innovation` is `Un:6.6` and splits the other way). The two that cannot agree
are `Pusher 6x10-Un/Sl`, which two rows share: the files read 7.0, which is
`324 Card`'s pinning, confirming `spec/DERIVED.md`'s reading that the `290 Card
(Mat)` geometry is the one absent from disk.

Text is not compared. Onshape sized it in one dimension and `cad/text.py` sizes
it in two, so it is expected to differ — deliberately, and most on the parts
Allan flagged.

## Settled by the Dominion export

**The first riser is at the leading edge.** Its outline drops `20.400`
(`calFirstSliderDistance`) at the first step and `9.600`
(`calSliderDistance`) at the second, so `slider_drops()` was right to put the
override first — and the `r = 1.000` round on that step (against `0.800` on the
rest) is confirmed by its riser face measuring `18.400` for an `18.400` length,
i.e. `PLATE - 2r = 1.000`.

**The assembly transform is a rule, not a constant.** X is `+3.000` and Y `0`
on both, and Z is `-18.000` on Compile against `-16.000` on Dominion — which
are their two `calHeightIncrement`s. Checked against all **32** component 3MFs
in `individual/`, `Z min = -calHeightIncrement` exactly, every time, across the
seven distinct rises in the catalogue (`9.667` to `22.000`).
`pusher.assembly_offset` is that rule; `cad/build.py` applies it, so a built
file lands where the Onshape one does and the two compare directly.
