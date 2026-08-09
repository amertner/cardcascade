#!/usr/bin/env python3
"""Stage 2 exporter/planner: decide WHEN to set parameters and WHAT to request,
minimising Onshape API calls, and (with --execute) actually export.

Each cascade is one full Primary parameter set (one POST). Setting parameters is
the expensive gate, so we set it once per cascade that still contributes a
not-yet-exported component, and request only those new components under it;
cascades whose components are all already exported are skipped.

Default is a dry run (0 API calls) that prints the plan as an outline. --execute
performs it: per batch → set Primary → export each component's whole part studio
as one combined 3MF → strip imported parts → validate → write file + provenance.

Every export is verified before it is written (verify.py, 0 API calls): the box
must match the cascade's parts.csv footprint and must not be byte-identical to
another component. Both guard the same failure — Onshape serving a translation
cached from the PREVIOUS parameter set, which otherwise lands silently under the
right filename. run_export also waits after setting variables for the same
reason; see onshape.settle.

Usage:
    export.py <Game> [--all] [--changed Box,Holder] [--labels]     # plan only
    export.py <Game> --execute [--sleeving un|sl] [--limit N]      # do it
      --all           ignore provenance (plan a full rebuild)
      --changed       force re-export of these component types
      --sleeving      restrict to unsleeved (un) or sleeved (sl) cascades
      --limit N       export at most N components (spend incrementally)
      --adopt         record present on-disk files as current, then exit
      --skip-verify   accept an export that fails the checks above
      --rehash        backfill provenance hashes from disk, then exit
"""
import argparse
import datetime
import sys

import assembly_split as ASM
import components as C
import make_cascade as MC
import mesh
import onshape as O
import onshape_config as OC
import plan_exports as P
import provenance as PROV
import set_variables as SV
import verify as V

# One combined 3MF (grouping=true) with all parts as named objects, Z-up, mm.
MESH_BODY = {"formatName": "3MF", "storeInDocument": False, "notifyUser": False,
             "resolution": "medium", "units": "millimeter", "grouping": True,
             "yAxisIsUp": False, "flattenAssemblies": False,
             "excludeHiddenEntities": True, "includeExportIds": False}


def comp_config(comp):
    """Human-readable config for provenance (toppers select an expansion)."""
    return f"Expansion={comp['key'][1]}" if comp["type"] == "Topper" else ""


def api_config(comp):
    """Onshape configuration string for the export. A single list input encodes
    as 'parameterId=value', so we build it locally (no configurationencodings)."""
    if comp["type"] == "Topper":
        return f"{OC.TOPPER_CONFIG_PARAM}={comp['key'][1]}"
    return ""


def param_summary(ctx):
    s = [f"GameName={ctx['folder']}", f"HorizontalSlots={ctx['horizontal']}",
         f"RisingSliders={ctx['risers']}",
         f"CardsPerSlidingSlot={ctx['cards_per_slot']}",
         f"FrontPocket={ctx['front_capacity']}",
         f"isSleeved={1 if ctx['sleeved'] == 'Sl' else 0}",
         f"MatPocket={1 if ctx['merged'] else 0}"]
    if ctx["first_riser"]:
        s.append(f"FirstSlidingSlot={ctx['first_riser']}")
    return "  ".join(s)


def batch(cascades, to_export_keys):
    """Greedy: each cascade contributes the components still needing export that
    an earlier parameter set hasn't already claimed. Returns (batches, skipped)."""
    assigned, batches, skipped = set(), [], []
    for casc in cascades:
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


# ----------------------------------------------------------------- execution
def set_primary(auth, row, sleeved, game_name):
    O.api(auth, "POST",
          f"/api/variables/d/{OC.DID}/w/{OC.WID}/e/{OC.PRIMARY}/variables",
          "set-primary", json=SV.build_primary(row, sleeved, game_name))


