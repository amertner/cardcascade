#!/usr/bin/env python3
"""`cad/project.py` writes a project Studio slices, and the same one it read.

The first project written without a donor is checked against its shipped
twin: Dominion 168 Card Unsleeved is read for its layout (`project.read`),
written again from the parts under `build/` in that exact layout, and the
result held to the shipped file — the same roles on the same plates at the
same positions and angles, the same two slots and extruders, the same object
sizes to the tolerance the corpus tests allow the rebuilt parts — then to the
two project guards (`filaments`, `towers`) and, where BambuStudio.app is
installed, to a CLI slice of every plate with `return_code` 0, which is the
only thing that sees a tower in unprintable space or an object off its plate.

    .venv/bin/python -m cad.build --part all     # needs build/Dominion
    .venv/bin/python tests/test_project.py      # a minute; three with the slice

The two constants copied from make_cascade while both exist — the bed table
and PRINT_SETTINGS — are held equal to it, so the copies cannot drift apart
unnoticed.
"""
import json
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "automation"))

from cad import build as B, derive as D, params, project as PJ   # noqa: E402
import filaments as FIL                                          # noqa: E402
import make_cascade as MC                                        # noqa: E402
import towers                                                    # noqa: E402


def shipped(folder, model):
    """The shipped project carrying `model`, whatever named it. The name is not
    stable — the version went into it on 2026-09-05 — but the model code in the
    bracket is, and it is unique per cascade (`refresh_cascades.find_project`)."""
    hits = sorted((ROOT / "cascades" / folder).glob(f"*({model}).3mf"))
    assert len(hits) == 1, f"{model}: {len(hits)} shipped projects"
    return hits[0]


SHIPPED = shipped("Dominion", "S4.16.10.32-Un")
MODEL = "S4.16.10.32-Un"
STUDIO = Path("/Applications/BambuStudio.app/Contents/MacOS/BambuStudio")
fails = []


def check(label, got, want, tol=0.0):
    ok = abs(got - want) <= tol if isinstance(want, (int, float)) and not isinstance(want, bool) else got == want
    print(f"  {'ok ' if ok else 'FAIL'}  {label:64s} {got!r:.60} vs {want!r:.60}" if not ok
          else f"  ok   {label}")
    if not ok:
        fails.append(label)


def role(name):
    """A shipped object's role from its (legacy-suffixed) name."""
    for r in ("HalfTokenHolder", "TokenHolder", "FirstHolder", "Holder", "Pusher", "Lid", "Box", "Topper"):
        if name.startswith(r):
            return r
    return name


print("=== the copies agree with make_cascade ===")
check("BEDS is make_cascade.BED_TABLE",
      [(v[0], v[1], v[2], v[3]) for v in PJ.BEDS.values()],
      [(w, d, prof, model) for _k, w, d, prof, model in MC.BED_TABLE])
check("PRINT_SETTINGS", PJ.PRINT_SETTINGS, MC.PRINT_SETTINGS)

print("\n=== the shipped layout, read ===")
lay = PJ.read(SHIPPED)
check("bed", lay.bed, "p1")
check("plates", len(lay.plates), 4)
check("objects", len(lay.objects), 9)
check("every object placed", sorted(lay.placements), sorted(o[0] for o in lay.objects))
check("the lid's inlays read as slot 2, its body as 1",
      sorted({e for _id, name, parts in lay.objects if role(name) == "Lid" for _p, e in parts}), [1, 2])

print("\n=== the parts, from build/ ===")
row = next(r for r in params.load_rows(ROOT / "automation" / "parts.csv")
           if D.derive(params.from_row(r, 0)).calModelName.replace(".Un", "-Un") == MODEL)
p = params.from_row(row, 0)
d = D.derive(p)
files = {"Box": B.box_file(d), "Lid": B.lid_file(d), "Pusher": B.pusher_file(d),
         "Holder": B.holder_file(d), "TokenHolder": B.token_holder_file(d, half=False)}
missing = [f for f in files.values() if not (ROOT / "build" / "Dominion" / f).exists()]
check("every part built", missing, [])
if missing or fails:
    print("\nFAIL: " + ", ".join(fails))
    sys.exit(1)

