# The Topper, measured

**IN PROGRESS.** Nothing is built yet — `cad/parts/topper.py` does not exist.
This is the measurement record so far, written down as it is established rather
than at the end, so the open questions are visible. "Still open" at the bottom
is the live list.

The cap that closes the top of a card slot. **Innovation only**: no other
game's studio has one, and `components.GAMES` carries `Toppers` under
Innovation's `extras` alone.

Six per parameter set — one per expansion (`Artifacts`, `Cities`, `Echoes`,
`Figures`, `Unseen`) plus a `Blank` — and they are **one shape with different
lettering**, not six designs.

## The references

| what | where |
|---|---|
| `Topper Unseen M5.15.15.62-Sl.step` | `spec/reference/` — Innovation `4 Ages 5 Expansions` Sl, 0 API calls. 13 solids, `Top and front edges` APPLIED |
| `Topper Blank M5.10.10.32-Un without top and front edges.step` | `Top and front edges` SUPPRESSED. A different parameter set from the sample — 10 cards, unsleeved. One solid, 133 faces against the other's 445 |
| `Topper Unseen M5.15.15.45-Un.step` | 15 cards, unsleeved |
| `Topper Unseen M5.10.10.32-Un.step` | 10 cards, unsleeved — the PAIR with the one above: same expansion, same size, same sleeving, and only the card count differs |
| `Topper Cities M5.15.15.62-Sl.step` | 15 cards, SLEEVED. The third axis: sleeving moves the depth without moving the card count, which is what the pair alone could not separate |
| `Topper M5.15.15.62-Sl to Remove Inner Hole.step` | the feature tree ROLLED BACK to that feature |
| `Topper M5.15.15.62-Sl after More Dividers.step` | rolled back to there. The two bracket `Main topper`, so each group is a subtraction rather than an inference |
| 48 cached components | `individual/Innovation/Topper *.3mf` — 6 expansions x S/M x 10/15 cards x Sl/Un |

The STEP holds **13 solids**: the body, the six letters of `Unseen`, and six
more making up the logo. **The body IS the blank topper** — the blank is not a
different part, it is this one without its name and logo — so the blank needs
no export of its own.

The 48 meshes are what say a rule holds rather than a coincidence: two sizes,
two card counts and both sleevings, which between them move every term below.

## The envelope, and its three rules

All three are exact on all 48:

    width  = calSlotwidth * HorizontalSlots      201/207 (S), 268/276 (M)
    depth  = 2.000 + calSlotDepth                6.000, 8.000, 8.500, 11.750
    height = 45.200                              CONSTANT, every one

The first two are the HOLDER's own dimensions, and that is the point:

    width = holder_width - 2 * holder.END_EXTRA      285.800 - 9.800 = 276.000
    depth = holder_depth                                             = 11.750

So the topper is the holder minus its two end blocks, at the same depth. It
spans the slots and not the end blocks that carry the side slots.

`45.200` is a constant — no derived variable produces it, and it does not move
across capacity, size or sleeving.

## Assembly position

    X   -34.500 .. 241.500      (sleeved; -33.500 .. 234.500 unsleeved)
    Y   -2 * depth .. -depth
    Z    48.450 .. 93.650

Constant on all 48. The Y rule is exact: the topper sits one full depth back
from the origin, which is the slot it caps. **What sets `Z = 48.450` is not yet
derived** — see "Still open".

## `#TopperHeight`

Allan's expression:

    #BoxHeight - #WallThickness*2 - #PusherFootThickness
               - #calPocketHeight - 4mm - 3.5mm

    = 105 - 3.2 - 1.6 - 88.5 - 4 - 3.5 = 4.200

which is `#TopperHeight = 4.2 mm` in the feature tree. It is confirmed a second
way, off the geometry: the section's REAR is `52.650 - 48.450 = 4.200` thick.
Two independent readings, so this is settled.

It is 4.200 for every Innovation row, because `calPocketHeight` pins at 88.500
(`CardHeight - 3.5` wins the `min`) — but the formula is real, not a constant.

## The section

Read at a divider on the sample (`calSlotwidth 69.000`, `calSlotDepth 9.750`):

    bottom      Z 48.450, from Y -22.700 to -12.550
    front wall  Y -11.750, vertical, Z 49.250 -> 69.050    (20.600 tall)
    rear wall   Y -23.500, vertical, Z 49.250 -> 52.650    (4.200 = TopperHeight)
    slant       (-12.550, 69.050) -> (-23.500, 52.650)
    top flat    0.800 wide at the front, Z 69.050
    corners     r 0.800, BOTH bottom corners
    floor       1.200 thick, Z 48.450 -> 49.650

