"""Post-export sanity checks for the exporter. ZERO API calls.

Two independent guards against one failure mode: Onshape serving a CACHED
translation computed for the PREVIOUS parameter set. The bytes are a valid 3MF
of a real component, just the wrong one — so it lands under the right filename,
parses fine, and is recorded as current in provenance. Nothing downstream
notices until make_cascade happens to refuse the layout, and only then if the
wrong part is the wrong SIZE in a way that overflows the bed.

  footprint  the exported Box's measured W x D must match the cascade's
             parts.csv W/D. Those columns are the ASSEMBLED, CLOSED cascade —
             the LID's outer size, since the box fits inside it. Over the 33
             built cascades the lid measures parts.csv to within 0.02 mm in
             depth and a flat -0.10 mm in width (the width column rounds 270.90
             up to 271.0), and the box measures the lid MINUS 2.00 mm on both
             axes, with no exceptions. WALL below is that 2.00 plus the 0.1
             rounding, which is why it is not a round number and why it is not
             "the box's wall": the 2 mm is the lid wrapping the box, 1 mm a
             side. WIDTH is the tight discriminator, so a width mismatch is
             fatal. DEPTH has a handful of parts.csv rows that have drifted from
             the model, so a depth mismatch only warns — D_TOL is 1.2 mm, wide
             enough that passing this check does NOT confirm a row's depth to
             better than a millimetre. An unbuilt row's estimated W/D should be
             replaced with the lid's measurements once its CAD exists, rather
             than left to ride on that slack.

  lid        the exported Lid's measured W x D must match the same columns
             DIRECTLY — it is the closed cascade they describe — so it is held
             to 0.2 mm on both axes, and fatally. This is the check that
             notices a row whose W/D were estimated rather than measured; the
             footprint check above cannot, its depth tolerance being 1.2 mm.

  pusher     the raised tabs on a Pusher's top face must sit on solid plate,
             not over the U-notch cut into the same end. Unlike the two checks
             above this is not about a stale translation — it is a CAD sizing
             defect that only shows on NARROW pushers, and it is a warning, not
             a refusal, because the export itself is exactly what the CAD says.
             See pusher_tabs() for the geometry and PIPELINE.md for the rule.

  identity   a new export's mesh hash must not equal one already recorded for a
             DIFFERENT component file, in ANY game (the stale export usually
             comes from the previous run, which is usually a different game).
             Over the 168 components on disk the only such collisions were the
             three Compile files this bug poisoned: legitimate duplicates don't
             occur, because every export is keyed on the parameters that
             determine its geometry.

All of them are cheap and local, so they run on every export by default;
export.py --skip-verify turns them off for the case where parts.csv is the
thing that's wrong.
"""
import hashlib
import io
import re
import zipfile

import mesh

MODEL = "3D/3dmodel.model"

# parts.csv W/D minus the measured mesh bbox, on both axes. Observed 2.00-2.10
# over every correct box in individual/ (4 games, 33 boxes).
WALL = 2.05
W_TOL = 0.6        # fatal beyond this
D_TOL = 1.2        # warn beyond this (some parts.csv depths have drifted)

# A lid needs no wall constant, so it is checked far tighter — and on both axes.
L_TOL = 0.2        # fatal beyond this


def _model_text(data):
    return zipfile.ZipFile(io.BytesIO(mesh.unwrap(data))).read(MODEL).decode()


def mesh_sha(data):
    """Stable hash of a 3MF's geometry, independent of packaging.

    Hashes the <mesh> blocks only, whitespace-normalised: the assembly splitter
    re-wraps a mesh into a fresh single-object 3MF and zipfile stamps its own
    timestamps, so hashing the file bytes would not be reproducible."""
    h = hashlib.sha256()
    for block in re.findall(r"<mesh>.*?</mesh>", _model_text(data), re.S):
        h.update(re.sub(r"\s+", " ", block).encode())
    return h.hexdigest()[:16]


