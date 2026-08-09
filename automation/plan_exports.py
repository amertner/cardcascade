#!/usr/bin/env python3
"""Stage 1 planner for the Card Cascade Onshape export pipeline (see
PIPELINE.md). Reads parts.csv + components.py, expands a game's rows into
cascades, composes each cascade's components, DEDUPLICATES them within the game
(many cascades share holders/pushers/boxes), diffs against individual/<Game>/,
and prints the unique export worklist with a projected Onshape API-call budget.
Emits manifest.json for the assembly stage.

MAKES ZERO API CALLS — pure local planning, safe to run freely.

Usage:
    plan_exports.py <Game> [--csv parts.csv] [--changed Holder,Pusher]
                            [--labels] [--out manifest.json]
"""
import argparse
import csv
import json
import sys
from collections import namedtuple
from pathlib import Path

import components as C
import onshape_config as OC
import provenance as PROV

Plan = namedtuple("Plan", "game spec rows cascades unique to_export skipped "
                          "parked present all_files")

HERE = Path(__file__).parent          # automation/
ROOT = HERE.parent                    # repo root — data dirs (individual/) live here
# A row is "ready" only if these geometry fields are present (else skip+report).
REQUIRED = ["Box Height / mm", "Unsleeved W/mm", "Unsleeved D/mm",
            "Sleeved W/mm", "Sleeved D/mm"]
CALLS_PER_EXPORT = 4          # translate + ~1-2 polls + download (planning est.)


def col(row, name):
    return (row.get(name) or "").strip()


def build_context(row, sleeved, game, spec):
    """Derived parameters for one cascade (one row + one sleeving)."""
    base = col(row, "Base model")
    model = col(row, "Sleeved model" if sleeved == "Sl" else "Unsl Model")
    first = col(row, "Cards/First Riser")
    size = base[0] if base else "?"
    return {
        "game": game, "folder": spec["folder"],
        "short_name": col(row, "Short name"),
        "base_model": base, "model": model,
        "size": size,
        "horizontal": int(col(row, "Horizontal") or 0),
        "risers": int(col(row, "Risers")),
        "cards_per_slot": int(col(row, "Cards/Riser slot")),
        "first_riser": int(first) if first else None,
        "front_capacity": col(row, "Front capacity"),
        "horizontal": col(row, "Horizontal"),
        "merged": col(row, "Merged-slot").upper() == "TRUE",
        "sleeved": sleeved, "sl": "S" if sleeved == "Sl" else "U",
        "pushers": C.pushers_for(spec, size),
    }


def holder(ctx, capacity, first=False, spans=False):
    """A holder keyed by (game, #cards it holds, sleeved). Compile holders span
    `Horizontal` protocols of Cards/Riser slot, so key on that instead."""
    slv = ctx["sleeved"]
    if spans:
        label = f"{ctx['horizontal']}x{ctx['cards_per_slot']}"
        key = ("Holder", "span", ctx["horizontal"], ctx["cards_per_slot"], slv)
    else:
        label = str(capacity)
        key = ("Holder", capacity, slv)
    name = f"Holder {label}-{slv}" + (" (first)" if first else "")
    return {"type": "Holder", "key": key, "file": f"{name}.3mf",
            "object": "Holder", "instance": "first" if first else None}


