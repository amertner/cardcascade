"""Where each object goes: the plate scheme, the bed, the packing, the tower.

Lifted from `automation/make_cascade.py --auto-plates` so that a project can
be laid out without a donor, with the same rules and numbers.
`spec/PROJECT.md`, "What the writer does not decide", is the record.

    from cad import layout as LY, project as PJ
    bed, plates, placements = LY.layout(objects)     # objects: [project.Obj]
    PJ.write(out, bed, objects, plates, placements, title)

Decided here, in order: THE BED (`choose_bed`), THE PLATES (`plate_groups`),
THE PACKING (`pack_plate`), THE TOWER (`tower`). A plate with no room for its
tower is REFUSED.
"""
import json
import math
from typing import NamedTuple

from . import project as PJ
from .refuse import refuse


BED_MARGIN = 8.0      # bed-fit slack: an object's 45-degree span must clear this
STRIP_MARGIN = 4.0    # bed edge clearance for a 45-degree strip's bounding box
GAP = 12.0            # between objects on a plate
STRIP_GAP = 2.0       # between thin strips (holders, toppers): they pack tight
CLEARANCE = 1.0       # validation: least distance between objects
EDGE = 10.0           # grid-search margin from the bed edge, flat objects
GRID = 4.0            # grid-search step
ROT = math.pi / 4
WIPE_GAP = 15.0       # tower clearance from printed parts, preferred
TIGHT_GAP = 5.0       # tower clearance when nothing clears WIPE_GAP
TOWER_INSET = 4.0     # the tower keeps this far inside its rectangle's every edge
BIG = 20.0            # an object longer than bed - BIG is turned 45 degrees
THIN = 30.0           # a strip is thinner than this


class Group(NamedTuple):
    """One entry of the plate scheme: the plate's name and the roles on it.
    `alt` marks a group whose objects are ALTERNATIVES (`PLATE_SCHEME`)."""
    label: str
    roles: tuple
    alt: bool = False


# One plate per role group, in this order. Pushers ride with the Box.
#
# `alt` is the Lid's alone: a cascade ships several lids and its owner prints
# ONE, so they go one per plate. It cannot be read off the objects — every
# other group of several is copies of one part or a named set printed whole.
# Alternatives already separate stay separate by ROLE: TokenHolder and
# HalfTokenHolder, the 7.2d PlainBox (LAST, where an owner who wants the
# ordinary box never reaches it) and the 7.2g NotchedBox. NB `role` is a
# PREFIX match, so neither may start with `Box` nor with `Pusher`.
PLATE_SCHEME = [
    Group("Box + pushers", ("Box", "Pusher")),
    Group("Lid", ("Lid",), alt=True),
    Group("Holders", ("Holder", "FirstHolder", "RearHolder")),
    Group("Toppers", ("Topper",)),
    Group("Token holders", ("TokenHolder",)),
    Group("Half token holders", ("HalfTokenHolder",)),
    Group("Labels", ("Label",)),
    Group("Box without label holders", ("PlainBox",)),
    Group("Box with pusher notches", ("NotchedBox",)),
]
ROLES = ("HalfTokenHolder", "TokenHolder", "FirstHolder", "RearHolder", "PlainBox",
         "NotchedBox", "Box", "Lid", "Holder", "Topper", "Pusher", "Label")


def role(name):
    for r in ROLES:
        if name.startswith(r):
            return r
    return "Other"


class Obb(NamedTuple):
    """A placed footprint: centre, half sizes on its own axes, turn about Z."""
    cx: float
    cy: float
    hx: float
    hy: float
    theta: float

    def moved(self, dx, dy):
        return self._replace(cx=self.cx + dx, cy=self.cy + dy)


def _proj(o, ax):
    """The interval an oriented box covers along the unit axis `ax`."""
    c, s = math.cos(o.theta), math.sin(o.theta)
    mid = o.cx * ax[0] + o.cy * ax[1]
    r = o.hx * abs(c * ax[0] + s * ax[1]) + o.hy * abs(-s * ax[0] + c * ax[1])
    return mid - r, mid + r


