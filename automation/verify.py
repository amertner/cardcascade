"""Post-export sanity checks for the exporter. ZERO API calls.

They all guard one failure mode: Onshape serving a CACHED translation
computed for the PREVIOUS parameter set — a valid 3MF of the WRONG
component, landing under the right filename and recorded as current.

  footprint  the Box's W x D against parts.csv W/D less WALL (those columns
             are the LID's outer size). Width is fatal; depth only WARNS, so
             passing D_TOL does NOT confirm a depth to better than a mm.
  lid        the Lid against the same columns DIRECTLY, 0.2 mm and fatal.
  pusher     two raised tabs on solid plate. The bytes are right and the CAD
             is wrong, so it only warns.
  stamp      a Box, Lid or Pusher must be ENGRAVED with the version its
             cascade is built at: a 7.0 pusher in a 6.6 lid misses the
             recesses by 5.6 mm.
  identity   a new export's mesh hash must not equal one recorded for a
             DIFFERENT component file, in ANY game.

LOCK_CLASSES / target_lock() hold the proposed five-design lock catalogue,
printed by `--catalogue`. export.py --skip-verify turns the checks off.
"""
import hashlib
import io
import re
import zipfile

import mesh

MODEL = "3D/3dmodel.model"

# parts.csv W/D less the mesh bbox: 2.00 of lid around the box plus rounding.
WALL = 2.05
W_TOL = 0.6        # fatal beyond this
D_TOL = 1.2        # warn beyond this (some parts.csv depths have drifted)

# A lid needs no wall constant, so it is checked far tighter — and on both axes.
L_TOL = 0.2        # fatal beyond this


def _model_text(data):
    return zipfile.ZipFile(io.BytesIO(mesh.unwrap(data))).read(MODEL).decode()


def mesh_sha(data):
    """Stable hash of a 3MF's geometry, independent of packaging: the <mesh>
    blocks only, whitespace-normalised, the file bytes not being
    reproducible."""
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
    """(fatal, warning) for a Box; silent when the row has no W/D."""
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
    """(fatal message or None, None) for an exported Lid. The parts.csv W/D
    columns measure the closed cascade, so the lid IS that figure — far
    tighter than check_box can manage (a lid measures its row to 0.12 mm over
    the 33 built cascades), and fatal on BOTH axes."""
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
    """'<Game>/<file>' of a recorded component with this geometry under
    another filename, or None. Cross-game on purpose."""
    for game, row in provenance_rows:
        if row.get("sha") == sha and row.get("file") != file:
            return f"{game}/{row['file']}"
    return None


# ---------------------------------------------------------------------------
# Pusher tab support — PIPELINE.md, "The pusher's second tab"
# ---------------------------------------------------------------------------
# Below D = 26.4 mm the end notch walks into tab B and leaves it cantilevered
# (0.19 mm of root at D = 19.2). MEASURED, not recomputed.

# Below this much continuous backing the tab has no root worth the name: the
# 32 pushers on disk anchor 0.19 / 0.98 / 1.01 at worst, then 2.31 and up.
TAB_ANCHOR_MIN = 2.0

# Every pusher carries exactly two tabs of this width. Fewer or fused is the
# same collision one stage on — and a support check alone then reports it
# clean.
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
    """Cross-section at `axis` = `at`; a closed mesh closes into loops."""
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
    """Widest continuous strip of the tab backed by plate."""
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
    """Per-tab support for a Pusher 3MF: [{'w', 'd', 'fraction', 'anchor'}],
    a correct tab reading 1.00 and 5.00 mm. Orientation-agnostic."""
    verts, tris = max(_meshes(data), key=lambda m: len(m[0]))
    spans = [(max(c) - min(c), a) for a, c in enumerate(zip(*verts))]
    axis = min(spans)[1]
    lo = min(v[axis] for v in verts)
    hi = max(v[axis] for v in verts)
    span = hi - lo

    def area(at):
        return sum((u1 - u0) * (w1 - w0)
                   for u0, u1, w0, w1, _ in _loops(_section(verts, tris, axis, at)))

    top = hi if area(hi - 0.2) < area(lo + 0.2) else lo
    sign = 1 if top == hi else -1
    tabs = _loops(_section(verts, tris, axis, top - sign * 0.2))
    # 3/4 down from the tab face: clear of the tabs and of the version string
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
# The five-design lock catalogue (proposed — PIPELINE.md, LOCK_STANDARD.md)
# ---------------------------------------------------------------------------
# A design is one number: s, the centreline-to-tab-centre distance. "Today's
# base" is D - 12.00, not D - 11.80: tab A sits 4.00 in from one edge, tab B
# 4.20 in from the other.
NOTCH_W = 5.40
EDGE_MIN = 2.00
LAND_MIN = 1.20
LOCK_CLASSES = [("C1", 3.10), ("C2", 5.10), ("C3", 8.50),
                ("C4", 13.50), ("C5", 24.00)]