def compose(ctx, spec, labels):
    """All component instances for one cascade. Each dict: type, key (dedup
    identity), file, object (make_cascade name), count, [instance]."""
    m, sl, slv = ctx["model"], ctx["sl"], ctx["sleeved"]
    items = [
        {"type": "Box", "key": ("Box", m, ctx["merged"]),
         "file": f"Box {m}{' merged' if ctx['merged'] else ''}.3mf",
         "object": "Box", "count": 1},
        {"type": "Lid", "key": ("Lid", m), "file": f"Lid {m}.3mf",
         "object": "Lid", "count": 1},
        {"type": "Pusher",
         "key": ("Pusher", ctx["risers"], ctx["cards_per_slot"], slv),
         "file": f"Pusher {ctx['risers']}x{ctx['cards_per_slot']}-{slv}.3mf",
         "object": "Pusher", "count": ctx["pushers"]},
    ]
    # Holders. Compile holders span the box (one type, Risers of them); other
    # games use per-slot holders, with a first-riser holder replacing one
    # standard holder when Cards/First Riser is set.
    if spec.get("holder_spans"):
        h = holder(ctx, ctx["cards_per_slot"], spans=True)
        h["count"] = ctx["risers"]
        items.append(h)
    else:
        n_std = ctx["risers"] - (1 if ctx["first_riser"] else 0)
        std = holder(ctx, ctx["cards_per_slot"])
        std["count"] = n_std
        items.append(std)
        if ctx["first_riser"]:
            f = holder(ctx, ctx["first_riser"], first=True)
            f["count"] = 1
            items.append(f)
    # Game-specific extras.
    if "TokenHolder" in spec["extras"]:
        items.append({"type": "TokenHolder",
                      "key": ("TokenHolder", ctx["size"], slv),
                      "file": f"TokenHolder {ctx['size']}-{slv}.3mf",
                      "object": "TokenHolder", "count": 1})
    # HalfTokenHolder rides only on merged-slot (Mat) cascades — the "(Mat)"
    # Dominion boxes; ignored everywhere else even though the assembly export
    # may still contain the object.
    if "HalfTokenHolder" in spec.get("merged_extras", []) and ctx["merged"]:
        items.append({"type": "HalfTokenHolder",
                      "key": ("HalfTokenHolder", ctx["size"], slv),
                      "file": f"HalfTokenHolder {ctx['size']}-{slv}.3mf",
                      "object": "HalfTokenHolder", "count": 1})
    if "Toppers" in spec["extras"]:
        # Each topper is a separate export (Topper studio configured per
        # expansion). Toppers vary by (expansion, size, sleeved) only, so they
        # dedup across cascades of the same size+sleeving and future Innovation
        # cascades reuse them.
        for exp in spec["toppers"]:
            items.append({"type": "Topper",
                          "key": ("Topper", exp, ctx["size"], slv),
                          "file": f"Topper {exp} {ctx['size']}-{slv}.3mf",
                          "object": f"Topper {exp}", "count": 1})
    if labels and spec.get("onshape_label"):
        items.append({"type": "Label", "key": ("Label", m),
                      "file": f"Label {m}.3mf", "object": "Label", "count": 1})
    return items