def sat_overlap(a, b, gap=0.0):
    """Do two oriented boxes come within `gap` of each other?"""
    for o in (a, b):
        c, s = math.cos(o.theta), math.sin(o.theta)
        for ax in ((c, s), (-s, c)):
            a0, a1 = _proj(a, ax)
            b0, b1 = _proj(b, ax)
            if a1 + gap <= b0 or b1 + gap <= a0:
                return False
    return True


def rect_obb(x0, y0, x1, y1):
    return Obb((x0 + x1) / 2, (y0 + y1) / 2, (x1 - x0) / 2, (y1 - y0) / 2, 0.0)


def obb_aabb(o):
    c, s = math.cos(o.theta), math.sin(o.theta)   # -> (x0, y0, x1, y1)
    rx = o.hx * abs(c) + o.hy * abs(s)
    ry = o.hx * abs(s) + o.hy * abs(c)
    return o.cx - rx, o.cy - ry, o.cx + rx, o.cy + ry


# --- 45-degree strips ---------------------------------------------------------
# A w x d strip turned 45 degrees has a SQUARE bounding box of side
# (w+d)/sqrt2, so its centre stays inside a square inset from the bed by half
# of that; a step of (d + gap)*sqrt2 along a bed axis moves it exactly
# (d + gap) across its own width, the separation neighbours need.


def strip_inset(w, d):
    return (w + d) / (2 * math.sqrt(2))


def strip_arm(bed, longest, depth, gap):
    side = bed - 2 * STRIP_MARGIN - 2 * strip_inset(longest, depth)
    if side < 0:
        return 0
    return int(side / ((depth + gap) * math.sqrt(2))) + 1


def strip_arms(bed, longest, depth, gap):
    return max(1, 2 * strip_arm(bed, longest, depth, gap) - 1)   # two arms


def strip_band(bed, longest, depth, gap):
    """How many strips fit ONE plate as a single centred diagonal band: they
    share a position along their length and are separated only across it."""
    half = (bed - 2 * STRIP_MARGIN) / math.sqrt(2) \
        - strip_inset(longest, depth) * math.sqrt(2)
    if half < 0:
        return 1
    return int(2 * half / (depth + gap)) + 1


def strip_capacity(bed, longest, depth, gap):
    """How many strips fit ONE plate, whichever arrangement holds more: an arm
    advances by (depth+gap)*sqrt2, so once a strip is thick relative to the
    bed the band holds more."""
    return max(strip_arms(bed, longest, depth, gap),
               strip_band(bed, longest, depth, gap))


def profile(bed):
    return json.loads((PJ.PROFILES / f"{PJ.BEDS[bed].profile}.config").read_text())


def usable(bed, ps):
    """(width, depth) an object may occupy on `bed`: the bed, unless the
    printer declares per-extruder areas and the profile maps every filament to
    extruder 1 — the H2C, where it is 325 of the 330. Studio holds an object
    to the reach of the extruder that prints it."""
    areas = ps.get("extruder_printable_area") or []
    if areas and all(str(m) == "1" for m in ps.get("filament_map", [])):
        pts = [tuple(map(float, q.split("x"))) for q in areas[0].split(",")]
        return max(x for x, _y in pts), max(y for _x, y in pts)
    return PJ.BEDS[bed].size


def fit_angle(w, d, uw, ud):
    """(angle in degrees, slack) that fits a w x d footprint into uw x ud with
    the most room to spare, searched between 30 and 60 degrees — for the
    object whose 45-degree span does not fit. Negative slack: no angle fits."""
    best = None
    a = 30.0
    while a <= 60.0 + 1e-9:
        th = math.radians(a)
        ex = w * abs(math.cos(th)) + d * abs(math.sin(th))
        ey = w * abs(math.sin(th)) + d * abs(math.cos(th))
        slack = min(uw - ex, ud - ey)
        if best is None or slack > best[1]:
            best = (a, slack)
        a += 0.25
    return best


