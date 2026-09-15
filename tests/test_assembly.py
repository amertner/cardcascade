#!/usr/bin/env python3
"""Every cascade's placement rules, over the whole catalogue.

    .venv/bin/python tests/test_assembly.py

`cad/fit.py --no-solids` on all 50 cascades in all three states — seconds, no
B-reps, and NOT the interference tier (`-m cad.fit --state all` on one cascade
is). A mate that cannot be measured off the BUILT holders is a failure, not a
note. Beyond the margins: the tread offset is a CONSTANT on every cascade
(`spec/ASSEMBLY.md`, "The finding") and a holder sits on its tread at the
release's exact numbers (`spec/BOX.md`).
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from cad import assemble, assembly as A, derive as D, fit  # noqa: E402
from cad.parts import box as box_part, lid as lid_part      # noqa: E402

fails = []
TREAD_OFFSET = 0.150            # spec/ASSEMBLY.md, "The finding" — less box.rib_shift from 7.2f
TREAD_SLACK = 0.400             # calSliderDistance tread against a sd - 0.400 holder


def tread_offset(d):
    """The studio's 0.150, less the rib and socket moves (both 7.2f)."""
    return TREAD_OFFSET - box_part.rib_shift(d) - (lid_part.SOCKET_BACK - lid_part.socket_back(d))


def fail(label, msg):
    fails.append(f"{label}: {msg}")
    print(f"    FAIL {label}: {msg}")


rows = assemble.catalogue()
seen = {"cascades": 0, "margins": 0}
offsets = set()

for folder, d, _tokens, _toppers in rows:
    model = f"{folder}/{d.calModelName}"
    holders = fit.built_holders(d, folder)
    if not holders:
        fail(model, "no side slot found on its built holder")
        continue
    seen["cascades"] += 1
    for state in A.STATES:
        margins = list(fit.lid_margins(d))
        if state == A.PLAY:
            margins += fit.socketed_pusher_margins(d) + fit.tread_margins(d)
        else:
            margins += fit.stored_pusher_margins(d)
        margins += fit.holder_margins(d, holders)
        for m in margins:
            seen["margins"] += 1
            if m.got != m.got:            # NaN: the slot was not found
                fail(f"{model} [{state}] {m.name}", m.note)
                continue
            if not m.ok:
                fail(f"{model} [{state}] {m.name}", f"{m.got:.3f} vs {m.want:.3f}")
            # A margin is a CLEARANCE: a negative one is parts overlapping.
            if "on its tread" in m.name:
                offset = tread_offset(d)
                want = (TREAD_SLACK / 2 + offset if m.name.endswith("front")
                        else TREAD_SLACK / 2 - offset)
                if abs(m.got - want) > 1e-6:
                    fail(f"{model} [{state}] {m.name}", f"{m.got:.3f} vs {want:.3f}")
            elif "clearance" in m.name:
                if m.got < 0:
                    fail(f"{model} [{state}] {m.name}", f"negative: {m.got:.3f}")

    # front + back is the tread's slack; their difference is twice the offset.
    treads = [m for m in fit.tread_margins(d) if "on its tread" in m.name]
    for i in range(0, len(treads), 2):
        back, front = treads[i].got, treads[i + 1].got
        offsets.add(round((front - back) / 2 - tread_offset(d) + TREAD_OFFSET, 6))

if len(offsets) != 1 or abs(offsets.pop() - TREAD_OFFSET) > 1e-9:
    fail("tread offset", f"not the constant {TREAD_OFFSET} (before the release's rib and socket moves): {sorted(offsets)}")
else:
    print(f"  ok   tread offset is {TREAD_OFFSET} less the release's rib and socket moves on every cascade, every riser")

print(f"\n  {seen['cascades']} cascades x {len(A.STATES)} states, "
      f"{seen['margins']} margins checked")
print(f"\n{'FAILED: ' + '; '.join(fails) if fails else 'PASS'}")
sys.exit(1 if fails else 0)
