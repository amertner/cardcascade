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
| `Lid Compile 126S.step` | Compile 126 Card Sl `S5.7.7.45-Sl` | `228.900 x 59.700` | a **second game's card size**, which nothing else in the lid references reaches, and the only Lid reference whose lock is C4 |
| `Lid FCM 105S.step` | FCM, `213.900 x 44.700`, **not a parts.csv row** | `213.900 x 44.700` | artwork only — see below |
| `Lid Innovation 270S.step` | Innovation 270 Card Sl `S5.15.15.62-Sl` | `225.900 x 84.600` | `#LogoScaleFactor 1`, and the export that shows its flourishes are **broken** — see below |

Each file carries the lid body plus the logo pattern's inlays as **separate
solids** — 6 for the Dominion lids, 31 for `Lid Innovation 130U`, 12 for
Compile, 10 for FCM. The body is the big one; `tests/test_lid.py` takes it by
volume.

`Lid FCM 105S` is **not a structural reference**: its envelope is
`213.900 x 44.700`, which no FCM row in parts.csv produces, and the envelope
alone does not pin the model — 30 parameter sets give that lid. Its staircase
has 10 edges, so `RisingSliders 4`, and its sockets sit at `+-65.3 / 64.7`, so
`calSlotwidth 65.000`; that narrows it to `S4.7.7 / S4.11.6 / S4.15.5 /
S4.19.4` at `.32.Sl`, all `105 Cards/S` and all geometrically identical apart
from the model code engraved on the floor. It is kept for its artwork.

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
being the box's answer). It is Onshape's own inconsistency between the two
parts, and `cad/` reproduces the lid as it is rather than tidying it.

**The unused one is the MIDDLE one, and it should eventually go** (Allan,
2026-09-03). It is not a spare that happens to be free: the two pushers use the
outer pair, so `socket_centres`' `k = 1` is dead material in every Innovation M
lid. Not done here, because it is a real geometry change and it is not free:

* it restates **four** lids — `M5.15.15` and `M5.10.10`, each sleeved and un —
  and no other row in the catalogue, S and XS Innovation being on two already;
* `tests/test_lid_corpus.py` currently **asserts** the three against the cached
  meshes, so the test has to gain the divergence on both sides, the way
  `cad/README.md`'s sixth decision requires;
* every shipped Innovation M cascade's lid goes stale the moment it lands, so
  it wants a version bump to carry it rather than a quiet re-cut.

The rule it becomes is `box.pusher_slot_count`'s — `isOnlyTwoPusherSlots`, the
variable that was always the right answer for this — which makes the two parts
agree instead of disagreeing.

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
| `Compile/lid_logo.dxf` | `Lid Compile 126S.step` | 12 | 740.286 | 97.771 x 39.333 |
| `FCM/lid_logo.dxf` | `Lid FCM 105S.step` | 10 | 547.218 | 45.029 x 27.598 |
| `Innovation/lid_logo.dxf` | `Lid Innovation 130U.step` | 31 | 685.790 | 109.028 x 33.498 |
| `Innovation/lid_logo_big.dxf` | `individual/Innovation/Lid S5.15.15.45-Un.3mf` | 31 | 1719.252 | 174.078 x 52.739 |
| `Innovation/lid_logo_plain*.dxf` | the two above, `--above` | 11 | — | the REFERENCE for `cad/marks.py`, not built from |

A **STEP** keeps the curves and is the better source where one exists. A
**cached component 3MF** has been meshed, so its outlines come back as
polylines. Both were needed: the meshes closed the artwork gap for Compile,
FCM and Innovation's big mark at 0 exports and 0 API calls, and Allan's STEPs
then replaced two of the three.

The mesh error is small and measured — lifted from the mesh, the same
Innovation mark the STEP gives as `685.790 mm2` comes back as `685.614`,
`0.026 %`, in 2773 segments over 31 regions. What a STEP really buys is
**edges, and so build time**, because every region is a separate boolean
against the floor:

| mark | from a mesh | from a STEP |
|---|---|---|
| Compile | 6493 edges | 1885 |
| FCM | 3664 | 1499 |
| Innovation, big | 2762 | 738 |

A Compile lid took `119 s` off the mesh-lifted mark where a Dominion lid, whose
459-edge artwork came off a STEP all along, takes `17 s`.

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

**The plain mark is the one that is not Allan's drawing.** It began as a crop
— the Ultimate composition splits cleanly into two bands, the `Innovation`
wordmark and everything below it (`Ultimate`, its `i` dot, the left flourish
and the two runs of five dashes), with a clear gap at `y -1.455 .. -4.392` in
the small drawing and `-2.328 .. -7.028` in the big, and
`make_lid_logo_dxf.py --above -3 --recentre` keeps the top band and puts it
back on the full mark's own centre in Y. Those two crops are still in
`logos/Innovation/`, but they are now the REFERENCE and not the source: the
mark itself is generated, "The Innovation mark, rebuilt" below.

