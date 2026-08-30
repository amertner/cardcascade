"""Split ONE Onshape assembly export carrying all six Innovation toppers into
the six individual component 3MFs the pipeline consumes — so a whole topper set
costs ONE translation call instead of six.

Toppers were on the per-part-studio path (one export per Expansion configuration
value), which is 6 translate ops per (size, sleeving). An assembly holding all
six collapses that to 1. At ~3 calls per translate op that is 18 calls -> 3,
and toppers are the largest single consumer of the Onshape budget for Innovation.

WHY THIS NEEDS A SPLITTER AT ALL, unlike assembly_split.py: the monochrome
assembly names its parts after their component type ("Box", "Pusher", ...), so
that splitter maps object -> role BY NAME. A topper assembly cannot: every
instance is the same part studio at a different configuration, so all six carry
the SAME body names ("Topper" plus "Part 3".."Part 12"). What separates them is
the assembly component transform — the six instances are laid out in a row, so
grouping components by their translation recovers exactly six groups, one per
topper. Which group is which EXPANSION then has to come from the geometry.

## Identifying an expansion from its lettering

Each topper's embossed name is a set of separate solids (letters are not
contiguous, and 'i' contributes two). Two properties make them identifiable:

  - the SOLID COUNT is a property of the word: Echoes 6, Cities 8 (two dotted
    i's), Unseen 6, Artifacts 10, Figures 8, Blank 0;
  - each glyph's width as a FRACTION of the whole word's width is a property of
    the word and the font, and nothing else.

The second is what makes this robust, because it is scale-invariant. The 10-card
toppers set their text at 65% of the 15-card toppers' size (the text sits in the
topper's depth, which tracks CardsPerSlidingSlot), yet every fingerprint below
reproduces to 0.0000 across that change. Solid count alone is NOT enough — it
leaves {Echoes, Unseen} and {Cities, Figures} tied — so both are used: the count
narrows, the widths decide, and the result must be a clean bijection or this
module refuses rather than guessing (see identify()).

SIGNATURES was calibrated from the unsleeved 15-card studio exports, whose values
are identical for S and M. Regenerate with --calibrate over a directory of
KNOWN-GOOD per-expansion files; both paths strip the logo the same way, through
split_logo, so a calibration and a split always see the same inlays.

Makes NO API calls.
"""
import argparse
import io
import re
import sys
import zipfile
from collections import defaultdict
from pathlib import Path

MODEL = "3D/3dmodel.model"

# Normalised glyph widths per expansion — each entry is one embossed solid's
# x-extent divided by the whole word's x-extent, ordered left to right.
# Scale-invariant, so one table serves every size/sleeving/cards-per-slot.
SIGNATURES = {
    "Artifacts": [0.1697, 0.1105, 0.0824, 0.0720, 0.0387,
                  0.1051, 0.1182, 0.1004, 0.0824, 0.0948],
    "Cities":    [0.2090, 0.1160, 0.0623, 0.1328, 0.1160, 0.0623, 0.1758, 0.1527],
    "Echoes":    [0.1719, 0.1285, 0.1808, 0.1504, 0.1396, 0.1212],
    "Figures":   [0.1505, 0.0856, 0.0460, 0.1489, 0.1659, 0.1313, 0.1297, 0.1126],
    "Unseen":    [0.1949, 0.1693, 0.1140, 0.1314, 0.1314, 0.1693],
    "Blank":     [],
}

# A correct match measures 0.0000; the nearest wrong one with the same solid
# count measures 0.034 (Echoes vs Unseen). TOL sits an order of magnitude below
# that gap, and MARGIN insists the runner-up is genuinely worse.
TOL = 0.005
MARGIN = 0.010

# A topper's inlays are its LOGO followed by its expansion name, and only the
# name identifies the expansion — so the logo has to come off before
# fingerprinting. It is NOT separated by a gap threshold. The logo/name gap beats
# the widest gap inside a name by 8.5x on a 10-card Cities but only 2.6x on the
# 15-card Unseen, whose logo is six overlapping solids, so any single cutoff is a
# guess — and guessing wrong either keeps the logo or eats the first letter.
#
# Instead both readings are offered to identify() and SIGNATURES decides. That is
# a far sharper instrument: a correct match measures 0.0000 where the nearest
# wrong one measures 0.034, and no with-logo solid count collides with a name's
# (9, 11, 7, 9, 12 against 8, 10, 6, 8, 6), so a mis-split cannot match anything.

