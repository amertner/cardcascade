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

  pusher     a Pusher must carry two raised tabs of the nominal width, and
             each must sit on solid plate rather than over the U-notch cut into
             the same end. Unlike the two checks above this is not about a stale
             translation — it is a CAD sizing defect that only shows on NARROW
             pushers, and it is a warning, not a refusal, because the export is
             exactly what the CAD says. The count is checked FIRST: past a
             point the notch swallows a tab outright, and the survivor's
             support looks perfect. See pusher_tabs() for the geometry and
             PIPELINE.md for the rule.

  stamp      a Box, Lid or Pusher must be ENGRAVED with the version its
             cascade is being built at. The stamp comes from Onshape's `Version`
             primary variable and the recorded version from
             onshape_config.expected_version() — two different places, and they
             drifted: 22 components on disk carry 7.0 lock geometry under a
             `CC 6.6` stamp. That is the one thing a person holding two pushers
             can read, and the 7.0 lock spans all three parts, so a wrong stamp
             is how a 7.0 pusher ends up being printed for a 6.6 lid, where the
             tabs miss the recesses by 5.6 mm. Fatal on a mismatch, a warning
             when the line cannot be read.

  identity   a new export's mesh hash must not equal one already recorded for a
             DIFFERENT component file, in ANY game (the stale export usually
             comes from the previous run, which is usually a different game).
             Over the 168 components on disk the only such collisions were the
             three Compile files this bug poisoned: legitimate duplicates don't
             occur, because every export is keyed on the parameters that
             determine its geometry.

Beyond the checks, LOCK_CLASSES / target_lock() hold the proposed five-design
lock catalogue and `verify.py --catalogue` prints the per-pusher worksheet for
it (PIPELINE.md, "Standardising the lock"). Nothing enforces it yet — the CAD
still places the features parametrically — so it reports, it does not refuse.

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

# Every pusher in the catalogue carries exactly two tabs of this width. Anything
# else is the same collision one stage further on: at D = 18.00 tab B's whole
# footprint falls inside the notch and the CAD emits no tab at all (one tab
# survives, fully backed, so a support check alone reports the pusher clean);
# at D = 14.04 the two tabs overlap and fuse into a single 5.84 mm boss.
TABS_EXPECTED = 2
TAB_W_NOMINAL = 3.80
TAB_W_TOL = 0.60


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


# ---------------------------------------------------------------------------
# The five-design lock catalogue (proposed — see PIPELINE.md)
# ---------------------------------------------------------------------------
#
# A design is one number: s, the distance from the pusher's centreline to each
# tab's centre. Tabs and notch keep today's sizes and sit symmetrically about
# that centreline, so a design is legal on a pusher of depth D when there is at
# least EDGE_MIN of plate outboard of each tab:
#
#     D >= 2 * (s + TAB_W_NOMINAL/2 + EDGE_MIN)
#
# and it can carry the notch when the land between tab and notch holds up:
#
#     s >= TAB_W_NOMINAL/2 + NOTCH_W/2 + LAND_MIN
#
# The five values below were chosen to maximise the WORST hang base (2s) as a
# fraction of the widest base the plate could give (D - 2*EDGE_MIN - TAB_W).
# Over the 32 pushers on disk that worst case is 63%, and 15 of the 32 come out
# with a wider base than they have today, because today's 4.00 mm inset is more
# generous than the 2.00 the catalogue allows at the bottom of a band.
#
# "Today's base" is D - 12.00, not D - 11.80: tab A is 4.00 in from one edge and
# tab B 4.20 in from the other, so the centres are 6.10 and D - 5.90 and the
# separation carries tab B's extra 0.20.
NOTCH_W = 5.40
EDGE_MIN = 2.00
LAND_MIN = 1.20
LOCK_CLASSES = [("C1", 3.10), ("C2", 5.10), ("C3", 8.50),
                ("C4", 13.50), ("C5", 24.00)]


def class_min_depth(s):
    """Narrowest pusher a design with tab offset `s` is legal on."""
    return 2 * (s + TAB_W_NOMINAL / 2 + EDGE_MIN)


def lock_class(depth):
    """(name, s, has_notch) for a pusher of this depth, or None if nothing fits."""
    # 0.01 of slack: a depth like 18.00 arrives from the mesh as 17.99999 and
    # must still take the design whose floor is exactly 18.00.
    fits = [(n, s) for n, s in LOCK_CLASSES if class_min_depth(s) <= depth + 0.01]
    if not fits:
        return None
    name, s = max(fits, key=lambda c: c[1])
    return name, s, s >= TAB_W_NOMINAL / 2 + NOTCH_W / 2 + LAND_MIN


