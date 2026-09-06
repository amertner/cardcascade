#!/usr/bin/env python3
"""Every built holder against the Onshape one it replaces.

    .venv/bin/python -m cad.build --part holder
    .venv/bin/python tests/test_holder_corpus.py     # about a minute, pooled

`tests/test_holder.py` checks the SOURCE against ten hand-exported STEPs, which
settle the geometry exactly and say nothing about the written file. This checks
the 3MFs `cad.build` writes against the 50 in `individual/`, through the same
reader the rest of the toolchain uses, so it covers the meshing and the
assembly placement too. Same split as the Pusher's two tests.

## What must match, and what must not

`individual/` is a mixed catalogue, as it was for the pushers — but the axis is
different and it took the provenance dates to see it. Every holder on disk is
recorded at studio version **6.6**, so `export.py` believes all 50 are current;
the meshes disagree. Thirty of them stand `5.000` beyond the outer slot edge at
each end and twenty stand `4.900`, and the split is EXACTLY the export date:

    ..2026-08-20  +10.000  x30      2026-08-24..  +9.800  x20

So the Holder studio changed between those dates and its version was never
bumped. `cad/` is `4.900` throughout — that is what all ten STEPs measure — so
it must REPRODUCE the twenty and MOVE the thirty. Both are reported; both are
asserted, but differently: the thirty have to differ in X and in NOTHING ELSE,
which is what makes "the end block moved 0.100" a measurement rather than an
anecdote. A re-export moves a file from one bucket to the other on its own —
the bucket is read off the mesh, not from a list here.

The engraved VERSION is the other difference, and it is not a divergence: all
50 cached files engrave `CC 6.6`, exact to a thousandth, while the STEPs Allan
exported by hand engrave `CC 7.0`. Everything is 7.0 now, and on the Holder that
bump changed NOTHING but the embossed number (Allan) — which is what licenses
comparing across it. The build is therefore priced at `Version="6.6"` for the
volume comparison — one build with `text=False`, less the 6.6 engraving by
intersection (`measure`) — as `tests/test_token_holder_corpus.py` rebuilds
for the same stated reason, and the two are compared like for like.

Note the two changes are independent: the end-block trim happened while the
studio was still at 6.6, so a cached holder can carry the 6.6 string (all of
them do) and either end block.

The engraved SIZE is a divergence, and a deliberate one: where Onshape's rule
makes the two blocks collide, `holder.text_size` shrinks them so they do not
(spec/HOLDER.md, "The size"). Smaller text engraves away less material, so those
holders come out HEAVIER, by the ink Onshape lost into the overlap. That is
asserted by sign and a bound rather than by a number — the number itself is held
against the STEPs, exactly, in `tests/test_holder.py`.

Per file, then:

  * all six bounding-box coordinates, from the written 3MF — the envelope AND
    where the part sits, which is what `make_cascade` places
  * the volume, tessellated the same way at `Version="6.6"`, to 0.05%. That
    tolerance is meshing, not geometry: OCCT and Onshape do not triangulate a
    12 mm scallop the same way. It is still 5x clear of the end-block move it
    has to tell apart.

and, on every written holder whether or not it has a cached twin, that the mesh
is CLOSED and MANIFOLD. That last one is the printability claim: a slicer will
take a hole or a doubled edge as far as a failed print. `individual/`'s 850
cached bodies have neither, and neither, now, does anything `cad.build` writes —
`mesh3mf._drop_flaps` is what closed the two holders that did.
"""
import sys
from collections import Counter
from dataclasses import replace
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from cad import build as B, derive as D, mesh3mf, params   # noqa: E402
from cad import text as TX                                 # noqa: E402
from cad.parts import holder                               # noqa: E402

BUILD = ROOT / "build"
INDIV = ROOT / "individual"
FOLDER = {"Compile": "Compile", "Dominion": "Dominion", "FCM": "FCM",
          "Innovation": "Innovation"}
# The two games whose holder spans the box rather than a slot, so `plan_exports`
# names it `Holder 3x7-r4-Sl` instead of `Holder S-40-r2-Sl`. From
# `automation/components.GAMES[...]["holder_spans"]`.
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
    """The name `plan_exports.holder` gives this holder in `individual/`.

    Keyed on `(size, front capacity, risers, sleeved, first)` for the per-slot
    games and on `(HorizontalSlots, cards per slot, risers, sleeved)` for the
    two that span — neither of which is `calModelName`, which is what
    `cad.build` uses. The size letter comes from the row's `Base model`, as
    `plan_exports.build_context` reads it, XS included.
    """
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
    """[(game, legacy name, built name, Primary, first)] — one per cached file.

    Several parts.csv rows can share one legacy name (the key carries neither
    the Mat branch nor the card count), and they agree on the geometry by
    construction; the first is taken.
    """
    out = {}
    for row in params.load_rows(ROOT / "automation" / "parts.csv"):
        for sleeved in (0, 1):
            p = params.from_row(row, sleeved)
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
    """Signed volume of a closed triangle mesh, by the divergence theorem."""
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
    """(unpaired, doubled) — `mesh3mf.faults`, which this test is where it
    came from; kept under its old name so the checks below read as before."""
    return mesh3mf.faults(tris)


def measure(entry):
    """Everything the checks below need for one cached/built pair, computed
    in a WORKER: the two meshes' boxes and volumes, and the built holder's
    volume at the cached generation's `CC 6.6` string.

    The 6.6 volume is NOT a second build. The holder is built once with
    `text=False` and the engraving priced by intersection at each string —
    the two differ by nothing but the version digits (Allan) — so what the
    cached file should weigh is the blank's tessellated volume less the 6.6
    engraving. That is what `holder.engraving` is for, and it is what took
    this test from a 6.6 rebuild of all 50 (12-15 minutes, serially) to a
    pool over one build each.
    """
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
    # --- every written holder is a sound mesh -------------------------------
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

    # --- and the 50 with a cached twin are the same part ---------------------
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
            # The current studio: the build reproduces it, ends included.
            for i, axis in ((0, "X min"), (1, "X max")):
                check(f"{tag} {axis}", round(bbox[i], 3), round(cbox[i], 3), 1e-3)
            if capped:
                check(f"{tag} is heavier by the text it does not engrave",
                      0.0 < delta < TEXT_TOL, True)
            else:
                check(f"{tag} volume", round(delta, 4), 0.0, VOL_TOL)
        elif end == STALE_END:
            # The pre-2026-08-24 studio, and the difference is the end block
            # ALONE: 0.100 in at each end, nothing else anywhere, and exactly
            # the volume that removes. Asserting the second half is the point
            # — a stale file that also differed in the lattice or the lip
            # would pass a width check.
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