def class_min_depth(s):
    return 2 * (s + TAB_W_NOMINAL / 2 + EDGE_MIN)

def lock_class(depth):
    """(name, s, has_notch) for a pusher of this depth, or None."""
    # 0.01 of slack: 18.00 arrives from the mesh as 17.99999.
    fits = [(n, s) for n, s in LOCK_CLASSES if class_min_depth(s) <= depth + 0.01]
    if not fits:
        return None
    name, s = max(fits, key=lambda c: c[1])
    return name, s, s >= TAB_W_NOMINAL / 2 + NOTCH_W / 2 + LAND_MIN


def target_lock(depth):
    """Where the catalogue puts a pusher's features, from the D = 0 plate
    edge: {'class', 's', 'tabs': [(lo, hi), (lo, hi)], 'notch'}."""
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
    """As-built lock geometry: {'depth', 'tabs', 'notch'}, every position from
    the D = 0 plate edge, so it compares with target_lock()."""
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
# `CC <version>` cut into every Box, Lid and Pusher is the only thing a person
# holding a printed part can read, and the 7.0 lock spans all three, so it is
# what stops a new pusher going into an old lid. Nothing checked it and it
# went wrong: 36 of 128 parts carry 7.0 geometry under a `CC 6.6` stamp
# (PIPELINE.md, "The engraved version is not the recorded version").
#
# Reading it is not OCR. The version is a WORD — `<digit> . <digit>` — and
# Orbitron Bold's digits are told apart by their COUNTERS: 6 one short, low;
# 0 one tall; 7 none; 4 one short, high; 8 two. A signature several versions
# share is reported as all of them, which costs nothing.
#
# From 7.1 the counters stop separating releases — `1` and `7` have none, so
# the whole 7.x family reads ("none", "none") — and no refinement helps, those
# glyphs differing in their strokes, not their holes. Hence `check_stamp` reads
# the METADATA too: the glyph is what a person reads off the plastic, the
# metadata names the build that wrote the file, and a disagreement is the file
# lying to itself. An ITERATION LETTER reads as its release does, a letter not
# being a counter — so `_dotted` must accept the trailing mark, or the version
# is not found on the line at all.
#
# 8.0 is the exception, and the reason the glyph is worth reading: `8` is the
# only digit with TWO counters and `0`'s is tall, so it reads ("two", "tall"),
# a pair no 7.x wears. It is the release that stopped fitting its predecessors
# (`cad/revisions.py`), and the one a person can name off the plastic.
STAMP_SIGNATURES = {
    "8.0": ("two", "tall"),
    "7.2g": ("none", "none"),
    "7.2f": ("none", "none"),
    "7.2e": ("none", "none"),
    "7.2d": ("none", "none"),
    "7.2c": ("none", "none"),
    "7.2b": ("none", "none"),
    "7.2a": ("none", "none"),
    "7.1d": ("none", "none"),
    "7.1c": ("none", "none"),
    "7.1b": ("none", "none"),
    "7.1a": ("none", "none"),
    "7.1": ("none", "none"),
    "7.0": ("none", "tall"),
    "6.6": ("low", "low"),
    "6.5": ("low", "none"),
    "6.4": ("low", "high"),
    "6.3": ("low", "none"),
}

