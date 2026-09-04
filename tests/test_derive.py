#!/usr/bin/env python3
"""Check cad/derive.py against every independently-measured number on record.

The formulae are transcribed from the Onshape variable studio; these anchors
were measured off exported meshes long before the studio was available, by
`verify.py` and by hand. Agreement between the two is what says the
transcription is right.

    python3 tests/test_derive.py        # exits 1 on any mismatch
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from cad import params, derive

ROOT = Path(__file__).resolve().parent.parent
CSV = ROOT / "automation" / "parts.csv"
fails = []


def check(label, got, want, tol=0.005):
    ok = abs(got - want) <= tol if isinstance(want, float) else got == want
    print(f"  {'ok ' if ok else 'FAIL'} {label:52s} {got!r:>12} vs {want!r}")
    if not ok:
        fails.append(label)


def cascade(short_name, sleeved):
    rows = [r for r in params.load_rows(CSV) if r["Short name"] == short_name]
    assert len(rows) == 1, f"{len(rows)} rows named {short_name!r}"
    return derive.derive(params.from_row(rows[0], sleeved))


print("\nverify.audit_rises — rise measured off printed pushers")
# "8 risers alternates 10.923/10.827 about 10.875" (verify.py). The mean is the
# formula's value; the alternation is the staircase not dividing evenly.
check("Dominion 400 Card Un rise (8 risers)", cascade("400 Card (Mat)", 0).calHeightIncrement, 10.875)
check("FCM 144 Card Un rise (5 risers, desired 20)", cascade("144 Card", 0).calHeightIncrement, 17.4)
check("Innovation Single Set Un rise (3 risers, capped at 22)",
      cascade("Single Set", 0).calHeightIncrement, 22.0)

print("\nLOCK_STANDARD.md / PIPELINE.md — pusher depths quoted by name")
check("FCM Pusher 3x6-Un depth", cascade("180 Card", 0).calPusherTotalDepth, 14.04)
check("FCM Pusher 3x6-Sl depth", cascade("180 Card", 1).calPusherTotalDepth, 18.00)
check("FCM Pusher 5x6-Un depth", cascade("144 Card", 0).calPusherTotalDepth, 23.40)
check("Dominion Pusher 9x10-Sl depth", cascade("333 Card", 1).calPusherTotalDepth, 75.60)
check("Dominion Pusher 9x10-Un depth", cascade("333 Card", 0).calPusherTotalDepth, 55.80)
check("Dominion Pusher 2x18-Sl depth", cascade("472 Card", 1).calPusherTotalDepth, 39.60)
check("Innovation Pusher 5x15-Sl depth", cascade("3 Ages 5 Expansions", 1).calPusherTotalDepth, 60.75)
check("Dominion S2.40.12-30 Un depth (PIPELINE table)",
      cascade("246 Card", 0).calPusherTotalDepth, 20.76)

print("\nPIPELINE.md — pre-7.0 tab pitch is D - 12.00, measured 12.80")
d = cascade("244 Card", 0)
check("M4.21.10.32-Un tab pitch", d.calTabDistance, 12.80)
check("  ... and equals D - 12.00", d.calPusherTotalDepth - d.calTabDistance, 12.00)

print("\ntopper_split.py — card thickness and topper depth")
check("Innovation card thickness Un", cascade("3 Ages 5 Expansions", 0).calCardThickness, 0.40)
check("Innovation card thickness Sl", cascade("3 Ages 5 Expansions", 1).calCardThickness, 0.65)
# Topper depth = 2.00 + thickness*cards; calHolderDepth is slider distance - 0.5
# = slotDepth + 1.9. Both are "2 mm plus the cards" to within the 0.1 the
# studio carries, so this checks the slot depth the topper is cut to.
check("Innovation 15-card slot depth Un (topper depth = 2.00 + this = 8.00)",
      cascade("3 Ages 5 Expansions", 0).calSlotDepth, 6.00)
check("Innovation 10-card slot depth Un (topper 6.00)",
      cascade("3 Later Ages 5 Expansions", 0).calSlotDepth, 4.00)

print("\nparts.csv — lid depth and model code across every row")
bad_d = bad_m = n = 0
def norm(m):
    return m.replace("/", "-").replace("-Un", ".Un").replace("-Sl", ".Sl")
for r in params.load_rows(CSV):
    for slv, dcol, mcol in ((0, "Unsleeved D/mm", "Unsl Model"),
                            (1, "Sleeved D/mm", "Sleeved model")):
        dv = derive.derive(params.from_row(r, slv))
        n += 1
        csvd = (r[dcol] or "").strip()
        if csvd and abs(float(csvd) - dv.calLidDepth) > 0.1:
            bad_d += 1
            print(f"  FAIL lid depth {r['Short name']} {slv}: "
                  f"{dv.calLidDepth:.2f} vs csv {csvd}")
        # -M (Mat) and the never-built row's placeholder '.0' label width are
        # known parts.csv transcription gaps, not formula errors.
        want = norm((r[mcol] or "").strip())
        if dv.calModelName != want and want.replace(".0.", f".{dv.calSideLabelWidth}.") \
                != dv.calModelName.replace("-M", ""):
            bad_m += 1
            print(f"  FAIL model {dv.calModelName} vs csv {want}")
check("lid depths within 0.1 mm of parts.csv", bad_d, 0)
check("model codes reproduce parts.csv (mod -M / placeholder)", bad_m, 0)
print(f"  ({n} cascades checked)")


print("\n=== the slant's max(): which term wins, on every row ===")
# `Top slant angle`'s vertical leg is max(calSlotDepth + 2, calHeightIncrement
# - 1). The rise term wins on every row today — asserted, with the tightest
# row named, so a new row that flipped the branch is seen rather than silently
# given a steeper holder.
_worst = None
for _row in params.load_rows(ROOT / "automation" / "parts.csv"):
    for _sl in (0, 1):
        _p = params.from_row(_row, _sl); _d = derive.derive(_p)
        _m = (_d.calHeightIncrement - 1.0) - (_d.calSlotDepth + 2.0)
        if _worst is None or _m < _worst[0]:
            _worst = (_m, _d.calModelName)
check("the rise term wins the slant's max() on every row", _worst[0] > 0, True)
check("... by 0.667 at the tightest, S9.21.10.62-Sl", (round(_worst[0], 3), _worst[1]),
      (0.667, "S9.21.10.62.Sl"))

print(f"\n{'PASS' if not fails else 'FAIL: ' + ', '.join(fails)}")
sys.exit(1 if fails else 0)
