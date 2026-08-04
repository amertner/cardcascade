#!/usr/bin/env python3
"""Stage 1 planner for the Card Cascade Onshape export pipeline (see
docs/PIPELINE.md). Reads parts.csv + components.py, expands a game's rows into
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
from pathlib import Path

import components as C

HERE = Path(__file__).parent
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
        "pushers": C.PUSHERS_BY_SIZE.get(size, 3),
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
    if "Toppers" in spec["extras"]:
        # One whole-studio export per sleeving -> all topper files share a key.
        for exp in spec["toppers"]:
            items.append({"type": "Topper", "key": ("Toppers", slv),
                          "file": f"Topper {exp} {slv}.3mf",
                          "object": f"Topper {exp}", "count": 1})
    if labels and spec.get("onshape_label"):
        items.append({"type": "Label", "key": ("Label", m),
                      "file": f"Label {m}.3mf", "object": "Label", "count": 1})
    return items


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

    with open(args.csv, newline="") as f:
        rows = [r for r in csv.DictReader(f) if col(r, "Game") == game]
    if not rows:
        sys.exit(f"no rows for game {game!r} in {args.csv}")

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
            items = compose(ctx, spec, args.labels)
            name = f"{ctx['short_name']} {sleeved} ({ctx['model']})"
            cascades.append({"name": name, "model": ctx["model"],
                             "sleeved": sleeved, "status": col(row, "Status"),
                             "components": items})
            for it in items:
                u = unique.setdefault(it["key"], {
                    "type": it["type"], "files": set(), "objects": set(),
                    "cascades": []})
                u["files"].add(it["file"])
                u["objects"].add(it["object"])
                u["cascades"].append(name)

    # Diff against what's already exported (by the planner's naming scheme).
    outdir = HERE / "individual" / spec["folder"]
    present = {p.name for p in outdir.glob("*.3mf")} if outdir.exists() else set()
    all_planned_files = {f for u in unique.values() for f in u["files"]}

    def needs_export(u):
        if u["type"] in changed:
            return True
        return not u["files"].issubset(present)

    to_export = {k: u for k, u in unique.items() if needs_export(u)}

    total_slots = sum(it["count"] for c in cascades for it in c["components"])
    n_export_ops = len(to_export)                 # toppers = 1 op (shared key)
    est_calls = n_export_ops * CALLS_PER_EXPORT

    # ---- report ----
    print(f"Game: {game}  (individual/{spec['folder']}/)")
    print(f"Rows: {len(rows)}   cascades planned: {len(cascades)}"
          f"   (skipped incomplete: {len(skipped)}, parked: {len(parked)})")
    for name in parked:
        print(f"  skipped (parked): {name}")
    for name, miss in skipped:
        print(f"  skipped (incomplete): {name} — missing {', '.join(miss)}")
    print(f"\nComponent instances across all cascades: {total_slots}")
    print(f"Unique components (deduped): {len(unique)}"
          f"   → dedup ratio {total_slots}:{len(unique)}")
    by_type = {}
    for u in unique.values():
        by_type.setdefault(u["type"], 0)
        by_type[u["type"]] += 1
    print("  by type:", ", ".join(f"{t}×{n}" for t, n in sorted(by_type.items())))
    print(f"\nAlready present (this naming scheme): "
          f"{len(all_planned_files & present)}/{len(all_planned_files)} files")
    print(f"To export{' (incl --changed ' + ','.join(sorted(changed)) + ')' if changed else ''}: "
          f"{n_export_ops} export op(s)")
    print(f"ESTIMATED API CALLS: ~{est_calls} "
          f"(@ ~{CALLS_PER_EXPORT}/export; toppers = 1 op → 6 files)")
    print("  Onshape element mapping not wired yet (Stage 2) — this is a plan.")

    # ---- manifest ----
    manifest = {
        "game": game, "folder": spec["folder"],
        "cascades": [
            {"name": c["name"], "model": c["model"], "sleeved": c["sleeved"],
             "status": c["status"],
             "parts": [{"object": it["object"], "file": it["file"],
                        "count": it["count"],
                        **({"instance": it["instance"]}
                           if it.get("instance") else {})}
                       for it in c["components"]]}
            for c in cascades],
        "exports": [
            {"type": u["type"], "files": sorted(u["files"]),
             "used_by": len(u["cascades"]),
             "status": "export" if k in to_export else "cached"}
            for k, u in unique.items()],
        "skipped": [{"name": n, "missing": m} for n, m in skipped],
        "parked": parked,
    }
    Path(args.out).write_text(json.dumps(manifest, indent=2))
    print(f"\nwrote {args.out}")


if __name__ == "__main__":
    main()