def target_lock(depth):
    """Where the catalogue puts a pusher's features, as distances from its
    D = 0 plate edge: {'class', 's', 'tabs': [(lo, hi), (lo, hi)], 'notch'}."""
    got = lock_class(depth)
    if not got:
        return None
    name, s, notched = got
    mid, half = depth / 2, TAB_W_NOMINAL / 2
    return {"class": name, "s": s,
            "tabs": [(mid - s - half, mid - s + half),
                     (mid + s - half, mid + s + half)],
            "notch": (mid - NOTCH_W / 2, mid + NOTCH_W / 2) if notched else None}


def pusher_lock(data):
    """As-built lock geometry: {'depth', 'tabs', 'notch'} with every position a
    distance from the pusher's D = 0 plate edge, so it compares directly with
    target_lock(). `notch` is None when the end carries no through-cut."""
    verts, tris = max(_meshes(data), key=lambda m: len(m[0]))
    spans = [(max(c) - min(c), a) for a, c in enumerate(zip(*verts))]
    axis = min(spans)[1]
    lo, hi = (min(v[axis] for v in verts), max(v[axis] for v in verts))
    span = hi - lo

    def area(at):
        return sum((u1 - u0) * (w1 - w0)
                   for u0, u1, w0, w1, _ in _loops(_section(verts, tris, axis, at)))

    top = hi if area(hi - 0.2) < area(lo + 0.2) else lo
    sign = 1 if top == hi else -1
    tabs = _loops(_section(verts, tris, axis, top - sign * 0.2))
    plate = _section(verts, tris, axis, top - sign * 0.75 * span)
    w = [a for a in (0, 1, 2) if a != axis][1]
    w0 = min(v[w] for v in verts)
    depth = max(v[w] for v in verts) - w0
    # the notch is the run along the leading edge with no plate behind it
    u0 = min(p[0] for seg in plate for p in seg)
    runs, cur = [], None
    for j in range(1200):
        y = w0 + (j + 0.5) * depth / 1200
        if not _inside(plate, u0 + 0.05, y):
            cur = [y, y] if cur is None else [cur[0], y]
        elif cur:
            runs.append(cur)
            cur = None
    if cur:
        runs.append(cur)
    runs = [r for r in runs if r[1] - r[0] > 0.3]
    return {"depth": depth,
            "tabs": sorted((t[2] - w0, t[3] - w0) for t in tabs),
            "notch": (runs[0][0] - w0, runs[0][1] - w0) if runs else None}


# ---------------------------------------------------------------------------
# The engraved version stamp
# ---------------------------------------------------------------------------
#
# Every Box, Lid and Pusher carries `CC <version>` cut into it, from the
# Onshape `Version` primary variable (set_variables.build_primary). That string
# is the ONLY thing a person holding a printed part can read, and the 7.0 lock
# is a whole-cascade change — "a pusher, a lid and a box must all come from the
# same version" (LOCK_STANDARD.md) — so the stamp is what stops someone mixing
# a new pusher into an old lid, where the tabs miss the recesses by 5.6 mm and
# the part simply will not go in.
#
# Nothing checked it, and it went wrong: 36 of the 128 boxes, lids and pushers
# on disk carry 7.0 lock geometry under a `CC 6.6` stamp, because the CAD's lock
# moved before the `Version` variable was bumped and provenance records
# expected_version(), not what the bytes say. The two are set in different places and only this reads
# both. cad/parts/pusher.py already REFUSES to build that part ("a Primary at
# '6.6' would get 7.0 tabs under a 'CC 6.6' stamp"); this is the same guard for
# the Onshape path.
#
# Reading it is not OCR. The version is a WORD — `<digit> . <digit>`, with a
# space either side of it — and Orbitron Bold's digits are told apart by their
# counters, the enclosed holes:
#
#     6   one counter, short (about a quarter of the cap) and low in the glyph
#     0   one counter, tall (about three fifths of the cap)
#     7   none
#     4   one counter, short and high
#     8   two counters
#
# So the pair of digits either side of the period names the version, and the
# ones that matter here are two low counters (6.6) against none-then-tall
# (7.0). A signature that several versions share (6.3 and 6.5 both read
# "low, none") is reported as all of them; the check only ever asks whether the
# expected version is among them, so the ambiguity costs nothing.
STAMP_SIGNATURES = {
    "7.0": ("none", "tall"),
    "6.6": ("low", "low"),
    "6.5": ("low", "none"),
    "6.4": ("low", "high"),
    "6.3": ("low", "none"),
}

