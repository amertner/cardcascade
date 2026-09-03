# Assemblies — the plan

Placing the `cad/` parts into a whole cascade, in the two states a cascade has:
**closed** (on the shelf) and **cascaded** (open, ready to play). Two purposes,
and they pull in the same direction:

1. **A fit test.** Every clearance in the design is currently asserted one part
   at a time, against a reference that only ever shows that part. An assembly
   is the first thing that can measure the mechanism: does the tab sit in the
   cutout, does the plate sit in the channel, does the holder clear the rib.
2. **Renders.** Front, back, side, top, bottom and one perspective, per state,
   for listings and for looking at a build without Studio.

Nothing here is a new geometry input. Every placement below is derived from
`derive.py` and the part modules, and where a placement had to be *chosen*
rather than derived, this file says so and says what settles it.

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
| `open` | Lid opening-up underneath, Box sitting in it, pushers standing in the Lid's sockets and rising through the Box's floor slot, holders on the pushers' steps and riding the sliders |

Counts come from `plan_exports.compose`: one Box, one Lid, `pushers` (2, or 3
on M/L for every game but Innovation), `RisingSliders` holders — one of them
the `FirstHolder` where `Cards/First Riser` is set — and, where parts.csv's
`TokenHolder` column says so, a TokenHolder plus a HalfTokenHolder on a merged
row.

## The placements

### Lid, closed — a 180° turn about Y

    box = (-lid_x,  lid_y + 2.250,  (WallThickness + BoxHeight) - lid_z)

Both terms are already written down in `parts/lid.py`: `lid_y = box_y - 2.250`
in the module docstring, and "a box height `h` arrives at `WALL + BoxHeight - h`
in the lid's frame" in `closing_grooves`. The check is the closing mechanism —
the Box's bump tops out at box `z 90.000` and the groove's bottom edge sits at
lid `z 16.600`, and `106.600 - 16.600 = 90.000` exactly. The Lid's rim lands at
box `z 66.600`, so the two overlap by 38.400.

The turn is about **Y**, not X: the Lid's sockets are placed `SOCKET_BACK` in
from its *back* face, so front and back are fixed and cannot flip. The X mirror
is what is left, and it is what the fit test confirms.

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

### TokenHolder

Its frame's origin is already **the slot's corner** — X at the slot's left edge,
Y at its front edge, Z at the base — so the placement is just where that slot is
in the box: `box.front_dividers` in X, `box.pocket_span` in Y,
`z = WallThickness`. The HALF sits behind the FULL in the merged slot.

### Topper — one per holder, capping its cards

Allan: **the toppers slide into the top of the holders, covering the cards**,
and his photos show them — a long strip, a label on its face, a lip at each end
and small tabs along its length.

The cached meshes make this measurable rather than inferred, because the
**Topper is exported in the Holder's own frame**. On Innovation `S5.15.15`:

| | X | Y | Z |
|---|---|---|---|
| `Holder 3x15-r5-Un` | −38.400 … 172.400 | −8.000 … 0.844 | −45.250 … 46.173 |
| `Topper Cities S15-Un` | −33.500 … 167.500 | −16.000 … −8.000 | 48.450 … 93.650 |

Three facts fall straight out, and each is confirmed on the 10-card pair
(`Holder 3x10-r5-Un` / `Topper Cities S10-Un`) as well:

* **X** — the topper is inset **4.900 = `holder.END_EXTRA`** at each end, so it
  spans exactly the holder's width between its two end blocks. That is what the
  end lips in the photo hook over, and it means the topper's width is
  `calSlotwidth * HorizontalSlots` with no constant of its own.
* **Y** — the topper is exactly one **holder depth** forward of the imported
  holder's body: −2d … −d against the holder's −d … 0, at d = 8.000 and again
  at d = 6.000. A rule, not a coincidence.
* **Z** — bottom at a constant **48.450**, top at **93.650**, identical at both
  card counts. That bottom sits just above the card tops (a 92.000 card in a
  pocket whose floor is at −43.050 reaches 48.950), which is the "covering the
  cards" of Allan's description: the strip receives the top of the stack.

What is **not** settled by bounding boxes is which slot the topper occupies —
its own holder's, or the one in front. The Onshape topper studio imports a
Holder for reference and the two readings differ by exactly one `d`. Sectioning
the two cached meshes at an end lip settles it: only one of the two puts the
lip's hook around the holder's end block. That is a mesh measurement in a frame
the two parts already share, 0 API calls, and it is the first thing the Topper
work does. If the section is ambiguous, it goes to Allan rather than being
picked.

Count: one topper per holder in use, from the six shipped (five expansions and
a blank); rows in `components.no_toppers` carry none.

## Where the parts come from

A resolver, because two of them are not finished:

| part | default | why |
|---|---|---|
| Box, Lid, Pusher, TokenHolder | `cad/` source (B-rep) | done, and they are the whole lock mechanism |
| Holder | cached `individual/<Game>/Holder *.3mf` | the source Holder is ~2 % heavy and not printable (`spec/HOLDER.md`) |
| Topper | cached `individual/Innovation/Topper *.3mf` | not written in `cad/`; the mate is measured off the cached mesh, see above |

`--holder=source` swaps the build123d Holder in, and is how the Holder's
convergence gets watched. The report names the source of every part, so no
render is ever ambiguous about what it is showing.

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

* **Which way the pusher's depth axis runs in storage.** Symmetric in the lock;
  the fit test picks it (step 1).
* **The Lid's X mirror when closed.** Symmetric in the grooves; the floor
  engraving and the fit test pick it (step 2).
* **Which slot a topper occupies** — its own holder's, or the one in front.
  Settled by sectioning the two cached meshes at an end lip; Allan if ambiguous.
* **A `--holder=source` run will report Holder margins that fail.** That is the
  Holder's known 2 %, not the assembly's, and the report says which part came
  from where so the two never get confused.