That the composition is right — the wordmark keeps the circle round its `I`
and the star over its `i`, and the flourishes that go with `Ultimate` leave
with it — is a reading of "without it saying Ultimate", and Allan's to
overrule.

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

### The Innovation mark, rebuilt

Allan's Innovation logo is not imported artwork, unlike Dominion's: he
recreated it as two sketches — the words in **Noto Serif** (`Ultimate` in Bold
Italic) and a separate `Logo Flourishes` sketch. So the PLAIN mark, the one
the two single-set cascades carry, is **generated** rather than drawn:
`cad/marks.py` builds it, and `logos/Innovation/lid_logo_plain*.dxf` are what
it is checked against rather than what is used.

That is worth the trouble for one reason: **an outline cannot be scaled
without scaling its strokes.** `#LineWidth` is `0.600` at every size in
Allan's sketch. Scale the crop to the `1.436` the fit gives `S5.10.10.32-Un`
and the `0.600` becomes `0.862`. A generated mark scales its letters and
leaves its strokes alone, which is what `cad/marks.growth` states: the mark's
width is `108.4596*n + 0.600`, affine and not proportional, and the `0.600` is
exactly the strokes.

Every number in it was measured off Allan's own two drawings.

**The word is Noto Serif Regular**, set at default advances with no kerning.
Fitted over its nine clean glyphs, every glyph edge lands within `0.016` on
the small drawing and `0.026` on the big, over 109 mm and 174 mm of wordmark;
`build123d`'s own `Text` then reproduces the same to `0.019`. The two sizes
are `20.8416` and `33.3466`, whose ratio is `1.59999` — `#LogoScaleFactor` to
five figures, which is what says the reading is right. Neither is a round
number in any standard metric (cap `14.881` / `23.810`, x-height `11.379` /
`18.207`), so the text was sized to fit rather than dimensioned.

**The circle round the `I`** is an annulus on the middle of that letter's top
serif — `693` font units up, where the slab runs `672..714` — with its bore
the letter's own ink half-width and its wall `LINE_WIDTH`. Measured
`r 3.0306 / 3.6306` on the small drawing against `3.0325` for the half-width:
a wall of `0.6000` exactly.

**The star over the `i`** is that letter's own tittle with five arms driven
through it — `LINE_WIDTH` wide, `2.500` long at the small size and `4.0002` at
the big, `67.5` apart, which is the `5x at 270` circular pattern the Logo
Flourishes sketch holds. Two things only came out of the numbers:

* each arm is offset `0.1039` off the centre, a slight pinwheel, and that
  offset is **absolute** — `-0.1039` on both drawings, where the arm length
  between them scales `1.6002`. With it the five arm tips land on the drawing
  to `0.0005` and `0.0003`; without it they are `0.10` out.
* the disc the arms seemed to stand on **is the tittle**. Fitting a circle to
  the central blob left a `+-0.09` wobble that no circle explains; the
  letter's own dot is `114 x 124` font units, and that ellipse is the wobble.

Against the two drawings the rebuild holds every region's edges to `0.019` at
the small size and `0.109` at the big, with the same 11 regions and the same
holes, and its area within `0.13 %`. The `0.109` is the star, and it is not an
error in the rebuild: **the star is hand-placed in Allan's sketches and the
two drawings disagree with each other** about where it sits by `3.4` font
units. The letters land within `0.035` at both sizes.

`Ultimate` is NOT rebuilt. It needs the second sketch's left flourish, its two
runs of dashes and its end circle, none of which is determined by the two
drawings alone; that mark stays the pair of lifted outlines and its strokes
still scale with it. `fonts/NotoSerif-BoldItalic.ttf` is bundled ready for it.

### `Ultimate` — measured, not yet built, and its scale-1 export is broken

`Lid Innovation 270S.step` is the `#LogoScaleFactor 1` export, taken so that
`Ultimate` could be rebuilt the way the plain mark was. **Its flourishes come
out wrong**, and that has to be fixed in Onshape before the rebuild is worth
doing. Against the cached `S5.15.15.45-Un`, which is the same mark at the same
factor and is right:

| | cached, correct | the scale-1 export |
|---|---|---|
| lead-in dashes | 5, `1.500 x 0.600`, pitch `4.500` | **4**, with a gap where the third belongs |
| the fan under the `U` | 5 dashes on an arc | **gone** — two have landed in that gap, rotated |
| stray | — | one `1.000 x 2.000` dash at `y -26.691`, `4.5` below anything else |