# The three parts the 7.0 lock spans, and so the three whose stamp is a claim
# about which lock a person is holding. LOCK_STANDARD.md: "a pusher, a lid and a
# box must all come from the same version. Holders and toppers carry over."
STAMPED = ("Box", "Lid", "Pusher")

MARK_MIN, MARK_MAX = 0.05, 12.0    # a glyph is never outside this, in mm
SPACE_PER_CAP = 0.25               # a word gap, against letter spacing under 0.1
BASELINE_TOL = 0.15                # two lines sit a full cap apart, so this is safe
MAX_PLANES = 80                    # bound the plane scan on a 46k-triangle box


def _populated_planes(verts, axis, min_hits=40):
    """Midpoints between the mesh's populated planes along `axis`.

    Sectioning a box every 0.1 mm to find its text is minutes of Python. But an
    engraved glyph is a slab bounded by two real planes — the face it is cut
    into and the 0.4 mm floor of the cut — so the midpoints of the planes the
    mesh actually populates always include one inside it, and there are a few
    dozen of those rather than a few thousand."""
    hits = {}
    for p in verts:
        z = round(p[axis], 3)
        hits[z] = hits.get(z, 0) + 1
    planes = sorted(z for z, n in hits.items() if n >= min_hits)
    mids = [((a + b) / 2, min(hits[a], hits[b]))
            for a, b in zip(planes, planes[1:]) if b - a > 0.02]
    if len(mids) > MAX_PLANES:      # the busiest slabs first — text is dense
        mids = sorted(sorted(mids, key=lambda m: -m[1])[:MAX_PLANES])
    return [at for at, _ in mids]


def glyph_plane(verts, tris, axis):
    """The plane through this mesh whose section carries the most glyph-sized
    loops, or None. Not the outer face: on a pusher the text is cut into the
    face the tabs stand proud of, 1.5 mm inside the bounding box."""
    best = (0, None)
    for at in _populated_planes(verts, axis):
        n = sum(1 for l in _loops(_section(verts, tris, axis, at))
                if MARK_MIN < l[1] - l[0] < MARK_MAX
                and MARK_MIN < l[3] - l[2] < MARK_MAX)
        if n > best[0]:
            best = (n, at)
    return best[1]


def _orientations(marks):
    """The same marks in each of the four in-plane orientations.

    Onshape runs some of these strings along the part's other axis — the box
    engraves its floor text reading down the depth — and a reader that knows
    only one baseline direction misses those. Each orientation puts the line's
    baseline at `w0` and reading order at increasing `u`.

    All four must be ROTATIONS. A transpose `(u, w) -> (w, u)` looks like it
    turns the page and is a reflection: it lands the baseline in the right place
    but reads the line backwards, so `7.0` comes out `0.7`. That went unnoticed
    while every rotated stamp read `6.6`, which is a palindrome; the first box
    re-exported at 7.0 failed to read at all."""
    yield marks
    yield [(-m[1], -m[0], -m[3], -m[2]) for m in marks]           # 180
    yield [(m[2], m[3], -m[1], -m[0]) for m in marks]             # +90
    yield [(-m[3], -m[2], m[0], m[1]) for m in marks]             # -90


def _lines(marks):
    """Marks grouped into text lines by baseline. A version line sits a full cap
    below the product line, so BASELINE_TOL never merges the two."""
    lines, cluster = [], []
    for m in sorted(marks, key=lambda m: m[2]):
        if cluster and m[2] - cluster[-1][2] > BASELINE_TOL:
            lines.append(cluster)
            cluster = []
        cluster.append(m)
    if cluster:
        lines.append(cluster)
    return lines


