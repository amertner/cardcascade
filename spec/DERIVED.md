# The Onshape variable studio, transcribed

*Fill this in from Onshape. It is the input to `cad/derive.py`, which is the
ONLY place a formula lives — no component module recomputes anything.*

**Paste expressions verbatim, in Onshape's own syntax and Onshape's own order.**
Do not tidy them, do not convert units, do not rename anything. A verbatim
expression is unambiguous and transcribes mechanically; a reformatted one hides
exactly the rounding and unit decisions that matter. Studio order gives the
dependency DAG for free.

Where a value is a *lookup* rather than a formula, put it in `tables/` and name
the file here.

---

## 1. Primary inputs (known — from `automation/set_variables.py`)

| Onshape name | Type | Source |
|---|---|---|
| `HorizontalSlots` | NUMBER | parts.csv `Horizontal` (S=3, M=4, L=5) |
| `RisingSliders` | NUMBER | parts.csv `Risers` |
| `FrontPocketCardCapacity` | NUMBER | parts.csv `Front capacity` |
| `CardsPerSlidingSlot` | NUMBER | parts.csv `Cards/Riser slot` |
| `isFirstSlidingSlotOverride` | NUMBER | 1 if `Cards/First Riser` set |
| `FirstSlidingSlotCards` | NUMBER | parts.csv `Cards/First Riser` |
| `isSleeved` | NUMBER | per-cascade (each row yields Un and Sl) |
| `MatPocket` | NUMBER | parts.csv `Merged-slot` |
| `GameName` | STRING | Compile / Dominion / FCM / Innovation |
| `Version` | STRING | embossed; see `automation/onshape_config.GENERATIONS` |

Anything else in the studio that these ten do not cover is a **missing primary**
— list it here, because `set_variables.build_primary` POSTs a replacement set and
would silently drop it.

| missing primary | type | default | notes |
|---|---|---|---|
| | | | |

---

## 2. Derived variables (formulae)

One row per derived variable, **in studio order**.

| # | Onshape name | Units | Expression (verbatim) | Consumed by |
|---|---|---|---|---|
| 1 | | mm | | Box, Lid |
| 2 | | mm | | Holder |
| 3 | | | | |

### Known-good anchors

Values already recovered by measurement, to check the transcription against.
**If a formula you paste disagrees with one of these, the formula wins** — these
were fitted to meshes and at least one has already been wrong once
(`PIPELINE.md`: "Today's base is `D − 12.00`, not `D − 11.80`").

| quantity | recovered value | source |
|---|---|---|
| card thickness | `Un 0.40`, `Sl 0.65` mm | `topper_split.CARD_MM` |
| topper depth | `2.00 + card_thickness * CardsPerSlidingSlot` | `topper_split.DEPTH_BASE` |
| topper text scale | `0.65` of the 15-card size | `PIPELINE.md` |
| lid outer | parts.csv W/D | `verify.check_lid`, ±0.2 mm |
| box outer | lid − 2.00 mm both axes | `verify.WALL` |
| old tab pitch | `D − 12.00` (pre-7.0) | `PIPELINE.md` |
| pusher rise | a function of `RisingSliders` within a game; 8 risers alternates `10.923 / 10.827` about `10.875` | `verify.audit_rises` |

That last row is the one to watch. The alternation says the rise is a *quantised*
division of some travel, not a plain one, and no amount of measuring 32 pushers
reveals which travel or which rounding. It needs the expression.

---

## 3. Lookups by `GameName`

`set_variables.py` says GameName "changes logo, height increment and card size".
One row per game; add columns for every game-varying value.

→ `tables/games.csv`

---

## 4. Lookups by depth / class

The pusher lock catalogue is already transcribed
(`automation/LOCK_STANDARD.md`, `verify.LOCK_CLASSES`) and `cad/lock.py` will
import it rather than restate it. List any OTHER depth-banded or
class-banded lookup here.

→ `tables/by_depth.csv`

---

## 5. Constants

Values that are neither primary nor derived — fixed in the CAD. The lock
constants are in `LOCK_STANDARD.md`; everything else goes here.

| name | value | units | notes |
|---|---|---|---|
| | | | |

---

## 6. What each part reads

A cross-check on section 2, and the thing that tells us whether the
`(key)` dedup identities in `automation/components.py` are actually right.

| part | variables it consumes |
|---|---|
| Box | |
| Lid | |
| Holder (standard) | |
| Holder (first riser) | |
| Pusher | |
| TokenHolder / HalfTokenHolder | |
| Topper | |