# Topper outer width, in mm per HorizontalSlot (measured: S=3 -> 201.0/207.0,
# M=4 -> 268.0/276.0). Used to derive the size class from the mesh.
WIDTH_PER_SLOT = {"Un": 67.0, "Sl": 69.0}
SIZE_BY_SLOTS = {2: "XS", 3: "S", 4: "M", 5: "L"}
# Topper depth = BASE + card thickness * CardsPerSlidingSlot. Measured against
# 8.00 (Un/15), 11.75 (Sl/15) and 6.00 (Un/10) — exact on all three.
DEPTH_BASE = 2.00
CARD_MM = {"Un": 0.40, "Sl": 0.65}
DIM_TOL = 0.15

_CONTENT_TYPES = (
    '<?xml version="1.0" encoding="UTF-8"?>\n'
    '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
    '<Default Extension="rels" ContentType="application/vnd.openxmlformats-'
    'package.relationships+xml"/><Default Extension="model" ContentType='
    '"application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/></Types>')
_RELS = (
    '<?xml version="1.0" encoding="UTF-8"?>\n'
    '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/'
    'relationships"><Relationship Target="/3D/3dmodel.model" Id="rel0" Type='
    '"http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/>'
    '</Relationships>')
_NS = ('xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02" '
       'xmlns:m="http://schemas.microsoft.com/3dmanufacturing/material/2015/02"')

_VERTEX = re.compile(r'<vertex x="([-\d.eE+]+)" y="([-\d.eE+]+)" z="([-\d.eE+]+)"')


class SplitError(Exception):
    """The assembly is not the six-topper set this module knows how to split."""


# ------------------------------------------------------------------ parsing
def _model_text(data):
    return zipfile.ZipFile(io.BytesIO(data)).read(MODEL).decode()


def _unit_scale(model):
    unit = (re.search(r'unit="(\w+)"', model) or [None, "meter"])[1] \
        if re.search(r'unit="(\w+)"', model) else "meter"
    scale = {"meter": 1000.0, "millimeter": 1.0}.get(unit)
    if scale is None:
        raise SplitError(f"unsupported unit {unit!r}")
    return unit, scale


def _palette(model):
    g = re.search(r'<m:colorgroup[^>]*>(.*?)</m:colorgroup>', model, re.S)
    return re.findall(r'color="([^"]+)"', g.group(1)) if g else []


def _parts(model):
    """{id: {name, mesh, pindex}} for every mesh-bearing object (skips the
    assembly container, which holds <components> rather than a <mesh>)."""
    out = {}
    for om in re.finditer(r'<object id="(\d+)"([^>]*)>(.*?)</object>', model, re.S):
        oid, attrs, body = om.groups()
        if "<components>" in body:
            continue
        mesh = re.search(r"<mesh>.*?</mesh>", body, re.S)
        if not mesh:
            continue
        name = re.search(r'name="([^"]*)"', attrs)
        pidx = re.search(r'pindex="(\d+)"', attrs)
        out[oid] = {"name": name.group(1) if name else "",
                    "mesh": mesh.group(0),
                    "pindex": int(pidx.group(1)) if pidx else None}
    return out


def _instances(model):
    """Group the assembly container's components by their translation.

    Every body of one topper shares one component transform (the instance's
    placement), so the distinct translations ARE the toppers. Returns a list of
    object-id lists, ordered by descending y — the row order in the assembly,
    which is reported for information only and never used to identify anything.
    """
    container = re.search(r'<object id="\d+"[^>]*>(?:(?!</object>).)*?'
                          r'<components>.*?</components>.*?</object>',
                          model, re.S)
    if not container:
        raise SplitError("no assembly container object with <components> — this "
                         "looks like a part-studio export, not an assembly")
    groups = defaultdict(list)
    for m in re.finditer(r'<component objectid="(\d+)"[^>]*transform="([^"]*)"',
                         container.group(0)):
        t = m.group(2).split()
        if [float(v) for v in t[:9]] != [1, 0, 0, 0, 1, 0, 0, 0, 1]:
            raise SplitError(f"component {m.group(1)} carries a ROTATION; this "
                             "splitter only handles translated instances")
        groups[tuple(round(float(v), 9) for v in t[9:12])].append(m.group(1))
    return [groups[k] for k in sorted(groups, key=lambda k: -k[1])]