def _record(comp, game, element, mv, when, sha):
    PROV.record(game, PROV.make_row(
        comp["file"], comp["type"], comp["key"], element, comp_config(comp),
        OC.VERSIONS.get(comp["type"], ""), mv, when, sha))


def _write(data, comp, folder, game, element, mv, when, verify=True):
    """Write export bytes to the component's file, validate, record provenance.

    The identity guard runs BEFORE the write: a stale export must never reach
    disk or provenance, because a provenance row marks it current and the next
    run would happily skip re-exporting it."""
    sha = V.mesh_sha(data)
    dup = V.duplicate(sha, comp["file"], PROV.all_rows()) if verify else None
    if dup:
        wait = O.bump_settle()
        sys.exit(
            f"\n✗ REFUSING {comp['file']}: its geometry is identical to "
            f"{dup}, an already-exported DIFFERENT component.\n"
            f"  Onshape served a cached translation from the previous "
            f"parameter set. Nothing was written.\n"
            f"  The settle wait is now {wait}s — re-run. Use --skip-verify if "
            f"the two components really are identical.")
    out = P.ROOT / "individual" / folder / comp["file"]
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(data)
    bodies = MC.load_export(str(out))            # validate it parses cleanly
    _record(comp, game, element, mv, when, sha)
    return len(bodies)


def cache_raw(folder, name, data):
    """Save a raw translation 3MF under individual/<folder>/_raw/ so a part that
    was dropped or re-keyed can be recovered by re-splitting locally, never by
    re-fetching. Every Onshape download is expensive; none should be thrown away.
    Returns the cache path."""
    d = P.ROOT / "individual" / folder / "_raw"
    d.mkdir(parents=True, exist_ok=True)
    out = d / f"{name}.3mf"
    out.write_bytes(data)
    return out


def assembly_tag(ctx):
    """Cache name for a (model, merged) parameter set's raw assembly export.
    Model codes can carry '/' (S2.40.12/30) — a path separator; fold it."""
    return (f"Assembly {ctx['model'].replace('/', '-')}"
            f"{' merged' if ctx['merged'] else ''}")


def cached_assembly(folder, ctx):
    """The cached raw assembly for a (model, merged) parameter set, or None."""
    p = P.ROOT / "individual" / folder / "_raw" / f"{assembly_tag(ctx)}.3mf"
    return p if p.exists() else None


def export_studio(auth, comp, folder, game, when, verify=True):
    """One part-studio component (Lid, Topper, Label): translate -> strip imports
    -> file + provenance."""
    typ = comp["type"]
    body = dict(MESH_BODY)
    cfg = api_config(comp)
    if cfg:
        body["configuration"] = cfg
    data, mv = O.translate(
        auth, "partstudio", OC.DID,
        f"/api/partstudios/d/{OC.DID}/w/{OC.WID}/e/{OC.ELEMENTS[typ]}/translations",
        body, reason=typ.lower())
    cache_raw(folder, comp["file"][:-4], mesh.unwrap(data))   # keep the raw studio
    clean, dropped = mesh.strip_objects(data, {t for t in OC.ELEMENTS if t != typ})
    n = _write(clean, comp, folder, game, OC.ELEMENTS[typ], mv, when, verify)
    return n, dropped


def assembly_role(comp):
    """Which split role a cascade component maps to inside the assembly export."""
    if comp["type"] == "Holder" and comp.get("instance") == "first":
        return "Holder_first"
    return comp["type"]