# `CardCascade:Version` is what `cad.build` writes into every component;
# `Title` is where a PROJECT carries it. An Onshape export has neither.
META_VERSION_KEY = "CardCascade:Version"
# The trailing `[a-z]?` is the iteration letter (`v7.1a`): without it this
# witness reads nothing for the whole of an unreleased release.
META_TITLE_VERSION = re.compile(r"\bv(\d+(?:\.\d+)+[a-z]?)\b")

# The three parts the 7.0 lock spans. LOCK_STANDARD.md: "a pusher, a lid and
# a box must all come from the same version. Holders and toppers carry over."
STAMPED = ("Box", "Lid", "Pusher")

MARK_MIN, MARK_MAX = 0.05, 12.0    # a glyph is never outside this, in mm
SPACE_PER_CAP = 0.25               # a word gap, against letter spacing under 0.1
BASELINE_TOL = 0.15                # two lines sit a full cap apart, so this is safe
MAX_PLANES = 80                    # bound the plane scan on a 46k-triangle box
DOTS_PER_LINE = 50                 # progress dots before wrapping


def _slicer(verts, tris, axis, bins=256):
    """A `section(at)` that only visits the triangles crossing `at`: a few
    dozen in front of each query, not sixty thousand."""
    lo = min(v[axis] for v in verts)
    hi = max(v[axis] for v in verts)
    width = ((hi - lo) or 1.0) / bins
    buckets = [[] for _ in range(bins + 1)]
    for t in tris:
        zs = (verts[t[0]][axis], verts[t[1]][axis], verts[t[2]][axis])
        first = max(int((min(zs) - lo) / width), 0)
        last = min(int((max(zs) - lo) / width), bins)
        for k in range(first, last + 1):
            buckets[k].append(t)

    def section(at):
        k = int((at - lo) / width)
        return _section(verts, buckets[k], axis, at) if 0 <= k <= bins else []
    return section


def _axis_order(verts):
    """Which axis to look for text on first: every engraved string lies
    in a plane normal to Z, so Z, then the thinnest axis."""
    thin = min((max(c) - min(c), a) for a, c in enumerate(zip(*verts)))[1]
    order = []
    for a in (2, thin, 0, 1):
        if a not in order:
            order.append(a)
    return order


def _populated_planes(verts, axis, min_hits=40):
    """Midpoints between the mesh's populated planes along `axis`: a glyph is
    a slab between two real planes, so one of these always lands inside it."""
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
    """(plane, marks) for the section with the most glyph-sized loops: a
    pusher's text is 1.5 mm inside the bbox, not on the outer face."""
    section = _slicer(verts, tris, axis)
    best = (0, None, [])
    for at in _populated_planes(verts, axis):
        marks = [l[:4] for l in _loops(section(at))
                 if MARK_MIN < l[1] - l[0] < MARK_MAX
                 and MARK_MIN < l[3] - l[2] < MARK_MAX]
        if len(marks) > best[0]:
            best = (len(marks), at, marks)
    return best[1], best[2]


def _orientations(marks):
    """The same marks in each of the four in-plane orientations — Onshape runs
    some strings along the part's other axis. All four must be ROTATIONS: a
    transpose is a reflection and reads `7.0` as `0.7`."""
    yield marks
    yield [(-m[1], -m[0], -m[3], -m[2]) for m in marks]           # 180
    yield [(m[2], m[3], -m[1], -m[0]) for m in marks]             # +90
    yield [(-m[3], -m[2], m[0], m[1]) for m in marks]             # -90


