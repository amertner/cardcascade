# Reference exports

Hand-exported from Onshape — the UI download, which costs **0 API calls**, not
the API translate path that `automation/onshape_api_log.csv` meters.

These are the ground truth `cad/` is checked against. `tests/test_pusher.py`
compares every X-normal face area, the whole mid-plate outline, the tab tops
and the volume against them, so they need to stay byte-stable: re-export only
to capture a deliberate CAD change, and say which change in the commit.

### Pusher

| file | cascade | primaries |
|---|---|---|
| `Pusher S4.7.7.32-Sl.step` | Compile 105 Card Sleeved | `H3 R4 fc7 cps7` no override, sleeved, 7.0 |
| `Pusher S2.40.12-30.45-Sl.step` | Dominion 246 Card Sleeved | `H3 R2 fc40 cps12` first riser 30, sleeved, 7.0 |

The pair is chosen to split the design: four equal risers against two with a
first-riser override, `C3` both times so the lock is held constant. The
Dominion one is what settles which step takes `calFirstSliderDistance` — see
`spec/PUSHER.md`.

Both are in **assembly position**: X `+3.000`, Y `0`, and Z at
`-calHeightIncrement` — `-18.000` on Compile (rise 18.000) and `-16.000` on
Dominion (rise 16.000). The rule is confirmed on all 32 component 3MFs in
`individual/`, and `pusher.assembly_offset` is it. Tests still align on the
bounding box, because that stays right if a future part places differently.

### Box

Five, because the Box has more independent axes than the Pusher did. What each
one splits, and what has been measured off them, is in `spec/BOX.md`.

| file | cascade |
|---|---|
| `Box Compile 105S.step` | Compile 105 Card Sl `S4.7.7.32-Sl` — S: 3 slots, 2 pusher slots, and the same cascade as the Pusher STEP above, so the box's rim cutouts can be checked against that pusher's tabs |
| `Box Dominion 244S.step` | Dominion 244 Card Sl `M4.21.10.45-Sl` — M: 4 slots, 3 pusher slots |
| `Box Dominion 202S Merged.step` | Dominion 202 Card (Mat) Sl — the SAME model code with `MatPocket = 1`, so the merge is isolated to `758.957 mm³` and 47 faces |
| `Box Dominion 650S.step` | Dominion 650 Card Sl `L8.50.10.62-Sl` — L: 5 slots, deepest box, the only C5 lock |
| `Box FCM 72S.step` | **not a parts.csv row** — scratch parameters (FCM Sl, `H3 R3 fc6 cps6`) Allan exported as an extra. Kept: it is the smallest box and the only C2 lock |

At 2.1 MB gzipped for all five they cost the repo almost nothing, and a
re-export costs an hour of somebody's afternoon rather than any API budget.
