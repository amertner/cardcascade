# The Topper, measured

**DONE** — `cad/parts/topper.py` builds the blank and all six expansions; the
closing section says what remains open. This is the measurement record, written
down as it was established rather than at the end, so the open questions stay
visible. "Still open" at the bottom
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
| `Topper Artifacts M5.15.15.62-Sl.step` | one per remaining expansion, all at M15-Sl, which is what solved the last three marks |
| `Topper Echoes M5.15.15.62-Sl.step` | " |
| `Topper Figures M5.15.15.62-Sl.step` | " — and the one that settled whether `Figures` is an annulus |
| `Topper Unseen M5.15.15.62-Sl.step` | " — REPLACES a stale export of the same name, and confirms the shield's rule at a second `calLogoSidelength` |
| `Topper M5.15.15.62-Sl to Remove Inner Hole.step` | the feature tree ROLLED BACK to that feature |
| `Topper M5.15.15.62-Sl after More Dividers.step` | rolled back to there |
| `Topper M5.15.15.62-Sl after Linear pattern 1.step` | rolled back to there — the last feature before `Upside Down`. The three bracket every group of the blank, so each one is a subtraction rather than an inference |
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

`45.200` is a constant across capacity, size and sleeving — but it is not an
arbitrary one. The tabs stand off the FLOOR and are extruded `44 mm` blind
(Allan), so the height is `FLOOR 1.200 + 44.000`. `topper.TOTAL_HEIGHT` is
written as that sum.

## Assembly position

    X   -34.500 .. 241.500      (sleeved; -33.500 .. 234.500 unsleeved)
    Y   -2 * depth .. -depth
    Z    48.450 .. 93.650

Constant on all 48. The Y rule is exact: the topper sits one full depth back
from the origin, which is the slot it caps.

`Z = 48.450` was a placement constant — asked whether it comes from a variable,
Allan's first answer was that it does not matter. On 2026-09-04 he described
the placement itself: there is NO mate; the topper rests on the holder, logo up,
diagonal meeting diagonal, its fins sliding into the holder's lip rooms. That
derives it: `topper.z_base(p, d) = holder.slant_top(d) + topper_height(p, d)`,
the holder's slant top plus the topper's own rear thickness, `44.250 + 4.200`
on every one of the eight parameter sets — constant because every Innovation
topper row has five risers. `Z_BASE` stays as the catalogue's value and
`tests/test_topper.py` holds the derivation to it on every set.

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
rather than to the holder being finished and correct. That mattered when this
was written — `holder.py` was then about 2% heavy and not printable, and the
parts the topper needs (envelope, slant, lip geometry) were in its proven half.
The Holder has since landed: all ten references asserted, `+0.007%` once its
intended text divergence is set aside, and every written mesh closed and
manifold (`spec/HOLDER.md`). The argument for binding to the rule stands
anyway, which is why it is kept.

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

### `Top and front edges` — solved exactly

The feature is named for the SKETCH's orientation; `Upside Down` sits between
them in the tree, so the sketch's top and front are the assembly's **bottom and
ends**.

The filleted `Topper Unseen M5.10.10.32-Un.step` says which edges without any
inference: its body carries exactly **eight cylinders at `r 0.800` and no
tori**, which is a complete answer.

| the edge | the cylinder |
|---|---|
| the bottom face's whole perimeter | 4, spanning `width - 2r` and `depth - 2r` |
| the ends' FRONT vertical edges | 2, `Z_BASE + r` up to the wall top |
| the ends' REAR vertical edges | 2, `Z_BASE + r` up to **`slant_z(rear + r)`** |

That last row is the tell that this is ONE fillet on a connected chain and not
four separate ones. The rear vertical edge itself stops at `Z_BASE +
#TopperHeight` — `52.650` — where the slant begins; the fillet surface runs
past it and the slant face trims it. `55.173` on M10-Un at slope `3.1538`, and
`53.848` on M15-Sl at `1.4977`: `slant_z` at `rear + r` on both, to three
decimals. A fillet built as four independent rounds would stop at `52.650` and
be wrong by `2.523` on one row and `1.198` on the other.

