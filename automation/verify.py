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

  identity   a new export's mesh hash must not equal one already recorded for a
             DIFFERENT component file, in ANY game (the stale export usually
             comes from the previous run, which is usually a different game).
             Over the 168 components on disk the only such collisions were the
             three Compile files this bug poisoned: legitimate duplicates don't
             occur, because every export is keyed on the parameters that
             determine its geometry.

Both are cheap and local, so they run on every export by default; export.py
--skip-verify turns them off for the case where parts.csv is the thing that's
wrong.
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


def duplicate(sha, file, provenance_rows):
    """'<Game>/<file>' of an already-recorded component with this exact geometry
    under a DIFFERENT filename, or None. Cross-game on purpose."""
    for game, row in provenance_rows:
        if row.get("sha") == sha and row.get("file") != file:
            return f"{game}/{row['file']}"
    return None