def _dotted(line):
    """(cap, digit before, digit after) for every `d.d` TOKEN on `line`.

    A period is a small near-square mark sitting ON the baseline — which is what
    separates it from a digit's counter, since every counter floats above the
    baseline. The baseline is the level MOST of the line's full-height marks sit
    on, not the lowest: a rotated neighbouring line (the pusher's detail string
    runs down the depth) drops one mark 0.15 mm below the rest, and the minimum
    would move the baseline out from under the period.

    The line is then split into WORDS on its spaces, and only a word of exactly
    `digit period digit` counts. That is what tells `CC 6.6` from a model code,
    which is nothing but digits around periods — `S5.15.15.62-Sl` offers three
    pairs and `M6.21.10.62-Sl` another three, and reading either as a version
    gives a confident wrong answer. A space measures over a quarter of the cap
    and letter spacing well under a tenth of it, on every string in the
    catalogue from the 0.535 mm version line on `Pusher 2x18-Sl` to the 5.484 mm
    model code on `Box S5.15.15.62-Sl`, so the two never have to be guessed at.

    Reading the version as a word is also what lets the box be read at all: its
    floor line carries a second word after the number, so a reader that wanted
    the line to be five marks and nothing else would skip every box."""
    rough = max(m[3] - m[2] for m in line)
    levels = {}
    for m in line:
        if m[3] - m[2] > 0.8 * rough:
            levels[round(m[2], 2)] = levels.get(round(m[2], 2), 0) + 1
    if not levels:
        return
    base = max(levels, key=lambda k: levels[k])
    on_base = sorted((m for m in line if abs(m[2] - base) <= 0.02),
                     key=lambda m: m[0])
    if not on_base:
        return
    cap = max(m[3] - m[2] for m in on_base)
    words, word = [], []
    for m in on_base:
        if word and m[0] - word[-1][1] > SPACE_PER_CAP * cap:
            words.append(word)
            word = []
        word.append(m)
    if word:
        words.append(word)
    for word in words:
        if len(word) != 3:
            continue
        a, dot, b = word
        w, h = dot[1] - dot[0], dot[3] - dot[2]
        if h > 0.35 * cap or abs(w - h) > 0.3 * max(w, h):
            continue
        if min(a[3] - a[2], b[3] - b[2]) < 0.8 * cap:
            continue
        yield cap, a, b


def _counter_class(glyph, cap, marks):
    """`none`, `low`, `tall`, `high` or `two` for a digit, from its counters.

    Counters arrive from the tessellation as one loop or as several overlapping
    ones — a `0` at 2.8 mm cap splits in two — so they are merged into spans
    along the cap axis first, and it is the count of DISJOINT spans that says
    whether the glyph is an 8."""
    inner = [m for m in marks if m != glyph
             and glyph[0] < m[0] and m[1] < glyph[1]
             and glyph[2] < m[2] and m[3] < glyph[3]]
    if not inner:
        return "none"
    spans = []
    for lo, hi in sorted((m[2], m[3]) for m in inner):
        if spans and lo <= spans[-1][1]:
            spans[-1][1] = max(spans[-1][1], hi)
        else:
            spans.append([lo, hi])
    if len(spans) > 1:
        return "two"
    lo, hi = spans[0]
    height, foot = (hi - lo) / cap, (lo - glyph[2]) / cap
    if height >= 0.45:
        return "tall"
    if height < 0.40 and foot < 0.30:
        return "low"
    if height < 0.40:
        return "high"
    return "?"


def version_stamp(data):
    """The version engraved on a component, e.g. `7.0`, or None if unreadable.

    A signature shared by several versions comes back as all of them, slash
    separated (`6.3/6.5`). Two DIFFERENT readings on one part come back as None
    rather than a guess — a model code carries periods too, and a wrong answer
    here is worse than no answer."""
    verts, tris = max(_meshes(data), key=lambda m: len(m[0]))
    thin = min((max(c) - min(c), a) for a, c in enumerate(zip(*verts)))[1]
    found = set()
    for axis in [thin] + [a for a in (2, 1, 0) if a != thin]:
        at = glyph_plane(verts, tris, axis)
        if at is None:
            continue
        marks = [l[:4] for l in _loops(_section(verts, tris, axis, at))
                 if MARK_MIN < l[1] - l[0] < MARK_MAX
                 and MARK_MIN < l[3] - l[2] < MARK_MAX]
        for oriented in _orientations(marks):
            for line in _lines(oriented):
                for cap, before, after in _dotted(line):
                    sig = (_counter_class(before, cap, oriented),
                           _counter_class(after, cap, oriented))
                    hits = frozenset(v for v, s in STAMP_SIGNATURES.items()
                                     if s == sig)
                    if hits:
                        found.add(hits)
        if found:
            break
    return "/".join(sorted(next(iter(found)))) if len(found) == 1 else None


def check_stamp(data, want):
    """(fatal message or None, warning or None) for a component that must be
    engraved `want`.

    Fatal on a POSITIVE mismatch — the bytes carry a version number that is not
    the one this cascade is being built at, and no later step can correct that;
    the part would print with a lie on it. Only a warning when the stamp cannot
    be read, so a reader that fails on some new layout never blocks an export
    that has already been paid for."""
    if want not in STAMP_SIGNATURES:
        return None, (f"no stamp signature is recorded for version {want!r}, "
                      f"so the engraved version was not checked — add it to "
                      f"verify.STAMP_SIGNATURES")
    got = version_stamp(data)
    if got is None:
        return None, "could not read the engraved version stamp"
    if want in got.split("/"):
        return None, None
    return (f"it is engraved CC {got} but is being built at {want}", None)


