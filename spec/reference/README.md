# Reference exports

Hand-exported from Onshape — the UI download, which costs **0 API calls**, not
the API translate path that `automation/onshape_api_log.csv` meters.

These are the ground truth `cad/` is checked against. `tests/test_pusher.py`
compares every X-normal face area, the whole mid-plate outline, the tab tops
and the volume against them, so they need to stay byte-stable: re-export only
to capture a deliberate CAD change, and say which change in the commit.

| file | cascade | primaries |
|---|---|---|
| `Pusher S4.7.7.32-Sl.step` | Compile 105 Card Sleeved | `H3 R4 fc7 cps7` no override, sleeved, 7.0 |
| `Pusher S2.40.12-30.45-Sl.step` | Dominion 246 Card Sleeved | `H3 R2 fc40 cps12` first riser 30, sleeved, 7.0 |

The pair is chosen to split the design: four equal risers against two with a
first-riser override, `C3` both times so the lock is held constant. The
Dominion one is what settles which step takes `calFirstSliderDistance` — see
`spec/PUSHER.md`.

Both are in **assembly position**, and the transform is not constant: X is
`+3.000` and Y `0` on both, but Z is `-18.000` on Compile and `-16.000` on
Dominion. Align on the bounding box.
