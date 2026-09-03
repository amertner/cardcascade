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
| `Topper Blank M5.15.15.62-Sl without top and front edges.step` | the same feature suppressed — but at a DIFFERENT parameter set, `M5.10.10.32-Un` (10 cards, unsleeved). One solid, 133 faces against the other's 445 |
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

It pairs instead with the cached **`Topper Blank M10-Un.3mf`**, which is the
same parameter set with the fillet applied. A mesh is lossy, but Onshape's
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
| `Top and front edges` | `r 0.800`, see above |

## The posts

Material stands at every slot boundary, **including both ends**:

    post width      14.800     centred on the boundary
    end posts        7.400     half a post, at each end of the part
    corner fillets   0.600     on each vertical edge
    opening/slot    calSlotwidth - 14.800    (55.400 Sl, 53.400 Un)

Confirmed on all eight blanks, across both sizes, both card counts and both
sleevings. `More Dividers` patterns the `Divider` feature at `calSlotwidth`
with an instance count of `HorizontalSlots - 1` — 3 on an M box — which is the
full posts; the two half-posts at the ends come from the body itself.

Re-measured on the UNFILLETED body, where nothing is blended: the posts are
`14.800` exactly at `Z 55` and above, the end posts `7.400`, and the first full
post's centre is `calSlotwidth` from the left edge.

`14.800` is `2 x 7.400` and `#FootDistanceFromWall` is `7.400`, which would
read as the post straddling the pusher's path. The `Divider` sketch is drawn on
`Face of Remove Inner Hole` and is a rectangle over the slant — it gives the
profile but not where the `14.800` comes from. **Still a hypothesis, not a
measurement.** It is not encoded.

## The holder tabs

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

### The rule holds on three of the four, and NOT on Unseen

Measured against all four M configurations of each expansion in
`individual/Innovation/`:

| expansion | M10-Un | M10-Sl | M15-Un | M15-Sl |
|---|---|---|---|---|
| `calLogoSidelength` | 4.2250 | 6.1000 | 5.7250 | 8.5375 |
| `Echoes` | **4.225** | **6.100** | **5.725** | **8.538** |
| `Cities` | **4.225** | **6.100** | **5.725** | **8.538** |
| `Artifacts` | **4.225** | **6.100** | **5.725** | **8.538** |
| `Unseen` | 5.342 | 5.342 | 7.239 | 5.342 |

So **the logo's width IS `calLogoSidelength`, exactly, twelve times out of
twelve** — for Echoes, Cities and Artifacts.

**Unseen does not follow it.** Its mark takes only two widths across the four
configurations, and neither is its own row's `calLogoSidelength`: three
configurations share 5.342 and one has 7.239. The two are in the same ratio to
each other as `calLogoSidelength` at 10 and 15 cards unsleeved (1.2645 either
way), so the mark is scaling with SOMETHING — just never with the value its own
row has.

**The logos are all meant to scale to the topper** (Allan), so this is a
DEFECT rather than a design, and it is Unseen's alone. Two candidates:

- **Its sketch is under-constrained.** Unseen has by far the most
  sub-dimensions and is the only one with elements placed by ANGLE (five
  rectangles at 0, +-25, +-50 degrees), so it is the most likely to have a
  dimension that did not get tied to `calLogoSidelength`.
- **Those exports are stale.** `automation/PIPELINE.md` records the 15-card
  toppers as the ones a version bump pulled back into the worklist, and
  `M15-Sl` carrying the same 5.342 as the 10-card files is what a stale export
  would look like.

The two have opposite fixes — a sketch to correct in Onshape, or four files to
re-export — so it wants settling before the logos are built. `cad/` will build
Unseen to the same rule as the other three, which means it will DIFFER from
the cached Unseen files; that divergence is intended and the test should assert
both ends, as the TokenHolder's clipped engravings do.

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
- **The `Expansion Name` group.** The logo constructions, `#LogoEdgeDist` and
  the placement are now recorded above; `#TopperTotalWidth = 4.4` is not, and
  the `Cities` FINAL sketch's own dimensions are not (only its draft's).
  Deliberately not started: the blank comes first (Allan), and there is no
  point fitting lettering to a body that cannot yet be reproduced.
- **Unseen's logo does not scale** where the other three do — see above. A
  defect, not a design, and it needs a decision on which fix.
- **The text scaling rule.** `PIPELINE.md` records the 10-card text as exactly
  65% of the 15-card, because the text sits in the topper's depth. That wants
  deriving rather than transcribing, and the pair that isolates it is one
  expansion at 10 and 15 cards, same size and sleeving.
