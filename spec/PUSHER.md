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

## Fonts

`Card Cascade` and `CC 7.0` are **Orbitron Bold** — the same
`fonts/Orbitron-Bold.ttf` `labelmaker.py` uses. Confirmed on both references:
worst glyph placement error `0.0008 mm` on Compile and `0.0002 mm` on Dominion.

**The third line is not Orbitron.** Its glyphs are far narrower relative to
their height — `l` measures `0.196` wide over tall against Orbitron Bold's
`0.331`, and `S` `0.634` against `1.000`. Matched against every font on hand
the closest is DejaVu Sans, still `0.311 mm` out on width, so it is some
humanist sans, most likely Onshape's default. **`cad/parts/pusher.py` does not
cut it** until the face is known.

## Text sizing is a rule now, not a reproduction

Onshape can constrain sketch text in only one dimension, so a text box that is
right for one parameter set is wrong for another. The evidence, same string and
same font on the two references:

| | strip depth | part length | Onshape cap |
|---|---|---|---|
| Compile 105 Sl | `8.00` | `72` | `4.4684` |
| Dominion 246 Sl | `9.60` | `32` | `1.1611` |

A factor of **3.85**, where nothing in the derived set moves by more than
`2.55` and most by under `1.3`. There is no formula on the derived variables
behind it — it is the box being fitted. So `cad/text.py` states the intent and
sizes to **both** dimensions, which is the thing Onshape cannot do:

```
cap = min( (strip - 2·margin) / ASC_PER_CAP,            # ascender clears the strip
           (x_end - x0) / (width_per_cap + LSB/CAP) )   # ink stops before the chamfer
```

`strip` is `calSliderDistance`, the depth of the region that spans the whole
rise; `x0` is the first step and `x_end` the start of the end chamfer. The side
bearing is inside the division because the ink starts one bearing right of the
anchor and that bearing scales with the size.

**Two rules of the CAD's are kept**, both confirmed on both parts: the version
line's baseline sits exactly one cap height below the product line's — which is
what `#LogoTextHeight` is measured back out of Onshape for — and it is set at
half the product line's cap.

Across all 34 pushers the rule gives caps of `1.27 .. 6.46`; 15 are length-bound
and 19 depth-bound. **The four 2-riser Dominion pushers are the hard case**
(`H = 32`, the shortest in the catalogue): `Card Cascade` needs about 11 cap
widths, so along the rise it cannot exceed `1.27` there. Making those legible
needs a layout change rather than a better fit — running the logo along the
depth of the large lower panel (`16 × 30` on that part) would allow roughly
`2.4`, or the string could shorten. That is a design call, not a fitting one.

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

## Settled by the Dominion export

**The first riser is at the leading edge.** Its outline drops `20.400`
(`calFirstSliderDistance`) at the first step and `9.600`
(`calSliderDistance`) at the second, so `slider_drops()` was right to put the
override first — and the `r = 1.000` round on that step (against `0.800` on the
rest) is confirmed by its riser face measuring `18.400` for an `18.400` length,
i.e. `PLATE - 2r = 1.000`.

**The assembly transform is not constant.** X is `+3.000` and Y `0` on both,
but Z is `-18.000` on Compile and `-16.000` on Dominion. Compare on the
bounding box, not a fixed offset.