def check_pusher(data, ctx=None):
    """(None, warning message or None) for an exported Pusher.

    Never fatal. The two checks above refuse an export because the BYTES are
    wrong — the wrong component under the right name. This one says the bytes
    are right and the CAD is wrong, and refusing would only block work on
    everything else in the same assembly. It has to be acted on in Onshape.

    Reports the tab COUNT before tab support, because a pusher that lost a tab
    to the notch has perfect support on the one that is left."""
    try:
        tabs = pusher_tabs(data)
    except (ValueError, KeyError, ZeroDivisionError):
        return None, None            # not a shape this check understands
    who = f" for {ctx['model']}" if ctx and ctx.get("model") else ""
    tail = ("The plate is too narrow for where the CAD puts the second tab; "
            "fix it in Onshape (see PIPELINE.md, \"The pusher's second tab\")")

    wide = [t for t in tabs if t["w"] > TAB_W_NOMINAL + TAB_W_TOL]
    if len(tabs) != TABS_EXPECTED or wide:
        what = (f"only {len(tabs)} raised tab" + ("s" if len(tabs) != 1 else "")
                if len(tabs) != TABS_EXPECTED else
                f"{len(wide)} tab(s) {max(t['w'] for t in wide):.2f} mm wide "
                f"instead of {TAB_W_NOMINAL}")
        return None, (f"Pusher{who} has {what}, not {TABS_EXPECTED} of "
                      f"{TAB_W_NOMINAL} mm — the notch has swallowed or merged "
                      f"one of them. {tail}")

    loose = [t for t in tabs if t["fraction"] < 0.999]
    if not loose:
        return None, None
    worst = min(loose, key=lambda t: t["anchor"])
    how = ("has almost nothing holding it"
           if worst["anchor"] < TAB_ANCHOR_MIN else "overhangs the notch")
    return None, (
        f"Pusher{who}: {len(loose)} of {len(tabs)} raised tab(s) sit partly over "
        f"the end notch — the worst is {worst['fraction'] * 100:.0f}% backed "
        f"with {worst['anchor']:.2f} mm of root on a {worst['w']:.1f} mm tab, so "
        f"it {how}. {tail}")


# ---------------------------------------------------------------------------
# Rise height, and the invariant the holder key rests on
# ---------------------------------------------------------------------------
#
# A Pusher is cut as a staircase: one tread per riser, each dropping the plate's
# width by D/risers, and the tread LENGTH is how far that riser travels — the
# rise height. So rise is measurable off any pusher, exactly.
#
# The Holder key carries RISERS (see plan_exports.holder) because the holder is
# genuinely not invariant with riser count: the diagonal edge has to form one
# line across the open cascade, and rise is capped by box height, so more risers
# means a shallower diagonal. Riser count stands in for rise because it is the
# only one of the two available when the filename is computed — and because,
# measured over all 32 pushers, RISE IS A FUNCTION OF RISER COUNT WITHIN A GAME.
#
# That is an assumption about the CAD, not a fact about the world, so it is
# checked rather than trusted: `verify.py --rises` refuses if any (game, risers)
# pair ever yields two different rises. If that fires, the holder key needs a
# real rise axis and the stand-in has stopped working.


def pusher_rise(data, risers):
    """(rise, treads) for a Pusher: the distance one riser travels, and every
    tread length measured. `rise` is their mean — they agree exactly except
    where a fixed travel does not divide evenly (8 risers alternates
    10.923/10.827 about 10.875)."""
    verts, tris = max(_meshes(data), key=lambda m: len(m[0]))
    c = list(zip(*verts))
    zlo, zhi = min(c[2]), max(c[2])
    segs = _section(verts, tris, 2, zlo + 0.5 * (zhi - zlo))   # clear of tabs
    x0, x1 = min(c[0]), max(c[0])
    y0, y1 = min(c[1]), max(c[1])
    unit = (y1 - y0) / risers
    edges, last = [], None
    for j in range(900):
        x = x0 + (j + .5) * (x1 - x0) / 900
        ins = [y for y in (y0 + (k + .5) * (y1 - y0) / 300 for k in range(300))
               if _inside(segs, x, y)]
        w = (max(ins) - min(ins)) if ins else 0.0
        n = round(w / unit)
        if last is None:
            last = n
            continue
        if abs(w - n * unit) < 0.6:
            if n < last:
                edges.append(x - x0)
            last = n
    treads = [b - a for a, b in zip(edges, edges[1:])]
    return (sum(treads) / len(treads) if treads else None), treads