def fits(bed, objects, relaxed=False, ps=None):
    """Does every object clear this bed once turned 45 degrees, with
    BED_MARGIN to spare? `relaxed` also accepts an object that fits at SOME
    angle with whatever margin is left — for a bed the row forces, never for
    the ladder's own choice (PIPELINE.md, "The Mini bed class")."""
    bw, bd = PJ.BEDS[bed].size
    m = min(bw, bd) - BED_MARGIN
    uw, ud = usable(bed, ps or profile(bed)) if relaxed else (None, None)
    for o in objects:
        w, d = o.size[0], o.size[1]
        if (w + d) / math.sqrt(2) <= m:
            continue
        if not relaxed or fit_angle(w, d, uw, ud)[1] < 0:
            return False
    return True


def choose_bed(objects, forced=None):
    """The smallest bed every object fits by the rule proper; failing every
    bed, the smallest it fits relaxed; or `forced` — the row's `3D printer`
    column — which need only fit relaxed and is refused otherwise."""
    if forced:
        if forced not in PJ.BEDS:
            refuse(f"unknown bed {forced!r}; one of {sorted(PJ.BEDS)}")
        if not fits(forced, objects, relaxed=True):
            refuse(f"the forced bed {forced} does not fit every part at any angle")
        return forced
    for bed in PJ.BEDS:                    # smallest first
        if fits(bed, objects):
            return bed
    for bed in PJ.BEDS:
        if fits(bed, objects, relaxed=True):
            return bed
    refuse("no candidate bed fits every part at any angle between 30 and 60 deg")


def _dims(obj):
    return obj.size[0], obj.size[1]


def _gap(obj):
    return STRIP_GAP if role(obj.name) in ("Holder", "FirstHolder", "RearHolder", "Topper") else GAP


def plate_groups(objects, bed):
    """[(plate name, [object indices])] in PLATE_SCHEME order, empty groups
    skipped."""
    bw, bd = PJ.BEDS[bed].size
    side = min(bw, bd)
    groups = []
    for label, roles, alt in PLATE_SCHEME:
        idxs = [i for i, o in enumerate(objects) if role(o.name) in roles]
        if not idxs:
            continue
        # ALTERNATIVES, not a set: a plate each, named by the object. One
        # object is the ordinary case and keeps the scheme's own label.
        names = list(dict.fromkeys(objects[i].name for i in idxs))
        if alt and len(names) > 1:
            for name in names:
                groups.append((name, [i for i in idxs if objects[i].name == name]))
            continue
        # A big object that must rotate fills its plate diagonally and leaves
        # no room for flat companions: give them their own plate.
        rot = [i for i in idxs if max(_dims(objects[i])) > side - BIG]
        flat = [i for i in idxs if i not in rot]
        if rot and flat:
            groups.append((role(objects[rot[0]].name), rot))
            groups.append((role(objects[flat[0]].name) + "s", flat))
            continue
        longest = max(max(_dims(objects[i])) for i in idxs)
        depth = max(min(_dims(objects[i])) for i in idxs)
        thin = depth < THIN and all(max(_dims(objects[i])) > side - BIG for i in idxs)
        per = strip_capacity(side, longest, depth, _gap(objects[idxs[0]])) \
            if thin and len(idxs) > 1 else len(idxs)
        if per >= len(idxs):
            groups.append((label, idxs))
        else:
            chunks = [idxs[k:k + per] for k in range(0, len(idxs), per)]
            for k, ch in enumerate(chunks, 1):
                groups.append((f"{label} {k} of {len(chunks)}", ch))
    return groups