def _lines(marks):
    """Marks grouped into lines by baseline; a version line sits a cap below
    the product line, so BASELINE_TOL never merges the two."""
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

    A period is a small near-square mark sitting ON the baseline, which is
    what separates it from a counter. The baseline is the level MOST of the
    line's full-height marks sit on, not the lowest, or a rotated neighbouring
    line would move it out from under the period.

    The line is split into WORDS on its spaces (over a quarter of the cap,
    against letter spacing under a tenth) and only a word of exactly
    `digit period digit` counts — which is what tells `CC 6.6` from a model
    code, itself nothing but digits around periods.

    A FOURTH mark is allowed at the END of the word, for the iteration letter,
    and only where the preceding word is the `CC`. Neither shape nor height
    can admit it: the merged Dominion codes trail the line as `M . U n`, which
    is `7 . 1 a` exactly, and Orbitron's lowercase straddles the digits at
    0.80 to 1.12 of a cap. The letter itself is not read — that is what the
    metadata is for."""
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
    def is_cc(word):
        """Is `word` the `CC` a stamp begins with? Two marks at the cap, the
        same width to a tenth."""
        if len(word) != 2:
            return False
        widths = [m[1] - m[0] for m in word]
        return (min(m[3] - m[2] for m in word) >= 0.8 * cap
                and abs(widths[0] - widths[1]) <= 0.1 * max(widths))

    for i, word in enumerate(words):
        if len(word) not in (3, 4):
            continue           # 4 = the iteration letter, e.g. `7.1a`
        if len(word) == 4 and not (i and is_cc(words[i - 1])):
            continue           # ... and only where the `CC` vouches for it
        a, dot, b = word[:3]
        w, h = dot[1] - dot[0], dot[3] - dot[2]
        if h > 0.35 * cap or abs(w - h) > 0.3 * max(w, h):
            continue
        if min(a[3] - a[2], b[3] - b[2]) < 0.8 * cap:
            continue
        yield cap, a, b


def _counter_class(glyph, cap, marks):
    """`none`, `low`, `tall`, `high` or `two` for a digit, from its counters.
    A counter can arrive as several overlapping loops, so they are merged
    first: the count of DISJOINT spans is what says an 8."""
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
    """The version engraved on a component, e.g. `7.0`, or None. A shared
    signature comes back as all of them (`6.3/6.5`); two DIFFERENT readings
    come back as None, not a guess."""
    verts, tris = max(_meshes(data), key=lambda m: len(m[0]))
    found = set()
    for axis in _axis_order(verts):
        at, marks = glyph_plane(verts, tris, axis)
        if at is None:
            continue
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


def version_metadata(data):
    """The release a 3MF states in its METADATA, or None:
    `CardCascade:Version`, then a project's `Title`. TEXT, so nothing can
    confuse it — and unreadable off a printed part, hence a second witness."""
    text = _model_text(data)
    m = re.search(rf'<metadata name="{re.escape(META_VERSION_KEY)}">'
                  r"([^<]*)</metadata>", text)
    if m and m.group(1).strip():
        return m.group(1).strip()
    m = re.search(r'<metadata name="Title">([^<]*)</metadata>', text)
    if m:
        t = META_TITLE_VERSION.search(m.group(1))
        if t:
            return t.group(1)
    return None


def check_stamp(data, want):
    """(fatal message or None, warning or None) for a component that must be
    engraved `want`.

    TWO witnesses: the GLYPH is what a person holding the plastic reads but
    cannot separate 7.1 from 7.2 (see STAMP_SIGNATURES); the METADATA names
    the release exactly. Fatal on a POSITIVE mismatch from either and when
    the two disagree; only a warning when NEITHER can be read, so a reader
    that fails on a new layout never blocks an export already paid for.
    """
    meta = version_metadata(data)
    if meta is not None and meta != want:
        return (f"its metadata says CC {meta} but it is being built at {want}",
                None)
    if want not in STAMP_SIGNATURES:
        # The metadata still stands on its own: a release with no signature
        # recorded is checkable the moment cad/ wrote the file.
        if meta == want:
            return None, None
        return None, (f"no stamp signature is recorded for version {want!r}, "
                      f"so the engraved version was not checked — add it to "
                      f"verify.STAMP_SIGNATURES")
    got = version_stamp(data)
    if got is None:
        if meta == want:
            return None, None      # the metadata answered; the glyph is silent
        return None, "could not read the engraved version stamp"
    if meta is not None and meta not in got.split("/"):
        return (f"it is engraved CC {got} but its metadata says CC {meta} — "
                f"the file disagrees with itself", None)
    if want in got.split("/"):
        return None, None
    return (f"it is engraved CC {got} but is being built at {want}", None)


def check_pusher(data, ctx=None):
    """(None, warning message or None) for an exported Pusher. Never fatal:
    the bytes are right and the CAD is wrong. Reports the tab COUNT first,
    a pusher that lost a tab having perfect support on the one left."""
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
# The tread LENGTH of a pusher's staircase is the rise height. The Holder key
# carries RISERS instead, that being the only one available when the filename
# is computed and rise being a function of it within a game — an assumption
# `--rises` checks rather than trusts.


def pusher_rise(data, risers):
    """(rise, treads) for a Pusher; `rise` is the treads' mean."""
    verts, tris = max(_meshes(data), key=lambda m: len(m[0]))
    c = list(zip(*verts))
    zlo, zhi = min(c[2]), max(c[2])
    segs = _section(verts, tris, 2, zlo + 0.5 * (zhi - zlo))   # clear of tabs
    x0, x1 = min(c[0]), max(c[0])
    y0, y1 = min(c[1]), max(c[1])
    # A step is a DISCONTINUITY in the plate's width: a riser face drops it by
    # a whole slider distance (4.800 at the least) between samples 0.1 apart.
    STEP = 2.0
    edges, last = [], None
    for j in range(900):
        x = x0 + (j + .5) * (x1 - x0) / 900
        ins = [y for y in (y0 + (k + .5) * (y1 - y0) / 300 for k in range(300))
               if _inside(segs, x, y)]
        w = (max(ins) - min(ins)) if ins else 0.0
        if last is not None and last - w > STEP:
            edges.append(x - x0)
        last = w
    treads = [b - a for a, b in zip(edges, edges[1:])]
    return (sum(treads) / len(treads) if treads else None), treads