### The slant is the Holder's, and that is measured

`TriangleMatch` extrudes **"Faces of Top slant angle"** — a face of the imported
Holder — `calSlotwidth * HorizontalSlots` along X. The measured slope is

    dZ/dY = 1.497717

against `holder.slant_slope(p, d, first=False)` = **1.497717**. Exact.

This is the whole answer to "does the rebuild need to import the holder?".
**It does not.** Every quantity `Import Holder` supplies is already a named
function:

| Onshape derived feature | `cad/` equivalent |
|---|---|
| `Leftmost Pusher Pos` | `holder.x_span`, `holder.compartment_x` |
| `Top slant angle` | `holder.slant_slope`, `slant_z`, `slant_band` |
| `Mid plane` / `Middle` | `holder.holder_width`, `x_span` |
| `Room for Lips` | `holder.lip_plan`, `lip_reach_y`, `LIP_*` |
| `GuideToTabs` | `holder.side_slots` and the lip geometry |

A named function is the better dependency: it binds the topper to the RULE
rather than to the holder being finished and correct. `holder.py` is still
about 2% heavy and not printable, but the parts the topper needs — envelope,
slant, lip geometry — are in its proven half, not the lattice and finger
cutouts that are still out.

**What it costs**: Onshape got the tab/holder mate right by construction, and
dropping the import gives that up. It has to be replaced by an assertion —
see "Still open".

## The unfilleted export, and what it is a twin of

The second STEP has `Top and front edges` suppressed, which is the trick that
made the Box's last feature measurable. It is **not** a twin of the Unseen
sample, though: that one is `M15-Sl` and this one is `M10-Un`. So the two
cannot be differenced directly.

It pairs instead with the cached **`Topper Blank M10-Un.3mf`**, and with
`Topper Unseen M5.10.10.32-Un.step`, both of which are the same parameter set
with the fillet applied. A mesh is lossy, but Onshape's
tessellation is good to about `0.01`, which is ample for locating a fillet.

It is also, by luck, **exactly the configuration every logo sketch was drawn
at** — `calLogoSidelength 4.2250`, `LogoEdgeDist 0.600` — so the whole
`Expansion Name` group can be checked against this body directly.

Its 133 faces against the Unseen sample's 445 make it the one to build against.

### What `Top and front edges` actually does

The filleted `M15-Sl` section carries `r 0.800` rounds on both BOTTOM corners
that this one does not have. The feature is named for the sketch's orientation;
`Upside Down` sits between them in the tree, so the sketch's top and front are
the assembly's bottom and front.

**It has to be built BEFORE the lettering** (Allan): the logo and text offsets
are measured from the edge of those fillets, so `Expansion Name` does not work
without it. That is an ordering constraint, not a cosmetic one — the same shape
of trap as the rim round that has to precede the TokenHolder's grip.

## The cell, between posts

Sectioned away from a post (`M10-Un`, `calSlotDepth 4.000`):

    floor        1.200 thick      Z 48.450 -> 49.650
    front wall   0.800 thick      Y -6.000 -> -6.800, 2.600 tall
    rear wall    0.242 thick      Y -12.000 -> -11.758

`0.242` is not a modelled number. It is `0.800 * cos(72.4 deg)` — the Y
component of `0.800` measured ALONG the slant, whose slope here is `3.153846`.
That is what says the `Inner Hole Outline` sketch really is IN the slant plane,
which is what its sketch plane (`Face of TriangleMatch`) says and what its two
dimensions, `1.4` and `0.8`, are measured in. Anything that builds this wall as
a Y-offset instead will be wrong by the slope, and wrong differently on every
row, because the slope moves with `calSlotDepth`.

## The fillets and the mirror

| feature | value |
|---|---|
| `Fillet front holes` | radius **2.0**, tangent propagation, allow edge overflow, on the edges of `Remove front section` |
| `Fillet Lip Room` | radius **1.4**, on two edges of `Remove Lip Room` |
| `Other side` | a FEATURE MIRROR of `Remove Lip Room` + `Fillet Lip Room` about the **Right plane** — so the lip clearance is cut at both ends and the fillet comes with it |
| `Linear pattern 1` | patterns `Remove Lip Room` + `Fillet Lip Room` + `Other side` along the **Right plane**, `distance = calSlotwidth` (67 on the sample), `count = HorizontalSlots` (4), **Centered**. So the lip clearance is cut once per slot, centred on the part |
| `Top and front edges` | `r 0.800`, see above |