def export_assembly(auth, ctx, use_cache=False, verify=True):
    """One assembly translation -> {role: clean 3mf bytes} (split locally),
    plus the shared documentMicroversion. With use_cache, re-split the cached raw
    assembly (0 API calls) instead of translating when one is on disk."""
    cached = cached_assembly(ctx["folder"], ctx) if use_cache else None
    if cached:
        print(f"    ↻ re-split from cache: {cached.name}  (0 calls)")
        raw, mv, fresh = mesh.unwrap(cached.read_bytes()), "", False
    else:
        data, mv = O.translate(
            auth, "assembly", OC.DID,
            f"/api/assemblies/d/{OC.DID}/w/{OC.WID}/e/{OC.ASSEMBLY}/translations",
            dict(MESH_BODY), reason="assembly")
        raw, fresh = mesh.unwrap(data), True
    card_mm = 0.64 if ctx["sleeved"] == "Sl" else 0.34
    parts = ASM.split(raw, cards_first=ctx.get("first_riser"),
                      cards_slot=ctx["cards_per_slot"], card_mm=card_mm)
    # Is this actually THIS cascade's assembly? Check before caching the raw
    # bytes, so a stale download can never be re-split by --use-cache later.
    fatal, warn = (V.check_box(parts["Box"], ctx)
                   if verify and "Box" in parts else (None, None))
    if warn:
        print(f"    ⚠ {warn}")
    if fatal:
        bad = cache_raw(ctx["folder"], f"REJECTED {assembly_tag(ctx)}", raw)
        wait = O.bump_settle() if fresh else 0
        sys.exit(
            f"\n✗ REFUSING the {ctx['model']} assembly: {fatal}\n"
            f"  This is what a cached translation from the PREVIOUS parameter "
            f"set looks like. Nothing was written to individual/"
            f"{ctx['folder']}/.\n  The download is kept at {bad.name} for "
            f"inspection (the 'REJECTED ' prefix keeps --use-cache away from "
            f"it)." + (f"\n  The settle wait is now {wait}s — re-run."
                       if fresh else "\n  Delete it and re-export without "
                                     "--use-cache.")
            + "\n  If parts.csv is the thing that's wrong, re-run with "
              "--skip-verify.")
    if fresh:
        cache_raw(ctx["folder"], assembly_tag(ctx), raw)
    return parts, mv


def run_export(game, spec, plan, batches, limit, use_cache=False, verify=True):
    O.begin()
    auth = O.LazyAuth()      # resolved only if a call is actually made
    when = datetime.datetime.now().isoformat(timespec="seconds")
    folder = spec["folder"]
    done = 0
    for casc, keys in batches:
        if limit and done >= limit:
            break
        bykey = {}
        for c in casc["components"]:
            bykey.setdefault(c["key"], c)
        needed = [bykey[k] for k in keys if k in bykey]
        asm = [c for c in needed if c["type"] in OC.ASSEMBLY_SOURCED]
        studio = [c for c in needed if c["type"] in OC.STUDIO_SOURCED]
        asm_cached = bool(use_cache and asm and cached_assembly(
            folder, casc["ctx"]))
        # Setting the Primary variables is itself an API call; skip it when
        # every needed part comes from the local cache.
        if (asm and not asm_cached) or studio:
            set_primary(auth, casc["row"], casc["sleeved"] == "Sl",
                        spec.get("onshape_name", spec["folder"]))
            print(f"● SET PARAMETERS  [{casc['name']}]")
            O.settle()      # let the change reach the model before translating
        else:
            print(f"● FROM CACHE  [{casc['name']}]")
        # ONE assembly export supplies every monochrome component of this cascade
        if asm and not (limit and done >= limit):
            parts, mv = export_assembly(auth, casc["ctx"], use_cache=use_cache,
                                        verify=verify)
            for comp in asm:
                if limit and done >= limit:
                    break
                role = assembly_role(comp)
                data = parts.get(role)
                if data is None:
                    print(f"    ⚠ {comp['file']} — role {role!r} absent from assembly")
                    continue
                n = _write(data, comp, folder, game, OC.ASSEMBLY, mv, when,
                           verify)
                print(f"    ✓ {comp['file']}  ({n} body, assembly)")
                done += 1
        # Lid / toppers / labels stay on the per-part-studio path
        for comp in studio:
            if limit and done >= limit:
                break
            if comp["type"] not in OC.ELEMENTS:
                print(f"    ⚠ skip {comp['file']} — no element id"); continue
            n, dropped = export_studio(auth, comp, folder, game, when, verify)
            extra = f", stripped {dropped}" if dropped else ""
            print(f"    ✓ {comp['file']}  ({n} bodies, studio{extra})")
            done += 1
    print(f"\nexported {done} component(s).\n{O.budget_line()}")