def audit_rises(root, tol=0.05):
    """Print rise height per pusher and check it is a function of riser count
    within each game. Returns the number of (game, risers) pairs that disagree."""
    from pathlib import Path
    root = Path(root)
    seen = {}
    print(f"    {'game':12s} {'pusher':20s} {'risers':>6s} {'rise':>9s}   treads")
    for path in sorted(root.glob("individual/*/Pusher*.3mf")):
        m = re.match(r"Pusher (\d+)x(\d+)-(Un|Sl)$", path.stem)
        if not m:
            continue
        risers = int(m.group(1))
        try:
            rise, treads = pusher_rise(path.read_bytes(), risers)
        except (ValueError, KeyError, ZeroDivisionError, IndexError):
            continue
        game = path.parent.name
        if rise is None:
            print(f"    {game:12s} {path.stem:20s} {risers:6d} {'--':>9s}   "
                  f"(one tread — rise not measurable)")
            continue
        print(f"    {game:12s} {path.stem:20s} {risers:6d} {rise:9.3f}   "
              + " ".join(f"{t:.3f}" for t in treads))
        seen.setdefault((game, risers), []).append((path.stem, rise))
    bad = 0
    for (game, risers), got in sorted(seen.items()):
        lo, hi = min(r for _n, r in got), max(r for _n, r in got)
        if hi - lo > tol:
            bad += 1
            print(f"\n  ✗ {game} at {risers} risers gives {lo:.3f}..{hi:.3f} — "
                  f"rise is NOT a function of riser count here, so the Holder "
                  f"key's riser axis no longer stands in for it: "
                  + ", ".join(f"{n} {r:.3f}" for n, r in got))
    print(f"\n  {len(seen)} (game, risers) pairs; {bad} inconsistent.")
    return bad


# ---------------------------------------------------------------------------
# How many pushers a box actually takes — read off the box, not off a table
# ---------------------------------------------------------------------------
#
# A box carries two rim cutouts per pusher, cut into the INNER back wall (the
# outer wall is uncut, which is why they are invisible from behind). So a
# section through the cutout band leaves the box's outline plus the back wall
# broken into pieces: 2N + 1 closed loops for N pusher slots, the two end pieces
# being part of the outline. Measured on all 48 boxes in individual/, every one
# reads a clean 5 or 7.
#
# `components.pushers_for` is the same fact written down by hand, and the two
# had drifted: Innovation's per-size map has no XS key, so Single Mini fell
# through to 3 against a box with 2 slots. This is the check that would have
# caught it, and that catches the next table to drift.

def box_pusher_slots(data):
    """How many pusher slots a Box 3MF has, from its rim cutouts."""
    verts, tris = max(_meshes(data), key=lambda m: len(m[0]))
    top = max(v[2] for v in verts)
    loops = _loops(_section(verts, tris, 2, top - 0.5))
    if len(loops) < 3 or len(loops) % 2 == 0:
        raise ValueError(f"box rim gives {len(loops)} loops, expected an odd "
                         f"2N+1; the section may have missed the cutout band")
    return (len(loops) - 1) // 2


def audit_box_slots(root):
    """Check every Box on disk against components.pushers_for. Returns the
    number that disagree."""
    import csv as _csv
    from pathlib import Path
    import components as C
    root = Path(root)
    # model code -> (game, size letter), from parts.csv
    rows = {}
    with open(root / "automation" / "parts.csv", newline="") as f:
        for r in _csv.DictReader(f):
            base = (r.get("Base model") or "").strip()
            size = ("XS" if base.startswith("XS") else base[0]) if base else "?"
            for col in ("Unsl Model", "Sleeved model"):
                m = (r.get(col) or "").strip().replace("/", "-")
                if m:
                    rows[m] = ((r.get("Game") or "").strip(), size)
    bad = seen = 0
    print(f"    {'box':40s} {'size':>4s} {'slots':>5s} {'table':>5s}")
    for path in sorted(root.glob("individual/*/Box*.3mf")):
        code = path.stem[len("Box "):].replace(" merged", "")
        got = rows.get(code)
        if not got:
            continue
        game, size = got
        _gname, spec = C.game_by_name(game)
        if not spec:
            continue
        want = C.pushers_for(spec, size)
        try:
            slots = box_pusher_slots(path.read_bytes())
        except (ValueError, KeyError, ZeroDivisionError, IndexError) as exc:
            print(f"    ?   {path.name:40s} {size:>4s}  {exc}")
            continue
        seen += 1
        mark = "ok " if slots == want else "✗  "
        bad += slots != want
        if slots != want:
            print(f"    {mark} {path.parent.name + '/' + path.stem:40s} "
                  f"{size:>4s} {slots:5d} {want:5d}   "
                  f"components.pushers_for disagrees with the box")
    print(f"\n  {seen} boxes checked; {bad} disagree with "
          f"components.pushers_for.")
    return bad