# ------------------------------------------------------- geometry + matching
def _bbox_mm(mesh, scale):
    vs = [(float(a) * scale, float(b) * scale, float(c) * scale)
          for a, b, c in _VERTEX.findall(mesh)]
    xs, ys, zs = zip(*vs)
    return (min(xs), max(xs), min(ys), max(ys), min(zs), max(zs))


def widest_gap(spans):
    """Index of the span that starts after the widest horizontal gap, or None.

    Reach, not the previous span's end: a multi-solid logo's parts overlap in x
    (the 15-card Unseen's six do), and comparing against the running maximum is
    what stops one of those overlaps reading as the widest gap."""
    if len(spans) < 2:
        return None
    gaps, reach = [], spans[0][1]
    for i in range(1, len(spans)):
        gaps.append((spans[i][0] - reach, i))
        reach = max(reach, spans[i][1])
    widest, at = max(gaps)
    return at if widest > 0 else None


def _norm(spans):
    """Span widths as fractions of the run's total width."""
    if not spans:
        return []
    width = max(hi for _, hi in spans) - spans[0][0]
    return [(hi - lo) / width for lo, hi in spans]


def inlay_spans(bodies, scale):
    """One topper's inlay x-spans, sorted left to right. Excludes the plate."""
    base = [b for b in bodies if b["name"] == "Topper"]
    if len(base) != 1:
        raise SplitError(f"group has {len(base)} bodies named 'Topper', expected 1")
    return sorted(_bbox_mm(b["mesh"], scale)[:2]
                  for b in bodies if b["name"] != "Topper")


def signatures(bodies, scale):
    """Candidate name fingerprints for one topper: the inlays as they come, and
    again with a leading logo run removed at the widest gap. identify() picks."""
    spans = inlay_spans(bodies, scale)
    out = [_norm(spans)]
    at = widest_gap(spans)
    if at is not None and len(spans) - at >= 2:
        out.append(_norm(spans[at:]))
    return out


def signature(bodies, scale, strip_logo=True):
    """One fingerprint, for the calibrator: the name with its logo removed at the
    widest gap (strip_logo=False for exports that carry no logo)."""
    spans = inlay_spans(bodies, scale)
    at = widest_gap(spans) if strip_logo else None
    return _norm(spans[at:] if at is not None else spans)


def _distance(a, b):
    if len(a) != len(b):
        return None
    if not a:
        return 0.0
    return sum(abs(x - y) for x, y in zip(a, b)) / len(a)


def identify(cands, table=None):
    """{expansion: index into cands}, or raise. Refuses rather than guessing.

    `cands` is one list of candidate fingerprints per group (see signatures). A
    group is assigned only when exactly one expansion is within TOL across ALL
    its candidates and every other is at least MARGIN worse; the result must also
    be a bijection onto the table.
    """
    table = table or SIGNATURES
    chosen = {}
    for i, sigs in enumerate(cands):
        best = {}
        for s in sigs:
            for e, ref in table.items():
                d = _distance(s, ref)
                if d is not None and d < best.get(e, float("inf")):
                    best[e] = d
        scored = sorted((d, e) for e, d in best.items())
        if not scored:
            raise SplitError(
                f"group {i}: no expansion in the table matches any reading of "
                f"its {[len(s) for s in sigs]} inlay solid(s) "
                f"({ {e: len(r) for e, r in table.items()} })")
        best_d, best_e = scored[0]
        if best_d > TOL:
            raise SplitError(f"group {i}: closest expansion {best_e!r} is "
                             f"{best_d:.4f} away, over TOL={TOL}")
        if len(scored) > 1 and scored[1][0] - best_d < MARGIN:
            raise SplitError(
                f"group {i}: {best_e!r} ({best_d:.4f}) and {scored[1][1]!r} "
                f"({scored[1][0]:.4f}) are too close to tell apart")
        if best_e in chosen:
            raise SplitError(f"groups {chosen[best_e]} and {i} both identify as "
                             f"{best_e!r} — not a bijection")
        chosen[best_e] = i
    missing = set(table) - set(chosen)
    if missing:
        raise SplitError(f"no group matched {sorted(missing)}")
    return chosen