# ---------------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("game")
    ap.add_argument("--all", action="store_true",
                    help="ignore provenance (plan a full rebuild)")
    ap.add_argument("--changed", default="")
    ap.add_argument("--labels", action="store_true")
    ap.add_argument("--adopt", action="store_true",
                    help="record present on-disk files as current, then exit")
    ap.add_argument("--execute", action="store_true",
                    help="actually export (default is a 0-call dry run)")
    ap.add_argument("--sleeving", choices=["un", "sl"],
                    help="restrict to unsleeved or sleeved cascades")
    ap.add_argument("--name", help="restrict to one cascade (Short name, "
                                   "e.g. '360 Card')")
    ap.add_argument("--limit", type=int, default=0,
                    help="export at most N components")
    ap.add_argument("--use-cache", action="store_true",
                    help="re-split cached raw assemblies (individual/<game>/_raw/) "
                         "instead of re-fetching — 0 API calls for those cascades")
    ap.add_argument("--skip-verify", action="store_true",
                    help="don't check the exported box against parts.csv W/D or "
                         "reject geometry identical to another component "
                         "(use when parts.csv is the row that's wrong)")
    ap.add_argument("--rehash", action="store_true",
                    help="fill in the provenance `sha` of on-disk components, "
                         "then exit (0 API calls) — arms the identity guard "
                         "against components exported before it existed")
    args = ap.parse_args()

    game, spec = C.game_by_name(args.game)
    if not spec:
        sys.exit(f"unknown game {args.game!r}; known: {list(C.GAMES)}")
    changed = {c.strip() for c in args.changed.split(",") if c.strip()}
    plan = P.compute_plan(game, spec, str(P.HERE / "parts.csv"),
                          args.labels, changed)
    prov = PROV.load(game)

    def on_disk_sha(f):
        """Mesh hash of a component already in individual/<folder>/, or ''."""
        p = P.ROOT / "individual" / spec["folder"] / f
        return V.mesh_sha(p.read_bytes()) if p.exists() else ""

    if args.rehash:
        n = 0
        for f, row in prov.items():
            if not row.get("sha"):
                row["sha"] = on_disk_sha(f)
                n += bool(row["sha"])
        PROV.save(game, prov)
        print(f"Hashed {n} on-disk component(s) → automation/state/{game}.csv")
        return

    if args.adopt:
        when = datetime.datetime.now().isoformat(timespec="seconds")
        seen, n = set(), 0
        for casc in plan.cascades:
            for comp in casc["components"]:
                f = comp["file"]
                if f in seen:
                    continue
                seen.add(f)
                if f in plan.present and not PROV.is_current(
                        prov, f, OC.VERSIONS.get(comp["type"])):
                    prov[f] = PROV.make_row(
                        f, comp["type"], comp["key"],
                        OC.ELEMENTS.get(comp["type"], ""), comp_config(comp),
                        OC.VERSIONS.get(comp["type"], ""), "", when,
                        on_disk_sha(f))
                    n += 1
        PROV.save(game, prov)
        print(f"Adopted {n} on-disk file(s) into provenance → "
              f"automation/state/{game}.csv")
        return

    to_export_keys = set(plan.unique) if args.all else set(plan.to_export)
    cascades = plan.cascades
    if args.sleeving:
        cascades = [c for c in cascades if c["sleeved"] == args.sleeving.capitalize()]
    if args.name:
        cascades = [c for c in cascades if c["ctx"]["short_name"] == args.name]
    batches, skipped = batch(cascades, to_export_keys)

    def classify(keys):
        """(assembly-sourced keys, studio-sourced keys) for one cascade."""
        asm = [k for k in keys if plan.unique[k]["type"] in OC.ASSEMBLY_SOURCED]
        studio = [k for k in keys if plan.unique[k]["type"] in OC.STUDIO_SOURCED]
        return asm, studio

    # translate operations per cascade: ONE assembly export covers all its
    # monochrome parts; each lid/topper/label is its own studio export.
    def translate_ops(keys):
        asm, studio = classify(keys)
        return (1 if asm else 0) + len(studio)

    PER = 3          # per translate op with adaptive polling: translate + 1 poll + download
    sets = len(batches)
    ops = sum(translate_ops(keys) for _, keys in batches)
    est = sets + ops * PER

    if args.execute:
        scope = f" [{args.sleeving}]" if args.sleeving else ""
        lim = f", limit {args.limit}" if args.limit else ""
        print(f"EXECUTE — {game}{scope}: {sets} parameter set(s), "
              f"{ops} translate op(s) ≈ {est} calls{lim}\n")
        run_export(game, spec, plan, batches, args.limit,
                   use_cache=args.use_cache, verify=not args.skip_verify)
        return

    # ---- dry run ----
    cache = ("IGNORING cache (--all)" if args.all
             else f"{len(plan.all_files & plan.present)}/{len(plan.all_files)} "
                  "components already cached")
    scope = f", {args.sleeving} only" if args.sleeving else ""
    print(f"EXPORT PLAN — {game}   (dry run, 0 API calls; {cache}{scope})\n")
    for casc, keys in batches:
        asm, studio = classify(keys)
        ncalls = 1 + translate_ops(keys)
        print(f"● SET PARAMETERS  [{casc['name']}]   (~{1 + translate_ops(keys) * PER} calls)")
        print(f"      {param_summary(casc['ctx'])}")
        if asm:
            files = sorted(sorted(plan.unique[k]["files"])[0] for k in asm)
            nnew = sum(1 for f in files if f not in plan.present)
            st = "new" if nnew == len(files) else f"{nnew} new, {len(files) - nnew} stale"
            print(f"      ├─ 1 ASSEMBLY export → {len(asm)} monochrome part(s) "
                  f"[{st}]: {', '.join(files)}")
        toppers = [k for k in studio if plan.unique[k]["type"] == "Topper"]
        other = [k for k in studio if plan.unique[k]["type"] != "Topper"]
        for k in other:
            u = plan.unique[k]
            f = sorted(u["files"])[0]
            state = "new" if f not in plan.present else "stale"
            tag = "" if u["type"] in OC.ELEMENTS else "  ⚠ no element id"
            print(f"      ├─ studio export {f}   [{u['type']} · {state}]{tag}")
        if toppers:
            exps = [k[1] for k in toppers]
            files = [sorted(plan.unique[k]["files"])[0] for k in toppers]
            nnew = sum(1 for f in files if f not in plan.present)
            st = ("new" if nnew == len(files)
                  else f"{nnew} new, {len(files) - nnew} stale")
            print(f"      └─ {len(exps)} studio topper export(s) [{st}]: "
                  f"{', '.join(exps)}")
        print()

    if skipped:
        print(f"Skipped {len(skipped)} cascade(s) — every component already "
              f"exported, so NO parameter-set call:")
        for casc in skipped:
            print(f"  · {casc['name']}")
        print()

    unknown = sorted({plan.unique[k]["type"] for _, keys in batches for k in keys
                      if plan.unique[k]["type"] in OC.STUDIO_SOURCED
                      and plan.unique[k]["type"] not in OC.ELEMENTS})
    print(f"Parameter sets: {sets}   Translate ops: {ops}   "
          f"(1 assembly export replaces all of a cascade's monochrome parts)")
    print(f"Estimated API calls: {sets} set + {ops}×~{PER} = ~{est}")
    if unknown:
        print(f"  ⚠ no element id yet for {unknown}")
    print(f"\nYear-to-date {_ytd()}/2500.  Re-run with --execute to perform it.")


def _ytd():
    try:
        return O.read_cumulative()
    except Exception:
        return "?"


if __name__ == "__main__":
    main()
