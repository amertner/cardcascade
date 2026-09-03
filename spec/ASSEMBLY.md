# Assemblies

Placing the `cad/` parts into a whole cascade, in the two states a cascade has:
**closed** (on the shelf) and **cascaded** (open, ready to play). Two purposes,
and they pull in the same direction:

1. **A fit test.** Every clearance in the design is currently asserted one part
   at a time, against a reference that only ever shows that part. An assembly
   is the first thing that can measure the mechanism: does the tab sit in the
   cutout, does the plate sit in the channel, does the holder clear the rib.
2. **Renders.** Front, back, left, right, top, bottom and one perspective, per
   state, for listings and for looking at a build without Studio.

They pull in the same direction more literally than expected: the closed lid's
logo came out upside down under a placement that measured `0.0000 mm3` against
every part, because the two candidates differed by a proper rotation and no
number could see it. A render is part of the checking, not its output.

Nothing here is a new geometry input. Every placement below is derived from
`derive.py` and the part modules, and where a placement had to be *chosen*
rather than derived, this file says so and says what settled it.

`cad/assembly.py` is this file in code — placements and nothing else, importing
no build123d, the same split `derive.py` has. `cad/assemble.py` writes the
3MFs, `cad/fit.py` measures them.

---

## The cascade frame

The **Box's part frame is the assembly frame**: X width with 0 at the centre,
Y depth with 0 at the centre and +Y toward the back, Z with 0 at the bed. The
Box is therefore placed by the identity, which is also what `cad/build.py`
already does ("Boxes are NOT placed in an assembly offset — the part studio's
origin is the assembly's").

Every other part carries a transform into that frame. The corpus cannot supply
one: `individual/<Game>/_raw/Assembly *.3mf` looks like it should, but its
`<components>` transforms are the **print layout** — six parts translated side
by side on a bed — and `assembly_split.py` discards them and writes each object
at its own part-studio coordinates. So the components on disk are each in their
own frame and no shared frame exists anywhere in the repo. Building one is the
work.

## The three assemblies

| state | contents |
|---|---|
| `closed` | Box, holders on the floor over the sliders, pushers stored in the rear, TokenHolder(s) in the front pocket, a topper on each holder (Innovation) |
| `closed-lid` | the same, plus the Lid inverted over the Box |
| `play` | Lid opening-up underneath, Box sitting in it, pushers standing in the Lid's sockets and rising through the Box's floor slot, holders on the pushers' treads and riding the sliders |

Counts come from `plan_exports.compose`: one Box, one Lid, `pushers` (2, or 3
on M/L for every game but Innovation), `RisingSliders` holders — one of them
the `FirstHolder` where `Cards/First Riser` is set — and, where parts.csv's
`TokenHolder` column says so, a TokenHolder plus a HalfTokenHolder on a merged
row. `--half` swaps the HALF in on a merged row; the two are alternatives for
one slot, so only one is ever placed.

## The placements

### Lid, closed — a 180° turn about Y, and it is a choice

    box = (-lid_x,  lid_y + 2.250,  (WallThickness + BoxHeight) - lid_z)

The Z half is written down in `parts/lid.py`: "a box height `h` arrives at
`WALL + BoxHeight - h` in the lid's frame", in `closing_grooves`. The check is
the closing mechanism — the Box's bump tops out at box `z 90.000` and the
groove's bottom edge sits at lid `z 16.600`, and `106.600 - 16.600 = 90.000`
exactly. The Lid's rim lands at box `z 66.600`, so the two overlap by 38.400.

**Which axis the turn is about, nothing geometric can decide — the lid goes on
either way round.** The two candidates differ by a half turn about Z, a proper
rotation, so:

* the closing groove fits either way. The Box's bump sits at box `y
  -1.750..6.250`, symmetric about the `2.250` both turns pivot on, so it
  arrives at lid `y -4.000..4.000` under both;
* interference is `0.0000 mm3` under both. The sockets hang from box `z
  105.000` to `100.000`; the rear storage caps at `REAR_TOP` 85.000, the front
  pocket at 87.500, and a holder tops out at ~93.05 on every cascade
  (`CardHeight` is 92.000 for every game), so nothing of the box or its
  contents reaches them at either end;
* the sockets are EMPTY when a cascade is closed — the pushers are in the rear
  storage — so nothing functional depends on where they land.

The only thing that can tell is the logo, and it does not agree with itself.

## The logo finding: three games disagree with the fourth

The lid's logo pattern is in the floor's OUTER face, which points up once the
lid is on, so it is the one mark a closed cascade shows. Rendered in plan:

| game | reads upright under |
|---|---|
| Dominion | a turn about **X** |
| Compile | a turn about **Y** |
| FCM | a turn about **Y** |
| Innovation | a turn about **Y** |

**One game's mark is upside down on a closed lid whichever turn is chosen.**
Nothing in `cad/` rotates the artwork — there is no per-game transform in
`parts/lid.py` or `art.py` — so the four `logos/<Game>/lid_logo.dxf` disagree
with each other. And the build's inlays match the cached Onshape lid's to 0.001
in every X span, so Onshape imported the same files and **this is on the
shipped product**, not on the rebuild.

`Y` is used, because three of the four read correctly under it. That is a
majority and not a proof. The fix is a rotation of one DXF or of three, and
which is Allan's call.

The route to this is worth recording, because it is a lesson about method
twice over. The placement was first written as `Y`, then changed to `X` on the
strength of a single Dominion render that came out upside down, then changed
back when four games were rendered instead of one. Inferring a placement from
one instance of imported artwork is exactly the mistake `spec/LID.md` records
under "What the fit got wrong". And it took a PICTURE to see any of it: an
upside-down logo is invisible to every number `cad/fit.py` computes, because
the two candidates differ by a proper rotation.

### Lid, open — the Box drops into it

    box = (lid_x,  lid_y + 2.250,  lid_z - WallThickness)

The Lid inner is `BoxWidth + 1.400` wide and `box_depth + 4.900` deep, against
a Box footprint of `BoxWidth` by `box_depth + 4.500` (the sketch box plus
`REAR_DEPTH`): **0.700 a side** in width and **0.400 total** in depth. The Box's
floor sits on the Lid's floor.

### Pusher, stored — hung in the rear storage

The part is turned on edge and upright: its **rise runs up the box's Z**, its
**depth across the box's X**, and its **thickness into the 3.200 slot band** in
Y. That is `pusher_rest`'s own reading — `#dBackSlotWidth` is
`calPusherTotalDepth + 4.000` measured along the width.

* **X** — the tabs sit at part `y = -D/2 ± s` and the Box's rim cutouts at
  `slot_centre ± s`, so part `y = -D/2` maps to `slot_centre`. Slot centres are
  `box.pusher_slots`.
* **Z** — part `x = 0` (the leading edge, where the tabs are) maps to box
  `z = BoxHeight`, i.e. **the pusher hangs by its tabs, top flush with the rim**.
  The evidence is `pusher_rest = min(25.000, BoxHeight - H - 0.500)`: it is a
  *catch* 0.500 below a top-flush pusher, not a shelf. Innovation's 87.000 mm
  pusher is the case where the `min` bites — rest 17.500, top 105.000, bottom
  18.000 — and the arithmetic only closes on the flush reading. The tab's
  5.000 then fills the rim cutout's `z 100.000..105.000` exactly.
* **Y** — the plate in the slot band (`box.slot_band`, 3.200 on a 3.000 plate),
  tabs pointing back into the cutouts cut through the 1.300 inner back wall.

Which way round the depth axis runs (`+y → +x` or `+y → -x`) is symmetric in
the tabs and is **not** derivable from the lock; only one lets the staircase
sit in the cavity. The fit test picks it.

### Pusher, in play — in the Lid socket

Vertical, plate in the socket's `LID_CHANNEL_W` (3.300 on a 3.000 plate — the
tightest running clearance in the mechanism), tabs in the two recesses cut into
the channel's −X wall at `centre ± s`, notch over the key rib (C3–C5). The
socket stands at lid `z 1.600..6.600`, so the leading edge goes down into it and
the rise runs up through the Box's `bottom_slot`. Confirmed reachable: on
Dominion `S4.16.10`, socket centres are ±63.0 against a floor slot 137.100 wide.

