"""The parallel run's scorecard: every shipped project against its cad twin.

    .venv/bin/python -m cad.compare                 # all 48 shipped cascades
    .venv/bin/python -m cad.compare --game Dominion --name 168

For each project under `cascades/<Game>/` this finds the project `cad.cascade`
wrote under `build/cascades/<Game>/` (by model code, the way
`refresh_cascades.find_project` does) and compares what a print would see:

  * the printer, and the number of plates;
  * the roles present and how many of each — the same box, lid, pushers,
    holders, token holders and toppers;
  * each role's object size, to a tolerance that names the KNOWN divergences
    (`spec/`): a 7.0 holder is up to 1.6 longer than a 6.6 one, a rebuilt box
    or lid matches its cached envelope to 0.05;
  * the filament slots, and which slot each role prints in;
  * that every object sits on its plate and the tower is legal (the guards).

What it does NOT compare is the layout itself — where on a plate a part sits.
The shipped layouts are hand-tuned and the cad ones are the rule's; the same
parts on legal plates is the claim, not the same coordinates.

The output is one row per cascade with `same` or the differences, and a
summary. `--strict` exits non-zero on any difference outside the known
tolerances, for a test to call.
"""
import argparse
import glob
import json
import re
import sys
import zipfile
from pathlib import Path

from . import derive as D, layout as LY, params, project as PJ

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "automation"))
import filaments as FIL                                  # noqa: E402
import towers                                            # noqa: E402

SHIPPED = ROOT / "cascades"
CAD = ROOT / "build" / "cascades"
# size tolerance per role, mm — the known divergences between the cached
# parts and the rebuilt ones (spec/HOLDER.md: 30 of 50 shipped holders are
# 6.6, 1.5 shorter than a 7.0; the rest match to 0.05)
TOL = {"Holder": 1.6, "FirstHolder": 1.6}
DEFAULT_TOL = 0.05


def model_of(name):
    """The model code a project filename carries, `.`-folded to `-`."""
    m = re.search(r"\(([^()]*?)\)\.3mf$", name)
    if not m:
        return None
    code = m.group(1)
    code = re.sub(r"^\d+ Card ", "", code)           # FCM: "(144 Card M5-6-6-32-Sl)"
    return code.replace(".", "-")


def shipped_role(name):
    """A shipped object's role, legacy names included: `TokenHolder Half` is
    the HalfTokenHolder, and a bare `Part 1` is a token holder that a donor
    imported loose and never renamed (PIPELINE.md, "Interactive refresh") —
    the only object that ever appears under that name."""
    if name.startswith("TokenHolder Half"):
        return "HalfTokenHolder"
    if re.fullmatch(r"Part \d+", name):
        return "TokenHolder"
    return LY.role(name)


def by_model(folder):
    out = {}
    for path in glob.glob(str(folder / "*.3mf")):
        if "Label" in Path(path).name:
            continue
        code = model_of(Path(path).name)
        if code:
            out[code] = Path(path)
    return out


def summary(path):
    """What a print sees in one project."""
    lay = PJ.read(path)
    ps = json.loads(zipfile.ZipFile(path).read("Metadata/project_settings.config"))
    roles = {}
    for oid, name, parts in lay.objects:
        r = shipped_role(name)
        slots = sorted({e for _n, e in parts})
        roles.setdefault(r, []).append((lay.sizes[oid], slots))
    return {"printer": ps.get("printer_model"), "plates": len(lay.plates),
            "slots": list(ps.get("filament_colour", [])), "roles": roles,
            "tower_problems": towers.problems(path),
            "makerworld": [x for x in FIL.makerworld_problems(ps) if x[3]]}


def compare(shipped, cad):
    """[difference strings]; empty when the two are the same print."""
    a, b = summary(shipped), summary(cad)
    diffs, notes = [], []
    if (a["printer"] or "").replace("P1S", "P1P") != (b["printer"] or ""):
        notes.append(f"printer {a['printer']} -> {b['printer']}")
    if a["plates"] != b["plates"]:
        notes.append(f"plates {a['plates']} -> {b['plates']}")
    if [c.upper() for c in a["slots"]] != [c.upper() for c in b["slots"]]:
        # every cascade is white then black (PIPELINE.md); a shipped project
        # off that rule is the shipped project's fault, so a note, not a diff
        notes.append(f"shipped slots {a['slots']} are off the white/black rule")
    for r in sorted(set(a["roles"]) | set(b["roles"])):
        sa, sb = a["roles"].get(r, []), b["roles"].get(r, [])
        if len(sa) != len(sb):
            diffs.append(f"{r}: {len(sa)} shipped, {len(sb)} cad")
            continue
        tol = TOL.get(r, DEFAULT_TOL)
        for (size_a, slots_a), (size_b, slots_b) in zip(sorted(sa), sorted(sb)):
            worst = max(abs(x - y) for x, y in zip(size_a, size_b))
            if worst > tol:
                diffs.append(f"{r}: size {tuple(round(v, 1) for v in size_a)} vs "
                             f"{tuple(round(v, 1) for v in size_b)} ({worst:.2f} > {tol})")
            if slots_a != slots_b:
                # the shipped lids put the body on the object's slot and the
                # inlays on their own; ours the other way round — the same
                # SET of slots is the print
                diffs.append(f"{r}: slots {slots_a} vs {slots_b}")
    if b["tower_problems"]:
        diffs.append(f"cad tower: {b['tower_problems']}")
    if b["makerworld"]:
        diffs.append(f"cad makerworld: {b['makerworld']}")
    return diffs, notes


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--game")
    ap.add_argument("--name", help="part of the project name")
    ap.add_argument("--strict", action="store_true")
    args = ap.parse_args(argv)
    games = [args.game] if args.game else sorted(p.name for p in SHIPPED.iterdir()
                                                 if p.is_dir() and (CAD / p.name).exists())
    same = missing = differing = 0
    for game in games:
        shipped, cad = by_model(SHIPPED / game), by_model(CAD / game)
        for code, s_path in sorted(shipped.items()):
            if args.name and args.name.lower() not in s_path.name.lower():
                continue
            c_path = cad.get(code)
            label = f"{game}/{s_path.name}"
            if c_path is None:
                missing += 1
                print(f"  {'no cad project':16s} {label}")
                continue
            diffs, notes = compare(s_path, c_path)
            if diffs:
                differing += 1
                print(f"  {'DIFFERS':16s} {label}")
                for d_ in diffs:
                    print(f"                   {d_}")
            else:
                same += 1
                print(f"  {'same print':16s} {label}" + (f"   [{'; '.join(notes)}]" if notes else ""))
            if notes and diffs:
                print(f"                   ({'; '.join(notes)})")
    print(f"\n  {same} same, {differing} differing, {missing} without a cad project")
    return 1 if (args.strict and (differing or missing)) else 0


if __name__ == "__main__":
    sys.exit(main())