def audit_rises(root, tol=0.05):
    """Rise height per pusher, checked to be a function of riser count within
    each game; returns the number of (game, risers) pairs that disagree."""
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
# Two rim cutouts per pusher in the INNER back wall, so a section through the
# band gives 2N + 1 loops for N slots. `components.pushers_for` is the same
# fact by hand, and the two had drifted — spec/BOX.md.

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
    """Every Box on disk against components.pushers_for; returns the number
    that disagree."""
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


def audit_pushers(root, verbose=False):
    """A lock line per exported Pusher under `root`; returns the number with a
    defective lock. individual/ only — cascades/ holds copies of these."""
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
    """The five-design catalogue's per-pusher worksheet: class, where the
    features move to, and the cost in hang base."""
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
        # today's base is the tab CENTRES' separation, 4.00 in from one edge
        # and 4.20 from the other, so D - 12.00
        base, now = 2 * want["s"], d - 12.00
        print(f"    {path.stem:32s} {d:6.2f} {want['class']:>4s} "
              f"{d / 2 - want['s'] - TAB_W_NOMINAL / 2:6.2f} {tabs:>25s} {notch:>13s} "
              f"{base:6.2f} {base - now:+7.2f}")
    print("\n  " + "  ".join(f"{n}: {tally.get(n, 0)}" for n, _s in LOCK_CLASSES)
          + f"   ({sum(tally.values())} pushers)")


def audit_stamps(root, verbose=False):
    """Read the engraved version off every Box, Lid and Pusher on disk and
    compare it with the generation its cascades are built at. Returns the
    number that disagree. Only the lock trio: a holder or a topper carries
    over between generations. A component shared by two generations is
    skipped — plan_exports reports that conflict already."""
    from pathlib import Path
    import components as C
    root = Path(root)
    bad = seen = unread = 0
    dotted = [0]                       # dots on the current line

    def tick():
        if dotted[0] == 0:                 # indent lazily, so a run that ends
            print("    ", end="", flush=True)   # on a finding leaves no stub
        print(".", end="", flush=True)
        dotted[0] += 1
        if dotted[0] == DOTS_PER_LINE:
            print(flush=True)
            dotted[0] = 0

    def report(*lines):
        if dotted[0]:
            print()
            dotted[0] = 0
        for line in lines:
            print(line)

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
                    report(f"    ✗  {folder}/{path.stem:42s} {fatal}",
                           *(f"           used by {name}"
                             for name in u["generations"][want]))
                elif warn:
                    unread += 1
                    report(f"    ?  {folder}/{path.stem:42s} {warn}")
                elif verbose:
                    report(f"    ok {folder}/{path.stem:42s} CC {want}")
                else:
                    tick()
    if dotted[0]:
        print()
    print(f"\n  {seen} boxes, lids and pushers checked; {bad} engraved with the "
          f"wrong version, {unread} unreadable.")
    return bad