## The rollbacks arrive in the PRE-`Upside Down` frame

`Upside Down` sits late in the tree, so anything rolled back before it comes
out turned over: `Y 0 .. -depth` where the finished part is `-2*depth .. -depth`,
and `Z` mirrored about `Z_BASE`. The transform is

    a 180-degree turn about X through (y = -depth, z = Z_BASE)

    y' = -y - 2*depth        z' = -z + 2*Z_BASE

and it puts all three bodies on the same envelope to `1e-6`. Worth knowing
before comparing any future rollback, because the two frames differ by exactly
the amount that makes a wrong answer look plausible.

## `Remove Inner Hole` — solved exactly

Differencing `wedge()` against the first rollback gives the tool itself: **one
prism of six faces**, swept along X, whose top IS the wedge's own slant plane —
so the cut needs no top of its own, it simply runs out through the slant.

    floor   Z_BASE + FLOOR
    front   FRONT_WALL (0.800) in from the front face, in Y
    rear    INNER_INSET (0.800) from the rear edge, ALONG THE SLANT
    ends    INNER_END_INSET (1.400) in from each end of the part

Those last two are the `Inner Hole Outline` sketch's `0.8` and `1.4`, and the
rear one is why the sketch plane matters: `0.800` along a slant of `1.4977`
lands `0.4442` in Y, and `0.242` on the `3.1538` row. `cad/` reproduces the
rollback with **zero volume difference either way** and the same 12 faces.

## `Divider` is the pocket, filled back in

The same difference on the second rollback gives three solids of six faces
whose YZ section is **identical to the pocket's** — the same area to four
decimals, the same four edges. So a rib is not a shape of its own: it is
`Remove Inner Hole`'s own profile put back over `RIB_W`, at each slot boundary.

## The front-wall removal, and the fillet that is not built

`Remove most of front` and its companions take the front wall away above
`FRONT_WALL_RISE`, over `calSlotwidth - 2*BAND_HALF`, centred on each SLOT
CENTRE — which is what leaves the `14.800` band at each boundary.

The rollback's removed solids measure `58.200` wide against that rule's
`54.200`, and the difference is not the cut. It is `Fillet front holes`: a
`2.000` round on each vertical corner, with "allow edge overflow", reaching
`2.000` past each end. The band measures `14.800` on all four references, which
is what says the cut is the narrower number.

**That fillet is not built.** OCCT will not put a `2.000` round on an `0.800`
wall, which is precisely what Onshape's overflow option is for. It moves
`5.494 mm3` — `0.086%` of the group — WITHOUT changing the total, so a volume
check alone would pass a body that does not have it; the test asserts the
symmetric difference instead, and that the reference carries it as 16 cylinders
at `r 2.000`.

## Ribs and front bands — a T in plan, not a post

An earlier revision of this file called these "posts, 14.800 wide". That came
from PLAN sections, which cannot tell a solid block from a T, and it was wrong.
Probing the unfilleted reference band by band in Y separates them. At `Z 55`,
around the boundary at `X 33.5`:

    Y -6.1, -6.5   (at the front face)   material runs 26.10 .. 40.90
    Y -6.9 and back                      material runs 32.70 .. 34.30