def footprint(data):
    """(width, depth, height) in mm of the largest object in a 3MF."""
    text = _model_text(data)
    scale = {"meter": 1000.0, "millimeter": 1.0}.get(
        re.search(r'unit="(\w+)"', text).group(1), 1.0)
    best = (0.0, 0.0, 0.0)
    for block in re.findall(r"<mesh>.*?</mesh>", text, re.S):
        v = [(float(a), float(b), float(c)) for a, b, c in re.findall(
            r'<vertex x="([^"]+)" y="([^"]+)" z="([^"]+)"', block)]
        if not v:
            continue
        span = tuple((max(c) - min(c)) * scale for c in zip(*v))
        if span[0] * span[1] > best[0] * best[1]:
            best = span
    return best


def check_box(data, ctx):
    """(fatal message or None, warning message or None) for an exported Box.

    Skips silently when the cascade's parts.csv row carries no W/D — plan_exports
    already refuses such rows, so this only guards ad-hoc callers."""
    want_w, want_d = ctx.get("box_w"), ctx.get("box_d")
    if not (want_w and want_d):
        return None, None
    w, d, _h = footprint(data)
    dw, dd = abs((want_w - w) - WALL), abs((want_d - d) - WALL)
    got = f"measured {w:.1f}x{d:.1f} mm, expected {want_w - WALL:.1f}x" \
          f"{want_d - WALL:.1f} mm (parts.csv {want_w:g}x{want_d:g} less the " \
          f"{WALL} mm wall)"
    if dw > W_TOL:
        return (f"Box for {ctx['model']} is the wrong size: {got}", None)
    if dd > D_TOL:
        return (None, f"Box for {ctx['model']} depth is off by {dd:.1f} mm: "
                      f"{got} — check the parts.csv row")
    return None, None


def check_lid(data, ctx):
    """(fatal message or None, None) for an exported Lid.

    The parts.csv W/D columns measure the closed cascade, so the lid IS that
    figure — no wall constant in between, and therefore a far tighter check
    than check_box can manage. Over the 33 built cascades a lid measures its
    row to within 0.12 mm in depth and 0.00 to -0.10 mm in width (the width
    column rounds a 270.90 lid up to 271.0), so L_TOL is slack beyond anything
    the CAD does while still catching a row whose W/D were never measured:
    Milestones' pre-build guesses of 40/48 mm were out by 0.22 and 0.30.

    Fatal on BOTH axes, unlike check_box, which has to tolerate a drifted
    depth because its own comparison is looser. Here a mismatch is either a
    stale translation or an estimate that wants replacing with these
    measurements, and both are worth stopping for.

    Skips silently when the row carries no W/D, as check_box does."""
    want_w, want_d = ctx.get("box_w"), ctx.get("box_d")
    if not (want_w and want_d):
        return None, None
    w, d, _h = footprint(data)
    off = [(axis, got, want)
           for axis, got, want in (("width", w, want_w), ("depth", d, want_d))
           if abs(got - want) > L_TOL]
    if not off:
        return None, None
    detail = ", ".join(f"{axis} {got:.2f} vs parts.csv {want:g} ({got - want:+.2f})"
                       for axis, got, want in off)
    return (f"Lid for {ctx['model']} disagrees with its parts.csv row by more "
            f"than {L_TOL} mm: {detail}. Those columns are the closed cascade, "
            f"which a lid should match exactly"), None


def duplicate(sha, file, provenance_rows):
    """'<Game>/<file>' of an already-recorded component with this exact geometry
    under a DIFFERENT filename, or None. Cross-game on purpose."""
    for game, row in provenance_rows:
        if row.get("sha") == sha and row.get("file") != file:
            return f"{game}/{row['file']}"
    return None