No tori means the four bottom corners are BSPLINE blends, not toroidal ones,
which is what one fillet on a closed loop gives.

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

## The front-wall removal, and its fillet

`Remove most of front` and its companions take the front wall away above
`FRONT_WALL_RISE`, over `calSlotwidth - 2*BAND_HALF`, centred on each SLOT
CENTRE — which is what leaves the `14.800` band at each boundary.

The rollback's removed solids measure `58.200` wide against that rule's
`54.200`, and the difference is not the cut. It is `Fillet front holes`: a
`2.000` round on each vertical corner, with "allow edge overflow", reaching
`2.000` past each end. The band measures `14.800` on all four references, which
is what says the cut is the narrower number.

### The fillet is built into the TOOL

OCCT will not put a `2.000` round on an `0.800` wall — which is precisely what
Onshape's "allow edge overflow" is for — so `front_removal` carries the round
in its own profile instead of running `fillet()` on the body. The reference
says what the answer has to be: **16 quarter-cylinders of `r 2.000`**, each
spanning the wall's own `0.800`, four per opening. Their positions say which
edges, and the two kinds go opposite ways:

| corner | the second face | which way |
|---|---|---|
| BOTTOM | the opening's own floor | the round ADDS material inside the opening, so the tool's corner is cut away |
| TOP | the WALL'S TOP FACE | the round REMOVES material, so the tool grows `2.000` into the band each side |

Each is `(4 - pi) * r^2 * t = 0.6867 mm3`, eight of each, so they cancel:
`5.494 mm3` moves in each direction and **the total does not change at all**.
A volume check alone passes a body with neither, which is exactly the trap this
sat in while it was unbuilt. `tests/test_topper.py` checks both one-sided
differences separately, and both are now `0.000000`.

The `58.200` the rollback's removed solids measure against the rule's `54.200`
is the top pair's overflow, not the cut. The band measures `14.800` on all four
references, which is what says the cut is the narrower number.

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

