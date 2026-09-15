"""Every body in every written 3MF under build/ is a closed surface.

`mesh3mf.write` refuses an open boundary, so this should find none: the guard
is what is under test. A doubled edge (two pieces touching along a line) is
warned about rather than refused, and is listed here. An empty build/ fails.

    .venv/bin/python tests/test_build_meshes.py
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from cad import mesh3mf                              # noqa: E402

BUILD = ROOT / "build"
files = sorted(p for p in BUILD.glob("*/*.3mf") if p.parent.name != "assemblies")
if not files:
    print("FAIL: nothing in build/ — run `python -m cad.build --part all` first")
    sys.exit(1)

bodies, holes, contacts = 0, [], []
for path in files:
    for name, _verts, tris in mesh3mf.read(path):
        bodies += 1
        unpaired, doubled = mesh3mf.faults(tris)
        tag = f"{path.parent.name}/{path.name} [{name}]"
        if unpaired:
            holes.append(f"{tag}: {unpaired} unpaired edges")
        if doubled:
            contacts.append(f"{tag}: {doubled} doubled edges")

print(f"{len(files)} files, {bodies} bodies")
print(f"\n=== open boundaries (a slicer has to guess): {len(holes)} ===")
for line in holes:
    print(f"  FAIL  {line}")
print(f"\n=== line contacts (non-manifold, but they print): {len(contacts)} ===")
for line in contacts:
    print(f"  warn  {line}")

print("\nPASS" if not holes else f"\nFAIL: {len(holes)} open bodies")
sys.exit(1 if holes else 0)