# ---------------------------------------------------------------------------
# Pusher tab support
# ---------------------------------------------------------------------------
#
# A Pusher is a flat plate, 4.5 mm thick, printed FACE DOWN (make_cascade lays
# every pusher on the bed with an identity rotation). Its leading end carries
# three interlocking features, all sized in the CAD from the pusher's own depth
# D — the card-stack dimension, i.e. the width of the leading end the features
# are cut into:
#
#   tab A     3.8 mm wide x 5.0 deep, raised 1.5 mm above the plate's top face,
#             set 4.0 mm in from the D=0 edge
#   tab B     the same, set 4.2 mm in from the D edge — so its inner edge lands
#             at 8.0 mm from that edge, wherever that edge is
#   notch     a 5.4 x 5.2 mm U cut clean THROUGH the plate from the leading end,
#             centred 2.5 mm off the plate's mid-line (edges at D/2 - 0.2 and
#             D/2 + 5.2 from the D=0 edge), with the near edge clamped so it
#             never runs into tab A
#
# Tab A is placed from one edge and the notch from the mid-line, and the CAD
# clamps the notch to keep those two apart. Tab B gets no such clamp, so as D
# shrinks the notch walks INTO it: tab B is fully backed only while
#
#     D - 8.0  >=  D/2 + 5.2      i.e.   D >= 26.4 mm
#
# and below that it loses (13.2 - D/2) mm of its 3.8 mm root, cantilevered over
# a 3 mm void that the slicer has to start in mid-air. At D = 19.2 mm
# (Innovation "Single Set" unsleeved, the narrowest two-tab pusher in the
# catalogue) 0.2 mm of root is left and the tab prints as a loose flag.
#
# The check measures rather than recomputes that inequality, so it also holds
# for pushers whose CAD has moved on: slice the tabs off the top face, slice the
# plate below them, and ask how much of each tab's footprint has plate under it.

# A tab is meant to be fully backed, so ANY unbacked footprint is a warning.
# Below this much continuous backing it is not a print artefact to live with —
# the tab has no root worth the name. The 32 pushers on disk split cleanly
# either side: the three worst anchor 0.19 / 0.98 / 1.01 mm, the next ones
# 2.31 / 3.01 / 3.61 / 3.80, and a correctly backed tab anchors its full 5.00.
TAB_ANCHOR_MIN = 2.0


def _meshes(data):
    """[(verts_mm, tris)] for every mesh in a plain (Onshape/split) 3MF."""
    text = _model_text(data)
    scale = {"meter": 1000.0, "millimeter": 1.0}.get(
        re.search(r'unit="(\w+)"', text).group(1), 1.0)
    out = []
    for block in re.findall(r"<mesh>.*?</mesh>", text, re.S):
        v = [(float(a) * scale, float(b) * scale, float(c) * scale)
             for a, b, c in re.findall(
                 r'<vertex x="([^"]+)" y="([^"]+)" z="([^"]+)"', block)]
        t = [(int(a), int(b), int(c)) for a, b, c in re.findall(
            r'<triangle v1="(\d+)" v2="(\d+)" v3="(\d+)"', block)]
        if v and t:
            out.append((v, t))
    return out


def _section(verts, tris, axis, at):
    """Cross-section of a mesh at `axis` = `at`, as segments in the other two
    axes. One segment per crossed triangle; the mesh is closed, so the segments
    close into loops."""
    u, w = [a for a in (0, 1, 2) if a != axis]
    segs = []
    for t in tris:
        p = [verts[i] for i in t]
        d = [q[axis] - at for q in p]
        hits = []
        for i in range(3):
            j = (i + 1) % 3
            if (d[i] > 0) != (d[j] > 0):
                f = d[i] / (d[i] - d[j])
                hits.append((p[i][u] + f * (p[j][u] - p[i][u]),
                             p[i][w] + f * (p[j][w] - p[i][w])))
        if len(hits) == 2:
            segs.append((hits[0], hits[1]))
    return segs