`7.400` is NOT `#FootDistanceFromWall`, which an earlier revision guessed. The
`Remove most of front` sketch (Allan's screenshot, 2026-09-04) is drawn on the
`Remove Inner Hole` face and dimensions each opening's edge **`6`** from that
pocket's end, and **`6 + 0.6`** from the rib's face. The pocket's end is
`INNER_END_INSET 1.400` in from the part's end and the rib's face `RIB_W / 2 =
0.800` from the boundary, so both read `7.400`, and `topper.BAND_HALF` is now
`FRONT_MARGIN + INNER_END_INSET` with the second reading asserted against it.

### The lip notches are the HOLDER's lip base, with no clearance

An earlier revision of this file read the band from the floor's top to `2.000`
above it as open and called that the lip clearance. That was a section taken
inside the POCKET, where everything above the floor is open anyway; it said
nothing about the rear wall and it was wrong about which side of `51.650` the
material is on. The rollback settles it.

`Room for Lips` / `Remove Lip Room` / `Fillet Lip Room` / `Other side` /
`Linear pattern 1` cut **eight notches through the rear wall**, two per slot:

    floor       LIP_ROOM_RISE 2.000 above the topper's own floor top
    open        upward, running out through the slant
    through     the rear wall's full Y thickness
    fillet      LIP_FILLET 1.400 on the two BOTTOM corners, which is why the
                notch measures 12.400 at the top and 9.600 across its floor
    in X        14.200 .. 26.600 either side of the slot centre

That last row is not a number of the topper's own. It is the **Holder's lip
base**, `holder.lip_plan`, which measures `14.200 .. 26.600` — `LIP_LEN + 2 *
LIP_CHAMFER` wide, starting `LIP_GAP - LIP_CHAMFER` past the scallop's filleted
edge at `FINGER_R + FINGER_FILLET`. Not `LIP_LEN` and not the lip's flat: its
CHAMFERED BASE, with **no clearance at all**.

That is the same relationship `spec/HOLDER.md` records for `Lip Rest`, and it
is why `topper.lip_room_x` calls `holder.lip_plan` rather than writing
`20.400 +- 6.200`. It is also the one place where dropping `Import Holder` has
been paid back: half the topper/holder mate is now asserted from BOTH ends, out
of two modules that computed it independently.

`LIP_ROOM_RISE 2.000` is `#LipHeight`, and stays written as its own number:
`2.000` on both parameter sets cannot tell a constant from a variable, and
binding it to `holder.SLANT_STEP` on a hunch would be a false economy.

## The holder tabs

**Two**, one at each end — not one per slot, and not the three the feature
name's `x3` suggests (that is sketch, extrude and chamfer, one body each side).

    thickness   TAB_W 1.600 (= #WallThickness)
    inset       TAB_INSET 1.300 from each end of the part
    Z           the FLOOR's top, TAB_RISE 44.000 blind (Allan) — which is what
                makes TOTAL_HEIGHT 45.200
    Y front     the front wall's inner face, front - FRONT_WALL
    Y rear      TAB_REAR_GAP 1.200 in front of the POCKET's rear wall
    chamfer     TAB_CHAMFER 0.500, all round the top and down the two REAR
                vertical edges; the front edges stay square, because the tab
                merges into the front wall there

`TAB_REAR_GAP` is the one worth stating carefully. Measured off the rear FACE
it is `1.442` on M10-Un and `1.644` on M15-Sl — not a constant, and a rule
written that way would be wrong on every other row. The difference is exactly
`INNER_INSET * (cos 0.55529 - cos 0.30224)`: taken off the pocket's own rear
wall, which is `INNER_INSET` along the SLANT and therefore moves with the
slope, it is `1.200` on both to six decimals.

At each end the pocket's end wall (`INNER_END_INSET 1.400`) and the tab
(`1.300 .. 2.900`) overlap into one `2.900` block, which is what a ray one step
behind the front wall reads. An earlier revision recorded that block as
`TAB_INSET + TAB_W` without noticing the end wall is under it.

## Single-set cascades carry no toppers

A topper says which expansion is in a slot, so a cascade that holds only one
has no use for them (Allan) — and `individual/` bears that out: `Single Set`
and `Single Mini` have no cached topper of any expansion. `parts.csv`'s
`Set/Extension` column is what says which they are, `Base set or one
expansion` against `Ultimate, 1/4` and `Ultimate, 1/3rd`.

`cad.build.topper_catalogue` skips them on that column, which takes the
catalogue from 10 parameter sets to the 8 the cache has — so
`tests/test_topper_corpus.py` can hold every catalogued set to having a cached
file, instead of reporting a gap and carrying on.

That column is free text, so the match is on the phrase and not the whole
string. A future single-set row worded differently would get toppers built,
and the corpus test is where that would show up.

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

### All five marks are SOLVED, from their own STEPs

A filleted STEP differences exactly out of the blank, so every mark could be
DERIVED rather than traced. Each is a fraction of `calLogoSidelength` and
nothing else, and each reproduces its reference's AREA to **0.00002%** — the
residual is the inlay height's own rounding:

| mark | area, source vs reference |
|---|---|
| `Artifacts` | 42.51853 / 42.51853 |
| `Cities` | 14.70963 / 14.70962 |
| `Echoes` | 36.44445 / 36.44444 |
| `Figures` | 36.63796 / 36.63795 |
| `Unseen` | 42.96615 / 42.96614 at M15-Sl; 10.52249 and 19.32039 at two more |

**`Echoes`** is a diamond — a square turned 45 degrees with its vertices on the
box's edge midpoints, `(0, +-L/2)` and `(+-L/2, 0)`. Its area is `L**2 / 2`
exactly.

**`Figures`** is an **ANNULUS**, and that was the open question. The reference
answers it directly: the mark is ONE solid with TWO wires, where a disc with a
separate ring round it would be two solids. Outer radius `L/2`, inner
`L/2 - L/5`, so the radial gap is Allan's `L/5` — `2.56125` against `2.5613`.

**`Artifacts`** is two tall triangles that OVERLAP, and the overlap is the
point:

    left    (-L/2, -L/2)  ( L/8, -L/2)  (-L/4, L/2)
    right   ( L/2, -L/2)  (-L/8, -L/2)  ( L/4, L/2)

Each has its base on the box's bottom edge and its apex `L/4` in from a top
corner, and the bases cross the centre line by `L/8`. The union has FIVE edges,
not six — below the crossing the two bases are one line — and the notch where
the inner edges meet falls out at `(0, -1.42292)`, which the reference reads as
`(0.0000, -1.4229)`. Nothing places that vertex; it is where two lines cross.

**`Unseen`** is a shield and five rays.

    C            the shield's arc centre, at (0, 5L/14) — which is L/2 - L/7
    lower        a semicircle of radius L/2 about C, so the tip sits at -L/7
    upper        an arc from (-L/2, 5L/14) to (L/2, 5L/14) peaking at (0, L/2),
                 i.e. on the box's top edge
    rays         L/5 by L/10 rectangles at 0, +-25 and +-50 degrees

The upper arc's radius is NOT a number of its own: `(a^2 + s^2)/2s` for
`a = L/2` and `s = L/7` gives `3.99866` against `3.9987` measured. And the
rays' pivot is **C**, not the box centre — about C they sit at one radius to
`3e-5`, about the box centre they read `2.2387`, `1.6479`, `1.3782`. Their
inner edge is `L/12` clear of the semicircle's own rim, which is the `L/12` in
Allan's sketch.

**`Cities`** is eight triangles through the centre, not a traced outline, and
`Cities Draft`'s two numbers are their BASES:

    4 on the axes       apex L/2 out,       base L/5 across the centre
    4 on the diagonals  apex at (L/4, L/4), base L/8 across the centre

Their union is the star; the 16 vertices are where adjacent triangles' edges
cross and nothing places them directly. Predicted inner vertex
`(1.086307, 0.636398)` against `(1.08649, 0.63645)` measured, and the outer
tips fall out at `L/2` and `L/(2*sqrt 2)` exactly. The eight fuse to ONE face,
which is what the reference carries.

### The constructions, as read from the sketches

| expansion | construction |
|---|---|
| `Echoes` | a square rotated 45 degrees — a diamond — with its four vertices at the midpoints of the bounding box's edges |
| `Artifacts` | two tall triangles, bases on the box's bottom edge, apexes inset `calLogoSidelength/4` (1.06) from the left and right; they overlap |
| `Cities` | an eight-pointed star. Drawn in TWO sketches, `Cities Draft` and `Cities` — the draft carries the construction (`/8` = 0.53, `/5` = 0.85) and the final is the single filled outline |
| `Unseen` | a shield: a curved triangle whose main arc is `R = calLogoSidelength/2` (2.11), its top corners inset `calLogoSidelength/7` (0.6) both ways; below it five small rectangles on an arc at 0, +-25 and +-50 degrees, each `calLogoSidelength/5` (0.85) long by `calLogoSidelength/10` (0.42) wide, offset `calLogoSidelength/12` from the centre |
| `Figures` | two CONCENTRIC CIRCLES — an annulus — the radial gap between them `calLogoSidelength/5` (0.85). One solid in the corpus, which an annulus is |
| `Blank` | none — the blank carries no name and no logo |

These are read off screenshots, so the RATIOS are exact (they are expressions).
Vertex placement is confirmed for `Artifacts` and `Cities` too since
2026-09-04: `Topper Artifacts / Cities / Figures S5.15.15.62-Sl.step` are a
SECOND SIZE (S, three horizontal slots, `calLogoSidelength` different), and all
three reproduce area, piece count, width, centre and every piece's centroid
and sign; `Topper Blank S5.15.15.45-Un.step` is the first filleted blank
reference and the third parameter set for `BAND_HALF` and `LIP_ROOM_RISE`,
which both hold on it (envelope to `1e-4`, volume to `0.05 mm3`, symmetric
difference under `0.5`).

### Placing the mark and the name

Both sit on the `Face of CardHeight`, and the `Expansion Name` sketch gives the
three numbers that place them:

    text starts at   #calLogoSidelength*3/2 + 3mm    9.34
    top margin       #LogoEdgeDist                   0.60
    bottom margin    #LogoEdgeDist*2                 1.20

All three are measured from the FLAT underside — inside `Top and front edges` —
and all three now check out against the engraving differenced exactly out of
the blank. `text starts at` places the **pen**, not the ink: what is left over
is the first glyph's own left bearing, and `U` reads `0.01609 em` and
`0.01610 em` on two parameter sets whose sizes differ by 54%.

The **mark** fills a `calLogoSidelength` square whose left edge is
`calLogoSidelength/2 + 1.000` past that datum — so its right edge lands at
`calLogoSidelength*3/2 + 1`, exactly `2.000` before the pen — and which is
centred in the DEPTH. The two fillets cancel in that centring, so it is the
face's own centre and does not move with `EDGE_ROUND`:

    box top = (front + rear)/2 - calLogoSidelength/2

    predicted   -11.11250   -14.86250   -21.89375
    measured    -11.112     -14.862     -21.894

for `calLogoSidelength` `4.225`, `5.725` and `8.5375`. `Cities` fills the
square exactly. `Unseen`'s shield fills its width and sits on its top edge,
and the five rays are drawn OUTSIDE it — symmetrically, so the group is
`1.2644 * L` wide and shares the box's centre. That is where the `1.2644`
comes from, and it is why the box is the shield's box and not the group's.

The engraving is **`0.810`** deep, not the `0.800` the wall and the fillet make
it tempting to assume: the pocket runs `Z 48.450..49.260` on all three
references. The STEP's separate inlay solids are `0.810` tall too, but sit at
`48.440..49.250` — so they stand `0.010` proud of the underside and leave
`0.010` clear at the pocket's top, the same trick the Lid's logo inlays use.
`topper.inlays` builds them the same way from the same sketch, and since
2026-09-05 `cad.build` writes them beside the body as `Part 2`, `Part 3`, ...
— until then the built topper was ONE body, a name cut as an empty pocket
with nothing to fill it, which `cad.compare` found the moment a cad project
was held to a shipped one (every shipped topper prints in two slots).
`tests/test_topper.py` holds our inlays to the STEP's solid for solid.

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

### ALL FOUR SLEEVED cached Unseen files are stale

Measured off the pocket's top rim in all eight, the mark's width is
`1.2644 * calLogoSidelength` on the four UNSLEEVED files and a flat `5.3422` on
the four SLEEVED ones — and `5.3422` is `1.2644 * 4.2250`, the M10-Un size. The
mark was frozen at one configuration in every sleeved export.

An earlier revision of this file said "two", which is what comparing only the
`M` files shows. The hand-exported `Topper Unseen M5.15.15.62-Sl.step` has it
right at `10.7949`, so this is a fault in the CACHE and not in the source, and
the four want re-exporting. `tests/test_topper_corpus.py` lists them, asserts
they are stale in exactly this way, and excludes only those four from the
volume comparison — so re-exporting them makes the test say so rather than
quietly passing on a shorter list.

### The original note, which found two of the four

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

**Floored since 2026-09-04** (`cad/text.py`, "floors"; Allan): the lettering
is held to the CUT floor of `0.200` mm — `3.70` em for Noto Serif Bold, whose
hairline is `0.054` em. Cut and not proud, although the sketch stands the
inlay `0.010` proud: the topper prints face down and flat, the lettering is
a second-filament fill in a pocket, and the `0.010` is there to make the
sliver work (Allan). The rule below gives `3.61` em on the two 10-card
unsleeved sizes (`S10-Un`, `M10-Un`; `5.4` and up everywhere else), and
those two are raised to `3.70`. A `6.00` topper's flat is `4.40`; with the
cap band at `BAND_EM` and `Figures`' `g` (Onshape's, `0.2406` em deep) under
it, the sketch's 1:2 margins hold `4.07` em, so the raise fits, and
`baseline_y` shares what the flat has left in that 1:2 rather than holding
the baseline at `2 * LogoEdgeDist`. The PROUD floor would have wanted `4.63`,
which the flat cannot hold — tried, and the `g` went `0.403` into the front
round, which `tests/test_topper.py`'s descender check caught; that is why
the floor's kind matters here. `tests/test_topper.py` measures `Unseen
M10-Un`'s STEP against the unfloored rule and the build against the floored
one, and the cached 10-card unsleeved toppers in `individual/` differ from
`build/` by exactly this.

The logo tracks `calLogoSidelength`. The lettering does **not** — they are two
different rules on the same face, and building the text off `calLogoSidelength`
would be wrong by 13%.

The rule is:

    cap height = depth - 2 * EDGE_ROUND - 3 * #LogoEdgeDist

with the margins being `#LogoEdgeDist` at the top and `#LogoEdgeDist*2` at the
bottom, so `3 *` is simply both of them. `depth` is the topper's own,
`2.000 + calSlotDepth`.

The `2 * EDGE_ROUND` is the two **`Top and front edges` fillets**, and an
earlier revision of this file had it as "the two `0.800` walls". That was
wrong and it was luck that it agreed: the front wall IS `0.800`, but the rear
one is `0.242` on M10-Un. It is why Allan said the offsets do not work without
the fillet — everything in this group is measured from the FLAT part of the
underside, `topper.face_datum`, not from the part's own edge.

The exact engraving confirms both margins on all three sound references:

    baseline   (front - EDGE_ROUND) - 2*#LogoEdgeDist    -8.000  -10.400  -14.950
    band top   (rear  + EDGE_ROUND) +   #LogoEdgeDist   -10.600  -14.400  -21.500

and the baseline is exact rather than close: the letters with flat bottoms —
`n` in `Unseen`, `t` and `i` in `Cities` — sit ON it, and only the round ones
overshoot, by the font's own `yMin`.

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

**`Figures` reads `0.45%` off the other four, and it is the FONT.** Measured
again on the exact STEPs rather than on meshes, the four agree with the
vendored Noto Serif Bold to `0.013%` and `Figures` is `0.455%` taller —
`9.1910` against `9.1493` at M15-Sl. The `g` is the only glyph the five do not
share, so Onshape's descends `0.00459 em` deeper than the vendored one.

That is the same difference `s` shows, and it puts the earlier note — "a
plausible cause is a different release of the `g`" — on evidence rather than on
a hunch. Nothing is tuned to it; what is checked instead is that the `g` still
CLEARS, with Onshape's deeper one, on every row.

### `Figures` is why the bottom margin is doubled

`1.4032` is the outlier and it is the one Allan flagged: the `g` descender puts
40% more ink below the cap line than any other expansion has, and the doubled
bottom margin is what catches it. On the deepest configuration its ink is
`9.191` in a `depth - 1.600` of `10.150` — it fits, with `0.959` to spare, and
it would not fit under symmetric margins.

So `#LogoEdgeDist*2` is load-bearing on exactly one of the six toppers. Anyone
tidying it to `#LogoEdgeDist` would see five of six still look right.

`tests/test_topper.py` checks it on all eight rows and with **Onshape's**
deeper `g`, not the vendored one — clearance runs `0.697` down to `0.212`, and
the tightest is the DEEPEST configuration, which is not where one would look
first.

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

## The vendored Noto Serif Bold is not Onshape's

Per-glyph, the lettering reproduces: every letter's ink box lands within
`0.005` of the reference, and the two `Unseen` references — sizes `3.6101` and
`5.5540`, a 54% difference — give the SAME deviations in font units, so
whatever this is, it is a property of the font and not of the fit.

What does not reproduce exactly is the advance. Measured as a per-pair
deviation in units of 1/1000 em, identically on both `Unseen` references:

    Un  +0.1     ns  -2.9     se  +10.0     ee  -1.1     en  -0.9

and on `Cities`:

    Ci  -1.0     it  +0.0     ti  +0.0      ie  -0.0     es  -4.1

The vendored file has **no kern pairs at all** for any of these, and OCCT's
whole-word render agrees with the per-glyph sum to `0.001`, so this is not
something the layout is doing. `s` is the common thread: its ink measures
`3.6/1000 em` WIDER in the references than the vendored file draws it, which
is a different outline, not a different position. `e -1.1/-0.9` against
`e -4.1` only stops being contradictory once `s`'s own left bearing is allowed
to differ too.

So the two files differ, and `s` at least is a different glyph. The vendored
one came from the Google Fonts CSS API (`fonts/README.md` records that), which
serves the current release; Onshape's is whatever it shipped with.

**It does not block anything, and it is closed.** Allan does not know which
version Onshape uses and is content with the vendored one.

What makes that safe to accept is the SHAPE of the error, not its size: the
ink's drift is a constant fraction of the em — `0.0055` on all three sizes
measured, which differ by 2.5x — so it is a difference in the font's METRICS
and not a fault in the placement, which would move with the configuration.
`tests/test_topper.py` bounds it at `0.008 em` and asserts the constancy
itself. In absolute terms it is `0.020` to `0.050` mm, on an engraving `0.810`
deep cut with a `0.400` nozzle.

## `Solid.volume` is the wrong metric for a NAMED topper

Worth writing down because it cost an hour of "fixing" a boolean that was
correct all along. OCCT's `GProp` over-reports a body carrying this many small
BSpline faces:

    M10-Un Unseen   reported 4101.406   but `blank - named` says 4100.663
    the same part,
    hand-exported   reported 4100.698   — the same kind of error, in the STEP

The tessellated volumes agree to `0.0014%` (`4100.2642` against `4100.2082`),
and the engraving differenced back out agrees to `0.03%` — `19.29311` against
`19.29953`, in 12 solids either way, with both `e`s and both `n`s identical.
So the source is right and the metric was not. `tests/test_topper.py` uses the
tessellated volume and the differenced engraving; `Solid.volume` appears
nowhere in the named-topper checks.

## The filename does not carry everything the shape depends on

Onshape names a topper `{size}{cards}-{Sl|Un}`, and that is the cache's own
key — but the topper's slant is the Holder's, which comes from
`calHeightIncrement`, which comes from **`RisingSliders`**. Every Innovation
row that gets toppers has 5 risers, so the name is sound in practice.

`Single Set` is the proof that it is not sound in principle: 3 risers, the same
three-part key as `3 Later Ages`, and a slope of `2.727` against `2.130` — a
5% difference in volume under one filename. It is excluded as a single-set
cascade, so nothing collides today, and `build.topper_catalogue` raises rather
than letting whichever row came first win.

## Still open

**The Topper is finished.** The blank reproduces all three rollbacks and the
unfilleted export with zero symmetric difference in both directions; all five
marks reproduce their references' area to `0.00002%`; and all 44 sound cached
files reproduce within `0.0061%`. `cad.build --part topper` writes the whole
48-file catalogue in 95 seconds.

What is left is small, and mostly not about the geometry.

- **The four sleeved cached `Unseen` files want re-exporting.** Not a
  modelling problem — see above. Everything else in the corpus reproduces.
- **The tab/holder mate is still only half asserted.** The LIP side is now
  proved from both ends — `topper.lip_room_x` is `holder.lip_plan`, and
  `tests/test_topper.py` holds them together. The TABS are not: `holder.py`
  stops after the rear lips and does not yet build the feature the tab lands
  in, so there is nothing on that side to assert against. It goes in as soon as
  the holder does.
- ~~**The `Divider` sketch has no dimensions**~~ (Allan, 2026-09-04): it maps
  onto the holder's imported `Top slant angle` triangle to replicate its
  diagonal, which `cascade_slope` already has. `BAND_HALF` was never its: it is
  `Remove most of front`'s `6` from the pocket's end plus the pocket's `1.400`
  end inset — see "Ribs and front bands". Settled.
- ~~**`LIP_ROOM_RISE 2.000`**~~ IS `holder.SLANT_STEP` by construction, the
  same imported points, and is bound to it (2026-09-04).
- **The text scaling rule.** `PIPELINE.md` records the 10-card text as exactly
  65% of the 15-card, because the text sits in the topper's depth. That wants
  deriving rather than transcribing, and the pair that isolates it is one
  expansion at 10 and 15 cards, same size and sleeving.
