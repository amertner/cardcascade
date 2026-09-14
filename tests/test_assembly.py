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

The holder mates are measured off the BUILT holders (`build/`, made on the
spot where missing), so every cascade has one and a mate that cannot be
measured is a failure, not a note.

Two things are asserted beyond the margins themselves:

* **the tread offset is a CONSTANT.** `spec/ASSEMBLY.md` derives 0.150 between
  a pusher's tread centre and its rib's, with every parameter cancelling. If it
  is ever a function of anything, the derivation is wrong and this catches it.
  From 7.2f the ribs sit `box.rib_shift` (0.850) forward and the treads do
  not move (`spec/BOX.md`, "The ribs move forward"), so the constant is
  `0.150 - rib_shift` = -0.700 — still one number on every cascade.
* **a holder sits on its tread as the release says** — through 7.2e fully
  supported, 0.350 inside the front and 0.050 inside the back on every riser;
  from 7.2f 0.500 OVER the front edge and 0.900 inside the back, the overhang
  the prototype is printed to judge. Either way an exact number, not a sign.
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
    """The release's tread-to-rib offset: the studio's 0.150, less the rib
    shift (7.2f), less the socket's own move (`lid.socket_back`, 7.2f's
    `shorter_box`, which brings it to 0.000)."""
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
            # A margin is a CLEARANCE: a negative one is parts overlapping,
            # whatever its nominal says, and the ones with no nominal (the
            # tread, the lid over the rear storage) are only checked here.
            # The tread's two are held to the release's own numbers: the
            # slack split by the offset, `0.350 / 0.050` through 7.2e and
            # `-0.500 / 0.900` from 7.2f (module docstring).
            if "on its tread" in m.name:
                offset = tread_offset(d)
                want = (TREAD_SLACK / 2 + offset if m.name.endswith("front")
                        else TREAD_SLACK / 2 - offset)
                if abs(m.got - want) > 1e-6:
                    fail(f"{model} [{state}] {m.name}", f"{m.got:.3f} vs {want:.3f}")
            elif "clearance" in m.name:
                if m.got < 0:
                    fail(f"{model} [{state}] {m.name}", f"negative: {m.got:.3f}")

    # The tread offset, from the two margins it splits: front + back is the
    # tread's own slack, and their difference is twice the offset.
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
