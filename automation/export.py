#!/usr/bin/env python3
"""Stage 2 export planner: decide WHEN to set parameters and WHAT to request,
minimising Onshape API calls.

Each cascade is one full Primary parameter set (one POST). Setting parameters is
the expensive gate, so we set them once per cascade that still contributes a
not-yet-exported component, and request only those new components under it;
cascades whose components are all already exported are skipped entirely (no
parameter-set call at all).

Dry run only (for now): prints the plan as an outline — each SET PARAMETERS step
with its parameter summary, then indented, the parts requested from it. Makes 0
API calls.

Usage:
    export.py <Game> [--all] [--changed Box,Holder] [--labels]
      --all      ignore the individual/ cache; plan a full rebuild
      --changed  force re-export of these component types
"""
import argparse
import sys

import components as C
import onshape_config as OC
import plan_exports as P


def param_summary(ctx):
    """The Primary variables this step would set (compact)."""
    s = [f"GameName={ctx['game']}",
         f"HorizontalSlots={ctx['horizontal']}",
         f"RisingSliders={ctx['risers']}",
         f"CardsPerSlidingSlot={ctx['cards_per_slot']}",
         f"FrontPocket={ctx['front_capacity']}",
         f"isSleeved={1 if ctx['sleeved'] == 'Sl' else 0}",
         f"MatPocket={1 if ctx['merged'] else 0}"]
    if ctx["first_riser"]:
        s.append(f"FirstSlidingSlot={ctx['first_riser']}")
    return "  ".join(s)


def batch(plan, to_export_keys):
    """Greedy assignment: each cascade contributes the components that still
    need export and haven't been claimed by an earlier parameter set. Returns
    (batches, skipped) where batches = [(cascade, [unique keys]), ...]."""
    assigned, batches, skipped = set(), [], []
    for casc in plan.cascades:
        keys, seen = [], set()
        for comp in casc["components"]:
            k = comp["key"]
            if k in seen:
                continue
            seen.add(k)
            if k in assigned or k not in to_export_keys:
                continue
            keys.append(k)
        if keys:
            batches.append((casc, keys))
            assigned |= set(keys)
        else:
            skipped.append(casc)
    return batches, skipped


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("game")
    ap.add_argument("--all", action="store_true",
                    help="ignore the individual/ cache (plan a full rebuild)")
    ap.add_argument("--changed", default="")
    ap.add_argument("--labels", action="store_true")
    args = ap.parse_args()

    game, spec = C.game_by_name(args.game)
    if not spec:
        sys.exit(f"unknown game {args.game!r}; known: {list(C.GAMES)}")
    changed = {c.strip() for c in args.changed.split(",") if c.strip()}
    plan = P.compute_plan(game, spec, str(P.HERE / "parts.csv"),
                          args.labels, changed)
    to_export_keys = set(plan.unique) if args.all else set(plan.to_export)

    batches, skipped = batch(plan, to_export_keys)
    n_set = len(batches)
    n_parts = sum(len(keys) for _, keys in batches)

    cache = ("IGNORING cache (--all)" if args.all
             else f"{len(plan.all_files & plan.present)}/{len(plan.all_files)} "
                  "components already cached")
    print(f"EXPORT PLAN — {game}   (dry run, 0 API calls; {cache})\n")

    for casc, keys in batches:
        print(f"● SET PARAMETERS  [{casc['name']}]   (1 call)")
        print(f"      {param_summary(casc['ctx'])}")
        for i, k in enumerate(keys):
            u = plan.unique[k]
            branch = "└─" if i == len(keys) - 1 else "├─"
            tag = "" if u["type"] in OC.ELEMENTS else "   ⚠ no element id yet"
            if u["type"] == "Topper":
                print(f"      {branch} request Toppers → {len(u['files'])} files "
                      f"(Topper studio, config per expansion){tag}")
            else:
                print(f"      {branch} request {sorted(u['files'])[0]}"
                      f"   [{u['type']} studio]{tag}")
        print()

    if skipped:
        print(f"Skipped {len(skipped)} cascade(s) — every component already "
              f"exported, so NO parameter-set call:")
        for casc in skipped:
            print(f"  · {casc['name']}")
        print()

    per = P.CALLS_PER_EXPORT
    unknown = sorted({plan.unique[k]["type"] for _, keys in batches for k in keys
                      if plan.unique[k]["type"] not in OC.ELEMENTS})
    print(f"SET-PARAMETER calls: {n_set}   (one per cascade with new parts)")
    print(f"Part requests:       {n_parts}   (each its own part studio → its "
          f"own export)")
    print(f"Estimated API calls: {n_set} set + {n_parts}×~{per} export "
          f"= ~{n_set + n_parts * per}")
    if unknown:
        print(f"  ⚠ no element id yet for {unknown} — those can't export until "
              "mapped in onshape_config.py")
    print(f"\nYear-to-date {_ytd()}/2500.")
    print("Notes: components are SEPARATE part studios (onshape_config.py), so "
          "one export each. Toppers use a Configuration per expansion — a Topper "
          "request may be 1 whole-studio export or one per expansion (TBD). "
          "Assemblies with all components exist and could later cut exports.")
    print("Execution not wired yet.")


def _ytd():
    try:
        import onshape as O
        return O.read_cumulative()
    except Exception:
        return "?"


if __name__ == "__main__":
    main()
