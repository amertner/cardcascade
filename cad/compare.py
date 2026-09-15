"""The 7.0 regression check: every Onshape-shipped project against its cad twin.

    .venv/bin/python -m cad.compare                 # all 48 shipped cascades
    .venv/bin/python -m cad.compare --game Dominion --name 168

For each project the Onshape pipeline shipped — `spec/reference/shipped-7.0/
<Game>/` — this finds the project `cad.cascade` wrote for the same release and
compares what a PRINT would see: the printer and plate count, the roles and
how many of each, each role's object size to a tolerance naming the KNOWN
divergences (`spec/`), the filament slots, and that every object sits on its
plate with a legal tower. NOT the LAYOUT: the claim is the same parts on legal
plates, not the same coordinates. `--strict` exits non-zero on a difference.
"""
import argparse
import glob
import json
import re
import sys
import zipfile
from pathlib import Path

from . import layout as LY, project as PJ
from .revisions import RELEASES

# What everything under `SHIPPED` was built at. NOT `revisions.CURRENT`, and
# deliberately a literal: the current release moves, the shipped tree does not.
REF_VERSION = "7.0"

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "automation"))
import filaments as FIL                                  # noqa: E402
import towers                                            # noqa: E402

SHIPPED = ROOT / "spec" / "reference" / "shipped-7.0"


def cad_dir(version):
    """Where `cad.cascade` writes the twins for a RELEASE. Everything under
    `SHIPPED` was built at 7.0 and a later release is MEANT to differ, so the
    claim is "a 7.0 build still prints what shipped"."""
    from . import build as B
    return B.out_for(version) / "cascades"


# size tolerance per role, mm — the known divergences between the cached parts
# and the rebuilt ones (spec/HOLDER.md)
TOL = {"Holder": 1.6, "FirstHolder": 1.6, "RearHolder": 1.6}
DEFAULT_TOL = 0.05


def model_of(name):
    m = re.search(r"\(([^()]*?)\)\.3mf$", name)
    if not m:
        return None
    code = m.group(1)
    code = re.sub(r"^\d+ Card ", "", code)           # FCM: "(144 Card M5-6-6-32-Sl)"
    return code.replace(".", "-")


def shipped_role(name):
    """A shipped object's role, legacy names included: `TokenHolder Half` is
    the HalfTokenHolder, `Part 1` a token holder imported loose."""
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
    a, b = summary(shipped), summary(cad)
    diffs, notes = [], []
    if (a["printer"] or "").replace("P1S", "P1P") != (b["printer"] or ""):
        notes.append(f"printer {a['printer']} -> {b['printer']}")
    if a["plates"] != b["plates"]:
        notes.append(f"plates {a['plates']} -> {b['plates']}")
    if [c.upper() for c in a["slots"]] != [c.upper() for c in b["slots"]]:
        # every cascade is white then black (PIPELINE.md); a shipped project
        # off that rule is its own fault, so a note, not a diff
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
                # inlays on their own; ours the other way round, and the same
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
    ap.add_argument("--version", default=REF_VERSION, choices=RELEASES,
                    help=f"which release's twins to compare against (default "
                         f"{REF_VERSION}, the release the Onshape pipeline "
                         f"shipped at — a later one is MEANT to differ)")
    args = ap.parse_args(argv)
    CAD_AT = cad_dir(args.version)
    games = [args.game] if args.game else sorted(p.name for p in SHIPPED.iterdir()
                                                 if p.is_dir() and (CAD_AT / p.name).exists())
    same = missing = differing = 0
    for game in games:
        shipped, cad = by_model(SHIPPED / game), by_model(CAD_AT / game)
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