Two instances are missing outright and the rest are displaced, so it is a
corrupted pattern and not a revision. The letters are untouched. So
`logos/Innovation/lid_logo_big.dxf` stayed the mesh lift of the cached lid until
the corrected export of 2026-09-04 replaced it with `lid_logo_big.brep` (see
"What is NOT built yet"), and `Ultimate` stays a drawing whose strokes scale
with the fit.

What the export IS good for is the letters, and between it and the two good
drawings the whole line is now measured. When the sketch is fixed, this is
what a rebuild needs:

* **`Ultimate` is Noto Serif Bold Italic**, default advances, no kerning, at
  `12.1539` on the small drawing — `0.5832` of the wordmark's size. Fitted
  over all eight glyphs the worst edge is `0.0030 mm`, which is the cleanest
  fit anywhere in this file. Its letters scale `1.6000` exactly between the
  drawings, and its baseline sits `12.620 * n` below the wordmark's.
* **The lead-in is 5 dashes**, each `1.500 x 0.600` ABSOLUTE, at a pitch of
  `2.8125 * n`. Their top edge and the flourish's horizontal bar share a line
  `7.500 * n` below the wordmark's baseline.
* **The end flourish is a ring with a cross through it.** The ring is
  `r 1.4000 / 2.0000` — a `0.600` wall, and **absolute**: identical in both
  drawings. Its centre is on that same bar line; the bar runs `8.750 * n` back
  from the centre, and the upright runs from the ring's bottom tangent up to
  `3.750 * n` below the wordmark's baseline.
* **The fan is 5 dashes of `1.250 x 0.625`** — not the lead-in's size — on an
  arc of `R 6.394` about a point `4.170` below the `Ultimate` baseline, at
  `18` degrees apart through `53..127`.

The one thing two drawings could not settle is where the lead-in run is
anchored in X: its span is exactly `4 * 2.8125 * n + 1.500`, but its position
decomposes to `a*n + b` with a `b` of `1.0..2.5` that nothing else explains.
A corrected scale-1 export would settle it.

### Dominion's mark WAS 180° out from the other three — turned 2026-09-04

Seen from `+Z` — the direction the floor's engraving reads from — Compile's,
FCM's and Innovation's marks are mirrored left-to-right and the right way up,
which is what a mark cut into the far side of the floor should be. Dominion's
read left-to-right correctly and was **upside down**. Those two differ by a
half turn in the plane, and which was out was not something `cad/` could
decide: the artwork is reproduced as drawn. Raised with Allan 2026-09-02.

Settled 2026-09-04 by the shipped product: `cascades/Innovation/Photos/3
Closed Boxes.jpeg` shows three closed boxes reading `Innovation Ultimate`
upright from the labelled front, i.e. the mark's top toward the back, which
is the convention the three share. Allan: turn Dominion's.
`logos/Dominion/lid_logo.dxf` is now the drawing turned a half turn about its
own bounding-box centre (`ezdxf`, every entity; six regions with the same
areas, centre and extent, each region's centre the original's mapped through
the turn). The reference STEP `Lid Dominion 246S with logo.step` still
carries the OLD orientation, and `tests/test_lid.py` asserts from both ends:
the build's regions are the reference's turned 180° about the mark's centre,
region for region, and are NOT the reference's as they stand. The 24 cached
Dominion lids in `individual/` differ from `build/` by exactly this turn.

## What is NOT built yet

Nothing on the Lid's shape, and every game now has a mark. What is left is
Allan's to settle, not the model's:

* the two fit constants, `LOGO_WIDTH_FRACTION` and `LOGO_DEPTH_FRACTION`;
* whether the plain Innovation composition is the right reading of "without it
  saying Ultimate";
* ~~whether Dominion's mark is a half turn out, or the other three are~~ —
  Dominion's was, and it is turned (above);
* the marks that are still outlines — Dominion, Compile, FCM and Innovation
  `Ultimate` — whose strokes scale with the fit where the generated plain mark
  holds its own.

## Verified

`tests/test_lid.py` — the source against the five structural STEPs, every check
run against the reference AND the build. On `Lid Dominion 246S`, the one export
without the pattern embedded, the build's volume lands within `0.01 mm3` of the
reference's `59542.001`. `tests/test_lid_corpus.py` — all 44 cached lids that
have a parts.csv row, against the placement rules and the engraving's two
anchors.

The references all predate the fit, so `test_lid.py` PINS `lid.logo_choice` to
each game's default mark at the size it was drawn while it checks them —
`Lid Innovation 130U` is an XS lid the rule now gives the plain mark, and its
pattern would otherwise be a different mark altogether. The fit is then
asserted on its own: seven named lids, and two invariants over all 50 — every
mark inside the flat floor, and none shrunk that did not have to be. The
generated Innovation mark is checked against both drawings it replaced, region
for region.