objects, placements = [], []
for oid, name, _parts in lay.objects:
    r = role(name)
    objects.append(PJ.Obj.from_file(PJ.object_name(r, d), ROOT / "build" / "Dominion" / files[r]))
    if r == "Lid":
        check("the lid keeps its capacity suffix", objects[-1].name, name)
    pl = lay.placements[oid]
    placements.append(PJ.Placement(len(objects) - 1, pl.plate, pl.x, pl.y, pl.angle))
    w, dd, h = objects[-1].size
    sw, sd, sh = lay.sizes[oid]
    # the rebuilt part's envelope is the cached one's (test_*_corpus), and the
    # 7.0 holder is 1.5 longer than a 6.6 one (spec/HOLDER.md); the token
    # holder's tray is the same part at the same depth
    tol = 1.6 if r == "Holder" else 0.05
    check(f"{name}: size {w:.2f} x {dd:.2f} x {h:.2f} within {tol} of the shipped mesh",
          max(abs(w - sw), abs(dd - sd), abs(h - sh)) <= tol, True)

print("\n=== written, read back, and held to the shipped file ===")
with tempfile.TemporaryDirectory() as tmp:
    out = Path(tmp) / SHIPPED.name
    PJ.write(out, lay.bed, objects, lay.plates, placements, title=SHIPPED.stem,
             metadata={"cardcascade:model": MODEL})
    check("written", out.exists() and out.stat().st_size > 100_000, True)
    back = PJ.read(out)
    check("same bed", back.bed, lay.bed)
    check("same plate count and towers", [(p.name, p.tower) for p in back.plates],
          [(p.name, p.tower) for p in lay.plates])
    # placements: by (role, plate, x, y, angle), order-free
    def key(layout):
        names = {oid: role(n) for oid, n, _p in layout.objects}
        return sorted((names[oid], pl.plate, round(pl.x, 4), round(pl.y, 4), round(pl.angle, 4))
                      for oid, pl in layout.placements.items())
    check("same roles at the same positions on the same plates", key(back), key(lay))
    # parts and slots
    check("lid: body on slot 1, every inlay on slot 2",
          sorted({(n.startswith("Part "), e) for _id, name, parts in back.objects
                  if name.startswith("Lid") for n, e in parts}), [(False, 1), (True, 2)])
    zf = zipfile.ZipFile(out)
    ps = json.loads(zf.read("Metadata/project_settings.config"))
    cfg = zf.read("Metadata/model_settings.config").decode()
    check("two slots, white then black", ps["filament_colour"], list(PJ.FILAMENTS))
    check("both slots used", FIL.used_extruders(cfg), [1, 2])
    check("arachne", ps["wall_generator"], "arachne")
    check("arachne listed as a process deviation",
          "wall_generator" in ps["different_settings_to_system"][0].split(";"), True)
    check("stock printer preset", ps["printer_settings_id"], FIL.stock_printer_id(ps))
    check("MakerWorld: nothing blocking",
          [x for x in FIL.makerworld_problems(ps) if x[3]], [])
    check("prime tower inside both nozzles' reach on every plate", towers.problems(out), [])
    shipped_ps = json.loads(zipfile.ZipFile(SHIPPED).read("Metadata/project_settings.config"))
    diff = sorted(k for k in ps if k in shipped_ps and ps[k] != shipped_ps[k])
    check("settings are the shipped project's (the profile's)", diff, [])
    members = sorted(zf.namelist())
    check("members Studio expects present",
          all(m in members for m in ("3D/3dmodel.model", "3D/_rels/3dmodel.model.rels",
                                     "Metadata/model_settings.config",
                                     "Metadata/project_settings.config", "[Content_Types].xml",
                                     "_rels/.rels")), True)

    if STUDIO.exists():
        print("\n=== a Studio slice of every plate ===")
        outdir = Path(tmp) / "slice"
        outdir.mkdir()
        proc = subprocess.run([str(STUDIO), "--slice", "0", "--outputdir", str(outdir), str(out)],
                              capture_output=True, text=True, timeout=900)
        result = outdir / "result.json"
        rc = json.loads(result.read_text()).get("return_code") if result.exists() else None
        check("slice return_code 0", rc, 0)
        if rc != 0:
            for line in (proc.stdout + proc.stderr).strip().splitlines()[-10:]:
                print(f"        {line}")
            print(f"        {result.read_text()[:600] if result.exists() else 'no result.json'}")
        gcodes = sorted(outdir.glob("*.gcode"))
        check("one gcode per plate", len(gcodes), len(lay.plates))
        # keep the written project for a look
        keep = ROOT / "tmp" / "test_project"
        keep.mkdir(parents=True, exist_ok=True)
        shutil.copy(out, keep / out.name)
        print(f"       written project kept at {keep / out.name}")
    else:
        print("\n  skip  BambuStudio.app not installed; the slice is unchecked here")

print("\nPASS" if not fails else "\nFAIL: " + ", ".join(fails))
sys.exit(1 if fails else 0)