Innovation is the one asymmetry, and it is settled: a lid gets 3 sockets from
M up (`lid.socket_count` is the plain size rule) while the cascade ships **2**
pushers (`isOnlyTwoPusherSlots`), and **the middle socket is the unused one**
(Allan). The open state uses the OUTER PAIR — `socket_centres`' `k = 0` and
`k = 2`. Only the two Innovation M rows are affected, `M5.15.15` and
`M5.10.10`; every S and XS Innovation lid has two sockets already. The socket
itself is to be dropped from the Lid eventually, at a cost `spec/LID.md`
records; until it is, the assembly renders will show it empty, which is the
honest picture of what ships.

### Holder

* **X** — `box_x = holder_x - (HorizontalSlots - 1) * calSlotwidth / 2`. The
  holder is `calSlotwidth * H + 9.800` wide in a `calSlotwidth * H + 11.100`
  inner box, so it centres with **0.650 a side**, and its 1.900 end slots take
  the Box's 1.500 slider ribs.
* **Y** — one holder per rib, its side slot on that rib: `box.slider_ribs`
  gives the rib backs, and the slot is centred on the holder's depth.
* **Z, closed** — the base on the floor: `box_z = holder_z + WallThickness +
  (CardHeight - 1.5)/2`. The two `side_floor` strips are what it rests on, which
  is what they are for.
