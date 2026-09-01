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

## What is still missing

1. **The font.** Not recoverable from geometry. `labelmaker.py` uses Orbitron
   Bold; these glyph proportions are not obviously the same face.
2. **The third text line.** 8 glyphs, a word space after the first, one
   full-height narrow glyph at position 3, and three identical glyphs at
   positions 4, 5 and 7. It matches none of the derived strings —
   `calCapacityLabel` "105 Cards/S" is 10 glyphs and `calModelName`
   "S4.7.7.32.Sl" is 12.
3. **`LogoTextHeight`'s expression.** It and `StepHypotenuse` are Part Studio
   variables, not Primary studio ones. `StepHypotenuse` is recovered
   (`sqrt(calHeightIncrement² + calSliderDistance²)`); `4.47` is not.
4. **Text placement as a rule.** The offsets above are measured at one size;
   whether the baselines are fixed margins or scale with the part needs either
   a second STEP at a different parameter set, or the sketch dimensions.

Nothing in 1–4 blocks the solid. The body, steps, rounds, chamfers, tabs and
notch are fully determined and can be built now.