Two things worth keeping in mind for the next part:

**Never aim a mesh ray at a feature's exact centre.** A rectangular face is two
triangles and a ray down their shared diagonal is counted once per triangle,
which cancels: the face vanishes from the reading. Aimed at the centres, half
the Compile lids read as pre-7.0 because their recess walls disappeared. Every
probe in `test_lid_corpus.py` is offset by an `EPS` no dimension is a multiple
of.

**A baseline is the modal glyph bottom, not the bottom of a box.** Adding the
Compile reference failed two probes at once, and both times the STEP and the
build agreed exactly on the wrong number — which is what said the model was
right and the probe was not. `Compile` has a descending `p` and `126 Cards/S` a
descending slash, so clustering the engraved text by bounding box merged two of
its three lines and read the third `1.118` low. `tests/test_lid.baselines`
takes the most common bottom edge instead. The other probe rounded the
staircase's height to 1 dp and compared exactly: Compile's reference slope is
`31.3` where ours is `31.2`, which is the `0.31 %` text divergence below
landing on a rounding boundary rather than a defect, so that dimension now
carries a tolerance.

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
- **The plain Innovation composition** — the wordmark with the circle round
  its `I` and the star over its `i`, and none of the flourishes that go with
  `Ultimate` — is a reading, not an export. The mark that renders it is
  measured off Allan's own drawings to `0.019`; whether it is the right
  composition is his call.
- ~~**Dominion's mark is a half turn out** from Compile's, FCM's and
  Innovation's.~~ Turned 2026-09-04; see "Dominion's mark WAS 180° out".
- **Stroke weight on the marks that are still outlines** — now FLOORED, not
  open (Allan, 2026-09-04): the mark is an inlay in a pocket and takes the
  cut floor, `0.200` mm, and `tests/test_lid_marks.py` rasterises every
  drawn mark at every scale the fit picks and holds its thinnest stroke to
  it. Compile's is `0.250` at its drawn size and `0.250` on its smallest lid
  (`0.905`), the closest in the catalogue; Dominion's, FCM's and Innovation's
  are `0.49` and up. Scaling an outline
  scales its strokes, where the Onshape sketches hold `#LineWidth` absolute.
  Innovation's plain mark no longer does this because it is generated; the
  other five drawings do, and it bites hardest where a mark is enlarged a long
  way — FCM's reaches `1.950`, and Innovation `Ultimate` `1.271`. The fix is
  the same rebuild, and `Ultimate` needs its Logo Flourishes sketch to do it.
- ~~**A corrected scale-1 Innovation export.**~~ Arrived 2026-09-04 as `Lid
  Innovation M5.15.15.45-Un with logo.step`, with the U's underline boxes
  placed correctly. `logos/Innovation/lid_logo_big.brep` is now LIFTED FROM IT
  — the 31 inlay faces themselves as OCCT wrote them, 846 edges against the
  mesh-lifted DXF's 2762, every prism within 0.0001 % of the STEP's inlay,
  and the five boxes under the U where the sketch has them (26 of 31 regions
  were already identical to 0.1 mm). A B-rep rather than a DXF because the
  DXF round trip re-fits a spline hole: the two `o` counters came back
  0.65 % small, invisible in area and visible in the prism. `tests/test_lid.py`
  holds the built inlays to that STEP region for region; the mesh-lifted
  `lid_logo_big.dxf` is gone (git history keeps it). The six cached Ultimate lids in
  `individual/` carry the old boxes. `logos/Innovation/sketch/Logo
  Flourishes.dxf` is the flourishes sketch itself at scale 1: 15 rectangles
  and 2 circles — the annulus at `r 4.849 / 5.449` (wall `0.600` = `LINE_WIDTH`,
  bore within `0.003` of the font's `I`), five arms `0.600 x 3.000`, five
  U-boxes `1.000 x 2.000` on an arc, five dashes `0.600 x 1.500` at a `4.500`
  pitch — the material for generating the Ultimate mark and for deriving
  `marks.TWIST` and `ARM0` from the sketch rather than a fit. Not done yet.
  The old note, kept for the record: the one previously on file had a
  corrupted flourish pattern (above), so `Innovation/lid_logo_big.dxf` was the
  mesh lift of a cached lid — 2762 edges where the STEP gives 846 — and
  `Ultimate` could not be rebuilt until the sketch was fixed.
- **The Mat branch.** Nothing in the lid's geometry reads `MatPocket`, but
  `calModelName` carries `-M`, so a Mat cascade's lid differs in its engraved
  model code alone. `plan_exports` keys one `("Lid", model)` for both and
  `individual/` has a single lid where `cad.build` will write two. Harmless
  today; it wants a decision when the engraving lands.