def _loops(segs):
    """Group a section's segments into connected loops: [(u0, u1, w0, w1, segs)]."""
    parent = {}

    def key(p):
        return (round(p[0], 4), round(p[1], 4))

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    for s in segs:
        for p in s:
            parent.setdefault(key(p), key(p))
        ra, rb = find(key(s[0])), find(key(s[1]))
        if ra != rb:
            parent[ra] = rb
    groups = {}
    for s in segs:
        groups.setdefault(find(key(s[0])), []).append(s)
    out = []
    for ss in groups.values():
        us = [p[0] for s in ss for p in s]
        ws = [p[1] for s in ss for p in s]
        out.append((min(us), max(us), min(ws), max(ws), ss))
    return out


def _inside(segs, u, w):
    """Even-odd point-in-section test, casting along +u."""
    crossings = 0
    for a, b in segs:
        if (a[1] > w) != (b[1] > w):
            if a[0] + (w - a[1]) * (b[0] - a[0]) / (b[1] - a[1]) > u:
                crossings += 1
    return crossings % 2 == 1


def _anchor(tab, plate, u0, u1, w0, w1, n=120, across=24):
    """Widest continuous strip of the tab that is backed by plate along its
    whole length, measured along whichever in-plane axis gives the larger
    answer. This is the tab's root: the tab's full 5.00 mm depth when it is
    properly backed, 0.19 mm on the Innovation Single Set unsleeved."""
    best = 0.0
    for along, other in (((w0, w1), (u0, u1)), ((u0, u1), (w0, w1))):
        flip = along == (u0, u1)
        step = (along[1] - along[0]) / n
        run = 0.0
        for i in range(n):
            a = along[0] + (i + 0.5) * step
            pts = [(a, b) if flip else (b, a)
                   for b in (other[0] + (j + 0.5) * (other[1] - other[0]) / across
                             for j in range(across))]
            on_tab = [p for p in pts if _inside(tab, *p)]
            if on_tab and all(_inside(plate, *p) for p in on_tab):
                run += step
                best = max(best, run)
            else:
                run = 0.0
    return best


def pusher_tabs(data, grid=80):
    """Per-tab support measurements for a Pusher 3MF:
    [{'w', 'd', 'fraction', 'anchor'}], one entry per raised tab.

    'fraction' is how much of the tab's footprint has plate directly under it,
    sampled on a `grid` x `grid` lattice (so it is good to about one cell);
    'anchor' is the widest continuous fully-backed strip, in mm. A correct tab
    reads 1.00 and 5.00 — its whole 5 mm depth.

    Orientation-agnostic: the plate normal is the mesh's thinnest axis, and the
    tabs are whichever face's near-surface section is the smaller of the two, so
    this reads a Pusher straight out of Onshape and one lifted back out of a
    built project alike."""
    verts, tris = max(_meshes(data), key=lambda m: len(m[0]))
    spans = [(max(c) - min(c), a) for a, c in enumerate(zip(*verts))]
    axis = min(spans)[1]
    lo = min(v[axis] for v in verts)
    hi = max(v[axis] for v in verts)
    span = hi - lo

    def area(at):
        return sum((u1 - u0) * (w1 - w0)
                   for u0, u1, w0, w1, _ in _loops(_section(verts, tris, axis, at)))

    # The tab face is the one whose near-surface section is the smaller.
    top = hi if area(hi - 0.2) < area(lo + 0.2) else lo
    sign = 1 if top == hi else -1
    tabs = _loops(_section(verts, tris, axis, top - sign * 0.2))
    # 3/4 of the way down from the tab face: clear of the 1.5 mm tabs and of
    # the version string embossed just under the top face.
    plate = _section(verts, tris, axis, top - sign * 0.75 * span)

    out = []
    for u0, u1, w0, w1, tab in sorted(tabs, key=lambda l: -l[3]):
        total = backed = 0
        for i in range(grid):
            u = u0 + (i + 0.5) * (u1 - u0) / grid
            for j in range(grid):
                w = w0 + (j + 0.5) * (w1 - w0) / grid
                if not _inside(tab, u, w):
                    continue
                total += 1
                if _inside(plate, u, w):
                    backed += 1
        out.append({"w": w1 - w0, "d": u1 - u0,
                    "fraction": backed / total if total else 0.0,
                    "anchor": _anchor(tab, plate, u0, u1, w0, w1)})
    return out


