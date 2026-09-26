"""CATALOGUE.md is generated: held equal to what `make_catalogue.py` writes
from parts.csv, so a row or a size cannot change without the published table
following. Also: every family in `catalogue.json` is a game the CAD builds,
and every `made_for` key names a row.

    .venv/bin/python tests/test_catalogue.py
"""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from cad import params                                   # noqa: E402
import make_catalogue as MC                              # noqa: E402

fails = []


def check(label, ok, detail=""):
    print(f"  {'ok ' if ok else 'FAIL'}  {label}" + ("" if ok else f"  {detail}"))
    if not ok:
        fails.append(label)


print("=== CATALOGUE.md is what the generator writes ===")
proc = subprocess.run([sys.executable, str(ROOT / "make_catalogue.py"), "--check"],
                      cwd=ROOT, capture_output=True, text=True)
check("make_catalogue.py --check", proc.returncode == 0, proc.stdout.strip())

print("=== catalogue.json names real rows ===")
spec, rows = MC.load()
keys = {f"{g}/{r['Short name'].strip()}" for g, r, _, _ in rows}
games = {g for g, *_ in rows}
built = {params.GAME_NAME[(r.get("Game") or "").strip()]
         for r in params.load_rows(str(MC.CSV))}
for fam in spec["families"]:
    check(f"family {fam} is a game the CAD builds", fam in built)
for g in games:
    check(f"game {g} has a family entry", g in spec["families"])
for g in spec.get("hidden", []):
    check(f"hidden {g} is kept out", g not in games)
for k in spec.get("made_for", {}):
    check(f"made_for {k} is a row", k in keys)
for k in spec["makerworld"]:
    check(f"makerworld {k} is a game or a row", k in built or k in keys)
for k, v in spec.get("profiles", {}).items():
    check(f"profiles {k} is a row", k in keys)
    check(f"profiles {k} names Un and/or Sl only", set(v) <= {"Un", "Sl"}, str(v))
for g, r, *_ in rows:
    check(f"{g}/{r['Short name']} printer class is named",
          (r.get("3D printer") or "").strip() in spec["printers"])

print(f"\n{len(fails)} failures" if fails else "\nall ok")
sys.exit(1 if fails else 0)
