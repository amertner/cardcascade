#!/usr/bin/env python3
"""A 7.0 build still prints what shipped: every project under `cascades/` has
a cad twin with the same parts in it.

Writes every cascade with `cad.cascade` AT 7.0 and holds each shipped project
to its twin with `cad.compare`: the same roles in the same numbers, each
object's size within the known divergence for its role, both slots used the
same way, the tower legal, MakerWorld clean. Every shipped project must have a
twin — Dominion 650 Sleeved included, at the H2C's limit (spec/PROJECT.md,
`layout.fit_angle`).

## Why 7.0 and not the current release

It was the evidence the design review of 2026-09-05 asked for before the
Onshape pipeline could be retired. It has been retired — `cad/` is
authoritative — so this is now a REGRESSION test, and what it regresses
against is what is on the shelf: the Onshape pipeline built everything under
`cascades/` at 7.0. A later release is MEANT to differ; 7.1 ships two pushers
where a 7.0 box has three (`spec/REVISIONS.md`), and comparing a 7.1 twin here
would report that intended change as 24 failures. So the release is PINNED,
the way every other reference test pins one (`tests/reference.py`).

    .venv/bin/python -m cad.build --part all --version 7.0    # -> build/v7.0/
    .venv/bin/python tests/test_parallel.py       # about 3 minutes
"""
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from cad import build as B, cascade as CC, compare as CMP   # noqa: E402
from cad.refuse import Refused                  # noqa: E402

# Everything under `cascades/` was built by the Onshape pipeline at 7.0, so
# that is the release the twins are written at — not the current one. A later
# release is MEANT to print differently (7.1 ships two pushers where a 7.0 box
# has three, `spec/REVISIONS.md`), and a test that took the default would
# report those intended differences as failures the day the default moved.
# The claim here is the one that stays true forever: a 7.0 build still prints
# what shipped.
VERSION = CMP.REF_VERSION
COMPONENTS = B.out_for(VERSION)
TWINS = CMP.cad_dir(VERSION)

AT_THE_LIMIT = set()
fails = []


def check(label, ok, detail=""):
    print(f"  {'ok ' if ok else 'FAIL'}  {label}" + (f"  ({detail})" if detail and not ok else ""))
    if not ok:
        fails.append(label)


print("=== every cascade, written ===")
t0 = time.time()
refused = {}
n = 0
for row, d in CC.catalogue(version=VERSION):
    try:
        CC.make(row, d, out_dir=TWINS, root=COMPONENTS)
        n += 1
    except Refused as e:
        refused[d.calModelName.replace(".Un", "-Un").replace(".Sl", "-Sl")] = str(e)
print(f"  {n} written, {len(refused)} refused in {time.time() - t0:.0f} s")
check("nothing is refused", set(refused) == AT_THE_LIMIT, str(refused))

print("\n=== each shipped project against its twin ===")
t0 = time.time()
same, missing, differing = [], [], []
for game in sorted(p.name for p in CMP.SHIPPED.iterdir() if p.is_dir()):
    if not (TWINS / game).exists():
        continue
    shipped, cad = CMP.by_model(CMP.SHIPPED / game), CMP.by_model(TWINS / game)
    for code, s_path in sorted(shipped.items()):
        c_path = cad.get(code)
        if c_path is None:
            missing.append(code)
            continue
        diffs, notes = CMP.compare(s_path, c_path)
        (differing if diffs else same).append((game, s_path.name, diffs))
for game, name, diffs in differing:
    print(f"  DIFFERS  {game}/{name}: {'; '.join(diffs)}")
print(f"  {len(same)} same print, {len(differing)} differing, {len(missing)} without a twin "
      f"in {time.time() - t0:.0f} s")
check("every shipped project with a twin prints the same parts", not differing)
check("every shipped project has a twin",
      set(missing) == {CMP.model_of(f"x ({m}).3mf") for m in AT_THE_LIMIT}, str(missing))
check("the shipped catalogue is covered", len(same) + len(missing) >= 46, f"{len(same)}")

print("\nPASS" if not fails else "\nFAIL: " + ", ".join(fails))
sys.exit(1 if fails else 0)