def pack_plate(objects, idxs, bed, exclude, turn=False, ps=None):
    """[(index, Obb)] in plate coordinates for the objects `idxs` on one plate
    of `bed`. `exclude` is the bed's exclude area as an Obb; `turn` packs
    everything a quarter turn round, the fallback when the tower has nowhere
    to go. Nothing here VALIDATES: the caller runs `misfit`."""
    bw, bd = PJ.BEDS[bed].size
    uw, ud = usable(bed, ps or profile(bed))
    quarter = math.pi / 2 if turn else 0.0
    dims = {i: (_dims(objects[i])[::-1] if turn else _dims(objects[i])) for i in idxs}
    rot_ids = [i for i in idxs if max(dims[i]) > min(bw, bd) - BIG]
    diagonal = _whole_diagonal(objects, idxs, dims, rot_ids, uw, ud, bw, bd)
    if diagonal:
        i, angle = diagonal
        w, d = dims[i]
        # centred in the USABLE area
        placed = [(i, Obb(uw / 2, ud / 2, w / 2, d / 2, math.radians(angle) + quarter))]
    elif rot_ids:
        placed = _strips(objects, rot_ids, dims, bw, bd, quarter)
        flat = sorted((i for i in idxs if i not in rot_ids),
                      key=lambda i: -dims[i][0] * dims[i][1])
        for i in flat:
            placed.append((i, _corner_spot(objects[i], dims[i], bw, bd, quarter,
                                           exclude, placed)))
    else:
        placed = _shelves(objects, idxs, dims, bw, bd, quarter)
    return _nudged_off(placed, exclude, bw)


def _whole_diagonal(objects, idxs, dims, rot_ids, uw, ud, bw, bd):
    """(index, angle) of the one object whose 45-degree span does not fit the
    usable area and so takes the angle that does (`fit_angle`) — ALONE on its
    plate, the strip packing assuming 45 degrees; or None. Refuses one that
    fits at no angle, two such, or one with company."""
    tight = {}
    for i in rot_ids:
        if sum(dims[i]) / math.sqrt(2) > min(uw, ud) - STRIP_MARGIN:
            angle, slack = fit_angle(dims[i][0], dims[i][1], uw, ud)
            if slack < 0:
                refuse(f"{objects[i].name} cannot fit the {bw:g}x{bd:g} bed at any "
                       f"angle between 30 and 60 degrees ({-slack:.1f} mm over)")
            tight[i] = angle
    if not tight:
        return None
    if len(tight) > 1 or len(rot_ids) > 1:
        refuse(f"{[objects[i].name for i in rot_ids]}: more than one object on the "
               f"plate needs the bed's whole diagonal")
    (i, angle), = tight.items()
    company = [objects[j].name for j in idxs if j != i]
    if company:
        refuse(f"{objects[i].name} takes its plate's whole diagonal; "
               f"{company} cannot share it")
    return i, angle


def _strips(objects, rot_ids, dims, bw, bd, quarter):
    """[(index, Obb)] for the thin strips, at 45 degrees along two bed edges
    from a shared corner, or in the centred band when the arms cannot hold
    them. Positions are relative to a local origin and centred afterwards."""
    side = min(bw, bd)
    sr = sorted(rot_ids, key=lambda i: -dims[i][1])
    longest = max(max(dims[i]) for i in sr)
    deep = max(min(dims[i]) for i in sr)
    gap = _gap(objects[sr[0]])

    def pitch(prev_d, i):
        """Centre-to-centre separation neighbours need ACROSS their width."""
        return prev_d / 2 + _gap(objects[i]) + dims[i][1] / 2

    rel, prev = {}, None
    if strip_arms(side, longest, deep, gap) >= len(sr):
        arm, cy = strip_arm(side, longest, deep, gap), 0.0
        for i in sr[:arm]:
            if prev is not None:
                cy -= pitch(prev, i) * math.sqrt(2)
            rel[i] = (0.0, cy)
            prev = dims[i][1]
        cx, prev = 0.0, dims[sr[0]][1]
        for i in sr[arm:]:
            cx -= pitch(prev, i) * math.sqrt(2)
            rel[i] = (cx, 0.0)
            prev = dims[i][1]
    else:
        n_hat, cn = (-1 / math.sqrt(2), 1 / math.sqrt(2)), 0.0
        for i in sr:
            if prev is not None:
                cn += pitch(prev, i)
            rel[i] = (n_hat[0] * cn, n_hat[1] * cn)
            prev = dims[i][1]
    ins = {i: strip_inset(*dims[i]) for i in sr}
    dx = bw / 2 - (min(rel[i][0] - ins[i] for i in sr)
                   + max(rel[i][0] + ins[i] for i in sr)) / 2
    dy = bd / 2 - (min(rel[i][1] - ins[i] for i in sr)
                   + max(rel[i][1] + ins[i] for i in sr)) / 2
    return [(i, Obb(rel[i][0] + dx, rel[i][1] + dy, dims[i][0] / 2, dims[i][1] / 2,
                    ROT + quarter))
            for i in sr]