So each slot boundary carries

    a RIB           1.600 wide (= #WallThickness), the full depth and height
    a FRONT BAND   14.800 wide, but only 0.800 deep — the front wall, left
                   standing here where `Remove most of front` takes it away
                   everywhere else

The two ends carry HALF a band each (`7.400`), because a band is centred on a
boundary and the part stops half a slot out from the first one. Both sets
reproduce exactly:

    ribs    32.700..34.300   99.700..101.300   166.700..168.300
    bands  -33.500..-26.100  26.100..40.900  93.100..107.900
           160.100..174.900  227.100..234.500

`7.400` is `#FootDistanceFromWall`, which would read as the band straddling the
pusher's path. The `Divider` sketch gives the profile but not where the width
comes from, so that stays a hypothesis and is not encoded as one.

### The lip clearance is a band exactly `#LipHeight` tall

Between the floor's top and `2.000` above it, everything between the ribs is
open — `49.650` to `51.650`, and `#LipHeight` is `2.000`. That is the room the
Holder's rear lips need, and it is what `Room for Lips`, `Remove Lip Room`,
`Other side` and `Linear pattern 1` cut. The pattern's own numbers agree: pitch
`calSlotwidth`, `HorizontalSlots` instances, centred, mirrored — and the
reference carries `16` cylinders at `r 1.400`, which is two fillet edges on
each of `4 x 2` cuts.

At each end the block left standing measures `2.900`, which is
`TAB_INSET 1.300 + TAB_W 1.600` — the tab's own footprint, so the tab has a
root to stand on.

## The holder tabs## The holder tabs

Two, one at each end of the part, standing above the body:

    thickness   1.600 (= #WallThickness)
    inset       1.300 from each end of the part
    Y           from the front inner face to the slant at that height
    Z           ~69.050 .. 93.650
    extrude     44 mm blind (Allan)

On the unfilleted `M10-Un` body: `X -32.200..-30.600` and
`231.600..233.200` — `1.600` wide, `1.300` in from each end — and
`Y -10.558..-6.800`, whose `-6.800` is the front wall's inner face.

The sketch carries `1.6`, `1.2` and `0.1`. These are what mate the topper to
the holder.

## The expansion logos

Each topper carries, to the LEFT of its expansion name, a small mark. Allan's
sketches for these arrived before the blank was built and are transcribed here
so they are not lost; **nothing below is implemented yet**.

### They are GENERATED marks, not drawings

Every one is sketched on the `Top plane` inside a bounding box of side
**`#calLogoSidelength`**, and **every dimension in every sketch is a FRACTION
of it** — `/2`, `/4`, `/5`, `/7`, `/8`, `/10`, `/12`. Nothing is absolute.

That variable already exists, and is already transcribed:

    calLogoSidelength = 3 * calHolderDepth / 4 - 0.2        (cad/derive.py)

In `cad/marks.py`'s terms this makes them **GENERATED** rather than DRAWING
marks — built from a rule, so they stay exact at any size, and no DXF is
needed. That is the opposite of most of the Lid's marks, which are artwork
scaled from `logos/<Game>/*.dxf` and whose strokes scale with them.

The screenshots were all taken at **`calLogoSidelength = 4.23`**, which is
Innovation's 10-card UNSLEEVED value (4.2250 exactly). Useful for checking a
transcription: any construction below, evaluated at 4.2250, has to reproduce
the numbers shown.

### The constructions, as read from the sketches

| expansion | construction |
|---|---|
| `Echoes` | a square rotated 45 degrees — a diamond — with its four vertices at the midpoints of the bounding box's edges |
| `Artifacts` | two tall triangles, bases on the box's bottom edge, apexes inset `calLogoSidelength/4` (1.06) from the left and right; they overlap |
| `Cities` | an eight-pointed star. Drawn in TWO sketches, `Cities Draft` and `Cities` — the draft carries the construction (`/8` = 0.53, `/5` = 0.85) and the final is the single filled outline |
| `Unseen` | a shield: a curved triangle whose main arc is `R = calLogoSidelength/2` (2.11), its top corners inset `calLogoSidelength/7` (0.6) both ways; below it five small rectangles on an arc at 0, +-25 and +-50 degrees, each `calLogoSidelength/5` (0.85) long by `calLogoSidelength/10` (0.42) wide, offset `calLogoSidelength/12` from the centre |
| `Figures` | two CONCENTRIC CIRCLES — an annulus — the radial gap between them `calLogoSidelength/5` (0.85). One solid in the corpus, which an annulus is |
| `Blank` | none — the blank carries no name and no logo |

These are read off screenshots, so the RATIOS are exact (they are expressions)
but exact vertex placement is not yet confirmed for `Artifacts` and `Cities`.
The Unseen sample STEP carries its own logo as six solids, so that one can be
checked against geometry directly.

### Placing the mark and the name

Both sit on the `Face of CardHeight`, and the `Expansion Name` sketch gives the
three numbers that place them:

    text starts at   #calLogoSidelength*3/2 + 3mm    9.34
    top margin       #LogoEdgeDist                   0.60
    bottom margin    #LogoEdgeDist*2                 1.20

with

    #LogoEdgeDist = CardsPerSlidingSlot > 10 ? (isSleeved ? 1.2 : 0.8)
                                             : (isSleeved ? 1.0 : 0.6)

All three reproduce exactly at 10-card unsleeved — `4.2250`, `0.60`, `9.338` —
which is the configuration every sketch screenshot was taken at, so the whole
group is consistent.

**The margins are deliberately asymmetric**, and the reason is worth keeping:
the bottom is doubled so the font's lower-case `g` descender does not run off
the face (Allan). `Figures` is the only expansion with one. Without that note
the `*2` looks like a mistake to be tidied up, and tidying it would push the
`g` off the part — the same class of error as the three token holders whose
engraving the outline clips.

`#LogoEdgeDist` and `#TopperHeight` are **part-studio** variables, not variable
studio ones, so unlike `#calTokenHolderSlotWidth` they do NOT belong in
`derive.py` — that module is the variable studio's transcription. They belong
in `cad/parts/topper.py`, as `holder.py` holds its own `LIP_*` constants.
`#calLogoSidelength` is different: it IS a studio variable and is already in
`derive.py`.

### The logo IS `calLogoSidelength`, on all four expansions

Measured against all four M configurations of each expansion in
`individual/Innovation/`, the mark's width is `calLogoSidelength` exactly —
`4.225`, `6.100`, `5.725`, `8.538` — for `Echoes`, `Cities` and `Artifacts`.
Twelve for twelve.

`Unseen` looks like an exception and is not. Its LOGO GROUP measures
`1.2644 x calLogoSidelength`, but the group is the shield plus the five small
rectangles arranged below it, and those extend past the mark. The **shield
alone** measures

    15-card unsleeved   5.7250   against calLogoSidelength 5.7250
    10-card unsleeved   4.2250   against calLogoSidelength 4.2250

exact to four decimals on both. So the rule is the same on all four
expansions, and `1.2644` is just how far Unseen's rectangles reach.

> An earlier revision of this file recorded Unseen as a defective sketch. That
> was wrong, and wrong for an avoidable reason: the group was measured where
> the mark should have been. The commit stands in history; this is the
> correction.

### Two of the cached Unseen files ARE stale

What survives from that is smaller and real. Across the four cached Unseen
configurations the group measures

    M10-Un  5.342     M10-Sl  5.342     M15-Un  7.239     M15-Sl  5.342

The two UNSLEEVED ones scale correctly (`1.2644 x` their own
`calLogoSidelength`). Both **SLEEVED** ones are stuck at the 10-card unsleeved
value. That is not a sketch that fails to scale — a broken sketch would fail
everywhere — it is two exports carrying older geometry, which is exactly what
`automation/PIPELINE.md` already records for the toppers a version bump pulled
back into the worklist.

So: `Topper Unseen M10-Sl.3mf` and `Topper Unseen M15-Sl.3mf` want re-exporting.
Nothing needs changing in Onshape.

## The lettering: its CAP BAND fills the space between the margins

The logo tracks `calLogoSidelength`. The lettering does **not** — they are two
different rules on the same face, and building the text off `calLogoSidelength`
would be wrong by 13%.

The rule is:

    cap height = depth - 1.600 - 3 * #LogoEdgeDist

with the margins being `#LogoEdgeDist` at the top and `#LogoEdgeDist*2` at the
bottom, so `3 *` is simply both of them, and `1.600` the two `0.800` walls.
`depth` is the topper's own, `2.000 + calSlotDepth`.

### What confirms it

Not one fit, but the SHAPE of the residual. Measured across **all 20** cached M
files — five expansions by four configurations — the ink's height divided by
that band is **constant per expansion to four decimal places** and varies only
between expansions:

| expansion | ink / band | why |
|---|---|---|
| `Unseen` | 1.0052 | `U n s e e n` — no ascenders, so the ink IS the cap band |
| `Echoes` | 1.0690 | the `h` |
| `Cities` | 1.0831 | the `t` and the `i` dots |
| `Artifacts` | 1.0831 | the `t` and `f` |
| `Figures` | **1.4032** | the `g` DESCENDER |

That is exactly the signature of a correct rule: a font's ink-to-cap ratio is a
property of the WORD, so a rule that sizes the cap band leaves a per-expansion
constant behind and nothing else. A wrong rule would leave a residual that
moved with the configuration, and none of these do.

`Unseen` at `1.0052` is the strongest single check — it has no ascender and no
descender, so its ink is the cap band itself, and it reproduces the band to
half a percent on all four configurations.

### The typeface, and what the band actually is

**Noto Serif Bold** (Allan), and the measured ratios confirm it in a way worth
recording: `Cities` and `Artifacts` measure the SAME ratio, `1.0831`, and Noto
Serif Bold is the only candidate that predicts them equal — it gives both
`1.0924`, because its `t` and `f` reach the same height. Noto Serif Regular
splits them (`1.0784` / `1.0924`), Open Sans Bold splits them
(`1.0780` / `1.0855`), and Orbitron Bold collapses everything to `1.0694`.
Two words agreeing exactly is a far sharper test than any single ratio.

The band is then **`0.7202 em`**, and NOT the font's `sCapHeight` of `0.714`.
Dividing each word's ink-per-em by its measured ratio gives the band directly:

    Unseen     0.72025      Cities     0.72016
    Echoes     0.72030      Artifacts  0.72016

Four words, four different first letters, agreeing to `1.5e-4`. `0.7202` is
within `0.03%` of the `0.720` that `cad/text.CAP` already carries for Orbitron,
which suggests Onshape constrains a nominal `0.72 em` box rather than the
face's own cap height — but that is an inference, and `0.7202` is what is
measured.

**`Figures` gives `0.71693`**, `0.45%` off the other four. Its ink is `0.041 mm`
taller than Noto Serif Bold 2.015 predicts on the deepest configuration. Not
understood. A plausible cause is a different release of the `g` — glyphs do
move between font versions — but nothing here confirms that, and it is written
down rather than smoothed over.

### `Figures` is why the bottom margin is doubled

`1.4032` is the outlier and it is the one Allan flagged: the `g` descender puts
40% more ink below the cap line than any other expansion has, and the doubled
bottom margin is what catches it. On the deepest configuration its ink is
`9.191` in a `depth - 1.600` of `10.150` — it fits, with `0.959` to spare, and
it would not fit under symmetric margins.

So `#LogoEdgeDist*2` is load-bearing on exactly one of the six toppers. Anyone
tidying it to `#LogoEdgeDist` would see five of six still look right.

### The 65% follows

`PIPELINE.md` records the 10-card lettering as "exactly 65%" of the 15-card,
and `topper_split.py`'s glyph fingerprints depend on that being a pure scale.
It is now a CONSEQUENCE rather than an observation: the bands are `2.600` and
`4.000` unsleeved, and `2.6 / 4.0` is `0.6500`.

## Cities, and `#TopperTotalWidth`

`Cities` is drawn in two sketches, and the second uses the first: `Cities Draft`
carries the construction geometry — `calLogoSidelength/8` and
`calLogoSidelength/5` — and `Cities` traces the eight-pointed star over it. Only
the draft's numbers are needed.

`#TopperTotalWidth` is a **measured** variable, not an assigned one: it reads
the length of an `Edge of Top and front edges` and exists for Allan's own
reference. Nothing consumes it, and nothing here should.

## Still open

- **`Top and front edges`, the last feature.** Every edge measured above
  already has it mixed in. An export with it SUPPRESSED would make it
  measurable on its own — the same trick as `Box Dominion 246S without final
  fillet` — and is the cheapest thing that would move this on.
- **The `Divider` sketch**, so `14.800` is derived rather than assumed.
- **`Fillet front holes` and `Fillet Lip Room`** radii.
- **`Other side` and `Linear pattern 1`** — what each mirrors or patterns, and
  the count. 46 features is too many to infer from an outline.
- **What sets `Z = 48.450`.** Constant on all 48; if it is only the assembly
  mate then it is placement, not a formula, and should be recorded as such.
- **The tab/holder mate has no guarantee any more.** Onshape's import made it
  true by construction. `tests/test_topper.py` must assert the topper's tabs
  land in the holder's tab slots, computed independently from both modules, or
  a divergence in either part will print as a part that does not clip on.
- **`Figures` sits 0.45% off the band constant** the other four share. See
  "The typeface" — not understood, and not blocking.
- **`Figures`' construction** is two concentric circles with a radial gap of
  `calLogoSidelength/5`, but which region is the mark — the annulus alone, or
  the disc with a ring — is not settled. It is one solid in the corpus, which
  an annulus is.
- **Two cached Unseen files are stale** (`M10-Sl`, `M15-Sl`) and want
  re-exporting. Not a modelling problem.
- **The text scaling rule.** `PIPELINE.md` records the 10-card text as exactly
  65% of the 15-card, because the text sits in the topper's depth. That wants
  deriving rather than transcribing, and the pair that isolates it is one
  expansion at 10 and 15 cards, same size and sleeving.
