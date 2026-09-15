#!/usr/bin/env python3
"""Every built holder against the Onshape one it replaces.

Needs `cad.build --part holder --version 7.0` first; about a minute, pooled.

`tests/test_holder.py` holds the SOURCE to ten hand-exported STEPs; this holds
the written 3MFs to the 50 in `individual/`, covering the meshing and the
placement. `individual/` is a MIXED catalogue its own provenance cannot see —
thirty cached holders stand `10.000` beyond the outer slot edge and twenty
`9.800` (spec/HOLDER.md, "`individual/` is a mixed catalogue") — so the twenty
are REPRODUCED and the thirty MOVED, differing in X and in NOTHING ELSE; the
bucket is read off the mesh, not listed here. Neither the engraved VERSION
(cache `CC 6.6`, STEPs `CC 7.0`, so it is priced at `Version="6.6"`) nor
the engraved SIZE (a deliberate divergence, spec/HOLDER.md "The size") is part
of that difference. Per file: the six bounding-box coordinates and the volume
at 6.6 to 0.05% — a MESHING tolerance, still 5x clear of the end-block move it
must tell apart — plus a CLOSED MANIFOLD mesh on every written holder.
"""
import sys
from collections import Counter
from dataclasses import replace
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

from cad import build as B, derive as D, mesh3mf, params   # noqa: E402
import reference as REF                                        # noqa: E402
from cad import text as TX                                 # noqa: E402
from cad.parts import holder                               # noqa: E402

# The tree for the release this file asserts: build `--version 7.0` first.
BUILD = REF.tree()
INDIV = ROOT / "individual"
FOLDER = {"Compile": "Compile", "Dominion": "Dominion", "FCM": "FCM",
          "Innovation": "Innovation"}
# Holder spans the box, not a slot: `components.GAMES[..]["holder_spans"]`.
SPANS = {"Compile", "Innovation"}
CURRENT_END = 9.800        # 2 * holder.END_EXTRA — what the STEPs measure
STALE_END = 10.000         # the pre-2026-08-24 studio
VOL_TOL = 0.05             # %, and it is meshing — see the docstring
TEXT_TOL = 0.5             # %, the ceiling on the deliberate text divergence
STALE_TOL = 2.0            # %, a sanity bound on the two end blocks

fails = []


def check(label, got, want, tol=1e-6):
    ok = abs(got - want) <= tol if isinstance(want, float) else got == want
    if not ok:
        fails.append(f"{label}: {got!r} vs {want!r}")
        print(f"    FAIL {label}: {got!r} vs {want!r}")
    return ok


def legacy_file(row, p, first):
    """The name `plan_exports.holder` gives this holder in `individual/`:
    keyed `(size, capacity, risers, sleeved, first)` or, where it spans,
    `(slots, cards per slot, risers, sleeved)` — never `calModelName`."""
    slv = "Sl" if p.isSleeved else "Un"
    if p.GameName in SPANS:
        label = f"{p.HorizontalSlots}x{p.CardsPerSlidingSlot}"
    else:
        base = (row.get("Base model") or "").strip()
        size = "XS" if base.startswith("XS") else (base[0] if base else "?")
        label = f"{size}-{p.FrontPocketCardCapacity}"
    return (f"Holder {label}-r{p.RisingSliders}-{slv}"
            + (" (first)" if first else "") + ".3mf")


def catalogue():
    """[(game, legacy name, built name, Primary, first)] — one per cached
    file. Rows sharing a legacy name agree on the geometry; the first is
    taken."""
    out = {}
    for row in params.load_rows(ROOT / "automation" / "parts.csv"):
        for sleeved in (0, 1):
            p = REF.from_row(row, sleeved)
            d = D.derive(p)
            for first in ((False, True) if p.isFirstSlidingSlotOverride
                          else (False,)):
                key = (p.GameName, legacy_file(row, p, first))
                out.setdefault(key, (p.GameName, key[1],
                                     B.holder_file(d, first), p, first))
    return [out[k] for k in sorted(out)]


def mesh(path):
    """(name, verts, tris) of a component 3MF's single body."""
    return mesh3mf.read(path)[0]


def box_of(verts):
    c = list(zip(*verts))
    return [min(c[0]), max(c[0]), min(c[1]), max(c[1]), min(c[2]), max(c[2])]


def mesh_volume(verts, tris):
    total = 0.0
    for a, b, c in tris:
        (x1, y1, z1) = verts[int(a)]
        (x2, y2, z2) = verts[int(b)]
        (x3, y3, z3) = verts[int(c)]
        total += (x1 * (y2 * z3 - y3 * z2)
                  - x2 * (y1 * z3 - y3 * z1)
                  + x3 * (y1 * z2 - y2 * z1)) / 6.0
    return abs(total)


def open_edges(verts, tris):
    """(unpaired, doubled) — `mesh3mf.faults`."""
    return mesh3mf.faults(tris)