# ---------------------------------------------------------------------------
# CLI: audit every Pusher on disk
# ---------------------------------------------------------------------------

def audit_pushers(root, verbose=False):
    """Print a lock line for every exported Pusher under `root`, and return the
    number that carry a defective lock.

    individual/ only. A built cascade carries copies of these exact files (the
    2-3 pushers in a project are one component instanced), so walking cascades/
    as well only re-reports the same meshes under project names — and costs 20x
    the time to unpack them out of Studio's layout. Which projects a flagged
    pusher reaches follows from its dedup key: (risers, cards, sleeved)."""
    from pathlib import Path
    root = Path(root)
    rows = []
    for path in sorted(root.glob("individual/*/Pusher*.3mf")):
        try:
            tabs = pusher_tabs(path.read_bytes())
        except (ValueError, KeyError, ZeroDivisionError, IndexError):
            continue
        wide = [t for t in tabs if t["w"] > TAB_W_NOMINAL + TAB_W_TOL]
        loose = [t for t in tabs if t["fraction"] < 0.999]
        worst = min(loose, key=lambda t: t["anchor"]) if loose else None
        rows.append((path.relative_to(root), len(tabs), bool(wide), worst))
    # gone/merged tabs first, then by how little root is left
    rows.sort(key=lambda r: (r[1] == TABS_EXPECTED and not r[2],
                             r[3]["anchor"] if r[3] else 99.0, str(r[0])))
    bad = sunk = 0
    for name, ntabs, merged, worst in rows:
        if ntabs == TABS_EXPECTED and not merged and worst is None:
            if verbose:
                print(f"    ok  {'':>16s}  {name}")
            continue
        bad += 1
        if ntabs != TABS_EXPECTED or merged:
            sunk += 1
            note = f"{ntabs} tab" + ("s" if ntabs != 1 else "")
            note += ", merged" if merged else ""
            print(f"    ✗  {note:>24s}  {name}")
        else:
            sunk += worst["anchor"] < TAB_ANCHOR_MIN
            mark = "✗" if worst["anchor"] < TAB_ANCHOR_MIN else "⚠"
            status = (f"{worst['fraction'] * 100:.0f}% backed, "
                      f"{worst['anchor']:.2f}mm root")
            print(f"    {mark}  {status:>24s}  {name}")
    print(f"\n  {bad} of {len(rows)} pushers have a defective lock; {sunk} of "
          f"those have lost a tab or have under {TAB_ANCHOR_MIN} mm of root.")
    return bad


def audit_catalogue(root):
    """Print the per-pusher worksheet for the five-design catalogue: which class
    each pusher takes, where its features have to move to, and what that does to
    the hang base. A conformance test the day the CAD lands; a to-do list until
    then."""
    from pathlib import Path
    root = Path(root)
    print(f"    {'pusher':32s} {'D':>6s} {'cls':>4s} {'inset':>6s} "
          f"{'tabs, from the D=0 edge':>25s} {'notch':>13s} {'base':>6s} {'vs now':>7s}")
    tally = {}
    for path in sorted(root.glob("individual/*/Pusher*.3mf")):
        try:
            got = pusher_lock(path.read_bytes())
        except (ValueError, KeyError, ZeroDivisionError, IndexError):
            continue
        d = got["depth"]
        want = target_lock(d)
        if not want:
            print(f"    {path.stem:32s} {d:6.2f}   --   no design fits")
            continue
        tally[want["class"]] = tally.get(want["class"], 0) + 1
        tabs = " / ".join(f"{a:.2f}-{b:.2f}" for a, b in want["tabs"])
        notch = (f"{want['notch'][0]:.2f}-{want['notch'][1]:.2f}"
                 if want["notch"] else "none")
        # today's base is the separation of the two tab CENTRES, and the CAD
        # sets tab A 4.00 in from one edge and tab B 4.20 in from the other:
        # centres at 6.10 and D - 5.90, so D - 12.00. Confirmed against the old
        # boxes' rim-cutout pitch (11.400 at D 23.40, 6.000 at D 18.00).
        base, now = 2 * want["s"], d - 12.00
        print(f"    {path.stem:32s} {d:6.2f} {want['class']:>4s} "
              f"{d / 2 - want['s'] - TAB_W_NOMINAL / 2:6.2f} {tabs:>25s} {notch:>13s} "
              f"{base:6.2f} {base - now:+7.2f}")
    print("\n  " + "  ".join(f"{n}: {tally.get(n, 0)}" for n, _s in LOCK_CLASSES)
          + f"   ({sum(tally.values())} pushers)")