# ------------------------------------------------------------------ writing
def build_topper_3mf(unit, palette, bodies):
    """A multi-object 3MF in the same shape as a per-studio topper export:
    every body its own <object>, build items with NO transform (make_cascade's
    load_export refuses a component whose bodies are placed by transform), and
    the source palette carried over so the file still opens in colour."""
    used = sorted({b["pindex"] for b in bodies if b["pindex"] is not None})
    remap = {p: i for i, p in enumerate(used)}
    colours = "".join(f'<m:color color="{palette[p]}"/>' for p in used
                      if p < len(palette))
    colour_res = (f'  <m:colorgroup id="1">{colours}</m:colorgroup>\n'
                  if colours else "")
    objs, items = [], []
    for n, b in enumerate(bodies, start=2):
        pref = (f' pid="1" pindex="{remap[b["pindex"]]}"'
                if colours and b["pindex"] is not None else "")
        objs.append(f'  <object id="{n}" name="{b["name"]}" type="model"'
                    f'{pref}>\n   {b["mesh"]}\n  </object>\n')
        items.append(f'  <item objectid="{n}"/>\n')
    model = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        f'<model unit="{unit}" xml:lang="en-US" {_NS}>\n <resources>\n'
        f'{colour_res}{"".join(objs)} </resources>\n'
        f' <build>\n{"".join(items)} </build>\n</model>\n')
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", _CONTENT_TYPES)
        z.writestr("_rels/.rels", _RELS)
        z.writestr(MODEL, model)
    return buf.getvalue()


# -------------------------------------------------------------------- split
def split(assembly_bytes, sleeved=None, cards=None):
    """Return ({expansion: 3mf bytes}, info).

    Bodies are emitted UNTRANSFORMED: the assembly places each instance with a
    component translation, but the underlying meshes are already in the part
    studio's own frame — verified against the per-studio exports, whose Topper
    body occupies the identical x/z box. Dropping the translation therefore
    reproduces the studio convention exactly, and every body of one topper shares
    that translation, so relative geometry is untouched either way.

    `sleeved` ("Un"/"Sl") and `cards` (CardsPerSlidingSlot) are checked against
    the measured mesh when given — the guard that a re-run under the wrong
    Primary variable set cannot pass itself off as the set you asked for.
    """
    model = _model_text(assembly_bytes)
    unit, scale = _unit_scale(model)
    palette = _palette(model)
    parts = _parts(model)
    groups = _instances(model)
    if len(groups) != len(SIGNATURES):
        raise SplitError(f"assembly has {len(groups)} instance group(s), "
                         f"expected {len(SIGNATURES)}")

    bodies = [[parts[i] for i in g if i in parts] for g in groups]
    order = identify([signatures(b, scale) for b in bodies])

    plate = [b for b in bodies[0] if b["name"] == "Topper"][0]
    x0, x1, y0, y1, _, _ = _bbox_mm(plate["mesh"], scale)
    width, depth = x1 - x0, y1 - y0

    info = {"width": width, "depth": depth, "unit": unit,
            "sleeved": sleeved, "cards": cards, "size": None, "warnings": []}

    slv = sleeved
    if slv is None:                     # infer from depth if cards are known
        slv = next((s for s in CARD_MM
                    if cards and abs(DEPTH_BASE + CARD_MM[s] * cards - depth)
                    <= DIM_TOL), None)
    if slv:
        slots = width / WIDTH_PER_SLOT[slv]
        info["size"] = SIZE_BY_SLOTS.get(round(slots))
        if abs(slots - round(slots)) * WIDTH_PER_SLOT[slv] > DIM_TOL:
            info["warnings"].append(
                f"width {width:.2f} mm is not a whole number of "
                f"{WIDTH_PER_SLOT[slv]:g} mm slots ({slots:.3f})")
        if cards is not None:
            want = DEPTH_BASE + CARD_MM[slv] * cards
            if abs(depth - want) > DIM_TOL:
                raise SplitError(
                    f"topper depth is {depth:.2f} mm but {cards} {slv} cards "
                    f"imply {want:.2f} mm. This assembly was exported under a "
                    f"different Primary variable set than the one requested — "
                    f"nothing written.")
    else:
        info["warnings"].append("sleeving unknown — dimension checks skipped")

    return ({exp: build_topper_3mf(unit, palette, bodies[i])
             for exp, i in order.items()}, info)


