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
| `Box Dominion 246S.step` | Dominion 246 Card Sl `S2.40.12/30.45-Sl` — the only one with a first-riser override, so the only one that can tell `calFirstSliderDistance` from `calSliderDistance` |
| `Box Dominion 246S without final fillet.step` | the same box with `Smooth box edges` suppressed. The PAIR is the point: it makes the last feature measurable (`0.600`, `129.190 mm³`) instead of a query to be guessed at, and it is the solid `cad/parts/box.py` is built against |

### Lid

Eight. What each one splits, and what has been measured off them, is in
`spec/LID.md`.

| file | cascade |
|---|---|
| `Lid Dominion 246S.step` | Dominion 246 Card Sl `S2.40.12/30.45-Sl` — the only one with a first-riser override, and the cascade whose Box and Pusher are both referenced above, so the 7.0 lock can be followed across all three parts of one design. The only export taken **without** the logo meshes embedded |
| `Lid Dominion 246S with logo.step` | the same lid with them embedded. The PAIR is the point: it makes the pattern pocket measurable on its own (`0.810` deep, `975.420` of footprint) instead of a feature to be guessed at — the same trick as the Box's filleted/unfilleted pair |
| `Lid Dominion 244U.step` | Dominion 244 Card Un `M4.21.10.32-Un` — M: three sockets, unsleeved |
| `Lid Dominion 333S.step` | Dominion 333 Card Sl `S9.21.10.62-Sl` — `RisingSliders 9`, past the logo block's eight-riser branch, and the only C5 lock among them |
| `Lid Innovation 130U.step` | Innovation 130 Card Un `XS5.15.10.32-Un` — XS: the narrowest lid, two horizontal slots, 31 pattern inlays, and the only one whose logo carries no staircase |
| `Lid Compile 126S.step` | Compile 126 Card Sl `S5.7.7.45-Sl` — a **second game's card size**, which nothing else here reaches, and the only Lid reference whose lock is C4. It found two bugs in the test's own probes on the day it arrived |
| `Lid FCM 105S.step` | **not a parts.csv row** — `213.900 x 44.700`, which no FCM row produces. Its staircase and sockets pin it to `RisingSliders 4` and `calSlotwidth 65.000`, which still leaves four model codes that differ only in the text engraved on the floor. Kept for its artwork, not as a structural reference |
| `Lid Innovation 270S.step` | Innovation 270 Card Sl `S5.15.15.62-Sl` — the `#LogoScaleFactor 1` export. Its LETTERS are sound and pinned Noto Serif Bold Italic for `Ultimate`; its **flourishes are corrupted** (two pattern instances missing, the rest displaced), so its artwork is not used. `spec/LID.md` has the comparison |

Each Lid file holds the lid body **plus** the logo pattern's inlays as separate
solids. The body is the biggest by volume, which is how the tests take it — and
the inlays are where `logos/<Game>/*.dxf` came from, lifted by
`make_lid_logo_dxf.py`. Four of the five marks now come from a STEP; only
Innovation's big one is still lifted from a cached mesh, for want of an export
whose flourishes are intact.

At 2.1 MB gzipped for the Boxes and 3.4 MB for the Lids they cost the repo
almost nothing, and a re-export costs an hour of somebody's afternoon rather
than any API budget.