def audit_stamps(root, verbose=False):
    """Read the engraved version off every Box, Lid and Pusher on disk and
    compare it with the generation the cascades using it are built at. Returns
    the number that disagree.

    Only the lock trio: those are the three parts 7.0 moved, so a wrong stamp on
    one of them is what puts a pusher that cannot go into a lid in someone's
    hands. Holders and toppers carry the stamp too, but they carry over between
    generations, so their stamp is a record of when they were last exported
    rather than a claim about the cascade.

    A component shared by cascades at two different generations has no single
    right answer; plan_exports already reports that as a conflict, and this
    skips it rather than reporting it twice."""
    from pathlib import Path
    import components as C
    root = Path(root)
    bad = seen = unread = 0
    for game, spec in C.GAMES.items():
        import plan_exports as P
        plan = P.compute_plan(game, spec, str(root / "automation" / "parts.csv"),
                              False, frozenset())
        folder = spec["folder"]
        for u in plan.unique.values():
            if u["type"] not in STAMPED or len(u["generations"]) != 1:
                continue
            want = next(iter(u["generations"]))
            for f in sorted(u["files"]):
                path = root / "individual" / folder / f
                if not path.exists():
                    continue
                seen += 1
                fatal, warn = check_stamp(path.read_bytes(), want)
                if fatal:
                    bad += 1
                    print(f"    ✗  {folder}/{path.stem:42s} {fatal}")
                    for name in u["generations"][want]:
                        print(f"           used by {name}")
                elif warn:
                    unread += 1
                    print(f"    ?  {folder}/{path.stem:42s} {warn}")
                elif verbose:
                    print(f"    ok {folder}/{path.stem:42s} CC {want}")
    print(f"\n  {seen} boxes, lids and pushers checked; {bad} engraved with the "
          f"wrong version, {unread} unreadable.")
    return bad


if __name__ == "__main__":
    import argparse
    import sys
    from pathlib import Path

    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--pushers", action="store_true",
                    help="audit the lock on every Pusher in the repo")
    ap.add_argument("--all", action="store_true",
                    help="with --pushers or --stamps, list the passing ones too")
    ap.add_argument("--catalogue", action="store_true",
                    help="print the five-design lock catalogue worksheet")
    ap.add_argument("--boxes", action="store_true",
                    help="check each Box's rim cutouts against the pusher "
                         "count components.pushers_for computes for it")
    ap.add_argument("--stamps", action="store_true",
                    help="read the engraved CC version off every Box, Lid and "
                         "Pusher and check it against the generation its "
                         "cascades are built at")
    ap.add_argument("--rises", action="store_true",
                    help="print rise height per pusher and check it is a "
                         "function of riser count within each game — the "
                         "invariant the Holder key's riser axis rests on")
    args = ap.parse_args()
    root = Path(__file__).resolve().parent.parent
    if args.boxes:
        print("  Pusher slots per box, counted from its rim cutouts:")
        sys.exit(1 if audit_box_slots(root) else 0)
    if args.stamps:
        print("  Engraved version stamp per box, lid and pusher:")
        sys.exit(1 if audit_stamps(root, verbose=args.all) else 0)
    if args.rises:
        print("  Rise height per riser, read off each pusher's staircase:")
        sys.exit(1 if audit_rises(root) else 0)
    if args.catalogue:
        print("  Lock catalogue — where each pusher's features would move to:")
        audit_catalogue(root)
        sys.exit(0)
    if not args.pushers:
        ap.error("nothing to do — try --pushers, --boxes, --stamps, "
                 "--catalogue or --rises")
    print("  Pusher lock (tab count, backed fraction, widest backed strip):")
    sys.exit(1 if audit_pushers(root, verbose=args.all) else 0)
