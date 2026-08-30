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
import topper_split as TS
import verify as V

# One combined 3MF (grouping=true) with all parts as named objects, Z-up, mm.
MESH_BODY = {"formatName": "3MF", "storeInDocument": False, "notifyUser": False,
             "resolution": "medium", "units": "millimeter", "grouping": True,
             "yAxisIsUp": False, "flattenAssemblies": False,
             "excludeHiddenEntities": True, "includeExportIds": False}


def comp_config(comp):
    """Onshape configuration recorded in provenance for a component.

    Empty for everything now. Toppers were the only configured component — one
    studio export per Expansion value — and they come from TOPPER_ASSEMBLY under
    the Primary variable set instead, with no configuration of their own; which
    expansion a file holds is carried by its `key`. Rows written before the move
    keep their `Expansion=...`, which is what they really were exported with."""
    return ""


def api_config(comp):
    """Onshape configuration string to send with a studio export. Nothing sets
    one today (see comp_config); kept as the hook for a configured component,
    since a single list input encodes simply as 'parameterId=value'."""
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
        OC.expected_version(comp["type"], comp["file"]) or "", mv, when, sha))


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


def cached_studio(folder, comp):
    """The cached raw studio export for one component, or None. export_studio
    caches under the component's OWN filename, so this also picks up a studio
    export downloaded by hand into _raw/ under that name."""
    p = P.ROOT / "individual" / folder / "_raw" / comp["file"]
    return p if p.exists() else None


def export_studio(auth, comp, folder, game, when, verify=True, use_cache=False,
                  ctx=None):
    """One part-studio component (Lid, Topper, Label): translate -> strip imports
    -> file + provenance. With use_cache, re-strip the cached raw studio export
    (0 API calls) instead of translating when one is on disk — the studio
    counterpart of export_assembly's cache path.

    A Lid is checked against its cascade's parts.csv W/D before it is written
    (verify.check_lid), the studio counterpart of export_assembly's check_box —
    tighter, because those columns describe the closed cascade and so are the
    lid's own size."""
    typ = comp["type"]
    cached = cached_studio(folder, comp) if use_cache else None
    if cached:
        print(f"    ↻ re-strip from cache: {cached.name}  (0 calls)")
        # A cached raw is never re-cached, and never deleted: it may be a file
        # staged there by hand, which is not ours to remove.
        data, mv, raw = cached.read_bytes(), "", None
    else:
        body = dict(MESH_BODY)
        cfg = api_config(comp)
        if cfg:
            body["configuration"] = cfg
        data, mv = O.translate(
            auth, "partstudio", OC.DID,
            f"/api/partstudios/d/{OC.DID}/w/{OC.WID}/e/{OC.ELEMENTS[typ]}/translations",
            body, reason=typ.lower())
        raw = cache_raw(folder, comp["file"][:-4], mesh.unwrap(data))
    clean, dropped = mesh.strip_objects(data, {t for t in OC.ELEMENTS if t != typ})
    fatal = (V.check_lid(clean, ctx)[0]
             if verify and typ == "Lid" and ctx else None)
    if fatal:
        wait = O.bump_settle() if raw else 0
        sys.exit(
            f"\n✗ REFUSING {comp['file']}: {fatal}.\n"
            f"  Either Onshape served a translation cached from the PREVIOUS "
            f"parameter set, or that parts.csv row's W/D are an estimate "
            f"rather than a measurement. Nothing was written to individual/"
            f"{folder}/.\n"
            + (f"  The settle wait is now {wait}s — re-run.\n" if raw else "")
            + f"  The download is kept in _raw/, so correcting the row and "
              f"re-running with --use-cache costs 0 calls. Use --skip-verify "
              f"if the row is the thing you want to keep.")
    n = _write(clean, comp, folder, game, OC.ELEMENTS[typ], mv, when, verify)
    # The raw studio download is cached BEFORE the write, so a refused export
    # (the identity guard exits) never costs its bytes. Past that point it only
    # earns its keep if stripping removed parts the component doesn't carry —
    # e.g. the Topper studio's imported Holder. Every Lid studio strips nothing,
    # so its raw IS the component: drop it rather than store the same 3MF twice.
    if raw and not dropped:
        raw.unlink()
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


def topper_tag(ctx):
    """Cache name for a (size, cards, sleeving) parameter set's raw topper
    assembly. Unlike the monochrome assembly this is NOT per model code — the
    toppers of every cascade sharing those three are the same six parts."""
    return f"Toppers {ctx['size']}{ctx['cards_per_slot']}-{ctx['sleeved']}"


def cached_toppers(folder, ctx):
    """The cached raw topper assembly for a parameter set, or None."""
    p = P.ROOT / "individual" / folder / "_raw" / f"{topper_tag(ctx)}.3mf"
    return p if p.exists() else None


