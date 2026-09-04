"""Every body in every written 3MF under build/ is a closed surface.

`mesh3mf.write` refuses a body with an open boundary, so this should find
none; it is here because the writer's own guard is the thing under test, and
because a doubled edge — two pieces of material touching along a line — is
written with a warning rather than refused, and this is where those are
listed. The review that added it found fifteen faulty bodies in seven files,
all Innovation: twelve logo inlays with an open boundary each (fixed: the
faces carried a stale triangulation, `mesh3mf.triangulate`) and three sleeved
boxes with a six-edge line contact where a hanging hole's edge landed exactly
on a divider face (fixed: `box.HOLE_CLEAR`).

Run `python -m cad.build --part all` first; this reads what is there and
fails on an empty build/.

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
