#!/usr/bin/env python3
"""`cad/layout.py` lays out what make_cascade --auto-plates lays out, and
every cascade in the catalogue gets a legal layout.

Three tiers:

1. EQUIVALENCE. Dominion 168 Card Unsleeved is laid out by make_cascade
   `--auto-plates` from the built parts (a donor mutation, into a temp file)
   and by `layout.layout` from the same parts; the two must agree object for
   object — plate, position, angle — and tower for tower. Same rules, same
   result, or the lift changed something.
2. THE CATALOGUE. Every parts.csv cascade — 50 — is composed (`cad.cascade`)
   from build/, laid out, written, read back and held to the guards: every
   object on its plate, clear of its neighbours, the tower inside every
   nozzle's reach and clear of the parts. Refusals are failures, and so is a
   missing part.
3. THE SLICE. Where BambuStudio.app is installed, three are sliced — the P1
   one above, Dominion 560 Card Sleeved (the H2C, whose two nozzles reach
   different parts of the bed) and Dominion 650 Card Sleeved (the one whose
   lid fits the H2C only at 44 degrees with half a millimetre to spare) —
   and every plate must return 0.

    .venv/bin/python -m cad.build --part all
    .venv/bin/python tests/test_layout.py         # 2 min; 6 with the slices
"""
import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "automation"))

from cad import cascade as CC, derive as D, layout as LY, params, project as PJ  # noqa: E402
import filaments as FIL                                                          # noqa: E402
import towers                                                                    # noqa: E402

STUDIO = Path("/Applications/BambuStudio.app/Contents/MacOS/BambuStudio")
def shipped(folder, model):
    """The shipped project carrying `model`, whatever named it. The name is not
    stable — the version went into it on 2026-09-05 — but the model code in the
    bracket is, and it is unique per cascade (`refresh_cascades.find_project`)."""
    hits = sorted((ROOT / "cascades" / folder).glob(f"*({model}).3mf"))
    assert len(hits) == 1, f"{model}: {len(hits)} shipped projects"
    return hits[0]


SHIPPED_168 = shipped("Dominion", "S4.16.10.32-Un")
fails = []


def check(label, ok, detail=""):
    print(f"  {'ok ' if ok else 'FAIL'}  {label}" + (f"  ({detail})" if detail and not ok else ""))
    if not ok:
        fails.append(label)


def rows():
    for row in params.load_rows(ROOT / "automation" / "parts.csv"):
        if (row.get("Status") or "").strip() == "Parked":
            continue
        for sleeved in (0, 1):
            p = params.from_row(row, sleeved)
            yield row, p, D.derive(p)


def find(model):
    for row, p, d in rows():
        if d.calModelName.replace(".Un", "-Un").replace(".Sl", "-Sl") == model:
            return row, p, d
    raise SystemExit(f"no row {model}")


def layout_key(bed, plates, placements, objects):
    """Order-free: (role, plate, x, y, angle) per object, plus the towers."""
    return (bed, sorted((LY.role(objects[pl.obj].name), pl.plate, round(pl.x, 3),
                         round(pl.y, 3), round(pl.angle % 360, 3)) for pl in placements),
            [(round(p.tower[0], 3), round(p.tower[1], 3)) for p in plates])


def read_key(path):
    lay = PJ.read(path)
    names = {oid: n for oid, n, _p in lay.objects}
    return (lay.bed, sorted((LY.role(names[oid]), pl.plate, round(pl.x, 3), round(pl.y, 3),
                             round(pl.angle % 360, 3)) for oid, pl in lay.placements.items()),
            [(round(p.tower[0], 3), round(p.tower[1], 3)) for p in lay.plates])


def slice_ok(path, tmp):
    outdir = Path(tmp) / ("slice_" + path.stem[:20].replace(" ", "_"))
    outdir.mkdir()
    subprocess.run([str(STUDIO), "--slice", "0", "--outputdir", str(outdir), str(path)],
                   capture_output=True, text=True, timeout=1200)
    result = outdir / "result.json"
    rc = json.loads(result.read_text()).get("return_code") if result.exists() else None
    return rc, len(list(outdir.glob("*.gcode")))


