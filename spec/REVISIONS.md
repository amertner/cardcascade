# Revisions — the release line, and what changed at each one

`cad/revisions.py` is the code; this is the record. It answers one question:
**what does a cascade built at 7.0 have that one built at 7.1 does not, and
why?**

## A REVISION CHANGE is not a DIVERGENCE

The distinction is the whole point of the mechanism, and getting it wrong is
what the mechanism prevents.

| | DIVERGENCE | REVISION CHANGE |
|---|---|---|
| what it is | `cad/` against **Onshape**, at the same version | `cad/` 7.0 against `cad/` 7.1 |
| how long | permanent | from its release on |
| lives in | the part, recorded in `spec/` | `cad/revisions.py`, recorded here |
| asserted by | the part's own test, both ends (`cad/README.md`, decision 6) | `tests/test_revisions.py`, both releases |

The four standing DIVERGENCES are the Box's hanging holes stopping at the slot
band, its `CC` where the sketch says `Rev`, the XS box's single fastener, and
the Lid's fitted logo. They apply at 7.0 and 7.1 alike and they are NOT in the
revisions table — putting them there would make the table read as a mixed bag
of switches instead of a release history. That was asked and settled (Allan,
2026-09-06).

## A version is a STRING

Short, usually numeric-looking — `7.0`, `7.1` — but it may be `7.1a`, `7.1.1`
or anything else that fits on a part, so nothing parses it (Allan,
2026-09-06). The iteration letter below is the first version on the line that
is not a number at all, and nothing had to change to admit it: it is a member
of `RELEASES` like any other string. A release's ORDER is its position in `RELEASES`, which is the only
place the line's order is stated, and `HISTORICAL` names the older versions
still asked about by name (`6.6`, which `tests/test_holder_corpus.py` prices
its engraving at). Anything else is refused: with opaque strings there is no
arithmetic that tells a real old release from a typo, so the answer is a list.

One consequence to know before choosing a version: the engraved-stamp reader
can only read a `digit . digit` word (`verify._dotted`), so a version of any
other shape — `7.1.1`, `7.1B` — is checkable by its METADATA alone. That is a
limit on the reader, not on the version, and it is why the metadata witness
exists at all.

## The two rules that keep it generalisable

**A part asks a NAMED question and never compares versions.** `d.rev.<flag>`,
never `d.Version >= "7.1"`. The flag name is what this file records and what a
reader greps for; a version comparison is invisible to both. Adding the next
change is one field in `revisions.Rev`, one `if` in the part, and one case in
`tests/test_revisions.py`.

**The line is monotonic.** A change introduced at 7.1 is in every release after
it — that is what a release line means. Undoing one later is a NEW flag with
its own `since`, not a hole in the table.

## How a release reaches a part

`Primary.Version` -> `derive` -> `d.rev`, a frozen record of one boolean per
change, riding on the `Derived`. That keeps the rule the rebuild already has:
every feature below `derive` takes the `Derived` alone. `rev` is deliberately
NOT one of the studio's variables — Onshape has no counterpart for it — so it
is a slot on `Derived` beside `_v` rather than a key inside it.

## The releases

### 7.0 — the Onshape generation

What every reference STEP in `spec/reference/` and every cached mesh in
`individual/` was exported at, and what every shipped cascade under
`cascades/` is. A 7.0 build must reproduce them exactly, forever; that is what
the corpus tests assert, and `tests/reference.py` is why they keep asserting it
when the default moves.

### 7.1 — the cad-built release, LOCKED 2026-09-10

On the line as plain **`7.1`**, at the END of it, and `CURRENT`. That is what
the lock means here: the line is ordered and a flag is on from its `since`
onward, so the last release carries every change the letters introduced — `7.1`
is `7.1d`'s geometry under a `CC 7.1` stamp, and its six flags are all six
below.