* **Z, open** — the base on the pusher's step `k`, whose tread is at part
  `x = k * calHeightIncrement`, so the whole set rises `calHeightIncrement` a
  riser and the slant tops make one diagonal.

The `FirstHolder` is the deeper one and takes the first (frontmost) rib, which
is the one `slider_ribs` places at `calFirstSliderDistance`.

### TokenHolder — a half turn about Z, and the FULL only

Its frame's origin is already **the slot's corner** — X at the slot's left edge,
Y at its front edge, Z at the base — so the placement is just where that slot is
in the box: `box.front_dividers` in X, `box.pocket_span` in Y,
`z = WallThickness`.

**Its Y runs the opposite way to the box's**, so with X alone flipped the
placement would be a MIRROR, which no physical part is. A half turn about Z is
the only proper rotation that fits, and it also says what "left edge of the
slot" means: left as seen from behind, which is the box's **+X** end.

Two independent expressions give that end and agree exactly — the last front
divider's right edge plus `calTokenHolderSlotWidth`, and the right inner wall
less `FrontPocketSidePaddingWidth`, both 94.250 on `S4.16.10`. The **divider**
is used as the datum, though they give the same number, because it is the
sketch's own. The rival placement at the inner wall itself collides with the
Box by 1457.2448 mm3, so this is a test that distinguishes rather than one that
merely permits.

**FULL and HALF are alternatives, not both at once.** They are the same width,
and `spec/TOKENHOLDER.md` says a half holder is not half of a full one and that
they are not meant to stack in depth. A merged cascade ships one of each and
the slot takes whichever suits; the assembly places the FULL, which every
token-holder row gets.

### Topper — sectioned, and one question left

Allan: **the toppers slide into the top of the holders, covering the cards**.
The cached Topper is exported in the **Holder's own frame**, so the mate is
measured off two meshes rather than guessed. On Innovation `S5.15.15`, and
confirmed on the 10-card pair:

| | X | Y | Z |
|---|---|---|---|
| `Holder 3x15-r5-Un` | -38.400 … 172.400 | -8.000 … 0.844 | -45.250 … 46.173 |
| `Topper Blank S15-Un` | -33.500 … 167.500 | -16.000 … -8.000 | 48.450 … 93.650 |