def _corner_spot(obj, dims_i, bw, bd, quarter, exclude, placed):
    """Where a flat object goes on a plate of strips: grid-searched from the
    top-left corner to the first spot GAP clear of everything."""
    w, d = dims_i
    cy = bd - EDGE - d / 2
    while cy >= EDGE + d / 2:
        cx = EDGE + w / 2
        while cx <= bw - EDGE - w / 2:
            cand = Obb(cx, cy, w / 2, d / 2, quarter)
            if not (exclude and sat_overlap(cand, exclude, GAP)) \
               and not any(sat_overlap(cand, ob, GAP) for _, ob in placed):
                return cand
            cx += GRID
        cy -= GRID
    refuse(f"no room left for {obj.name}")


def _shelves(objects, idxs, dims, bw, bd, quarter):
    """[(index, Obb)] for a plate with nothing to rotate: centred shelf rows,
    widest first."""
    order = sorted(idxs, key=lambda i: -dims[i][0] * dims[i][1])
    rows, cur, cur_w = [], [], 0.0
    for i in order:
        w = dims[i][0]
        if cur and cur_w + GAP + w > bw - 2 * EDGE:
            rows.append(cur)
            cur, cur_w = [], 0.0
        cur.append(i)
        cur_w += (GAP if cur_w else 0.0) + w
    if cur:
        rows.append(cur)

    def row_gap_role(row):
        rs = {role(objects[i].name) for i in row}
        r = rs.pop() if len(rs) == 1 else None
        return r if r in ("Holder", "FirstHolder", "RearHolder", "Topper") else None

    # the tight gap between rows only when BOTH rows are the same strip
    # kind (topper to topper), else GAP
    rgaps = [STRIP_GAP if row_gap_role(a) and row_gap_role(a) == row_gap_role(b) else GAP
             for a, b in zip(rows, rows[1:])]
    depths = [max(dims[i][1] for i in r) for r in rows]
    y0 = (bd - (sum(depths) + sum(rgaps))) / 2
    placed = []
    for j, (row, depth) in enumerate(zip(rows, depths)):
        widths = [dims[i][0] for i in row]
        x0 = (bw - (sum(widths) + GAP * (len(row) - 1))) / 2
        for i, w in zip(row, widths):
            placed.append((i, Obb(x0 + w / 2, y0 + depth / 2, w / 2, dims[i][1] / 2, quarter)))
            x0 += w + GAP
        y0 += depth + (rgaps[j] if j < len(rgaps) else 0.0)
    return placed


