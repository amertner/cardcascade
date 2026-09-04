# The TokenHolder, measured

The open tray that drops into the last compartment of the box's front pocket —
the one `calFrontSlotsExceptTokenHolderSlot` does not count — and holds the
game's tokens instead of cards. **Dominion only**: no other game's studio has
one and no other parts.csv row asks for one.

Two configurations, **FULL** and **HALF**, which turn out to be the same part
at two depths. `automation/plan_exports.compose` is the design record for when
each is emitted; this file is the geometry.

## The references

Two hand-exported STEPs in `spec/reference/`, 0 API calls, and the whole of
`individual/Dominion/`:

| file | row | configuration |
|---|---|---|
| `TokenHolder M6.21.10.62-Sl.step` | Dominion `324 Card` Sl, `M6.21.10.62-Sl` | FULL |
| `HalfTokenHolder M6.21.10.62-Sl.step` | the same row | HALF |

**The pair is the point**, the same trick as the Box's filleted/unfilleted twin
and the Lid's with/without-logo one: it is ONE configuration exported twice, so
the difference between them isolates exactly what `half` changes and nothing
else. What it changes is one number. The two have the **same 231 faces and the
same 644 edges**, and differ only in Y.

Behind them are **18 cached components** in `individual/Dominion/` — five front
capacities (16, 21, 40, 50, 60), both sleevings, both Mat states. Those are
what say a rule holds rather than a coincidence, and they are usable as a
regression target rather than merely a shape reference, because:

> **The TokenHolder has not changed in 7.0** (Allan). The divider has always
> been there.

So the only thing the version bump moves is the `CC 6.6` / `CC 7.0` in the
engraved string, and `tests/test_token_holder_corpus.py` builds at
`Version="6.6"` and compares like for like. This is the opposite of the
Pusher's situation, where 14 of the 32 cached files are pre-7.0 geometry that
`cad/` deliberately does not reproduce.

## The frame

    X   0 at the LEFT EDGE OF THE SLOT, the part starting CLEARANCE in
    Y   0 at the FRONT EDGE OF THE SLOT, NEGATIVE going back, again CLEARANCE in
    Z   0 at the base, the wall tops at 75.000

The origin is **the slot's corner, not the part's**. That is not a reading of
one export — all 18 cached components and both STEPs start at exactly
`X +0.400, Y -0.400, Z 0`, whatever their width or depth, and the part's own
size is `2 * 0.400` short of the opening on both axes. It is the clearance that
lets the tray drop into the front pocket, and it means `build()` needs no
assembly transform at all, unlike the Pusher's.

## The slot it fits

`#calTokenHolderSlotWidth` is what is left of the front pocket once the card
compartments have taken their slots. Allan's expression, transcribed into
`derive.py` as written:

    #BoxWidth
      - #calFrontSlotsExceptTokenHolderSlot * #calSlotwidth
      - 2 * #WallThickness
      - #calFrontDividerLeftSpacing
      - #FrontPocketSidePaddingWidth

**`HorizontalSlots` cancels out of it.** `#BoxWidth` is
`2*WallThickness + 11.1 + calSlotwidth*HorizontalSlots` and
`calFrontSlotsExceptTokenHolderSlot` is `HorizontalSlots - 1`, so the whole
thing collapses to

    plain box    calSlotwidth      - 0.600
    Mat box    2*calSlotwidth      - 0.600

because `MatPocket` drops one more from the count
(`calFrontSlotsForCards = HorizontalSlots - 2`). **That is the whole of what
"merged" means to this part**: the mat merges two front slots into one and the
token holder gets both of them. Confirmed against the four widths on disk:

| | `calSlotwidth` | slot | part width |
|---|---|---|---|
| Sl, plain | 65.000 | 64.400 | **63.100** |
| Un, plain | 63.000 | 62.400 | **61.100** |
| Sl, merged | 65.000 | 129.400 | **128.100** |
| Un, merged | 63.000 | 125.400 | **124.100** |

