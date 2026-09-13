"""cad.scene builds a poster scene for one cascade per game: the 3MF has a
label, every planned stack, and no riser stack proud of its topper. Needs
the parts under build/ (cad.build --part all). No Blender.

    .venv/bin/python tests/test_scene.py
"""
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from cad import cascade as CC, mesh3mf, scene as SC   # noqa: E402

fails = []


def check(label, got, want=True):
    ok = got == want
    print(f"  {'ok ' if ok else 'FAIL'}  {label}" + ("" if ok else f"  ({got!r} != {want!r})"))
    if not ok:
        fails.append(label)


spec = SC.load_spec()
picks = {"Compile": "L5.7.7.45-Sl", "FCM": "S4.18.12.45-Sl", "Dominion": "S2.40.12-30.45-Sl",
         "Innovation": "S5.15.15.62-Sl"}
for game, model in picks.items():
    rows = CC.catalogue(CC.CSV, game)
    row, d = [(r, dd) for r, dd in rows if CC.B.model_stem(dd.calModelName) == model][0]
    game_rows = [r for r, _d in rows]
    with tempfile.TemporaryDirectory() as tmp:
        path, glb = SC.write_scene(row, d, spec, game_rows, glb=Path(tmp) / "s.glb")
        objects = mesh3mf.read_assembly(path)
        names = [n for n, _v, _t in objects]
        check(f"{game}: label plate and its detail", ("Label" in names, "Label Part 2" in names), (True, True))
        plan = SC.card_plan(d, SC.render_spec(spec, row, d))
        stacks = [n for n in names if n.startswith("Cards ") and not n.startswith("Cards Label")]
        check(f"{game}: a stack per planned slot", len(stacks), len(plan))
        check(f"{game}: glb written", glb.exists() and glb.stat().st_size > 10000)
        if game == "Innovation":
            tops = [max(v[2] for v in verts) for n, verts, _t in objects if n == "Topper"]
            stack_tops = [max(v[2] for v in verts) for n, verts, _t in objects
                          if n.startswith("Cards ") and not n.startswith("Cards Label")]
            check("Innovation: no stack stands above the highest topper",
                  not stack_tops or max(stack_tops) <= max(tops))

print(f"\n{len(fails)} failure(s)")
sys.exit(1 if fails else 0)
