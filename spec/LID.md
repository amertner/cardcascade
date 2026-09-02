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
block    9.200 wide x (calPusherTotalDepth - 0.400) long x 5.000 tall
channel  3.300 wide down the middle, open at BOTH ends
walls    2.950 each side of it
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
count        2 for XS and S, 3 for M and L
X            the set spans (HorizontalSlots - 1) * calSlotwidth
             and is centred on x = -0.300
Y            back edge 9.000 in from the lid's back face,
             running forward by calPusherTotalDepth - 0.400
```

Both are exact on all 46 lids and all 5 STEPs — the `9.000` across depths from
`34.980` to `111.300`, which is what says it is an offset from the back and not
a centring rule.

**The count is the plain size rule and NOT `isOnlyTwoPusherSlots`.** An
Innovation M lid carries three sockets where its Box has two rear storage slots
and its cascade ships two pushers (`spec/BOX.md` records the same variable
being the box's answer). The third socket is harmless — a spare — but it is
Onshape's own inconsistency between the two parts, and `cad/` reproduces the
lid as it is rather than tidying it.

**`x = -0.300` is measured, not derived.** It is constant on every lid, and no
expression in the derived set produces it: the card slots' own centres are
`-0.450` (`box.thumb_centres` less half a slot), the front pocket's dividers
`-0.050`. So the socket set sits `0.300` left of the lid's centreline and
nothing yet says why. **Open — worth an answer from the sketch.**

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

## What is NOT built yet

Three things, all on the floor, and `tests/test_lid.py` accounts for the whole
volume difference with them so that nothing else can hide behind them.

### The engraving, `0.400` proud

Three lines standing on the inner floor, right-aligned, reading up in Y:
`calModelName`, then `GameName`, then `calCapacityLabel`, with `calVersion`
("CC 7.0") on the far left of the GameName's line — except on the XS lid,
which is too narrow and gives the version a line of its own. Every line is
Orbitron Bold, as the Box's are, and the cap heights differ line to line
(`3.000 / 2.819 / 3.500` on `Lid Dominion 246S`), so the sizes are fitted
rather than set — the same problem `cad/text.py` solves for the Pusher and the
Box.

Note this is EMBOSSED where the Box's floor text is ENGRAVED.

### The staircase logo, `0.600` proud

`ProductName` over a staircase pad with **`RisingSliders` equal steps**,
descending to the right. Measured on three references:

| | R | pad | step |
|---|---|---|---|
| `246S` | 2 | `43.800 x 22.018` | `21.900 x 11.009` |
| `244U` | 4 | `41.800 x 17.119` | `10.450 x 4.280` |
| `333S` | 9 | `43.800 x 67.618` | `4.867 x 7.513` |

Two of its four edges are already pinned:

* its **front edge is the socket span's own `y0`** — `-4.550`, `-9.960` and
  `-33.050`, exact on all three;
* its **width is the `ProductName` line's text box**, and its top sits
  `0.6234 x` that line's ink height below it — `2.633 / 2.512 / 2.633` against
  ink heights of `4.223 / 4.030 / 4.223`.

`Lid Innovation 130U` has **no staircase at all**, only the `Card Cascade`
line. Whatever suppresses it — the XS width, or the lid's depth against nine
risers' worth of steps — is not yet known.

### The logo pattern, and its pocket

The per-game motif in the underside of the floor, printed in the second
filament. It is a pocket `0.810` deep cut up from `z = 0`, and the inlay solids
are `0.810` prisms sitting `0.010` LOWER, so they stand `0.010` proud of the
lid's underside — which is what gives the slicer an unambiguous boundary, and
what makes a cached lid mesh measure `40.010` tall rather than `40.000`.

The pocket's footprint is a constant per game: `975.420` on both Dominion
lids, `685.682` on the Innovation one. The inlays fill it exactly.

**`Lid Dominion 246S.step` has the inlay solids but NO pocket**; the four later
exports have both. The pair is what settles the depth, and `tests/test_lid.py`
asserts both sides of it.

## Verified

`tests/test_lid.py` — the source against the four structural STEPs, 186 checks,
every one of them run against the reference AND the build. `tests/test_lid_corpus.py`
— all 44 cached lids that have a parts.csv row, against the placement rules.

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

- **`x = -0.300`**, the socket set's centre. Measured constant, underived.
- **The engraving's sizing rules**, and the staircase's height rule. The
  fitted-text problem the Box needed Allan's four sketches to close.
- **Why `Lid Innovation 130U` has no staircase.**
- **The logo pattern.** Deferred deliberately — it is a per-game motif and a
  second filament, and it does not interact with anything above.
- **The Mat branch.** Nothing in the lid's geometry reads `MatPocket`, but
  `calModelName` carries `-M`, so a Mat cascade's lid differs in its engraved
  model code alone. `plan_exports` keys one `("Lid", model)` for both and
  `individual/` has a single lid where `cad.build` will write two. Harmless
  today; it wants a decision when the engraving lands.