**What the topper is.** Sectioning it: the material at `x -33` and `x 167` — its
two ends — spans the full 45.200 of Z and the full 8.000 of Y, and between them
there is almost nothing except a rail at `z ~51.6` and another at `z ~93`. So it
is a FRAME: two tall end plates joined by two rails, which is exactly the shape
of the loose toppers in Allan's third photo, a long bar with an arm at each end.

**X is settled and is a real mate.** The end plates run `-33.500 … -32.700`,
0.800 thick, and the holder's end block's inner face is at `-34.400` with the
first compartment wall's outer face at `-33.500`. The plate therefore sits
inside the outermost card compartment, hard against its outer wall — and a card
is `calSlotwidth - 3.000` wide in a compartment `calSlotwidth - 1.600` wide, so
there is 1.500 of slack at each end of the compartment for a 0.800 plate to
slide down in. That is the "slides into the top of the holder".

**Z says which holder it belongs to.** The topper's underside is `48.450`. Its
own holder's cards top out at `48.550` — a 92.000 card in a pocket whose floor
is at `-43.450`. The topper caps its own holder's cards with 0.100 of overlap.
Under the alternative reading (the topper belonging to the holder one slot
forward, which in a cascade is one `calHeightIncrement` lower) its underside
would float 17.300 above that holder's cards, which is not a mate at all.

**The one question left.** The export has the topper exactly one holder DEPTH
(8.000, not the 8.400 of a slider distance) forward of the holder drawn with
it. Either the studio drew the holder alongside for reference and the mate is
`topper Y = holder Y`, or the offset is deliberate. Z says the first; the
suspiciously exact 8.000 says the offset means something. Both positions are
collision-free against the cached holder, so the meshes cannot separate them.
**Allan.** Until then Innovation assembles without toppers, as it does now.

## The finding: the treads sit 0.150 forward of the ribs

Three things have to agree in Y, and two of them are a sliding fit:

* the Box's slider **ribs**, `SLIDER_W` 1.500;
* the Holder's **side slot**, `SLOT_W` 1.900, so the rib has 0.400 of play in
  it and the holder 0.200 either way from centred;
* the Pusher's **tread**, `calSliderDistance` long against a holder
  `calSliderDistance - 0.400` deep, so another 0.400 of play.

They do not agree. With the pusher centred in its lid socket, a tread's centre
lands **0.150 forward** of its rib's, and

    rib centre   = BD/2 - WallThickness - SLIDER_W/2 - sd/2
    tread centre = BD/2 - 2.500 - sd/2

so the difference is `2.500 - (1.600 + 0.750)` — a **constant**, with every
parameter cancelling. It is the same 0.150 on every cascade in the catalogue.

Nothing is broken by it: the holder is still fully supported. But it eats
0.150 of the 0.400 the tread has, so a holder centred on its rib sits with
**0.350 at the front of its tread and 0.050 at the back**, and 0.050 is the
tightest number anywhere in a cascade.

The holder is left centred on its **rib** in both states rather than split
between the two datums, because the rib is the datum that exists in both, and
the design's own claim is that the holders ride the same ribs whether the
cascade is open or shut. Re-datuming the pusher to close the 0.150 is a change
to the Lid's socket placement — `SOCKET_BACK` — and that is a geometry change
with its own cost, not a placement decision.

## Where the parts come from

A resolver, because two of them are not finished:

| part | default | why |
|---|---|---|
| Box, Lid, Pusher, TokenHolder | `cad/` source (B-rep) | done, and they are the whole lock mechanism |
| Holder | cached `individual/<Game>/Holder *.3mf` | the source Holder is ~2 % heavy and not printable (`spec/HOLDER.md`) |
| Topper | cached `individual/Innovation/Topper *.3mf` | not written in `cad/`; the mate is measured off the cached mesh, see above |

`cad.assemble --holder source` swaps the build123d Holder in, and is how the
Holder's convergence gets watched. It is also the only way to assemble the two
`M6.21.10-12` cascades at all: `Holder M-21-r6-{Un,Sl} (first)` has never been
exported from Onshape, so they have no first-riser holder on disk. With cached
holders they are skipped and named, rather than quietly given a standard holder
of the wrong DEPTH. The run prints which source it used.

