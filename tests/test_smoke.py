"""Every command-line entry point runs end to end on one cascade.

The part suites hold the GEOMETRY to its references; this holds the TOOLS
around it to "still works": each CLI is run as a subprocess on one Dominion
cascade and its output file checked for existence and format, which is the
whole claim. It is what catches a renamed argument or a broken import in a
script no other suite imports — `cad.gltf`, `cad.render` and
`render/cascade.py` had none until this file.

    .venv/bin/python -m cad.build --part all          # needs build/
    .venv/bin/python tests/test_smoke.py             # about a minute; assembles what it needs

Blender is an APPLICATION, not a dependency (`spec/RENDER.md`): the photoreal
check runs only where `/Applications/Blender.app` is, and says so when it is
not. Everything else fails rather than skips.
"""
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PY = sys.executable
BLENDER = Path("/Applications/Blender.app/Contents/MacOS/Blender")
ASSEMBLY = ROOT / "build" / "assemblies" / "Dominion" / "S4.16.10.32-Un closed-lid.3mf"
BOX = ROOT / "build" / "Dominion" / "Box M6.21.10.45-Un.3mf"
PROJECT = ROOT / "cascades" / "Dominion" / "Dominion 168 Card Unsleeved (S4.16.10.32-Un).3mf"
fails = []


def check(label, ok, detail=""):
    print(f"  {'ok ' if ok else 'FAIL'}  {label}" + (f"  ({detail})" if detail else ""))
    if not ok:
        fails.append(label)


def run(label, *cmd):
    t0 = time.time()
    proc = subprocess.run([str(c) for c in cmd], cwd=ROOT, capture_output=True, text=True)
    dt = time.time() - t0
    check(f"{label}: exit 0", proc.returncode == 0, f"{dt:.1f} s")
    if proc.returncode:
        for line in (proc.stdout + proc.stderr).strip().splitlines()[-8:]:
            print(f"        {line}")
    return proc.stdout + proc.stderr


# The assembly is made here if it is missing — a fresh clone has no
# build/assemblies/, and a test that needs one should not wait for a hand to
# run cad.assemble first (found on the first run on a second machine).
if not ASSEMBLY.exists() and BOX.exists():
    print("=== the assembly this needs, made first ===")
    run("cad.assemble --state closed-lid", PY, "-m", "cad.assemble", "--model",
        "S4.16.10.32-Un", "--state", "closed-lid")
for needed in (ASSEMBLY, BOX, PROJECT):
    check(f"input on disk: {needed.relative_to(ROOT)}", needed.exists())
if fails:
    print("\nFAIL: run cad.build --part all first")
    sys.exit(1)

with tempfile.TemporaryDirectory() as tmp:
    tmp = Path(tmp)

    print("=== cad.assemble --list imports no build123d ===")
    out = run("assembly + assemble import", PY, "-c",
              "import sys; import cad.assembly, cad.assemble; "
              "print('build123d' in sys.modules)")
    check("build123d not loaded", out.strip().endswith("False"), out.strip()[-40:])

    print("\n=== cad.gltf ===")
    glb = tmp / "cascade.glb"
    run("gltf", PY, "-m", "cad.gltf", ASSEMBLY, "-o", glb)
    check("glb written with the glTF magic", glb.exists() and glb.read_bytes()[:4] == b"glTF",
          f"{glb.stat().st_size // 1024 if glb.exists() else 0} KB")
    run("gltf --check-project", PY, "-m", "cad.gltf", ASSEMBLY, "-o", tmp / "check.glb",
        "--check-project", "--project", PROJECT)

    print("\n=== cad.render ===")
    contact = tmp / "contact.png"
    run("render --box --contact", PY, "-m", "cad.render", BOX, "--box", "--contact", contact)
    check("contact sheet is a PNG", contact.exists() and contact.read_bytes()[:4] == b"\x89PNG")
    views = tmp / "views"
    run("render --assembly", PY, "-m", "cad.render", ASSEMBLY, "--assembly", "--out", views)
    pngs = sorted(views.glob("*.png")) if views.exists() else []
    check("assembly views written (six named + hero)", len(pngs) >= 7,
          ", ".join(p.stem for p in pngs))

    print("\n=== cad.fit, solids tier ===")
    out = run("fit --state play", PY, "-m", "cad.fit", "--model", "S4.16.10.32-Un",
              "--state", "play")
    check("fit reports the interference tier", "interference" in out)
    check("fit reports no failure", "FAIL" not in out)

    print("\n=== cad.assemble --holder source ===")
    # The one cascade with NO cached holder, so the source is the only way.
    # Written under build/, where the box and pusher already are: an --out
    # elsewhere would have both built again into it.
    made = ROOT / "build" / "assemblies" / "Dominion" / "M6.21.10-12.45-M-Un closed.3mf"
    made.unlink(missing_ok=True)
    run("assemble --holder source", PY, "-m", "cad.assemble", "--model",
        "M6.21.10-12.45-M-Un", "--holder", "source", "--state", "closed")
    check("assembly written from source holders", made.exists(),
          f"{made.stat().st_size // 1024 if made.exists() else 0} KB")

    print("\n=== render/cascade.py in Blender ===")
    if BLENDER.exists():
        photo = tmp / "photo"
        run("blender -b -P render/cascade.py", BLENDER, "-b", "-P",
            ROOT / "render" / "cascade.py", "--", glb, "--out", photo,
            "--samples", "4", "--width", "240")
        shots = sorted(photo.glob("*.png")) if photo.exists() else []
        check("photoreal hero written", len(shots) >= 1, ", ".join(p.name for p in shots))
    else:
        print("  skip  Blender.app not installed; the photoreal renderer is unchecked here")

print("\nPASS" if not fails else "\nFAIL: " + ", ".join(fails))
sys.exit(1 if fails else 0)