Exact on all 18. That a token holder does not depend on the slot count is worth
stating plainly, because it is why `plan_exports` can key one on
`(capacity, merged, sleeved)` and be right — see "One file, two model codes"
below for where the same key then goes wrong.

## The two sketched numbers

Allan's sketches give the outline directly, and both read against the `324
Card` sleeved row (`calSlotwidth 65.000`, `calFrontPocketDepth 12.600`):

    #calTokenHolderSlotWidth - 0.5mm        =  63.9
    2.6mm + #calFrontPocketDepth/2          =   8.9

The first is the width of the sketched rectangle; the finished part is that
less `2 * CLEARANCE`, so `63.900 - 0.800 = 63.100`. The second is the **HALF**
holder's depth, likewise less the clearances: `8.900 - 0.800 = 8.100`. The FULL
holder simply takes the whole pocket, `calFrontPocketDepth - 0.800 = 11.800`.

So:

    width       = calTokenHolderSlotWidth - 0.500 - 2*0.400
    depth FULL  = calFrontPocketDepth               - 2*0.400
    depth HALF  = 2.600 + calFrontPocketDepth/2     - 2*0.400

Both depth rules are exact on all 18 — twelve FULL holders from 5.280 to 35.200
and four HALF ones at 8.100, 13.800, 5.790 and 9.400.

**A HALF holder is not half of a FULL one**, and the `2.600` is why: two of
them (17.800 on the 21-card sleeved row) do not fit in one pocket (12.600).
They are not meant to stack in depth. `PIPELINE.md` records the rule that
emits them — the merged mat pocket always splits into full + half, so a
merged-slot cascade gets one of each and a plain one gets only the full.

## The shell

    outer       width x depth x 75.000
    side walls  1.900   (the two ends, in X)
    end walls   1.400   (front and back, in Y)
    floor       1.400
    rim round   0.600, on the INNER top edge ONLY

`75.000` is `#FrontPocketHeight`, and it is a constant on every reference
whatever the capacity. The outer top edge stays sharp: the rim reads as an
`0.800` flat at the front and back and `1.300` at the ends, which is each wall
less the round, and the sections confirm it at every height.

## The token divider

One wall across the middle:

    2.000 wide, the full cavity depth, from the floor to a half-round cap
    whose apex is 10.000 below the rim — a 2.000 bead at Z 65.000

It is **centred on the part, and there is exactly one however wide the part
gets**. The eight merged references are twice as wide and still carry a single
centred divider; nothing splits into three. Read off the meshes as the only
material in the cavity's height band that is not a side wall, and confirmed in
the STEP as a `1.000` cylinder on a Y axis at `(31.950, ·, 64.000)` whose area
is exactly `π * 1 * 9 = 28.274`.

## The grip

The thumb tab standing above the rear wall:

    a half-disc of radius 7.500, centred in X, its centre ON the rim
    1.600 thick — #WallThickness, 0.200 MORE than the wall it stands on
    both its top edges rounded 0.500

The radius is not assumed. Two sections give the chord — `14.866` at Z 76 and
`11.180` at Z 80 — and a circle through both has its centre at `Z 75.000`
exactly, on the rim, with `r = 7.500`. So the part's overall height is
`75.000 + 7.500 = 82.500` on **every** parameter set, which is why all 18
cached meshes are 82.489 tall (the 0.011 is the chord of the tessellated apex).

The `0.200` it stands proud of the wall shows as a ledge at the rim, and the
section at the grip's own X is what settles the feature ORDER:

    Y -10.800, Z 65 -> 75   the rear wall's inner face, STRAIGHT to the rim
    Y -10.800 -> -10.600 at Z 75    the ledge
    Y -10.600, Z 75 -> 82   the grip's inner face