`7.1a` .. `7.1d` STAY on the line, unrenamed, each still only the flags at or
before its own letter. They are what the release was built as while it was
being worked on, and a version that has been built has to remain describable
and buildable. Not one flag's `since` moved at the lock either: they still name
the letter each change shipped in, which is what the letters are for and what
`tests/test_revisions.py` isolates them by.

**The first letter after the lock is `7.2a`** (2026-09-11), not `7.1e`: `7.1`
is on the line, so a change after it is a change after the release. `7.2a` is
below, with `rear_holder`, `7.2b` after it with `unmarked_lid`, `7.2c` after
that with `larger_lid_text`, and `7.2d` after that — open, with
`plain_box_plate`.

The same 7.0 **lock** (`lock.SAME_LOCK`, and `pusher.build` refuses a release
that has not declared one) under a `CC 7.1` stamp, so a cad-built cascade can
be told from an Onshape-exported one on the shelf — and, since the version goes
into the project name and title, in the file too.

Its geometry changes, in the order they were made:

* **`lid_socket_per_pusher`** — the Lid cuts one pusher socket per pusher the
  cascade ships (`box.pusher_slot_count`) instead of Onshape's plain size rule,
  so the four Innovation M lids lose their unused MIDDLE socket. Four lids and
  no others; the outer pair does not move, so no pusher and no margin changes.
  `spec/LID.md`, "The middle socket is gone".
* **`two_pushers`** — every cascade takes TWO pushers, whatever its size, where
  Onshape gave 3 to every M and L box that is not Innovation. It restates 24 of
  the 50 boxes — one fewer rear storage slot, divider and pair of rim cutouts —
  moves their thumb cutout, and ships one Pusher fewer in each of their
  projects. The Lid follows through the flag above, so nothing has three
  sockets at 7.1. `spec/BOX.md`, "Two pusher slots, at every size".
* **`thick_floor`** — the Box's floor is `2.000` where every wall stays
  `WallThickness`'s `1.600` (Allan). It is the two SIDE FLOORS that matter: the
  card area is cut clean through (`bottom_slot`), so what the floor actually is
  is the pair of strips the holders rest on, plus the front pocket's and the
  rear storage's. It grows **upward**, into the cavity, so nothing about the
  box's outside changes — same bounding box, same rim, same rim cutouts, same
  `Top of back`, same hanging holes, all of them measured from the bed — and
  the `0.400` comes out of the interior, which has `12.900` of headroom over
  the tallest holder on all 50 rows. Everything standing on the floor rises
  with it by exactly `0.400`: every holder and the token holder. The Lid keeps
  its `1.600` floor. `spec/BOX.md`, "The floor is 2.000, and it grows UPWARD".

The first three are `7.1a`. `7.1b` adds one:

* **`rear_thumbs_spread`** (`7.1b`) — the back pocket gets as many
  `Thumb Cutout in back`s as it takes to put one every `70.000` along it,
  spread evenly and centred on the pocket (Allan). Before it there is exactly
  one however wide the pocket is, and the pocket is `45.3` to `290.5` mm wide
  — `two_pushers` having just widened 24 of them by a whole slot pitch. The
  pitch is a CEILING and not a target: the gap cut is the largest one no wider
  than `70.000`, `34.90 .. 69.15` across the catalogue, and the outer pair
  keep `10.000` of wall at each end. `#calFingerHoleOffset` stops placing the
  cutout — the pocket does — so `box.rear_thumb_x` is now 7.0's and 7.1a's
  answer alone. It costs the outer back ledge its place in `sharp_edges`,
  which is a kernel limit and no geometry. `spec/BOX.md`, "A thumb cutout
  every 70 mm of back pocket".

And `7.1c` adds a fifth, the only one that reaches TWO parts at once:

