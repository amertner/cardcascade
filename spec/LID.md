# The Lid, measured

Allan supplied five hand-exported STEPs on 2026-09-01/02 (0 API calls), and
`individual/` already held 46 cached Lid meshes. This file records the
transcription and what it has been checked against; it is the Lid's counterpart
to `spec/BOX.md` and `spec/PUSHER.md`, and is incomplete until the floor's
engraving and the logo pattern are built.

The Lid is the shallow tray that closes over the top of the Box **and stows the
pushers while the cascade is open**. That second job is the whole of its
interesting geometry: the sockets on its floor are the lid's half of the 7.0
pusher lock.

---

## The envelope, exact on all 46 lids and all 5 STEPs

```
lid width  = #BoxWidth + 4.600
lid depth  = calLidDepth            — the studio variable, unmodified
lid height = LidHeight              — 40.000 throughout
```

`calLidDepth` IS the lid's measured depth, to `0.001` on every one of the 46
cached lids. That is worth stating plainly: the Box needed `#BoxDepth` plus a
measured `6.100` of features standing proud of its sketch, where the Lid needs
nothing — its sketch box is its envelope.

The sketch is centred on the origin in X and Y, and the floor's OUTSIDE is
`z = 0`, so the lid opens **upward** and its rim is at `z = LidHeight`.

**The lid's frame is the Box's, shifted `-2.250` in Y.** The lid is `8.100`
deeper than `#BoxDepth` and has to swallow the box's `4.500` of rear storage,
which leaves `0.200` of clearance at each end:

```
lid_y = box_y - 2.250
```

Two independent measurements land on it. The box's closing bump sits at box
`y -1.750..6.250`, and the lid's groove for it is centred on `y = 0` — an
`8.000` pad arriving at `-4.000..4.000` inside a `10.000` groove. And the box's
own envelope in the lid's z range is `#BoxDepth + 4.500` against the lid's
inner `#BoxDepth + 4.900`.

In X the two frames coincide: `lid_x = box_x`. The lid's inner width is
`#BoxWidth + 1.400`, so `0.700` a side over the box's plain wall — and the
box's closing bumps, `1.000` proud, are what take up the difference.

The `4.600` is **not** the same 2.00 mm CLAUDE.md records: that is the
difference between the two MEASURED envelopes (`#BoxWidth + 2.600` against
`#BoxWidth + 4.600`), and the box's `2.600` is its side label holder and its
closing bump, neither of which the lid clears — both are below `z = 65`, which
is where the lid's rim stops.

## The reference STEPs

Hand-exported from the Onshape UI, 0 API calls, in `spec/reference/`.

| file | cascade | envelope | what it splits |
|---|---|---|---|
| `Lid Dominion 246S.step` | Dominion 246 Card Sl `S2.40.12-30.45-Sl` | `213.900 x 68.100` | the only reference with a first-riser override, and the cascade whose Box and Pusher are BOTH referenced — so the lock can be followed across all three parts of one design. The only export taken **without** the logo meshes embedded |
| `Lid Dominion 246S with logo.step` | the same lid, logo embedded | identical | the PAIR. It is what makes the pattern pocket measurable on its own — the same trick as the Box's filleted/unfilleted pair |
| `Lid Dominion 244U.step` | Dominion 244 Card Un `M4.21.10.32-Un` | `270.900 x 46.880` | M: three sockets, and unsleeved |
| `Lid Dominion 333S.step` | Dominion 333 Card Sl `S9.21.10.62-Sl` | `213.900 x 102.300` | `RisingSliders 9`, past the logo block's eight-riser branch, and the only C5 lock among the references |
| `Lid Innovation 130U.step` | Innovation 130 Card Un `XS5.15.10.32-Un` | `152.900 x 52.100` | XS: the narrowest lid in the catalogue, two horizontal slots, and the only reference whose logo has no staircase |

Each file carries the lid body plus the logo pattern's inlays as **separate
solids** — 6 for the Dominion lids, 31 for the Innovation one. The body is the
big one; `tests/test_lid.py` takes it by volume.

## The corpus is a MIXED generation, exactly as the pushers are

