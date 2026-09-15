"""Every project's name, held to the one rule that generates it.

`components.cascade_filename` names a cascade on BOTH pipelines, and CLAUDE.md
("A NAME is an identity") is the rule. Held here: every shipped project is
EXACTLY what the rule generates and carries no version; each TITLE's version is
the row's GENERATION; FCM's form; and `cad.cascade`'s titles at `p.Version`.

    python3 tests/test_names.py
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "automation"))

from cad import cascade as CC, params, revisions as R  # noqa: E402
import components as C                               # noqa: E402
import onshape_config as OC                          # noqa: E402
import plan_exports as P                             # noqa: E402
import refresh_cascades as RC                        # noqa: E402

fails = []


def check(label, got, want):
    ok = got == want
    print(f"  {'ok ' if ok else 'FAIL'}  {label}" + ("" if ok else f"  ({got!r} != {want!r})"))
    if not ok:
        fails.append(label)


print("=== the form ===")
check("canonical carries the version before the bracket",
      C.cascade_filename("Dominion", "168 Card", "Sl", "S4.16.10.32-Sl", "7.0"),
      "Dominion 168 Card Sleeved v7.0 (S4.16.10.32-Sl).3mf")
check("a '/' in the model code still folds",
      C.cascade_filename("Dominion", "246 Card", "Un", "S2.40.12/30.32-Un", "7.0"),
      "Dominion 246 Card Unsleeved v7.0 (S2.40.12-30.32-Un).3mf")
check("None is a deliberate 'no version', and what the tracked trees pass",
      C.cascade_filename("Dominion", "168 Card", "Sl", "S4.16.10.32-Sl", None),
      "Dominion 168 Card Sleeved (S4.16.10.32-Sl).3mf")
check("FCM: a label ending in a digit takes the sleeving letter directly",
      C.cascade_filename("Food Chain Magnate", "180 Card", "Sl", "L3.18.6.20-Sl",
                         "7.0", "Occ 2"),
      "FCM Occ 2S v7.0 (180 Card L3-18-6-20-Sl).3mf")
check("FCM: a label ending in a letter takes it after a space",
      C.cascade_filename("Food Chain Magnate", "198 Card", "Un", "S4.18.12.32-Un",
                         "7.0", "Alt"),
      "FCM Alt U v7.0 (198 Card S4-18-12-32-Un).3mf")

print("\n=== parts.csv's Project label ===")
labels = {(r["Game"], r["Short name"]): (r.get("Project label") or "").strip()
          for r in params.load_rows(ROOT / "automation" / "parts.csv")}
check("only FCM rows carry one",
      sorted(g for (g, _n), v in labels.items() if v), ["Food Chain Magnate"] * 4)
check("and all four do",
      sorted(v for (g, _n), v in labels.items() if g == "Food Chain Magnate"),
      ["Alt", "Milestones 1", "Occ 1", "Occ 2"])

print("\n=== every shipped project is what the rule generates ===")
expected = {}                                   # folder -> {filename: cascade}
for game, spec in C.GAMES.items():
    plan = P.compute_plan(game, spec, str(ROOT / "automation" / "parts.csv"), False,
                          frozenset())
    for c in plan.cascades:
        expected.setdefault(spec["folder"], {})[RC.project_name(game, c)] = c

for folder, names in sorted(expected.items()):
    on_disk = {p.name for p in (RC.SHIPPED / folder).glob("*.3mf")}
    unnamed = sorted(on_disk - set(names))
    check(f"{folder}: no project is named outside the rule", unnamed, [])
    # Not every row has a project, so the reverse is not a failure; but one
    # that is there must be found under its canonical name, not the fallback.
    for name, c in sorted(names.items()):
        if name not in on_disk:
            continue
        got, _how = RC.find_project(RC.SHIPPED / folder, c["ctx"]["game"], c)
        check(f"{folder}: find_project takes {name!r} as canonical",
              got and got.name, name)

check("and no shipped name carries a version",
      sorted(n for names in expected.values() for n in names if " v" in n), [])

print("\n=== the version each TITLE carries is the row's generation ===")
# The generation is what parts.csv's `Build` pins, not CURRENT. No PLANNED row
# is below CURRENT today, so this drives the rule directly.
for build, want in (("", OC.CURRENT), ("6.6", "6.6"), ("Un:6.6 Sl:7.0", "6.6")):
    gen = OC.generation_for(build, "Un")
    name = C.cascade_filename("Dominion", "290 Card (Mat)", "Un",
                              "M6.21.10/12.0-Un", gen)
    check(f"Build {build!r} titles the unsleeved cascade v{want}",
          name, f"Dominion 290 Card (Mat) Unsleeved v{want} (M6.21.10-12.0-Un).3mf")
check("and a 7.0 name does not promise 7.0 PARTS — the generation is a set",
      OC.GENERATIONS["7.0"]["Holder"], "6.6")

print("\n=== cad.cascade's titles ===")
rows = CC.catalogue()
one = [(row, d) for row, d in rows if d.calModelName.startswith("S4.16.10.32")
       and not d.isSleeved][0]
check("a cad title is the same rule at p.Version",
      CC.title(*one) + ".3mf",
      C.cascade_filename("Dominion", "168 Card", "Un", "S4.16.10.32-Un", R.CURRENT))
# Read to the SPACE before the model code, not by width: `7.1a` broke `[:3]`.
check("every cad title carries a version, and it is the default release",
      sorted({t.split(" v")[1].split(" ")[0] for t in
              (CC.title(row, d) for row, d in rows)}), [R.CURRENT])
check("cad names 50 distinct projects",
      len({CC.title(row, d) for row, d in rows}), len(rows))
# The OLD release is named explicitly, never taken from the default.
NEW = R.RELEASES[-1]
at70 = CC.catalogue(version="7.0")
at71 = CC.catalogue(version=NEW)
check(f"a {NEW} set is titled apart from the 7.0 one",
      {CC.title(row, d) for row, d in at71}
      & {CC.title(row, d) for row, d in at70}, set())

print("\n=== a name is an identity, a version is a release ===")
check("the cad file name carries no version",
      CC.filename(*one), C.cascade_filename("Dominion", "168 Card", "Un",
                                            "S4.16.10.32-Un", None))
check("and neither does any of them",
      sorted(n for n in (CC.filename(row, d) for row, d in rows)
             if " v" in n), [])
check("--publish puts it back, and is the title plus the suffix",
      CC.filename(*one, versioned=True), CC.title(*one) + ".3mf")
check(f"so a {NEW} publish is 50 files apart from a 7.0 one",
      {CC.filename(row, d, True) for row, d in at71}
      & {CC.filename(row, d, True) for row, d in at70}, set())
check("while the two write the SAME 50 names into the repo",
      {CC.filename(row, d) for row, d in at71},
      {CC.filename(row, d) for row, d in at70})
check("cad and refresh_cascades agree on the tracked name",
      CC.filename(*one),
      RC.project_name("Dominion", {"ctx": {"short_name": "168 Card", "label": ""},
                                   "sleeved": "Un", "model": "S4.16.10.32-Un"}))

print("\nPASS" if not fails else "\nFAIL: " + ", ".join(fails))
sys.exit(1 if fails else 0)