def export_toppers(auth, ctx, use_cache=False, verify=True):
    """ONE assembly translation -> {expansion: clean 3mf bytes} for all six
    toppers (split locally), plus the shared documentMicroversion.

    topper_split identifies each instance from its lettering and refuses on
    anything it cannot pin down, so its SplitError is the topper counterpart of
    check_box: a translation cached from the PREVIOUS parameter set is caught
    before anything reaches individual/ or provenance. The raw download is kept
    either way — under a REJECTED prefix when refused, so --use-cache cannot
    later re-split a download we already know is wrong."""
    cached = cached_toppers(ctx["folder"], ctx) if use_cache else None
    if cached:
        print(f"    ↻ re-split from cache: {cached.name}  (0 calls)")
        raw, mv, fresh = mesh.unwrap(cached.read_bytes()), "", False
    else:
        data, mv = O.translate(
            auth, "assembly", OC.DID,
            f"/api/assemblies/d/{OC.DID}/w/{OC.WID}/e/{OC.TOPPER_ASSEMBLY}"
            f"/translations",
            dict(MESH_BODY), reason="toppers")
        raw, fresh = mesh.unwrap(data), True
    try:
        parts, info = TS.split(
            raw,
            sleeved=ctx["sleeved"] if verify else None,
            cards=ctx["cards_per_slot"] if verify else None)
    except TS.SplitError as e:
        bad = cache_raw(ctx["folder"], f"REJECTED {topper_tag(ctx)}", raw)
        wait = O.bump_settle() if fresh else 0
        sys.exit(
            f"\n✗ REFUSING the {topper_tag(ctx)} assembly: {e}\n"
            f"  Nothing was written to individual/{ctx['folder']}/.\n"
            f"  The download is kept at {bad.name} for inspection (the "
            f"'REJECTED ' prefix keeps --use-cache away from it)."
            + (f"\n  The settle wait is now {wait}s — re-run." if fresh else
               "\n  Delete it and re-export without --use-cache.")
            + "\n  Use --skip-verify to take the split without the dimension "
              "checks.")
    for w in info["warnings"]:
        print(f"    ⚠ {w}")
    if fresh:
        cache_raw(ctx["folder"], topper_tag(ctx), raw)
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
        topper = [c for c in needed if c["type"] in OC.TOPPER_SOURCED]
        studio = [c for c in needed if c["type"] in OC.STUDIO_SOURCED]
        asm_cached = bool(use_cache and asm and cached_assembly(
            folder, casc["ctx"]))
        top_cached = bool(use_cache and topper and cached_toppers(
            folder, casc["ctx"]))
        studio_live = [c for c in studio
                       if not (use_cache and cached_studio(folder, c))]
        # Setting the Primary variables is itself an API call; skip it when
        # every needed part comes from the local cache.
        if (asm and not asm_cached) or (topper and not top_cached) or studio_live:
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
        # ONE assembly export supplies all six of this cascade's toppers
        if topper and not (limit and done >= limit):
            parts, mv = export_toppers(auth, casc["ctx"], use_cache=use_cache,
                                       verify=verify)
            for comp in topper:
                if limit and done >= limit:
                    break
                exp = comp["key"][1]
                data = parts.get(exp)
                if data is None:
                    print(f"    ⚠ {comp['file']} — expansion {exp!r} absent "
                          f"from the topper assembly")
                    continue
                n = _write(data, comp, folder, game, OC.TOPPER_ASSEMBLY, mv,
                           when, verify)
                print(f"    ✓ {comp['file']}  ({n} bodies, topper assembly)")
                done += 1
        # Lid / labels stay on the per-part-studio path
        for comp in studio:
            if limit and done >= limit:
                break
            if comp["type"] not in OC.ELEMENTS:
                print(f"    ⚠ skip {comp['file']} — no element id"); continue
            n, dropped = export_studio(auth, comp, folder, game, when, verify,
                                       use_cache=use_cache, ctx=casc["ctx"])
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
                    help="record present on-disk files as current, then exit — "
                         "including any whose bytes changed under us, so "
                         "overwriting a component in place is enough to update "
                         "it (0 API calls). SCOPE IT with --types: adopting a "
                         "whole game blesses every version-stale component, "
                         "including ones whose geometry really is out of date")
    ap.add_argument("--types", default="",
                    help="restrict --adopt to these component types "
                         "(e.g. 'Lid'); default is every type. --name and "
                         "--sleeving narrow it further, to the components of "
                         "one cascade")
    ap.add_argument("--execute", action="store_true",
                    help="actually export (default is a 0-call dry run)")
    ap.add_argument("--sleeving", choices=["un", "sl"],
                    help="restrict to unsleeved or sleeved cascades")
    ap.add_argument("--name", help="restrict to one cascade (Short name, "
                                   "e.g. '300 Card')")
    ap.add_argument("--limit", type=int, default=0,
                    help="export at most N components")
    ap.add_argument("--use-cache", action="store_true",
                    help="reuse cached raw downloads (individual/<game>/_raw/) "
                         "instead of re-fetching — re-split an assembly, "
                         "re-strip a studio export; 0 API calls for those")
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

    def selected(cascades):
        """Apply --sleeving / --name to a cascade list. Shared by --adopt and the
        export path so a filter means the same thing on both."""
        if args.sleeving:
            cascades = [c for c in cascades
                        if c["sleeved"] == args.sleeving.capitalize()]
        if args.name:
            cascades = [c for c in cascades
                        if c["ctx"]["short_name"] == args.name]
        return cascades

    if args.adopt:
        when = datetime.datetime.now().isoformat(timespec="seconds")
        types = {t.strip() for t in args.types.split(",") if t.strip()}
        seen, adopted = set(), []
        for casc in selected(plan.cascades):
            for comp in casc["components"]:
                f = comp["file"]
                if f in seen or f not in plan.present:
                    continue
                if types and comp["type"] not in types:
                    continue
                seen.add(f)
                sha = on_disk_sha(f)
                row = prov.get(f)
                want = OC.expected_version(comp["type"], f)
                # Adopt a file whose recorded version is stale OR whose bytes
                # have changed under us: overwriting a component in place (a
                # part re-downloaded from Onshape by hand) is a supported way to
                # update one, and the sha is what makes the record — and the
                # identity guard that reads it — true.
                if not row:
                    why = "new"
                elif not PROV.is_current(prov, f, want):
                    why = f"version {row.get('version') or '?'} → {want}"
                elif row.get("sha") != sha:
                    why = f"changed on disk ({row.get('sha') or '?'} → {sha})"
                else:
                    continue
                prov[f] = PROV.make_row(
                    f, comp["type"], comp["key"],
                    OC.source_element(comp["type"]), comp_config(comp),
                    want or "", "", when, sha)
                adopted.append((f, why))
        PROV.save(game, prov)
        for f, why in sorted(adopted):
            print(f"    ✓ {f}  [{why}]")
        print(f"Adopted {len(adopted)} on-disk file(s) into provenance → "
              f"automation/state/{game}.csv")
        return

    to_export_keys = set(plan.unique) if args.all else set(plan.to_export)
    batches, skipped = batch(selected(plan.cascades), to_export_keys)

    def classify(keys):
        """(assembly, topper-assembly, studio) keys for one cascade."""
        def of(group):
            return [k for k in keys if plan.unique[k]["type"] in group]
        return of(OC.ASSEMBLY_SOURCED), of(OC.TOPPER_SOURCED), \
            of(OC.STUDIO_SOURCED)

    # translate operations per cascade: ONE assembly export covers all its
    # monochrome parts, a second covers all six toppers, and each lid/label is
    # its own studio export.
    def translate_ops(keys):
        asm, topper, studio = classify(keys)
        return (1 if asm else 0) + (1 if topper else 0) + len(studio)

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
        asm, topper, studio = classify(keys)
        print(f"● SET PARAMETERS  [{casc['name']}]   (~{1 + translate_ops(keys) * PER} calls)")
        print(f"      {param_summary(casc['ctx'])}")
        if asm:
            files = sorted(sorted(plan.unique[k]["files"])[0] for k in asm)
            nnew = sum(1 for f in files if f not in plan.present)
            st = "new" if nnew == len(files) else f"{nnew} new, {len(files) - nnew} stale"
            print(f"      ├─ 1 ASSEMBLY export → {len(asm)} monochrome part(s) "
                  f"[{st}]: {', '.join(files)}")
        for k in studio:
            u = plan.unique[k]
            f = sorted(u["files"])[0]
            state = "new" if f not in plan.present else "stale"
            tag = "" if u["type"] in OC.ELEMENTS else "  ⚠ no element id"
            print(f"      ├─ studio export {f}   [{u['type']} · {state}]{tag}")
        if topper:
            exps = [k[1] for k in topper]
            files = [sorted(plan.unique[k]["files"])[0] for k in topper]
            nnew = sum(1 for f in files if f not in plan.present)
            st = ("new" if nnew == len(files)
                  else f"{nnew} new, {len(files) - nnew} stale")
            print(f"      └─ 1 TOPPER ASSEMBLY export → {len(exps)} topper(s) "
                  f"[{st}]: {', '.join(exps)}")
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
          f"(1 assembly export replaces all of a cascade's monochrome parts, "
          f"1 more replaces all six toppers)")
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