def check_pusher(data, ctx=None):
    """(None, warning message or None) for an exported Pusher.

    Never fatal. The two checks above refuse an export because the BYTES are
    wrong — the wrong component under the right name. This one says the bytes
    are right and the CAD is wrong, and refusing would only block work on
    everything else in the same assembly. It has to be acted on in Onshape."""
    try:
        tabs = pusher_tabs(data)
    except (ValueError, KeyError, ZeroDivisionError):
        return None, None            # not a shape this check understands
    loose = [t for t in tabs if t["fraction"] < 0.999]
    if not loose:
        return None, None
    worst = min(loose, key=lambda t: t["anchor"])
    who = f" for {ctx['model']}" if ctx and ctx.get("model") else ""
    how = ("has almost nothing holding it"
           if worst["anchor"] < TAB_ANCHOR_MIN else "overhangs the notch")
    return None, (
        f"Pusher{who}: {len(loose)} of {len(tabs)} raised tab(s) sit partly over "
        f"the end notch — the worst is {worst['fraction'] * 100:.0f}% backed "
        f"with {worst['anchor']:.2f} mm of root on a {worst['w']:.1f} mm tab, so "
        f"it {how}. The plate is too narrow for where the CAD puts the second "
        f"tab; fix it in Onshape (see PIPELINE.md, 'The pusher's second tab')")


# ---------------------------------------------------------------------------
# CLI: audit every Pusher on disk
# ---------------------------------------------------------------------------

def audit_pushers(root, verbose=False):
    """Print a tab-support line for every exported Pusher under `root`, and
    return the number that carry an unbacked tab.

    individual/ only. A built cascade carries copies of these exact files (the
    2-3 pushers in a project are one component instanced), so walking cascades/
    as well only re-reports the same seven meshes under project names — and
    costs 20x the time to unpack them out of Studio's layout. Which projects a
    flagged pusher reaches follows from its dedup key: (risers, cards,
    sleeved)."""
    from pathlib import Path
    root = Path(root)
    rows = []
    for path in sorted(root.glob("individual/*/Pusher*.3mf")):
        try:
            tabs = pusher_tabs(path.read_bytes())
        except (ValueError, KeyError, ZeroDivisionError, IndexError):
            continue
        loose = [t for t in tabs if t["fraction"] < 0.999]
        rows.append((path.relative_to(root),
                     min(loose, key=lambda t: t["anchor"]) if loose else None))
    rows.sort(key=lambda r: (r[1]["anchor"] if r[1] else 99.0, str(r[0])))
    bad = sunk = 0
    for name, worst in rows:
        if worst is None:
            if verbose:
                print(f"    ok  {'':>6s} {'':>6s}  {name}")
            continue
        bad += 1
        sunk += worst["anchor"] < TAB_ANCHOR_MIN
        mark = "✗" if worst["anchor"] < TAB_ANCHOR_MIN else "⚠"
        print(f"    {mark}  {worst['fraction'] * 100:5.1f}% "
              f"{worst['anchor']:5.2f}mm  {name}")
    print(f"\n  {bad} of {len(rows)} pushers have a tab hanging over the "
          f"notch; {sunk} of those have under {TAB_ANCHOR_MIN} mm of root.")
    return bad


if __name__ == "__main__":
    import argparse
    import sys
    from pathlib import Path

    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--pushers", action="store_true",
                    help="audit tab support on every Pusher in the repo")
    ap.add_argument("--all", action="store_true",
                    help="with --pushers, list the passing ones too")
    args = ap.parse_args()
    if not args.pushers:
        ap.error("nothing to do — try --pushers")
    print("  Pusher tab support (backed fraction, widest backed strip):")
    sys.exit(1 if audit_pushers(Path(__file__).resolve().parent.parent,
                                verbose=args.all) else 0)