def audit_tree(tree, want=None, verbose=False):
    """Both witnesses off every component in a cad BUILD tree, held to each
    other and to one release; returns the number that disagree. Stricter than
    `audit_stamps`: everything in a cad tree came from one `cad.build
    --version`. Run it before publishing. `want` defaults to what the tree's
    metadata states — a tree with two releases in it is the failure.
    """
    from pathlib import Path
    tree = Path(tree)
    # not a component of THIS release: sidecars, projects, published copies,
    # assemblies, and `v<version>/`
    def mine(f):
        parts = f.relative_to(tree).parts
        return not (any(x in (".stamps", "cascades", "dist", "assemblies",
                              "components") for x in parts)
                    or any(x[:1] == "v" and x[1:2].isdigit() for x in parts))

    files = sorted(f for f in tree.rglob("*.3mf") if mine(f))
    if not files:
        print(f"  no components under {tree} — build one first "
              f"(python -m cad.build --part all)")
        return 0
    stated = {}
    for f in files:
        stated.setdefault(version_metadata(f.read_bytes()), []).append(f)
    if want is None:
        named = {v: fs for v, fs in stated.items() if v is not None}
        if len(named) > 1:
            print(f"  {tree} holds more than one release: "
                  + ", ".join(f"{v} ({len(fs)} files)" for v, fs in sorted(named.items())))
            return sum(len(fs) for fs in named.values())
        if not named:
            print(f"  no component under {tree} states a release in its "
                  f"metadata — it was written before cad.build wrote one, so "
                  f"pass --version to say what to check against")
            return 0
        want = next(iter(named))
    print(f"  {len(files)} components under {tree}, against CC {want}")
    bad = unread = glyphed = 0
    for f in files:
        rel = f.relative_to(tree)
        data = f.read_bytes()
        # BOTH witnesses on the lock trio, which is what a wrong stamp costs
        # someone; the metadata alone on the rest, which carry over.
        if f.stem.split()[0] in STAMPED:
            fatal, warn = check_stamp(data, want)
            glyphed += 1
        else:
            meta = version_metadata(data)
            fatal = (None if meta == want else
                     f"its metadata says CC {meta} but the tree is CC {want}"
                     if meta else None)
            warn = None if meta else "states no release in its metadata"
        if fatal:
            bad += 1
            print(f"    ✗  {str(rel):52s} {fatal}")
        elif warn:
            unread += 1
            print(f"    ?  {str(rel):52s} {warn}")
        elif verbose:
            print(f"    ok {str(rel):52s} CC {want}")
    print(f"\n  {len(files)} components checked against CC {want} "
          f"({glyphed} of them by engraving as well as metadata); "
          f"{bad} disagree, {unread} unreadable.")
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
    ap.add_argument("--tree", metavar="DIR",
                    help="with --stamps, audit a cad BUILD tree instead of "
                         "individual/ (e.g. build, build/v7.0): every "
                         "component's metadata and engraving must agree with "
                         "each other and name one release")
    ap.add_argument("--version", metavar="V",
                    help="with --stamps --tree, the release to check against "
                         "(default: the one the tree's own metadata states)")
    ap.add_argument("--rises", action="store_true",
                    help="print rise height per pusher and check it is a "
                         "function of riser count within each game — the "
                         "invariant the Holder key's riser axis rests on")
    args = ap.parse_args()
    root = Path(__file__).resolve().parent.parent
    if args.boxes:
        print("  Pusher slots per box, counted from its rim cutouts:")
        sys.exit(1 if audit_box_slots(root) else 0)
    if args.stamps and args.tree:
        sys.exit(1 if audit_tree(args.tree, args.version, args.all) else 0)
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