## What the fit test measures

Per pair of placed parts:

* **Interference** — exact B-rep common volume where both sides are source,
  which covers Box/Lid/Pusher/TokenHolder, i.e. every surface of the lock.
  Mesh-level AABB then triangle intersection where a cached Holder is involved.
  Any non-zero volume is a failure.
* **Margin** — minimum distance on each *named* mate, reported against what the
  standard says it should be:

  | mate | expected |
  |---|---|
  | plate in lid channel | 0.300 |
  | tab in box rim cutout | ±0.350 |
  | tab in lid recess | ±0.100 |
  | plate in box slot band | 0.200 |
  | holder in box, each side | 0.650 |
  | box in lid, each side | 0.700 (width), 0.400 total (depth) |
  | holder gap, front to back | `CardHolderGap` 0.400 |
  | pusher catch below a hung pusher | 0.500 |

  A margin outside its band is a warning with its number, not a pass.

`tests/test_assembly.py` asserts the table over the whole catalogue, the way
`test_lid_corpus.py` asserts the Lid's rules over all 44 cached lids. A margin
that holds on one cascade and not on 50 is the finding worth having.

## Output

* `build/assemblies/<Game>/<model> <state>.3mf` — gitignored and disposable,
  like the rest of `build/`. Written in the shape Onshape's `_raw` assemblies
  have: one `<object>` per distinct component and one carrying `<components>`
  with the transforms, so eight holders cost one mesh and Studio reads it.
  `mesh3mf` grows a `write_assembly`/`read_assembly` pair for it.
* `tmp/render/…` — the PNGs, also disposable.

## Renders

`cad/render.py` grows what an assembly needs and keeps what it has:

* an RGB buffer and a colour per part, instead of one grey Lambert;
* a scene of several meshes sharing one z-buffer;
* named cameras — `front`, `back`, `left`, `top`, `bottom`, plus one
  perspective hero shot, which needs a real perspective divide (the renderer is
  orthographic today);
* `--assembly` as the shorthand, beside the existing `--box`.

## Order of work

1. `mesh3mf` assembly writer/reader, and `cad/assembly.py` with the **closed,
   no lid** state for Dominion `S4.16.10`. Look at it.
2. The Lid, both states — bump into groove, box into lid.
3. The open/cascaded state.
4. `cad/fit.py` and `tests/test_assembly.py`.
5. The renderer: colour, the six views, the perspective.
6. Generalise to the four representatives — a Dominion Mat row (TokenHolder and
   Half), Innovation, Compile (spanning holders), FCM — with `--game`/`--model`
   for any other and `--all` in the background.

## Open, and what settles each

* ~~Which way the pusher's depth axis runs in storage.~~ Not open: two axes are
  forced by features and the third by right-handedness.
* **Which lid mark is the reference, and which three turn.** Parked (Allan,
  2026-09-03 — away from the printed boxes). Nothing geometric in the lid
  distinguishes the two ways it closes, so the physical product is the only
  authority: look at a closed box, and whichever game reads upright is the
  reference. The placement stays on the **Y** turn meanwhile, which leaves
  Dominion upside down and Compile, FCM and Innovation upright.

  When it is settled the fix is a 180° rotation of one DXF or of three, and it
  is **geometry-neutral**: the mark is sized and placed from its bounding box
  (`logo_scale`, `logo_offset`), and a half turn preserves that exactly — same
  size, same position, same fit. Cost is a wash either way: Dominion is 24 of
  the 50 lids, the other three games 26 between them.
* **The topper's Y** — whether the exported 8.000 offset is the mate or a
  reference layout. Sectioning settled everything else about the part; this it
  cannot settle. Allan.
* **A `--holder=source` run will report Holder margins that fail.** That is the
  Holder's known 2 %, not the assembly's, and the report says which part came
  from where so the two never get confused.
