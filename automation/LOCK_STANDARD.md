# The pusher lock standard

How a pusher locks into its lid and hangs in its box, as a rule rather than a
computation. Introduced at **7.0**. `PIPELINE.md` holds the history, the costings
and the rejected alternatives; this file is the standard itself.

`verify.LOCK_CLASSES` / `target_lock()` are this document in code.

---

## The one rule

> **Every lock feature, on all three parts, is placed from the pusher's
> centreline.**

That is the whole standard. Before 7.0 the three features were placed from three
different datums — tab A 4.00 in from one plate edge, tab B 4.20 in from the
other, the notch from the mid-line — and nothing kept them apart. Below
`D = 26.4` the notch walked into tab B; at `D = 18.00` it swallowed the tab
whole; at `D = 14.04` the two tabs fused into one boss. Eight of 32 pushers were
defective, and the CAD would have gone on producing more at any new depth.

One datum makes that class of failure unconstructable. Nothing else about the
redesign matters as much.

## A design is one number

`s` — the distance from the pusher's centreline to each tab's centre. Tabs and
notch keep their sizes and sit symmetrically about that centreline.

```
fits when    D >= 2 * (s + TAB_W/2 + EDGE_MIN)     EDGE_MIN = 2.00
hang base    = 2s
notch when   s >= TAB_W/2 + NOTCH_W/2 + LAND_MIN   LAND_MIN = 1.20, so s >= 5.80
```

A pusher takes **the largest class that fits its depth** — never a tweaked `s`.

| class | `s` | use when D ≥ | hang base | notch | pushers |
|---|---|---|---|---|---|
| C1 | ±3.10 | 14.00 | 6.20 | no | 1 |
| C2 | ±5.10 | 18.00 | 10.20 | no | 5 |
| C3 | ±8.50 | 24.80 | 17.00 | yes | 10 |
| C4 | ±13.50 | 34.80 | 27.00 | yes | 11 |
| C5 | ±24.00 | 55.80 | 48.00 | yes | 5 |

**Adding a new box size:** check `s <= D/2 - 3.90`. A depth that violates it
takes the next class down. It never gets an `s` of its own — one exception and
this stops being a catalogue and goes back to being a computation.

## What the three parts each carry

The lock is one mechanism spread across three parts, and all three are driven by
the same `s`:

| part | feature | placed at |
|---|---|---|
| Pusher | two tabs `3.80 × 5.00`, `1.50` proud | centreline ± `s` |
| Pusher | notch `5.40 × 5.20` through the plate | on the centreline (C3–C5 only) |
| Lid | two socket recesses | centreline ± `s` |
| Lid | key rib | on the centreline (C3–C5 only) |
| Box | two rim cutouts `4.50` wide × `5.25` deep | centreline ± `s` |

The tabs do **two** jobs, which is why the ladder costs what it does: they hold
the pusher in the lid socket, *and* they hang it in the box slot. `2s` is the
hang base — the span the pusher hangs on — so a class that pulls the tabs inboard
buys datum safety with stability.

## Sizes that do not move

Constants across all 32 pushers, before and after 7.0. Treat a departure from
these as a defect, not a variant:

| | |
|---|---|
| pusher overall / plate thickness | `4.500` / `3.000` |
| tab, proudness | `3.80 × 5.00`, `1.500` (one face) |
| notch | `5.400 × 5.200` |
| lid socket span, plain channel | `D − 0.40`, `3.300` |
| lid recess length | `4.00` |
| lid recess step | `1.700` |
| box slot depth | `3.200` |
| box rim cutout | `4.50` wide, `5.25` deep (`z 99.75 → 105.00`) |

Running clearances, measured: plate in channel `0.300`; tab in cutout `±0.35`;
tab `3.80` in a `4.00` recess `±0.10`. The plate's `0.300` is the tightest fit in
the mechanism, so it, not the tabs, sets how much slop the lock has.

**The recess step is `1.700`, and it was set by hand for a reason.** It is how far
one socket wall retreats to give the tab room, so it has to clear the tab's `1.500`
proudness — `0.200` of play. It was `1.800` before 7.0; a test print showed that
gave too much gap. It is the one running clearance the catalogue changed, and the
only number here that came from a printed part rather than a calculation, so
**do not tune it back on the grounds that `1.800` also fits.** It does fit; it is
just loose.

**Two things are called "tab depth" — keep them apart.** In the CAD, *tab depth*
is this `1.700` recess step. In this file and in `PIPELINE.md` the tab's *depth*
is its `5.000` along the insertion direction, the other half of `tab 3.80 × 5.00`.

## Three consequences to keep in mind

**A fixed class costs hang base at the top of each band.** A pusher at the wide
end of its class carries its tabs well inboard of its own edges — worst case 63 %
of what the plate could give. That is the price of the standard and it was
accepted knowingly. 15 of 32 pushers nonetheless come out *wider* than before,
because the old 4.00 mm inset was more generous than the 2.00 this allows at the
bottom of a band.

**`EDGE_MIN = 2.00` lands on the narrowest pusher in every band.** Two millimetres
of plate outboard of a tab. The load path is sound — the tab's full `5.00` root
sits on solid plate, and the strip outboard of it carries little — but it is thin
in the hand, and it is the first thing to check on any test print.

**Old and new parts do not mix, in either direction.** The socket's key rib blocks
the channel outright, so the notch position is a hard key; away from a recess the
socket wall leaves `3.27` against the `4.50` a tab needs, so a tab anywhere else
jams; and the box's rim cutouts are cut at the tab pitch. Box compatibility and a
fixed catalogue are mutually exclusive — a class stays box-compatible only over a
1.40 mm window of `D`, and just two of the 32 depths fall in one.

> **The rule to publish: a pusher, a lid and a box must all come from the same
> version. Holders and toppers carry over.**

## Checking a part

The conformance test is exact — measure the tabs, look up the class, compare:

```
.venv/bin/python automation/verify.py --catalogue    # per-pusher worksheet
.venv/bin/python automation/verify.py --pushers      # exits 1 on any defect
```

`verify.target_lock(D)` returns where the features belong, as distances from the
pusher's `D = 0` plate edge, so an export can be diffed against it directly.
`check_pusher` warns rather than refuses: the bytes are right and the CAD is
wrong, and refusing would block the rest of the assembly.