There is **no arc between them**, where every other X has one. The rim round is
missing exactly where the grip stands, and the reference carries it as two
`0.600` cylinders rather than one — so, whatever the features are called, the
grip exists before the rim is rounded. (The feature tree for this part has not
been seen; the three sketches name only `Extrude 1`, `Shell 1`, `Token divider`
and `Branding`, and nothing here invents the rest.) `cad/` builds the round first and patches its footprint back in over
the grip's chord, which gives the same solid: a fillet asked to run out against
the grip's flank is one OCCT will not build, and asked to do it on the finished
part it segfaults.

That patch is the ONLY place the build and the reference differ in shape. At
the two ends of the grip's chord, Onshape's grip round and rim round blend into
each other and this one stops short. **0.15 mm³ of a 17819 mm³ part**, 0.0008%,
and every section outside a 0.6 mm band at the rim matches to 1e-3 mm².

## The branding

`CC <version> <model>` engraved `0.200` into the **underside**, in Orbitron
Bold — the same face and depth the Pusher and the Holder use. The model is
`calTokenHolderModel`, so the `324 Card` sleeved tray reads `CC 7.0 M21.Sl`.
The Holder writes `CC <version> - <GameName>` instead; this one carries the
model because a token holder's identity is its slot, not its game.

**The glyphs run toward -Y.** The tell is the `.`, which sits at Y
`-4.995..-4.248`, hard against `-4.248`: a period rests on the baseline, so
`-4.248` is the baseline and the ascender of `l` — which reaches `0.051` em
past the caps — goes to `-8.642` on the far side of it. That is what an
underside engraving has to be. Onshape sketched it on the bottom face, whose
outward normal is `-Z`, and a right-handed sketch on that face runs `(+X, -Y)`.
Built `+Y` it is legible from the wrong side.

Placement, both exact:

- the text box's origin sits **`10.000` in from the part's left edge** —
  measured to within `0.0002 mm` on every unclipped reference;
- the **CAP BAND** is centred on the part's depth. Not the ink: the cap band's
  midpoint is the part's midpoint exactly, while the ink's is `0.145` off,
  because `l` reaches past the caps on one side only.

### The size, and the term that is not explained

The em is fitted to the WIDTH. The ink starts one left bearing past `10.000`
and stops `TRAIL` em short of the right-hand `10.000`:

    em = (width - 2*10.000) / (advance - right_bearing(last glyph) + TRAIL)

with **`TRAIL`** — since 2026-09-04 DERIVED: a quarter of the font's space
advance, `text.box_trail`, `0.0765` for Orbitron Bold. Allan's right-aligned
samples (`spec/reference/Text right-aligned sample*.step`: four lines in three
fonts, boxes `10` tall, one right edge at `x 110.135`) read the ink `0.0761
±0.0004` em short of the edge for Orbitron Bold and `0.0646 ±0.0004` for Open
Sans Bold, whatever the last glyph; a quarter space is `0.0765` and `0.0649`,
and the Holder's own constant was `0.0646`. The `0.0754` below was measured,
not derived, and carries `±0.002` once the cap-band reading it rests on is
propagated, so it never disagreed. The record of that measurement: off the STEP,
where it is exact, it puts the em at `5.70000` against two independent readings
of the reference — the cap band at `0.720` em and the `l` at `0.771`, which
agree to four decimals. All 18 cached meshes give `0.0764 ± 0.001`, and
Onshape's own tessellation of a glyph outline is worth about that.

What makes it a constant of the LAYOUT rather than a fudge fitted to one
string: the sleeved family ends in `l` (right bearing `0.019`) and the
unsleeved in `n` (`0.053`), the two raw shortfalls are `0.0564` and `0.0234`,
and **the same number falls out of both** once the bearing is taken off. It
holds across five capacities, four widths and both Mat states.

**What it IS in Onshape's terms is not known.** It is not the left bearing
(`0.056`), not either right bearing, not their sum, and not any derived
variable. `spec/LID.md` records that a rule which reproduces the whole
catalogue can still be the wrong rule and that the tell is a term no derived
variable produces; this is such a term, and it is written down as one rather
than dressed up. Anyone who finds out what it is should say so here.