* **`stout_lattice`** (`7.1c`) — the lattice window is `9.000` wide rather
  than `10.000` and there are FOUR rows of them where there were three, in the
  Box's `Hanging holes` and the Holder's `Vertical slits in holder` alike (and
  in the front pocket's slits, which are the same openings). The PITCH does
  not move and neither does the row band, so every `1.000` the window gives up
  is `1.000` the pillar between two windows gains, and four rows divide
  `HOLE_ROW_BOTTOM..HOLE_ROW_TOP` where three did. Both halves are for the
  PILLARS, which break: the Holder's is `1.800 x 0.800` at `calSlotwidth 63`
  and stands `18.167` free, and in every layer inside a window row it is an
  ISLAND — four per compartment per wall, each a free cantilever the nozzle
  brushes and the bridge above pulls on as it cools. It snaps at its base
  mid-print and is then captured by that bridge, which is why a broken one is
  found hanging from it (Allan, 2026-09-09, with the print to show it). `9.000`
  hands the mullion the whole `1.000` — `+56%` of section at `63` — and the
  fourth row cuts the free run to `13.125`, a tip deflection of `0.24x`.
  **Filleting the window corners was tried first, on real prints, and is
  WORSE**: a fillet at a window's TOP corner turns a clean short bridge into a
  progressively worsening overhang, and the sides stop running vertical. The
  constraint this change respects, and the reason it is a width and a count
  and not a shape, is **sides vertical, top horizontal**. `spec/BOX.md` and
  `spec/HOLDER.md`, "A stouter lattice".

And `7.1d` adds a sixth, the only one that changes no geometry at all:

* **`both_lid_editions`** (`7.1d`) — a cascade that carries a NON-DEFAULT
  edition of its game's mark ships the default edition too, as a second Lid on
  a plate of its own (Allan, 2026-09-10: "I need to include two lids on
  separate plates: one with the Innovation Ultimate logo, and one with the
  plain Innovation logo"). That is Innovation's two single-set cascades and so
  four projects — `S3.15.10` and `XS5.15.10`, sleeved and unsleeved — each of
  which keeps the plain `Innovation` lid it already carried and gains an
  `Innovation Ultimate` one beside it, for its owner to choose between at the
  printer. The rule is stated once, as a rule and not a table
  (`tables.lid_editions`): the edition the cascade carries, then the game's
  default where the two differ. Nothing a lid IS changes — the alternate is
  the same lid with the other mark in its underside, fitted by the same rule —
  so this is a change to what a project CONTAINS, which `two_pushers` already
  was in its second half. The alternate takes the edition's word as a suffix
  (`Lid S3.15.10.20-Un Ultimate.3mf`, object `Lid 135U Ultimate`) and the two
  plates are named after their objects, because "Lid 1 of 2" would not say
  which mark is on it. `spec/LID.md`, "Both editions ship, on a plate each".

**The flags are separable and the tests keep them so.** Two of the four reach
the Lid, so comparing 7.0 with 7.1 shows 28 lids changing and says nothing about
which flag did what; `tests/test_revisions.py` turns one flag on at a time
against a 7.0 Derived to isolate them. `thick_floor` needs the same treatment
for a different reason: `two_pushers` restates 24 boxes wholesale, so only a
7.0 Derived carrying the floor flag ALONE — same three slots, same `CC 7.0` ink
— can show that the floor moved and nothing else did. `rear_thumbs_spread` is
isolated the same way, and for a third reason: at 7.0 the pocket is a slot
pitch narrower, so the row it lays down there is not the row it lays down at
7.1b, and only the flag alone can price a cutout. That technique is the
reason a `Rev` is a record of independent booleans rather than a version number
to compare against.

### 7.2a — opened 2026-09-11, frozen 2026-09-13

`cascades/` stays the 7.1 release until 7.2 locks. One flag:

* **`rear_holder`** (`7.2a`, 2026-09-13) — every cascade's rearmost holder is
  a **`RearHolder`**: the same holder without its rear lips. The lips hook
  the holder behind, and behind the rearmost there is only the box's back
  wall, 0.950 away; a shallow slant's lips reach past it (0.3–0.4 mm of
  interference on Dominion's 8- and 9-riser cascades, 0.65 on a deep holder
  at the back — measured by intersecting the placed holder with the box,
  `spec/HOLDER.md`, "The RearHolder"). It replaces one plain Holder in every
  project, and where the row puts the deep slot at the BACK it replaces the
  FirstHolder, keeping that holder's depth and slant under the RearHolder
  name (`holder.build(..., rear=True)`, `assembly.rear_of`,
  `assembly.holder_kinds`, `build.holder_file`). The plain and first holders
  are byte-identical to 7.1's. Allan: generalised from the Three Expansions
  print, where the rear holder was the first to be built without lips.

**Opened for a flag that was withdrawn.** `low_profile` (2026-09-11) made
`S3.15.10.32-Sl` a 100 box with a 35 lid and a 3 mm, 3.2-wide, 12.2-wide
flared lid socket, so the closed single-set cascade lost 5 mm. Allan printed it
and withdrew it on 2026-09-13: the Innovation game box is 76 mm inside and
holds its cards flat, so a standing cascade lifts its lid whatever its height,
and 5 mm of lift was not worth a lid and box that only fit each other. The
flag and everything it gated are gone from the tree; the analysis that went
with it is kept here in one paragraph, because it is easy to get wrong again:
the label holder is NOT what stops a box being shorter (the closed lid's rim
sits at 66.6 to cover the front cutout, which the front-pocket cards set, so a
lid shrinks with its box), and slider engagement is not either (the design's
floor is 18 mm of rib, `(BoxHeight - 18) / RisingSliders`); what is, is the
lid's pusher sockets hanging 5 mm from its floor dead over the first and last
card compartments, 4.2 mm above a standing sleeved card. A shorter box is a
shorter socket, and a 3 mm socket wants a 3.2 channel and a wider, flared
block. `cad.fit` keeps the two margins that came out of it: "socket underside
over the card top" and "over the tallest holder".

**What 7.2a carries instead** — none of it a flag, all of it a ROW:

* the `Three Expansions` row, `M8.16.10-16`: four columns, eight 10-card
  risers, a 16-card first riser and front pocket, so 36 slots for three
  Innovation expansions of twelve sets each; two of them lie on their backs in
  the game box (286.9 along the 288, two closed heights along the 263, 74.1
  deep as the height unsleeved; 99.6 sleeved, which lifts the lid 23.6). Its
  card sets are placed by `assembly.card_fill` and drawn by `cad.assemble
  --cards` (`spec/RENDER.md`);
* three row options in parts.csv, each a `Primary` field and a `derive`
  variable, read by parts on that row alone: **`Deep slot` = back** (the deep
  first-riser slot at the back: `box.slider_ribs`, `pusher.slider_drops`,
  `box.lip_slope`, `assembly.holder_rib`, and the holder itself —
  `holder.deep_at_back`: no rear lips, the plain slant with a taller rear,
  `spec/HOLDER.md`); **`Sleeved card width`** (64 on this row, so the sleeved
  twin is as wide as the unsleeved); **`Toppers` = none** (the row's toppers
  would share Onshape's cache name with `M5.10.10`'s at a different slant,
  `build.ships_toppers`).

A row option is not a release change: no existing part moves, so there is no
flag for it and nothing for `tests/test_revisions.py` to assert at two ends —
except the one thing the new row DID change about an existing case, the
`lid_socket_per_pusher` set, which now names six Innovation M lids.

### 7.2b — opened and frozen 2026-09-13

One flag:

* **`unmarked_lid`** (`7.2b`, 2026-09-13) — every cascade ships a SECOND lid
  on a plate of its own, with **no mark in its underside** and **`(C)
  Mertner`** embossed where the game's name is on the lid the cascade carries
  (Allan: "a separate plate with a lid that has no logo on it, and where the
  game name embossed inside that lid is replaced"). Everything else on it is
  the cascade's own lid's — the capacity and model lines, the `Card Cascade`
  block with its version and staircase, the sockets, the grooves, the rounds
  — so it is one body in the second filament's absence, where the own lid is
  a body and its inlays. Like `both_lid_editions` a change to what a project
  CONTAINS: no existing lid moves, Innovation's two single-set cascades ship
  three lids, every other cascade two, and from here no project has a plate
  called just `Lid` (`layout.PLATE_SCHEME`'s `alt` names every lid plate
  after its object: `Lid 168U`, `Lid 168U Unmarked`).

  A lid is now one of three **variants** — `tables.LID_VARIANTS`: `LID_OWN`,
  `LID_ALTERNATE` (7.1d) and `LID_UNMARKED` — where it was a bool, and every
  name follows the alternate's suffix rule: `Lid S4.16.10.32-Un Unmarked.3mf`,
  object `Lid 168U Unmarked` (`tables.LID_UNMARKED_NAME`). `build.lid_variants_built`
  is the only place the two flags are asked; the part builds any variant at
  any release.

  **Why "(C) Mertner" and not "(C) Allan Mertner".** The full line was
  measured first: 45.6 wide at the game line's 3.5 cap, and right-aligned on
  the game line's edge it crosses a pusher socket on both XS lids (where the
  text block sits beside the sockets) and the staircase's top step on five
  3-slot S lids. Allan chose the short form everywhere rather than a per-lid
  fit (2026-09-13): 30.1 wide, and at least 12.4 clear of the logo block and
  every socket on all 52 lids at full size, which `tests/test_revisions.py`
  measures on the text solids. `(C)` is spelled out because Orbitron Bold
  has no `©`. `lid.CREDIT`, `spec/LID.md` "An unmarked lid, on a plate of
  its own".

### 7.2c — 2026-09-13

One flag:

* **`larger_lid_text`** (`7.2c`, 2026-09-13) — the Lid's three-line text
  block (capacity, game name or credit, model) is **scaled up where the lid
  has room** (Allan: "a bit larger when space permits ... easier to read and
  nicer on larger cascades. Do not simply expand to use all space as that
  would be too large sometimes"). Before the flag the block is the same
  3.5/3.5/3.0 cap, ~35 x 14 mm, on every lid, while the room beside it runs
  from ~10 mm on an S lid to ~140 on an L. From it, ONE factor per cascade
  scales every cap and gap — `lid.text_scale`, anchored at the block's cap
  top and right edge (`text_anchor`, which do not move), growing left and
  down until the ink is `LINE_GAP` from what is to its left (the Card Cascade
  block's right edge; on an XS lid, where the block sits beside the sockets,
  the left socket) or keeps at the front wall what it keeps at the back
  (`FootDistanceFromWall + 2`), and **never past `TEXT_SCALE_MAX` = 1.5**
  (Allan's, from 1.3 / 1.5 / 1.75: lines 5.25 cap, the model line 4.5).
  Measured: 26 of the 30 M and L lids reach 1.5, and the four that do not
  are the shallow ones, bound by depth — `L3.18.6.20-Un` (35.0 deep) stays
  at 1.0, `M5.6.6.20-Un` (39.8) comes to 1.27, `L5.7.7.20-Un` and
  `L3.18.6.20-Sl` (42.9) to 1.49 — the S lids come to 1.0-1.37 against the
  Card Cascade block (the
  two `S2.40.12-30` rows ~1.0, their model line being 44 mm), and XS to
  1.07-1.18. The width is the widest of all FOUR lines a cascade's lids can
  carry, so its own and unmarked lids share the scale. The Card Cascade
  block, its version and the staircase do not scale: they are already sized
  to the slot width (Allan, 2026-09-13). `spec/LID.md`, "The text block
  grows with the lid".

### 7.2d — 2026-09-13

One flag:

* **`plain_box_plate`** (`7.2d`, 2026-09-13) — a cascade whose parts.csv
  row sets **`Plain box`** ships a SECOND box on a plate of its own, at the
  END of the project: the same box built without its front and side label
  holders, for an owner who wants no label on the shelf (Allan: Compile's
  three rows, so six projects). The geometry is the `Label holders` option's
  (`isLabelHoldersOnBox = 0`, in the catalogue since 2026-09-05 and held to
  a reference STEP by `tests/test_box.py`); what is new is that a project
  CARRIES it, as `unmarked_lid` carries a second lid — no box moves, the
  ordinary one stays on plate 1 with its pushers, and the plain one is an
  alternative to it, printed instead of it. `build.plain_box_twin` is the
  cascade's own Derived re-derived with `LabelHolders` 0, so its file is
  `box_file`'s `Box <model> no label holders.3mf` and `build_box` needs no
  variant; `build.ships_plain_box` is the ONLY place the flag is asked, and
  the column is a row property the way `TokenHolder` and `Toppers` are. The
  object is a `PlainBox` — a role of its own, because `layout.role` matches
  a prefix and `Box ...` would seat it with the pushers — on the last
  `layout.PLATE_SCHEME` plate, `Box without label holders`. A row whose own
  box already has no holders is refused a twin. `spec/BOX.md`, "A plain box
  on a plate of its own".

### 7.2e — 2026-09-13

One flag:

* **`seated_lips`** (`7.2e`, 2026-09-13) — every lip seats in the rest of
  the part behind it when the cascade is open, and reaches no further
  (Allan, off flat cascades whose lips were "a bit too long": they should
  overlap the holder behind, fit into the indent there, and no more). The
  review found three unrelated formulas doing that job — the lip's reach
  (`2.100` ALONG the slant, `0.38` to `1.81` in Y), the rest's start
  (`2 * calSlotDepth` along the slant, leaving 333 Sl a `0.332` notch and
  246 Sl none) and the slant itself (`(inc-1)/(sd-1.2)`, which puts a lip
  `0.4` to `5.5` above the notch it should sit in) — and measured the
  result on the placed B-reps: 246 Sl's holder lands on the one behind by
  134 mm³, 333 Sl's by 46, M8.16 Sl's by 35, and the Box's lip, `1.250`
  from its holder, reaches only six front holders and meets the wall under
  the notch on each. One rule replaces them: the slant is the cascade's own
  diagonal, `calHeightIncrement / sliderDistance` (`derive.cascade_slope`,
  so the Box's lip angle and the Topper's slant follow), a lip reaches the
  gap plus one wall in Y (`1.200` for a holder's, `2.050` for the box's),
  and the rest is notched through the whole front wall, the lip's base plus
  `REST_CLEARANCE` (`0.200`) a side and `rest_depth` deep — the lip band plus
  the clearance, or deeper where the box lip, fixed at `85.500`, needs it
  (`assembly.box_lip_seat`). The deep holder at the back continues the plain
  diagonal exactly. Slopes move a few degrees on steep rows and hardly at all
  on flat ones. `cad.fit` builds and intersects every holder from here, and
  `lip_margins` reports each lip's seat. `spec/HOLDER.md`, "Lips that seat".

### 7.2f — OPEN 2026-09-14, a PROTOTYPE

`CURRENT`; `build/` is 7.2f. One flag, opened to PRINT a test of it before
the catalogue moves (`cad.testkit`), so it may be revised or withdrawn as
7.2a's `low_profile` was:

* **`ribs_forward`** (`7.2f`, 2026-09-14) — Allan, on the 7.2e box lip: it
  should not have further to go than a holder's. The studio's `#BoxDepth`
  leaves 1.800 of unused space between the last card slot and the divider
  panel, so the box lip crossed 1.250 where a holder's lips cross 0.400.
  Every slider rib — and so every holder — moves FORWARD by `box.rib_shift`
  (derived, 0.850 on every row) so the front holder is `CardHolderGap` from
  the panel. The box lip becomes a FLAT block that BITES that wall by
  0.150 (`box.lip_reach`, 0.550 proud) — inside the holder's 0.200 rib
  slack, so the holder still slides straight down its ribs past it, which
  7.2e's lip (0.800 into the wall) did not allow: a holder cannot pass a
  fixed lip on its way in, and `cad.fit` now sweeps the front holder onto
  its seat in the closed state to prove it — with its top on the holder's
  slant at the wall's face in play (`box.lip_z`, on a 0.800 post above the
  panel's bevel), so every rest is the plain 2.200 and every lip floats the
  same 0.200. The lid and pusher do not
  move: a holder now hangs 0.500 past the front edge of its tread instead of
  sitting 0.350 inside it (`cad.fit`'s tread margins), and the rearmost
  holder is 1.800 from the back wall instead of 0.950, space a later change
  can take out of the box and lid together. `spec/BOX.md`, "The ribs move
  forward", including what the test print is to show.

## What a release moves besides its flags

**The stamp.** Every part engraves `CC <version>`, so a 7.1 part differs from
a 7.0 one in ink even where no flag touched it — `1.44 mm3` on the Innovation M
lid, which is the `0` against the `1`. `tests/test_revisions.py` separates the
two deliberately: it prices the FLAG by building a 7.0 `Derived` carrying 7.1's
`Rev` (same ink, one socket fewer) and the STAMP as what is left. A tolerance
wide enough to swallow both would hide a second change.

**Two witnesses to the release, because one is not enough.** Reading the
engraved version back is not OCR: it is a signature over the COUNTERS of the
two digits either side of the period (`verify.STAMP_SIGNATURES`), and at 7.1
that stops being sufficient. `7` has no counter and neither has `1`, so 7.1
reads `("none", "none")` — and so would 7.2, 7.3, 7.5 and 7.7. The counters
cannot separate them and no better reader will: those glyphs differ in their
strokes, not in their holes.

So every component `cad.build` writes now STATES its release in the file as
well, as `CardCascade:Version` metadata under a declared namespace, beside a
human `Title` and `Description` Studio will show. The two witnesses answer
different questions and neither replaces the other:

| | the ENGRAVING | the METADATA |
|---|---|---|
| who can read it | anyone holding the printed part | anything reading the file |
| how exact | ambiguous from 7.1 on | exact |
| what it guards | a 7.x pusher going into a 6.6 lid | which release wrote this file |

`verify.check_stamp` holds both to the release AND to each other: a positive
mismatch from either is fatal, and so is the two disagreeing, which means the
file is not self-consistent whatever the cascade wanted. Only when NEITHER can
be read is it a warning. An Onshape export carries no metadata and is checked
by its glyph exactly as before.

`verify.py --stamps --tree build` is the release-time check: every component in
a cad tree must state one release, and the Box, Lid and Pusher must be engraved
with it too.

**The tree.** Filenames carry no version — a NAME is an identity
(`components.tracked_name`) — so two releases written to one tree overwrite
each other part for part. `cad.build --out` therefore follows `--version` by
default: `build/` for the current release, `build/v<version>/` for any other.
`cad.cascade --components` follows the same rule, and `cad.promote` reads the
LOCK GENERATION's tree, because what it stages goes into a shipped cascade
whose other parts are Onshape 7.0 exports.

## Defaults, and why the tests pin

`revisions.CURRENT` is the newest release on the line (**`7.2d`** as of
2026-09-13): a plain `cad.build` or `cad.cascade` builds the current release
(Allan, 2026-09-06). `cad.compare` and `tests/test_parallel.py`
are the exception that proves the rule: they pin **7.0**, because what they
regress against is the shipped tree, which the Onshape pipeline built at 7.0 —
and from 7.1 a twin is MEANT to print differently, two pushers against three. That makes the default a moving target by
design, so **every test that compares against a reference pins the release it
means** — `tests/reference.py`, `VERSION = "7.0"`, a literal and not
`revisions.CURRENT`. `tests/test_holder_corpus.py` had already been pricing its
engraving at an explicit `Version="6.6"` long before the default moved, which
is the same idea; this generalises it.

A test that does not pin is a test that re-baselines itself the next time the
default moves — the one failure a regression corpus must not have.

## An unreleased release is iterated by LETTER

`CURRENT` is not a finished thing. The way this repo is worked (Allan,
2026-09-06) is: **sit at a version for a while, accumulate changes in it, then
lock it and release it.** The letter is how those accumulating states are told
apart (Allan, 2026-09-08): **`7.1a`, `7.1b`, `7.1c`, `7.1d`, ... and then plain
`7.1` at the lock** — which happened on 2026-09-10, after four of them.

**The problem it solves is physical.** While 7.1 is being worked on its
geometry moved — five times over four letters — and every part printed that way
says `CC 7.1`. A shelf of them cannot say which is which, and the stamp is the
only thing a person holding the plastic can read. A letter makes each state
nameable on the part itself.

**A letter is a release like any other**, and that is the whole design: a full
member of `RELEASES`, with its own position on the line, its own
`lock.SAME_LOCK` entry and its own row in `verify.STAMP_SIGNATURES`. It is what
makes the letter MEAN something — a change lands as a flag whose `since` is the
NEW letter, so a build at `7.1a` keeps producing what `7.1a` always produced,
and the part stamped with it stays reproducible.

The alternative was considered and rejected: a letter as a mere build marker,
with the flags still keyed on `7.1`. It reads simpler and it is wrong — a
change would move the geometry under every earlier letter, so two different
shapes would wear the same stamp, which is the one thing the stamp exists to
prevent.

### Bumping, and locking

To bump: add the letter to `RELEASES` and to `lock.SAME_LOCK`, move `CURRENT`
onto it, give the new change's flag `since: "<the new letter>"`, and leave
every earlier flag alone — the line is monotonic, so they carry forward.
Nothing is rebuilt in place any more; the earlier letter is FROZEN, which is
what a version stamped on plastic has to be.

At the lock, plain `7.1` joins the END of the line and becomes `CURRENT`. The
letters STAY on it. Parts printed at `7.1b` exist, and the rule this repo
keeps everywhere is that a version you can hold must remain describable and
buildable; `7.1` sitting after them all carries every flag they introduced.

**`7.1` was not on the line until then**, deliberately: while the release was
unfinished, nothing could build it, stamp it or title a project with it, so
there was no way to put an unfinished `CC 7.1` on a part by accident. It went
on at the lock, on 2026-09-10, after four letters — and the same will hold for
`7.2`, which is not on the line while `7.2a` is being worked on.

**Prose in `spec/` says "from 7.1" and means the release**, not the letter —
the geometry sections were written about the release and stay true of every
letter in it. The flags' `since` is the exact answer and `cad/revisions.py` is
where to read it.

The reference corpus is the model for what a locked release looks like: 7.0 is
locked, `tests/reference.py` pins it, and a 7.0 build must reproduce
`individual/` forever.

## Adding the next release — or the next LETTER

The steps are the same for both, because a letter IS a release.

1. Add it to `RELEASES`, set `CURRENT` if it is the new default, and add it to
   `lock.SAME_LOCK` if it keeps the 7.0 lock. Leaving it out of `SAME_LOCK` is
   a loud failure (`pusher.build` refuses it) rather than a quiet wrong stamp.
2. For each change: a field in `revisions.Rev` with its `since` and `spec`, and
   an `if d.rev.<flag>` in the part.
3. A case in `tests/test_revisions.py`, asserting the old release still has the
   old behaviour. Its coverage check names any flag with no case.
4. A section here.
5. A stamp signature in `verify.STAMP_SIGNATURES`, and then
   `verify.py --stamps --tree build` before publishing. Adding the signature
   may not be enough on its own: see below.