def measure(entry):
    """One cached/built pair's boxes and volumes, computed in a WORKER. The
    6.6 volume is NOT a second build: the holder is built once with
    `text=False` and the engraving priced by intersection, so the expected
    weight is the blank less the 6.6 engraving."""
    game, legacy, built, p, first = entry
    cpath = INDIV / FOLDER[game] / legacy
    bpath = BUILD / game / built
    if not cpath.exists():
        return {"tag": f"{game}/{legacy}", "absent": True}
    if not bpath.exists():
        return {"tag": f"{game}/{legacy}", "unbuilt": f"{game}/{built}"}
    d = D.derive(p)
    _cn, cv, ct = mesh(cpath)
    _bn, bv, bt = mesh(bpath)
    blank = holder.build(D.derive(p), first, text=False)
    mv, mt = mesh3mf.triangulate(blank)
    cut66 = sum((blank & tool).volume
                for tool in holder.engraving(D.derive(replace(p, Version="6.6")), first))
    by_depth = (holder.holder_depth(d, first) - 2.0) / TX.CAP
    return {"tag": f"{game}/{legacy}", "legacy": legacy, "built": built,
            "cbox": box_of(cv), "bbox": box_of(bv),
            "got_vol": mesh_volume(cv, ct),
            "want_vol": mesh_volume(mv, mt) - cut66,
            "end": round((max(c[0] for c in cv) - min(c[0] for c in cv))
                         - d.calSlotwidth * p.HorizontalSlots, 3),
            "capped": holder.text_size(d, first) < by_depth - 1e-6}


def main():
    print("=== the written meshes ===")
    written = sorted(BUILD.glob("*/Holder *.3mf")) + \
        sorted(BUILD.glob("*/FirstHolder *.3mf"))
    if not written:
        print("  none in build/ — run `python -m cad.build --part holder` first")
        fails.append("nothing built")
    before = len(fails)
    for path in written:
        name, verts, tris = mesh(path)
        unpaired, doubled = open_edges(verts, tris)
        tag = f"{path.parent.name}/{path.name}"
        check(f"{tag} object name", name,
              "FirstHolder" if path.name.startswith("First") else "Holder")
        check(f"{tag} has no unpaired edge", unpaired, 0)
        check(f"{tag} has no doubled edge", doubled, 0)
    print(f"  {len(written)} written, closed and manifold" if len(fails) == before
          else f"  {len(written)} written, {len(fails) - before} problem(s)")

    print("\n=== against individual/ ===")
    print(f"  {'cached file':34s} {'end':>7s} {'corpus mm3':>11s} "
          f"{'built mm3':>11s} {'d%':>8s}        {'built file'}")
    entries = catalogue()
    import concurrent.futures as cf
    import multiprocessing as mp
    with cf.ProcessPoolExecutor(mp_context=mp.get_context("spawn")) as ex:
        measured = list(ex.map(measure, entries))
    buckets = Counter()
    absent = []
    for m in measured:
        tag = m["tag"]
        if m.get("absent"):
            absent.append(tag)
            continue
        if m.get("unbuilt"):
            fails.append(f"{m['unbuilt']} was not built")
            print(f"    FAIL {m['unbuilt']} was not built — run "
                  "`python -m cad.build --part holder` first")
            continue
        cbox, bbox, end = m["cbox"], m["bbox"], m["end"]
        got_vol, want_vol, capped = m["got_vol"], m["want_vol"], m["capped"]
        buckets[end] += 1
        delta = (want_vol / got_vol - 1) * 100
        print(f"  {m['legacy']:34s} {end:+7.3f} {got_vol:11.3f} {want_vol:11.3f} "
              f"{delta:+8.4f}%  {'text' if capped else '    '}  {m['built']}")
        # Y and Z are the same part in both generations, whatever the ends do.
        for i, axis in ((2, "Y min"), (3, "Y max"), (4, "Z min"), (5, "Z max")):
            check(f"{tag} {axis}", round(bbox[i], 3), round(cbox[i], 3), 1e-3)
        if end == CURRENT_END:
            for i, axis in ((0, "X min"), (1, "X max")):
                check(f"{tag} {axis}", round(bbox[i], 3), round(cbox[i], 3), 1e-3)
            if capped:
                check(f"{tag} is heavier by the text it does not engrave",
                      0.0 < delta < TEXT_TOL, True)
            else:
                check(f"{tag} volume", round(delta, 4), 0.0, VOL_TOL)
        elif end == STALE_END:
            # 0.100 in at each end and NOTHING else — the second half is the
            # point: a stale file differing elsewhere passes a width check.
            moved = (STALE_END - CURRENT_END) / 2
            check(f"{tag} X min moves in by {moved}",
                  round(bbox[0] - cbox[0], 3), round(moved, 3), 1e-3)
            check(f"{tag} X max moves in by {moved}",
                  round(cbox[1] - bbox[1], 3), round(moved, 3), 1e-3)
            check(f"{tag} is lighter by the two end blocks only",
                  delta < 0 and abs(delta) < STALE_TOL, True)
        else:
            fails.append(f"{tag} stands {end} beyond the slots, "
                         f"which is neither generation")
            print(f"    FAIL {tag} stands {end} beyond the slots, which is "
                  f"neither {CURRENT_END} nor {STALE_END}")

    print(f"\n  {buckets[CURRENT_END]} reproduced (+{CURRENT_END}), "
          f"{buckets[STALE_END]} moved (+{STALE_END})")
    for a in absent:
        print(f"  no cached file for {a} — never exported")

    print("\nPASS" if not fails else "\nFAIL: " + "; ".join(fails[:20]))
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