# ---------------------------------------------------------------- calibrate
def calibrate(directory, pattern="Topper * *-Un.3mf", strip_logo=True):
    """Rebuild SIGNATURES from known-good per-expansion exports."""
    import mesh as M
    out = {}
    for p in sorted(Path(directory).glob(pattern)):
        exp = p.name.split()[1]
        model = _model_text(M.unwrap(p.read_bytes()))
        _, scale = _unit_scale(model)
        sig = signature(list(_parts(model).values()), scale, strip_logo)
        prev = out.get(exp)
        if prev and _distance(prev, sig) is None:
            raise SplitError(f"{exp}: inconsistent solid count across sizes")
        out[exp] = [round(v, 4) for v in sig]
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("assembly", help="the six-topper assembly 3MF")
    ap.add_argument("-o", "--out", help="directory to write the six components into")
    ap.add_argument("--sleeving", choices=["Un", "Sl"],
                    help="declared sleeving; checked against the mesh")
    ap.add_argument("--cards", type=int,
                    help="declared CardsPerSlidingSlot; checked against the mesh")
    ap.add_argument("--pattern", default="Topper {expansion} {size}{cards}-{sleeved}.3mf",
                    help="output filename template")
    ap.add_argument("--calibrate", metavar="DIR",
                    help="print a SIGNATURES table rebuilt from DIR, then exit")
    ap.add_argument("--no-logo", action="store_true",
                    help="with --calibrate: the files carry no logo body, so "
                         "take every inlay as part of the name")
    ap.add_argument("--dry-run", action="store_true",
                    help="identify and measure, but write nothing")
    args = ap.parse_args()

    sys.path.insert(0, str(Path(__file__).parent))
    import mesh as M

    if args.calibrate:
        for exp, sig in sorted(calibrate(args.calibrate,
                                        strip_logo=not args.no_logo).items()):
            print(f'    "{exp}": {sig},')
        return

    data = M.unwrap(Path(args.assembly).read_bytes())
    try:
        files, info = split(data, sleeved=args.sleeving, cards=args.cards)
    except SplitError as e:
        sys.exit(f"✗ {Path(args.assembly).name}: {e}")

    size = info["size"] or "?"
    print(f"{Path(args.assembly).name}: 6 toppers, "
          f"{info['width']:.2f} x {info['depth']:.2f} mm "
          f"(size {size}"
          + (f", {args.cards} cards" if args.cards else "")
          + (f", {info['sleeved']}" if info["sleeved"] else "") + ")")
    for w in info["warnings"]:
        print(f"  ⚠ {w}")

    if not args.out or args.dry_run:
        for exp in sorted(files):
            print(f"  · {exp}  ({len(files[exp]):,} bytes)")
        if not args.out:
            print("  (no --out given — nothing written)")
        return

    outdir = Path(args.out)
    outdir.mkdir(parents=True, exist_ok=True)
    for exp in sorted(files):
        name = args.pattern.format(expansion=exp, size=size,
                                   cards=args.cards if args.cards else "",
                                   sleeved=info["sleeved"] or "")
        (outdir / name).write_bytes(files[exp])
        print(f"  ✓ {name}  ({len(files[exp]):,} bytes)")
    print(f"wrote {len(files)} component(s) → {outdir}")


if __name__ == "__main__":
    main()
