#!/usr/bin/env python3
"""Every cascade's placement rules, over the whole catalogue.

    .venv/bin/python tests/test_assembly.py

`cad/fit.py --no-solids` on all 50 cascades in all three states. No B-reps, so
it is seconds where a solids pass is hours — and it is the tier that generalises:
a margin that holds on one cascade and not on 50 is the finding worth having,
which is what `tests/test_lid_corpus.py` exists for on the Lid.

The interference tier is NOT run here. It builds a Box and a Lid per cascade,
which is minutes each; run `.venv/bin/python -m cad.fit --state all` on the
cascade you care about instead.

Two things are asserted beyond the margins themselves:

* **the tread offset is a CONSTANT.** `spec/ASSEMBLY.md` derives 0.150 between
  a pusher's tread centre and its rib's, with every parameter cancelling. If it
  is ever a function of anything, the derivation is wrong and this catches it.
* **a holder is fully supported on its tread** — both margins non-negative on
  every riser of every cascade. That is what the 0.150 threatens and the reason
  it is worth a test rather than a note.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from cad import assemble, assembly as A, derive as D, fit  # noqa: E402

fails = []
TREAD_OFFSET = 0.150            # spec/ASSEMBLY.md, "The finding"


def fail(label, msg):
    fails.append(f"{label}: {msg}")
    print(f"    FAIL {label}: {msg}")


rows = assemble.catalogue()
seen = {"cascades": 0, "margins": 0, "skipped": [], "unchecked": []}
offsets = set()

for folder, p, _tokens in rows:
    d = D.derive(p)
    model = f"{folder}/{d.calModelName}"
    cached = fit.cached_holders(p, d, folder)
    if not cached:
        seen["skipped"].append(model)
        continue
    seen["cascades"] += 1
    for state in A.STATES:
        margins = list(fit.lid_margins(p, d))
        if state == A.PLAY:
            margins += fit.socketed_pusher_margins(p, d) + fit.tread_margins(p, d)
        else:
            margins += fit.stored_pusher_margins(p, d)
        margins += fit.holder_margins(p, d, cached)
        for m in margins:
            seen["margins"] += 1
            if m.got != m.got:            # not checked: no cached mesh
                seen["unchecked"].append(f"{model} {m.name}")
                continue
            if not m.ok:
                fail(f"{model} [{state}] {m.name}", f"{m.got:.3f} vs {m.want:.3f}")
            # A margin is a CLEARANCE: a negative one is parts overlapping,
            # whatever its nominal says, and the ones with no nominal (the
            # tread, the lid over the rear storage) are only checked here.
            if "on its tread" in m.name or "clearance" in m.name:
                if m.got < 0:
                    fail(f"{model} [{state}] {m.name}", f"negative: {m.got:.3f}")

    # The tread offset, from the two margins it splits: front + back is the
    # tread's own slack, and their difference is twice the offset.
    treads = [m for m in fit.tread_margins(p, d) if "on its tread" in m.name]
    for i in range(0, len(treads), 2):
        back, front = treads[i].got, treads[i + 1].got
        offsets.add(round((front - back) / 2, 6))

if len(offsets) != 1 or abs(offsets.pop() - TREAD_OFFSET) > 1e-9:
    fail("tread offset", f"not the constant {TREAD_OFFSET}: {sorted(offsets)}")
else:
    print(f"  ok   tread offset is {TREAD_OFFSET} on every cascade, every riser")

print(f"\n  {seen['cascades']} cascades x {len(A.STATES)} states, "
      f"{seen['margins']} margins checked")
if seen["skipped"]:
    print(f"  skipped (no cached holder): {', '.join(seen['skipped'])}")
if seen["unchecked"]:
    n = len(set(seen["unchecked"]))
    print(f"  {n} holder mate(s) not checked, no cached mesh: "
          f"{', '.join(sorted(set(seen['unchecked']))[:3])}"
          + (" ..." if n > 3 else ""))
print(f"\n{'FAILED: ' + '; '.join(fails) if fails else 'PASS'}")
sys.exit(1 if fails else 0)