def _nudged_off(placed, exclude, bw):
    """The plate shifted in x off a corner exclude area if centring clipped it
    — by just enough, and only if everything stays on the bed."""
    if not (exclude and placed):
        return placed
    ex_x0, ex_y0, ex_x1, ex_y1 = obb_aabb(exclude)
    min_x0 = min(obb_aabb(ob)[0] for _, ob in placed)
    max_x1 = max(obb_aabb(ob)[2] for _, ob in placed)
    left = (ex_x0 + ex_x1) / 2 < bw / 2
    dx = 0.0
    for _, ob in placed:
        x0, y0, x1, y1 = obb_aabb(ob)
        if y0 >= ex_y1 + CLEARANCE or y1 <= ex_y0 - CLEARANCE:
            continue
        if left and x0 < ex_x1 + CLEARANCE and x1 > ex_x0:
            dx = max(dx, ex_x1 + CLEARANCE - x0 + 0.5)
        elif not left and x1 > ex_x0 - CLEARANCE and x0 < ex_x1:
            dx = min(dx, ex_x0 - CLEARANCE - x1 - 0.5)
    if dx and 0 <= min_x0 + dx and max_x1 + dx <= bw:
        return [(i, ob.moved(dx, 0.0)) for i, ob in placed]
    return placed


def misfit(objects, placed, bed, exclude):
    """Why this plate is not legal — the first placed object off the bed, in
    the exclude area or within CLEARANCE of a neighbour — or None."""
    bw, bd = PJ.BEDS[bed].size
    for k, (i, ob) in enumerate(placed):
        x0, y0, x1, y1 = obb_aabb(ob)
        if x0 < -1e-6 or y0 < -1e-6 or x1 > bw + 1e-6 or y1 > bd + 1e-6:
            return (f"{objects[i].name} does not fit the bed "
                    f"({x0:.1f},{y0:.1f})-({x1:.1f},{y1:.1f})")
        if exclude and sat_overlap(ob, exclude, CLEARANCE):
            return f"{objects[i].name} enters the bed's exclude area"
        for j, ob2 in placed[:k]:
            if sat_overlap(ob, ob2, CLEARANCE):
                return f"{objects[i].name} overlaps {objects[j].name}"
    return None


def shifted(placed, dx, dy):
    return [(i, ob.moved(dx, dy)) for i, ob in placed]


def slides(placed, bed, exclude):
    """Where a plate's contents can be slid to open a corner for the tower:
    unmoved first, then hard against each of the four edges."""
    bw, bd = PJ.BEDS[bed].size
    x0 = min(obb_aabb(ob)[0] for _, ob in placed)
    y0 = min(obb_aabb(ob)[1] for _, ob in placed)
    x1 = max(obb_aabb(ob)[2] for _, ob in placed)
    y1 = max(obb_aabb(ob)[3] for _, ob in placed)
    ex_x1 = ex_y1 = 0.0
    if exclude:
        _a, _b, ex_x1, ex_y1 = obb_aabb(exclude)
    yield 0.0, 0.0
    for dx, dy in ((0.0, bd - y1), (0.0, -y0), (bw - x1, 0.0), (-x0, 0.0)):
        if abs(dx) < 1e-6 and abs(dy) < 1e-6:
            continue
        yield dx, dy
    # ... and off the exclude area's corner rather than the bed's, when
    # sliding to the bottom or the left would otherwise land in it
    if exclude:
        yield 0.0, ex_y1 + CLEARANCE - y0
        yield ex_x1 + CLEARANCE - x0, 0.0


def tower_bounds(ps):
    """The rectangle a prime tower must lie inside: the INTERSECTION of every
    extruder's printable area, NOT the bed. The H2C declares extruder 1 over
    x 0..325 and extruder 2 over 25..330 and every filament purges into the
    tower, so one legal for one nozzle can be unreachable for the other — and
    Studio notices only after slicing, which MakerWorld does on upload."""
    boxes = []
    for spec in ps.get("extruder_printable_area") or []:
        pts = [tuple(map(float, p.split("x"))) for p in spec.split(",")]
        boxes.append((min(p[0] for p in pts), min(p[1] for p in pts),
                      max(p[0] for p in pts), max(p[1] for p in pts)))
    if not boxes:
        pts = [tuple(map(float, p.split("x"))) for p in ps["printable_area"]]
        boxes.append((min(p[0] for p in pts), min(p[1] for p in pts),
                      max(p[0] for p in pts), max(p[1] for p in pts)))
    return (max(b[0] for b in boxes), max(b[1] for b in boxes),
            min(b[2] for b in boxes), min(b[3] for b in boxes))