Of the 44 cached lids that still have a parts.csv row, **25 are 7.0 and 19 are
not**. The tell is the recess step: `1.700` is 7.0, `1.800` is the pre-7.0
figure `LOCK_STANDARD.md` records as "loose". The 7.0 lids put their recesses
at the socket centreline `+- s`; the pre-7.0 ones inset them from the socket's
two ends, which is the same rule their pushers' tabs follow.

`cad/` builds 7.0 only, so `tests/test_lid_corpus.py` asserts the lock on the
25 and reports the other 19 as moved onto the catalogue — the same split
`tests/test_pusher_regression.py` makes for the 14 still-6.6 pushers.

**All five STEPs are 7.0**, and on every one the recesses land on
`calTabCentreDistance` exactly.

## The shell

```
walls    WallThickness = 1.600, all four
floor    1.600, its outside at z = 0 and its inside at z = 1.600
rim      z = LidHeight, the wall band less the outer rounds
```

Every one of the **twelve outer edges is rounded `1.000`** — four vertical,
four at the rim, four at the bottom — which OCCT closes with eight spherical
corner patches of `pi/2` each, exactly as the STEP has them. Nothing on the
inside is rounded: the rim's inner edge, the floor-to-wall corner and the
socket blocks are all square.

The radius was read three ways off the profile before the STEP arrived and
confirmed by it: at `0.400` below the rim the outer face has receded `0.201`,
at `0.600` `0.084`, at `0.800` `0.021` — `r - sqrt(2ru - u^2)` for `r = 1.000`
at every one.

## The pusher sockets — the lid's half of the 7.0 lock

One socket per stored pusher, standing on the floor. A pusher goes in **on
edge, leading edge down**, so the socket is `5.000` tall — the tab's own length
along the insertion direction.

```
block    #calFootTotalWidth (9.200) wide x (calPusherTotalDepth - 0.400) long
         x 5.000 tall
channel  #PusherThickness + 0.3mm (3.300) down the middle, open at BOTH ends
walls    2.950 each side of it — what the block leaves
rib      5.000 of channel left standing on the socket's centreline, C3-C5 only
recess   4.000 long x 1.700 deep, in the channel's -X wall, at centreline +- s
```

Every number is `LOCK_STANDARD.md`'s. `D - 0.400` is its "lid socket span",
`3.300` its "plain channel" (the pusher's `3.000` plate and `0.300` of running
clearance, the tightest fit in the mechanism), `4.000` its "lid recess length"
and `1.700` its "lid recess step". The rib is what the pusher's notch keys
onto, so it follows `has_notch`: `s >= 5.800`, i.e. C3 and up. C1 and C2 lids
have a plain unbroken channel.

**The recesses are both in the `-X` wall**, because a pusher's tabs stand
`1.500` proud of ONE face. Confirmed on every socket of every 7.0 lid.

The socket's own faces make this measurable in one probe, because their areas
are a function of what has been taken out of them:

| face | area |
|---|---|
| block side, each | `5.000 x (D - 0.400)` |
| channel `+X` wall | that, less the rib's `5.000 x 5.000` |
| channel `-X` wall | that, less both recesses' `4.000 x 5.000` |
| recess floor, both | `2 x 4.000 x 5.000` |

On `Lid Dominion 246S` those are `148.000 / 122.995 / 82.995 / 40.000`, and
`tests/test_lid.py` asserts the set.

### Where the sockets sit

```
count   2 for XS and S, 3 for M and L
X       first block's LEFT edge = the left inner wall
                                  + #calSlotwidth/2 + #calSliderSpaceLeftRight/2
        then the set spans (HorizontalSlots - 1) * calSlotwidth
Y       back edge #FootDistanceFromWall in from the inner back face,
        running forward by calPusherTotalDepth - 0.400
```

with

```
#calFootTotalWidth    = 2*#PusherThickness + 2*#PusherFootThickness    9.200
#FootDistanceFromWall = 2*#WallThickness + #PusherThickness + 1.2mm    7.400
channel               = #PusherThickness + 0.3mm                       3.300
```