def compute_plan(game, spec, csv_path, labels=False, changed=frozenset()):
    """Expand a game's rows into cascades + components, dedup within the game,
    and diff against individual/<folder>/. Returns a Plan. No I/O beyond the CSV
    and the component directory — makes zero API calls."""
    with open(csv_path, newline="") as f:
        rows = [r for r in csv.DictReader(f) if col(r, "Game") == game]
    if not rows:
        sys.exit(f"no rows for game {game!r} in {csv_path}")

    cascades, skipped, parked = [], [], []
    unique = {}          # dedup key -> {files:set, objects:set, type, cascades:[]}
    for row in rows:
        if col(row, "Status").strip().lower() == "parked":
            parked.append(col(row, "Short name"))
            continue
        missing = [c for c in REQUIRED if not col(row, c)]
        if missing:
            skipped.append((col(row, "Short name"), missing))
            continue
        for sleeved in ("Un", "Sl"):
            ctx = build_context(row, sleeved, game, spec)
            items = compose(ctx, spec, labels)
            name = f"{ctx['short_name']} {sleeved} ({ctx['model']})"
            cascades.append({"name": name, "model": ctx["model"],
                             "sleeved": sleeved, "status": col(row, "Status"),
                             "ctx": ctx, "row": row, "components": items})
            for it in items:
                u = unique.setdefault(it["key"], {
                    "type": it["type"], "files": set(), "objects": set(),
                    "cascades": []})
                u["files"].add(it["file"])
                u["objects"].add(it["object"])
                u["cascades"].append(name)

    outdir = ROOT / "individual" / spec["folder"]
    present = {p.name for p in outdir.glob("*.3mf")} if outdir.exists() else set()
    all_files = {f for u in unique.values() for f in u["files"]}
    prov = PROV.load(game)

    def needs_export(u):
        # Version-aware: a component is cached only if its file is recorded in
        # provenance AT THE CURRENT per-studio version. Missing file, no
        # provenance, or an older version -> re-export.
        if u["type"] in changed:
            return True
        ver = OC.VERSIONS.get(u["type"])
        # The Blank topper wasn't upgraded at 6.4 (no expansion logo) -> 6.3.
        if u["type"] == "Topper" and all("Blank" in f for f in u["files"]):
            ver = "6.3"
        return not all(PROV.is_current(prov, f, ver) for f in u["files"])

    to_export = {k: u for k, u in unique.items() if needs_export(u)}
    return Plan(game, spec, rows, cascades, unique, to_export, skipped,
                parked, present, all_files)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("game")
    ap.add_argument("--csv", default=str(HERE / "parts.csv"))
    ap.add_argument("--changed", default="",
                    help="comma-separated component types to force re-export")
    ap.add_argument("--labels", action="store_true",
                    help="include Onshape-generated labels (Compile)")
    ap.add_argument("--out", default=str(HERE / "manifest.json"))
    args = ap.parse_args()

    game, spec = C.game_by_name(args.game)
    if not spec:
        sys.exit(f"unknown game {args.game!r}; known: {list(C.GAMES)}")
    changed = {c.strip() for c in args.changed.split(",") if c.strip()}
    p = compute_plan(game, spec, args.csv, args.labels, changed)

    total_slots = sum(it["count"] for c in p.cascades for it in c["components"])
    n_export_ops = len(p.to_export)               # toppers = 1 op (shared key)
    est_calls = n_export_ops * CALLS_PER_EXPORT

    # ---- report ----
    print(f"Game: {game}  (individual/{spec['folder']}/)")
    print(f"Rows: {len(p.rows)}   cascades planned: {len(p.cascades)}"
          f"   (skipped incomplete: {len(p.skipped)}, parked: {len(p.parked)})")
    for name in p.parked:
        print(f"  skipped (parked): {name}")
    for name, miss in p.skipped:
        print(f"  skipped (incomplete): {name} — missing {', '.join(miss)}")
    print(f"\nComponent instances across all cascades: {total_slots}")
    print(f"Unique components (deduped): {len(p.unique)}"
          f"   → dedup ratio {total_slots}:{len(p.unique)}")
    by_type = {}
    for u in p.unique.values():
        by_type[u["type"]] = by_type.get(u["type"], 0) + 1
    print("  by type:", ", ".join(f"{t}×{n}" for t, n in sorted(by_type.items())))
    prov = PROV.load(game)
    current = {f for u in p.unique.values() for f in u["files"]
               if PROV.is_current(prov, f, OC.VERSIONS.get(u["type"]))}
    print(f"\nOn disk: {len(p.all_files & p.present)}/{len(p.all_files)}   "
          f"current version (provenance): {len(current)}/{len(p.all_files)}")
    print(f"To export{' (incl --changed ' + ','.join(sorted(changed)) + ')' if changed else ''}: "
          f"{n_export_ops} export op(s)")
    print(f"ESTIMATED API CALLS: ~{est_calls} "
          f"(@ ~{CALLS_PER_EXPORT}/export; toppers = 1 op → 6 files)")
    print("  Onshape element mapping not wired yet (Stage 2) — this is a plan.")

    # ---- manifest ----
    manifest = {
        "game": game, "folder": spec["folder"],
        "cascades": [
            {"name": c["name"], "short_name": c["ctx"]["short_name"],
             "model": c["model"], "sleeved": c["sleeved"],
             "status": c["status"],
             "file": C.cascade_filename(game, c["ctx"]["short_name"],
                                        c["sleeved"], c["model"]),
             "parts": [{"object": it["object"], "file": it["file"],
                        "count": it["count"],
                        **({"instance": it["instance"]}
                           if it.get("instance") else {})}
                       for it in c["components"]]}
            for c in p.cascades],
        "exports": [
            {"type": u["type"], "files": sorted(u["files"]),
             "used_by": len(u["cascades"]),
             "status": "export" if k in p.to_export else "cached"}
            for k, u in p.unique.items()],
        "skipped": [{"name": n, "missing": m} for n, m in p.skipped],
        "parked": p.parked,
    }
    Path(args.out).write_text(json.dumps(manifest, indent=2))
    print(f"\nwrote {args.out}")


if __name__ == "__main__":
    main()