### Where the build deliberately differs

Onshape constrains the width **alone**. On a merged box that width doubles
while the depth is unchanged — or, on a half holder, nearly halved — and on
three of the 18 the rule asks for more ink than the part has:

| reference | ink wanted | part depth |
|---|---|---|
| `HalfTokenHolder 21-Sl merged` | 9.105 | 8.100 |
| `HalfTokenHolder 21-Un merged` | 7.180 | 5.790 |
| `TokenHolder 21-Un merged` | 7.180 | 7.180 |

On each, the engraving runs off the underside and nicks the outer faces of the
front and back walls. The tell is that **the ink's Y extent equals the part's
own to three decimals** — an outline clipping a sketch, not a size that fits.

So `cad/` bounds the depth too, keeping the same `CLEARANCE` of margin the part
keeps from its slot. It binds on exactly those three and on nothing else —
including `TokenHolder 21-Sl merged`, which at `9.105` in `11.800` is the
tightest of the ones that do fit and is left untouched. This is the same
divergence `cad/text.py` already carries for the Pusher, for the same reason:
Onshape can constrain sketch text in one dimension and a box that suits one
parameter set does not suit another.

`tests/test_token_holder_corpus.py` asserts **both ends** — the defect on the
reference and the fix on the build — so re-converging fails rather than passing
quietly.

## One file, two model codes

`plan_exports` keys a token holder `(front capacity, merged, sleeved)`. That
key is right about the geometry, for the reason in "The slot it fits":
`HorizontalSlots` cancels out, so a 3-slot and a 4-slot box with the same front
capacity genuinely want the same tray.

It is **wrong about the engraving**, which carries the size letter. Dominion
`324 Card` (`M`, 4 slots) and `333 Card` (`S`, 3 slots) both land on
`TokenHolder 21-Sl.3mf`, and the cached file is stamped `M21.Sl` — so one of
the two cascades ships a tray labelled for the other. The same collision hits
`40` (`S` from `300 Card`, `L` from `560 Card`).

`cad.build` therefore names the file by `calTokenHolderModel`, as it carries
the Pusher's first-riser axis for the same reason, and the catalogue comes out
at **22 files against `individual/`'s 18**. `--legacy-names` writes the old
names for a promotion and refuses when two model codes would land on one file.
CLAUDE.md's "the CAD is the authority on a box's model code" is the rule being
followed.

## Still open

- ~~**No unsleeved STEP.**~~ `HalfTokenHolder M6.21.10.45-Un.step` (2026-09-04)
  — exported as the HALF, `5.790` deep. Envelope to `1e-6`, volume to
  `0.001 %`, and the engraving reproduces with an `n` (right bearing `0.053`)
  where the sleeved string ends in `l` (`0.019`): **`TRAIL` is a property of
  the text box, not of the last glyph**, which is what one export with a
  different final glyph was asked to say. Its cause in Onshape's terms is
  still not known.
- ~~**No merged STEP.**~~ `HalfTokenHolder M4.21.10.45-M-Sl.step` (2026-09-04)
  — the merged HALF, `8.100` deep and `128.100` wide, which is ONE OF THE THREE
  clipped references (`9.105` of ink in an `8.100` part). It is now the exact
  record of that divergence: `tests/test_token_holder.py` reads Onshape's ink
  reaching the part's own front and back faces and ours stopping `CLEARANCE`
  short, heavier by under `0.1 %`. The FULL unsleeved and FULL merged trays
  still have no STEP; both rest on the cached meshes.
- **The three clipped engravings should be fixed in Onshape too**, or the
  divergence stays permanent. Until then `individual/` keeps three trays with
  nicked walls.
- **`Version` in the engraving.** The cached components say `CC 6.6` and
  `cad.build` writes `CC 7.0`, so promoting a built file into `individual/`
  changes the text even though the shape is identical. That is a real change to
  a published project, not a no-op — the same two-step job `PIPELINE.md`
  describes for a re-exported topper.
