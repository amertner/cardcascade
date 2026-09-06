#!/usr/bin/env python3
"""The parallel run: every shipped cascade project has a cad twin that prints
the same parts.

Writes every cascade with `cad.cascade` (into build/cascades/, the parallel
tree) and holds each shipped project under `cascades/` to its twin with
`cad.compare`: the same roles in the same numbers, each object's size within
the known divergence for its role, both slots used the same way, the tower
legal, MakerWorld clean. Every shipped project must have a twin — Dominion 650
Sleeved included, at the H2C's limit (spec/PROJECT.md, `layout.fit_angle`).

This is the evidence the design review of 2026-09-05 asked for before the
Onshape pipeline can be retired: not a feeling, a scorecard.

    .venv/bin/python -m cad.build --part all
    .venv/bin/python tests/test_parallel.py       # about 3 minutes
"""
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from cad import cascade as CC, compare as CMP   # noqa: E402
from cad.refuse import Refused                  # noqa: E402

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
for row, d in CC.catalogue():
    try:
        CC.make(row, d)
        n += 1
    except Refused as e:
        refused[d.calModelName.replace(".Un", "-Un").replace(".Sl", "-Sl")] = str(e)
print(f"  {n} written, {len(refused)} refused in {time.time() - t0:.0f} s")
check("nothing is refused", set(refused) == AT_THE_LIMIT, str(refused))

print("\n=== each shipped project against its twin ===")
t0 = time.time()
same, missing, differing = [], [], []
for game in sorted(p.name for p in CMP.SHIPPED.iterdir() if p.is_dir()):
    if not (CMP.CAD / game).exists():
        continue
    shipped, cad = CMP.by_model(CMP.SHIPPED / game), CMP.by_model(CMP.CAD / game)
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