def start_spot(bed):
    """The tower's PREFERRED position on `bed`: inset from the near-left
    corner, high up the plate, where every shipped project has put it. DERIVED
    from the bed's depth, NEVER a constant — a constant written for the P1 was
    off the end of the A1 mini and Studio refused to slice the result
    (`spec/PROJECT.md`, "What the writer does not decide", point 4)."""
    return (15.0, PJ.BEDS[bed].depth - 56.0)


def tower(ps, bed, placed, exclude, start=None):
    """Where the plate's prime tower goes: `start_spot` if it is legal and
    clear, else the legal spot furthest from the bed's centre that clears the
    parts by WIPE_GAP, else by TIGHT_GAP — or None when no spot clears.

    Legal is TOWER_INSET inside `tower_bounds`, on EVERY side: a tower's
    `(x, y)` is its origin corner and Studio's geometry spills below and left
    of it, so one flush to the near edges will not slice (`spec/PROJECT.md`,
    point 4)."""
    start = start or start_spot(bed)
    bw, bd = PJ.BEDS[bed].size
    w = float(ps.get("prime_tower_width", 35))
    tx0, ty0, tx1, ty1 = tower_bounds(ps)
    tx0, ty0, tx1, ty1 = (tx0 + TOWER_INSET, ty0 + TOWER_INSET,
                          tx1 - TOWER_INSET, ty1 - TOWER_INSET)

    def free(x, y, gap):
        if x < tx0 or y < ty0 or x + w > tx1 or y + w > ty1:
            return False
        t = rect_obb(x, y, x + w, y + w)
        if exclude and sat_overlap(t, exclude, gap):
            return False
        return not any(sat_overlap(t, ob, gap) for _, ob in placed)

    if free(start[0], start[1], WIPE_GAP):
        return start
    for gap in (WIPE_GAP, TIGHT_GAP):
        best = None
        gy = ty0
        while gy + w <= ty1:
            gx = tx0
            while gx + w <= tx1:
                if free(gx, gy, gap):
                    d2 = (gx + w / 2 - bw / 2) ** 2 + (gy + w / 2 - bd / 2) ** 2
                    if best is None or d2 > best[0]:
                        best = (d2, gx, gy)
                gx += GRID
            gy += GRID
        if best is not None:
            return best[1], best[2]
    return None


def layout(objects, bed=None):
    bed = choose_bed(objects, bed)
    ps = profile(bed)
    ex = [tuple(map(float, p.split("x"))) for p in ps.get("bed_exclude_area", [])]
    exclude = (rect_obb(min(p[0] for p in ex), min(p[1] for p in ex),
                        max(p[0] for p in ex), max(p[1] for p in ex)) if ex else None)
    plates, placements = [], []
    for k, (name, idxs) in enumerate(plate_groups(objects, bed), start=1):
        placed, at = plate(objects, idxs, bed, ps, exclude, name)
        plates.append(PJ.Plate(name, at))
        placements += [PJ.Placement(i, k, ob.cx, ob.cy, math.degrees(ob.theta))
                       for i, ob in placed]
    return bed, plates, placements


def plate(objects, idxs, bed, ps, exclude, name):
    """One plate packed WITH a home for its tower: as packed if the tower
    clears; else slid to an edge; else the whole plate a quarter turn round
    and the same again. Refuses when nothing works."""
    for turn in (False, True):
        packed = pack_plate(objects, idxs, bed, exclude, turn=turn, ps=ps)
        for dx, dy in slides(packed, bed, exclude):
            placed = shifted(packed, dx, dy)
            if misfit(objects, placed, bed, exclude):
                continue
            at = tower(ps, bed, placed, exclude)
            if at is not None:
                return placed, at
    refuse(f"plate {name}: no room for the prime tower, as packed or turned "
           f"a quarter round")
