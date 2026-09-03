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
| `Topper Unseen M5.15.15.62-Sl.step` | `spec/reference/` — Innovation `4 Ages 5 Expansions` Sl, 0 API calls |
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

`14.800` is `2 x 7.400` and `#FootDistanceFromWall` is `7.400`, which would
read as the post straddling the pusher's path. **That is a hypothesis, not a
measurement** — the `Divider` sketch has not been seen. It is not encoded.

## The holder tabs

Two, one at each end of the part, standing above the body:

    thickness   1.600 (= #WallThickness)
    inset       1.300 from each end of the part
    Y           -21.856 .. -12.550   (9.306 of the 11.750 depth)
    Z           ~69.050 .. 93.650
    extrude     44 mm blind (Allan)

The sketch carries `1.6`, `1.2` and `0.1`. These are what mate the topper to
the holder.

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
- **The `Expansion Name` group** — 19 features, `#LogoEdgeDist = 0.6`,
  `#TopperTotalWidth = 4.4`, and the logo. Deliberately not started: the blank
  comes first (Allan), and there is no point fitting lettering to a body that
  cannot yet be reproduced.
- **The text scaling rule.** `PIPELINE.md` records the 10-card text as exactly
  65% of the 15-card, because the text sits in the topper's depth. That wants
  deriving rather than transcribing, and the pair that isolates it is one
  expansion at 10 and 15 cards, same size and sleeving.