so **not one number in the socket is its own**: the block is the pusher's foot,
the channel is its plate and the standard's tightest running clearance, and the
inset is the box's two walls with the plate between them.

`35.450` in on a `calSlotwidth 65` lid, and exact on all 46 lids and all 5
STEPs — the `#FootDistanceFromWall` across depths from `34.980` to `111.300`,
which is what says it is an offset from the back and not a centring rule.

**The first socket is placed and the rest step off it**, which is why the set
is not centred on the lid: it leaves `35.450` at the left and `36.050` at the
right. That `0.300` of asymmetry is the `x = -0.300` this file carried as a
measured constant until the sketch turned up.

**The count is the plain size rule and NOT `isOnlyTwoPusherSlots`.** An
Innovation M lid carries three sockets where its Box has two rear storage slots
and its cascade ships two pushers (`spec/BOX.md` records the same variable
being the box's answer). The third socket is harmless — a spare — but it is
Onshape's own inconsistency between the two parts, and `cad/` reproduces the
lid as it is rather than tidying it.

**`x = -0.300` was measured before it was derived**, and it is worth keeping
the story: it is constant on every lid, and nothing in the derived set produces
it — the card slots' own centres are `-0.450`, the front pocket's dividers
`-0.050`. It reads as a centring rule with a mysterious offset, and it is not
one. The sketch anchors the FIRST socket to the left wall and lets the rest
follow; the `0.300` is what the right-hand margin comes out at.

## The closing groove

The receptacle for the Box's `Closing mechanism`, one in each end wall:

```
10.000 long in Y, centred on y = 0     (the bump is 8.000, so 1.000 clear each end)
1.000 deep                             (the bump stands 1.000 proud)
3.800 tall, z 16.600 .. 20.400
chamfer 0.500 on the two horizontal edges of the groove's FLOOR
```

The z is the box's bump, transferred: the lid goes on over the box's rim, so a
box height `h` arrives at `WALL + BoxHeight - h`, and the bump's top —
`box.BUMP_Z1 = 90.000` — lands on `1.600 + 105.000 - 90.000 = 16.600`, the
groove's own bottom edge. That is what stops the lid. The bump occupies
`16.600..19.600` of the groove's `16.600..20.400`; the spare `0.800` is on the
side it comes in from.

The chamfer is on the floor, not the mouth, so the mouth keeps a square
`0.500` step — `Gripperwidth`, the studio's "side closing grip holding box and
lid". It is what the bump cams over.

Constant on every lid and every STEP, and it has to be: `BoxHeight` is
`105.000` for every game but Colours.

## The floor's engraving

Two blocks, both EMBOSSED — where the Box's floor text is engraved. On the `+X`
side three right-aligned lines reading up in Y; on the `-X` side the
`Card Cascade` logo, its version, and a staircase. All Orbitron Bold.

Allan supplied the sketches on 2026-09-02, so every expression below is the
part studio's own rather than a fit. Each was then checked against all four
STEPs **and** all 44 cached lids, which is what the measurement was for: the
same numbers were reachable by fitting, and two of them came out wrong that
way — see "What the fit got wrong" below.

### The variables

```
#calLidTextOffset = #calSliderSpaceLeftRight                        5.900
#LogoWidth        = #calSlotwidth - 12mm - #calFootTotalWidth      43.800 at w=65
#LogoHeight       = ProductName's cap, fitted to #LogoWidth
#LogoHeight23     = 2/3 * #LogoHeight               — the version's cap
#LogoStepWidth    = #LogoWidth / #RisingSliders
#LogoStepHeight   = #SlopeHeight / #RisingSliders
#FootDistanceFromWall = 7.400                       — and it places the sockets
```

`#LogoWidth` is why the logo's size is a pure function of `calSlotwidth` across
the whole catalogue, `5.2346` at `w = 63` through `6.1112` at `w = 70`. Fitting
`ProductName`'s ADVANCE to it reproduces every one of the 44 to a **constant
`0.31 %`** — the same residual `spec/BOX.md` records for the Box's
`ProductName`, to two decimals, and the same cause: how Onshape measures an
advance. So the build's logo is `0.31 %` larger than the reference's and its
ink stops up to `0.25 mm` further right. Nothing else differs.

### Horizontal

```
text block, right edge, in from the RIGHT inner wall
    #calLidTextOffset + 2*#calSlotwidth/3 + #calFootTotalWidth + 2mm
logo block, left edge, in from the LEFT inner wall
    #calLidTextOffset + 2*#calSlotwidth/3
    + (#HorizontalSlots > 2 ? #calFootTotalWidth + 2mm : 0)
```

`60.43` on a `calSlotwidth 65` lid. The two are the same expression except that
only the logo's carries the conditional — which is the whole of why an XS lid's
blocks stack instead of sitting side by side.

### Vertical

Every line hangs off the pusher socket line, `#FootDistanceFromWall` in from
the lid's inner back face:

```
calCapacityLabel  cap top  = socket line - (#HorizontalSlots > 2 ? 2mm : 15mm)
GameName          cap top  = calCapacityLabel's baseline - 2.000
calModelName      cap top  = GameName's baseline - 2.000
ProductName       cap top  = socket line - 1.000
calVersion        cap top  = ProductName's baseline - 2.000
```

with caps of `3.500`, `3.500` and `3.000` for the three lines, `#LogoHeight`
for `ProductName` and `#LogoHeight23` for the version. So the baselines come
out `5.500` and `5.000` apart, which is what a measurement sees; the `2.000` is
the gap, and the caps are what differ.

### The staircase

`RisingSliders` steps of `#LogoStepWidth` by `#LogoStepHeight`, descending to
the right, filling `#LogoWidth` by `#SlopeHeight`.

`#SlopeHeight` is not a number of its own. The slope runs from the pusher
sockets' own front edge up to `#LogoHeight23` below `ProductName`'s baseline,
so one rule gives `67.620` on the nine-riser lid and `22.018` on the two-riser
one. `#SlopeLength` — `80.56` — is just its hypotenuse.

R equal steps fill exactly `(R + 1) / 2R` of the rectangle they descend, which
is what `tests/test_lid.py` asserts, against each solid's OWN box so the
`0.31 %` cancels.

**Suppressed on an XS lid**, which carries the word alone — dynamic
suppression in the studio, and Allan's reason is the obvious one: there is not
really room for it.

### What the fit got wrong

Worth recording, because the fitted values reproduced all 44 lids and were
still not the model. Before the sketches arrived, both blocks' horizontal
placement had been fitted to `last socket centre - calSlotwidth/6 - 9.320` and
its mirror. That is exactly right on every catalogue lid, and it is
arithmetically the same expression: the socket set spans
`(HorizontalSlots - 1) * calSlotwidth` about `x = -0.300`, so `2*w/3` in from
the wall lands `w/6` in from the end socket, and the `0.370` between the two
readings is the ink stopping short of its text box.

It is still not the model. It hangs the engraving off the sockets where the
sketch hangs it off the wall, so it would follow the sockets anywhere they
moved — including off the `x = -0.300` this file still cannot derive. And the
`calSlotwidth/6` that no derived variable produces was the tell that something
was being attributed to the wrong datum.

The second was the XS branch. Fitted, it read as "the text block sits 13.000
lower"; the sketch says the same thing as `2mm : 15mm` on one dimension, and
the 13 is the difference rather than a number in the model.

## The logo pattern

The game's logo, in the UNDERSIDE of the floor, printed in the second
filament. In Onshape it is one sketch and two features (Allan's screenshots,
2026-09-02):

```
Remove logo         blind extrude, 0.810, Remove, merge scope Lid
Add Logo Material   blind extrude, 0.810, NEW solid, starting offset -0.800
```

So one set of regions makes both: the pocket runs `z 0.000..0.810` up into the
floor, and the inlay `-0.010..0.800`, which fills it and stands `0.010` proud
of the lid's underside. That `0.010` is what gives the slicer an unambiguous
boundary between the two filaments, and it is why a cached lid mesh measures
`40.010` tall rather than `40.000`.

`cad/parts/lid.py` builds both from one list of faces, so the inlay cannot
drift out of its pocket, and `cad.build` writes the inlays as their own
objects — `Lid`, `Part 2`, `Part 3`, ... — which is the shape Onshape's export
has and what `make_cascade.load_export` pairs by name.

### The artwork

One DXF per drawing in `logos/<Game>/`, drawn in the lid's own frame, so
nothing is placed here — only scaled. `cad/art.py` loads it: a DXF holds
outlines, not regions, so a loop nested in an odd number of others is a hole
and one nested in an even number is an island, exactly as
`labelmaker.load_art` reads the printed labels' artwork.

**Every file on disk was LIFTED from a reference**, by `make_lid_logo_dxf.py`,
and should be replaced by Allan's own exports of the sketches when those
arrive; `tests/test_lid.py` compares the built pattern against the reference
either way, so the swap is checkable.

| file | lifted from | regions | area mm2 | drawn size |
|---|---|---|---|---|
| `Dominion/lid_logo.dxf` | `Lid Dominion 246S with logo.step` | 6 | 975.420 | 124.693 x 42.850 |
| `Compile/lid_logo.dxf` | `individual/Compile/Lid S5.7.7.20-Un.3mf` | 12 | 740.054 | 97.771 x 39.333 |
| `FCM/lid_logo.dxf` | `individual/FCM/Lid L3.18.6.20-Un.3mf` | 10 | 546.843 | 45.029 x 27.598 |
| `Innovation/lid_logo.dxf` | `Lid Innovation 130U.step` | 31 | 685.790 | 109.028 x 33.498 |
| `Innovation/lid_logo_big.dxf` | `individual/Innovation/Lid S5.15.15.45-Un.3mf` | 31 | 1719.252 | 174.078 x 52.739 |
| `Innovation/lid_logo_plain*.dxf` | the two above, `--above` | 11 | — | see below |

A **STEP** keeps the curves and is the better source where one exists. A
**cached component 3MF** has been meshed, so its outlines come back as
polylines — but every game already has one, which is what closed the artwork
gap for Compile, FCM and Innovation's big mark without an export or an API
call. The error that costs is small and measured: lifted from the mesh, the
same Innovation mark that the STEP gives as `685.790 mm2` comes back as
`685.614`, `0.026 %`, in 2773 segments over 31 regions — about 90 a region,
which is Onshape's own export tolerance and invisible in a `0.810` inlay.

The lift takes the top faces of the solids that are not the lid body. From a
mesh that means the triangles at the object's maximum z, whose singly-used
directed edges are the outline; **two loops can meet at a vertex**, so the
chaining is the standard face traversal — arriving along `u->v`, leave along
the first edge clockwise from `v->u` — and not "follow the only other edge",
which turned one FCM inlay into a single 1592-point figure of eight that no
plane could be fitted to. Every lifted file reconstructs its mesh's top area
to `0.000 %`, which is the check that says the loops are right.

### Sizing the mark — `cad/` policy, not Onshape's

Onshape draws each mark at one size, and on Innovation alone at a second one
through `#LogoScaleFactor` (below). Allan has asked for the mark to follow the
box instead — "if the bigger version fits, I'd like to use that one ... having
scaling factors that adapt to the size of the box would be better" — so from
here the Lid's mark is **fitted**, and this section is the first place `cad/`
deliberately parts company with the Onshape model.

"As big as fits" alone is not it. Fitted to the flat floor, Dominion's mark
would be `199 x 69` on its deepest lid and Innovation's plain one `218` across
a `220` lid, edge to edge. What the catalogue actually holds to is a
PROPORTION — Allan's drawn marks sit at 22..79 % of their tightest lid's width
— so that is the rule, with the floor as a hard limit underneath it:

```
want  = min(WIDTH_FRACTION * W / w,  DEPTH_FRACTION * D / h)     0.600, 0.850
hard  = min((W - 2*OUTER_ROUND) / w, (D - 2*OUTER_ROUND) / h)
scale = min(max(want, 1.0), hard)
```

The two clamps are what keep it honest at the ends:

* a mark is **never taken below its drawn size to satisfy a proportion** —
  that would shrink marks already published, and the ask was for bigger;
* it **is** taken below to satisfy `hard`, because a pocket that runs into an
  outer round breaks the rim. Compile's smallest lid is the one that needs it:
  its mark is `39.333` deep on a `37.700` lid and comes down to `0.908`.
  Onshape draws that lid at `0.798`, its own second Compile size.

`WIDTH_FRACTION 0.600` is Dominion's own — `124.693` on a `207.900` lid — and
it is the constant that does the work, because depth is slack on every deep
lid. `DEPTH_FRACTION 0.850` is Innovation's big mark on the `62.100` lid it
was drawn for. Between them, 13 of the 50 lids keep exactly the mark they have
today and the rest grow; the extremes land at 15..79 % of width and 27..95 %
of depth. Both constants are Allan's to set — they are two lines in
`cad/parts/lid.py`.

Where a game has more than one DRAWING, the list in `cad/tables.LID_LOGO` is
largest first and the first that fits the flat floor as drawn is taken, then
scaled. A second drawing is only needed where the two sizes are not a scale of
each other:

* **Compile's are.** Its small mark is the big one at `1/1.25297` — line
  weights and all, `740.054 / 471.383 = 1.2530^2` — so one file serves its six
  lids.
* **Innovation's are not.** `#LineWidth` and the flourish dashes are absolute
  in that sketch, so between the two drawings 25 of 31 regions scale by
  `1.600` while the five dashes stay `1.500 x 0.600` and the long flourish
  scales in length but not in width. Measured on the marks themselves: X
  scales `1.5966` and Y `1.5744`.

### Two editions of the Innovation mark

Allan: "one that is just Innovation, and one that is Innovation Ultimate. The
two single-set boxes would be the Innovation version, without it saying
Ultimate on the box." So the mark is chosen by WHICH SETS the cascade holds,
which is not a dimension — `cad/tables.LID_LOGO_EDITION` keys it on the base
model, `calModelName` up to its third dot:

```
S3.15.10   Single Set      plain
XS5.15.10  Single Mini     plain
```

and the other four Innovation rows keep the Ultimate mark.

**The plain drawings are DERIVED, and are the one piece of artwork here that
is not Allan's.** The Ultimate composition splits cleanly into two bands — the
`Innovation` wordmark, 11 regions, and everything below it: `Ultimate`, its
`i` dot, the left flourish and the two runs of five dashes — with a clear gap
at `y -1.455 .. -4.392` in the small drawing and `-2.328 .. -7.028` in the
big. `make_lid_logo_dxf.py --above -3 --recentre` keeps the top band and puts
it back on the full mark's own centre in Y. That is a reading of "without it
saying Ultimate", not an export, and one DXF from Allan replaces it.

### The `#LogoScaleFactor` this replaces

Innovation's logo sketch carries (Allan):

```
#LogoScaleFactor = (#LidWidth < 70mm ? 1.6 : 1)
```

with two things worth stating plainly, because both invite a wrong reading:

* **`#LidWidth` there is the lid's DEPTH**, `calLidDepth`. The name belongs to
  the lid's own rectangle sketch, where it really is the width.
* **Every dimension in the logo sketch is DIVIDED by the factor** — `24 mm /
  #LogoScaleFactor` reads `15` at 1.6 — so the factor runs the opposite way to
  its name. `1.6` draws the SMALL mark, on a shallow lid; `1` draws the big
  one.

The rule reproduces 10 of the 12 cached Innovation lids. The two it does not
are `S5.15.15.45-Un` and `M5.15.15.45-Un`, both `62.100` deep, which carry the
big mark where the rule asks for the small one. **They are not stale.** The
fit rule above gives them the big mark too, because it fits: `62.100` of depth
takes `52.739` of mark at `0.850`, to `1.0007`. The cached corpus agrees with
the fit rather than with the factor, and the four Innovation lids that carry
the big mark are exactly the four `15.15` rows.

### What the Innovation sketch actually is

Not imported artwork at all, unlike Dominion's: Allan has recreated it as two
sketches — the words in **Noto Serif** (`Ultimate` in Bold Italic) and a
separate `Logo Flourishes` sketch holding the circle-and-`I`, the five-armed
star (`5x` at `270°`) and the dashed lead-in (`5x`, `1.500` by `#LineWidth`).
Rebuilding it from the font and those dimensions would make it parametric —
letters scaling while strokes hold — which is the only way a fitted mark keeps
its drawn stroke weight at every size. What is on file is two lifted outlines
scaled uniformly, so a mark at `1.210` has strokes `21 %` heavier than drawn.

### Dominion's mark is 180° out from the other three

Seen from `+Z` — the direction the floor's engraving reads from — Compile's,
FCM's and Innovation's marks are mirrored left-to-right and the right way up,
which is what a mark cut into the far side of the floor should be. Dominion's
reads left-to-right correctly and is **upside down**. Those two differ by a
half turn in the plane, so one of them is a half turn out relative to the
other, and it is not something `cad/` can decide: the artwork is reproduced as
drawn, and `logos/dominion_logo_v1_0/dl_black_640px.png` is in the repository
for comparison. Raised with Allan 2026-09-02.

## What is NOT built yet

Nothing on the Lid's shape, and every game now has artwork. What is left is
Allan's to settle, not the model's:

* the two fit constants, `LOGO_WIDTH_FRACTION` and `LOGO_DEPTH_FRACTION`;
* the plain Innovation drawings, derived here rather than exported;
* whether Dominion's mark is a half turn out, or the other three are;
* whether a fitted mark should keep its drawn stroke weight, which needs the
  Innovation sketch rebuilt from Noto Serif rather than scaled as an outline.

## Verified

`tests/test_lid.py` — the source against the four structural STEPs, every check
run against the reference AND the build. On `Lid Dominion 246S`, the one export
without the pattern embedded, the build's volume lands within `0.01 mm3` of the
reference's `59542.001`. `tests/test_lid_corpus.py` — all 44 cached lids that
have a parts.csv row, against the placement rules and the engraving's two
anchors.

Two things worth keeping in mind for the next part:

**Never aim a mesh ray at a feature's exact centre.** A rectangular face is two
triangles and a ray down their shared diagonal is counted once per triangle,
which cancels: the face vanishes from the reading. Aimed at the centres, half
the Compile lids read as pre-7.0 because their recess walls disappeared. Every
probe in `test_lid_corpus.py` is offset by an `EPS` no dimension is a multiple
of.

**The volume closes where the areas do not.** The build's floor face and the
reference's differ by `0.02 .. 0.33 mm2` more than the engraving's own
footprint, while the volumes agree to `0.3 mm3` in `6e4`. The reference's floor
carries about a thousand inner wires — every glyph — and OCCT's area
integration over it is good to a few parts in `1e5`. The volume is the tighter
statement; the area check is corroboration at `0.5 mm2`.

## Still open

- Nothing on the shape. Every number on the Lid is now either the studio's own
  expression or a constant read off a sketch.
- **The two fit constants.** `LOGO_WIDTH_FRACTION 0.600` and
  `LOGO_DEPTH_FRACTION 0.850` are read off Allan's own drawings, but they are
  taste and not measurement — they are what decides how big every mark in the
  catalogue is.
- **The plain Innovation drawings** are derived here by dropping the `Ultimate`
  band, not exported. One DXF from Allan replaces each.
- **Dominion's mark is a half turn out** from Compile's, FCM's and
  Innovation's. Reproduced as drawn until Allan says which is right.
- **Stroke weight under a fit.** Scaling an outline scales its strokes, where
  the Onshape sketches hold `#LineWidth` absolute. It only bites where a mark
  is enlarged a long way — FCM's reaches `1.950` — and the fix is the
  parametric rebuild from Noto Serif, not a different fit.
- **Allan's own exports.** Every artwork file here was lifted from a reference
  rather than exported from the sketch; four of the six came off a mesh, which
  costs `0.026 %` of area and turns curves into ~90-segment polylines.
- **The Mat branch.** Nothing in the lid's geometry reads `MatPocket`, but
  `calModelName` carries `-M`, so a Mat cascade's lid differs in its engraved
  model code alone. `plan_exports` keys one `("Lid", model)` for both and
  `individual/` has a single lid where `cad.build` will write two. Harmless
  today; it wants a decision when the engraving lands.