with tempfile.TemporaryDirectory() as tmp:
    tmp = Path(tmp)

    print("=== 1. the same layout as make_cascade --auto-plates ===")
    row, p, d = find("S4.16.10.32-Un")
    objects = CC.objects(row, p, d)
    bed, plates, placements = LY.layout(objects)
    check("bed p1", bed == "p1", bed)
    # make_cascade's own regeneration, from the same built files
    by_role = {}
    for name, fn in CC.parts(row, p, d):
        by_role.setdefault(LY.role(name), fn)
    mc_out = tmp / "mc.3mf"
    cmd = [sys.executable, str(ROOT / "automation" / "make_cascade.py"), str(SHIPPED_168),
           "-o", str(mc_out), "--auto-plates", "--bed", "p1"]
    shipped_names = {"Lid": "Lid 168U", "Box": "Box", "Holder": "Holder", "Pusher": "Pusher",
                     "TokenHolder": "TokenHolder"}
    for r, fn in by_role.items():
        cmd += ["--part", f"{shipped_names[r]}={ROOT / 'build' / 'Dominion' / fn}"]
    proc = subprocess.run(cmd, capture_output=True, text=True, cwd=ROOT)
    check("make_cascade --auto-plates ran", proc.returncode == 0, proc.stderr[-300:])
    if proc.returncode == 0:
        mine, theirs = layout_key(bed, plates, placements, objects), read_key(mc_out)
        check("same bed", mine[0] == theirs[0])
        check("same placements: role, plate, position, angle", mine[1] == theirs[1],
              f"\n      mine   {mine[1]}\n      theirs {theirs[1]}")
        check("same towers", mine[2] == theirs[2], f"{mine[2]} vs {theirs[2]}")

    print("\n=== 2. every cascade in the catalogue ===")
    # Nothing is refused: Dominion 650 Sleeved, whose 343.9 x 111.3 lid
    # spans 321.9 turned 45 degrees against an H2C's 320, takes the angle
    # that fits with the margin reduced to what is left (layout.fit_angle) —
    # Allan: it fits, just, and prints. Its layout is checked by the slice.
    AT_THE_LIMIT = set()
    written = {}
    n_ok = 0
    for row, p, d in rows():
        model = d.calModelName
        try:
            objs = CC.objects(row, p, d)
            bed, plates, places = LY.layout(objs)
            out = tmp / f"{model}.3mf"
            PJ.write(out, bed, objs, plates, places, title=CC.title(row, p, d))
        except SystemExit as e:
            check(f"{p.GameName} {model}: refused, and known to be at the bed's limit",
                  model in AT_THE_LIMIT, str(e))
            continue
        check(f"{model}: laid out, yet listed as at the limit", model not in AT_THE_LIMIT)
        back = PJ.read(out)
        problems = []
        if towers.problems(out):
            problems.append(f"tower {towers.problems(out)}")
        # the tower clears every object on its plate by at least TIGHT_GAP —
        # the collision make_cascade used to warn about and leave in place
        ps_w = float(LY.profile(bed).get("prime_tower_width", 35))
        for k, plate in enumerate(back.plates, start=1):
            tx, ty = plate.tower
            tower_obb = LY.rect_obb(tx, ty, tx + ps_w, ty + ps_w)
            for oid, pl in back.placements.items():
                if pl.plate != k:
                    continue
                w, dd, _h = back.sizes[oid]
                ob = (pl.x, pl.y, w / 2, dd / 2, __import__("math").radians(pl.angle))
                if LY.sat_overlap(tower_obb, ob, LY.TIGHT_GAP - 1e-6):
                    problems.append(f"plate {k} tower within {LY.TIGHT_GAP} of an object")
                    break
        ps = json.loads(__import__("zipfile").ZipFile(out).read("Metadata/project_settings.config"))
        if [x for x in FIL.makerworld_problems(ps) if x[3]]:
            problems.append("makerworld")
        if len(back.placements) != len(objs):
            problems.append(f"{len(back.placements)} of {len(objs)} placed")
        if problems:
            check(f"{p.GameName} {model}: clean", False, "; ".join(problems))
        else:
            n_ok += 1
        written[model] = (out, bed, len(plates))
    print(f"  {n_ok} cascades laid out, written and clean")
    beds = {}
    for _m, (_o, bed, _n) in written.items():
        beds[bed] = beds.get(bed, 0) + 1
    print(f"  beds: {beds}")
    check("every cascade laid out",
          len(written) == sum(1 for _ in rows()) - len(AT_THE_LIMIT), f"{len(written)}")

    if STUDIO.exists():
        print("\n=== 3. Studio slices: a P1 and an H2C cascade ===")
        for model in ("S4.16.10.32.Un", "L6.40.12.62.Sl", "L8.50.10.62.Sl"):
            if model not in written:
                check(f"{model} written", False)
                continue
            out, bed, n_plates = written[model]
            rc, n_gcode = slice_ok(out, tmp)
            check(f"{model} on {bed}: slice return_code 0", rc == 0, f"rc {rc}")
            check(f"{model}: one gcode per plate", n_gcode == n_plates, f"{n_gcode} vs {n_plates}")
    else:
        print("\n  skip  BambuStudio.app not installed; slices unchecked")

print("\nPASS" if not fails else "\nFAIL: " + ", ".join(fails))
sys.exit(1 if fails else 0)
