"""Where each object goes: the plate scheme, the bed, the packing, the tower.

Lifted from `automation/make_cascade.py --auto-plates` (its lines 60-326 and
1019-1360 as of 2026-09-05), which laid out every regenerated cascade so far,
so that a project can be laid out without a donor to mutate. The rules are
the same rules and, where one was learned the hard way, the reason is kept
beside it; `tests/test_layout.py` holds this module to make_cascade's own
placements on a real cascade while both exist.

    from cad import layout as LY, project as PJ
    bed, plates, placements = LY.layout(objects)     # objects: [project.Obj]
    PJ.write(out, bed, objects, plates, placements, title)

What is decided here, in order:

1. THE BED — the smallest of `project.BEDS` every object clears once turned
   45 degrees (its rotated span is the diagonal of its footprint) with
   BED_MARGIN to spare; or the one the caller forces.
2. THE PLATES — one per role group in PLATE_SCHEME order, pushers riding with
   the box. A group splits when a big object that must rotate fills its plate
   diagonally and would leave no room for flat companions (the box and its
   pushers on a P1), and when more thin strips (holders, toppers) than one
   plate holds need several.
3. THE PACKING, per plate — thin strips turned 45 degrees and packed along
   two bed edges from a shared corner, or in one centred diagonal band when
   that holds more; flat objects grid-searched into the free corners; a
   plate with nothing to rotate laid out in centred shelf rows, widest first.
   The whole plate is nudged off a corner exclude area if centring clipped
   it, and every placement is validated: on the bed, clear of the exclude
   area, clear of its neighbours by CLEARANCE.
4. THE TOWER, per plate — inside the intersection of every extruder's
   printable area (the H2C's two nozzles reach different parts of the bed,
   and both purge into it), and clear of the parts by WIPE_GAP if any spot
   is, else TIGHT_GAP, preferring the spot furthest from the bed's centre.
   When no spot clears, the plate's contents are slid to each edge in turn to
   open the opposite one, then turned 90 degrees and tried again; a plate
   that still has no room for its tower is REFUSED, not warned about (Allan,
   2026-09-05 — make_cascade left the tower colliding and said so).
"""
import json
import math

from . import project as PJ

# --- the numbers -------------------------------------------------------------

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
BIG = 20.0            # an object longer than bed - BIG is turned 45 degrees
THIN = 30.0           # a strip is thinner than this

# One plate per role group, in this order. Pushers ride with the Box.
PLATE_SCHEME = [
    ("Box + pushers", ("Box", "Pusher")),
    ("Lid", ("Lid",)),
    ("Holders", ("Holder", "FirstHolder")),
    ("Toppers", ("Topper",)),
    ("Token holders", ("TokenHolder",)),
    ("Half token holders", ("HalfTokenHolder",)),
    ("Labels", ("Label",)),
]
ROLES = ("HalfTokenHolder", "TokenHolder", "FirstHolder", "Box", "Lid",
         "Holder", "Topper", "Pusher", "Label")


def role(name):
    """An object's role from its name — `Lid 168U` is a Lid."""
    for r in ROLES:
        if name.startswith(r):
            return r
    return "Other"


def fail(msg):
    raise SystemExit(f"REFUSING: {msg}")


# --- oriented boxes ------------------------------------------------------------
# (cx, cy, half x, half y, theta): the footprint of a placed object.


def _proj(o, ax):
    c, s = math.cos(o[4]), math.sin(o[4])
    mid = o[0] * ax[0] + o[1] * ax[1]
    r = o[2] * abs(c * ax[0] + s * ax[1]) + o[3] * abs(-s * ax[0] + c * ax[1])
    return mid - r, mid + r


def sat_overlap(a, b, gap=0.0):
    """Do two oriented boxes come within `gap` of each other?"""
    for o in (a, b):
        c, s = math.cos(o[4]), math.sin(o[4])
        for ax in ((c, s), (-s, c)):
            a0, a1 = _proj(a, ax)
            b0, b1 = _proj(b, ax)
            if a1 + gap <= b0 or b1 + gap <= a0:
                return False
    return True


def rect_obb(x0, y0, x1, y1):
    return ((x0 + x1) / 2, (y0 + y1) / 2, (x1 - x0) / 2, (y1 - y0) / 2, 0.0)


def obb_aabb(o):
    c, s = math.cos(o[4]), math.sin(o[4])
    rx = o[2] * abs(c) + o[3] * abs(s)
    ry = o[2] * abs(s) + o[3] * abs(c)
    return o[0] - rx, o[1] - ry, o[0] + rx, o[1] + ry


# --- 45-degree strips ---------------------------------------------------------
# A w x d strip turned 45 degrees has a SQUARE bounding box of side (w+d)/sqrt2,
# so its centre must stay inside a square inset from the bed by half of that.
# Step a strip along the bed's x or y axis by (d + gap)*sqrt2 and it moves
# exactly (d + gap) across its own width — the separation neighbours need —
# while also sliding (d + gap) along its own length, which costs nothing
# because the strips are parallel. So a column down one edge plus a row along
# the next packs them at the right pitch, the two arms sharing their corner
# strip. It replaced a centred diagonal band, which held fewer: 5 Innovation M
# holders (285.80 x 9.39 on a P1) went onto two plates when they fit one.


def strip_inset(w, d):
    """Half-side of a w x d strip's bounding box once turned 45 degrees."""
    return (w + d) / (2 * math.sqrt(2))


def strip_arm(bed, longest, depth, gap):
    """How many strips fit along ONE bed edge, corner strip included."""
    side = bed - 2 * STRIP_MARGIN - 2 * strip_inset(longest, depth)
    if side < 0:
        return 0
    return int(side / ((depth + gap) * math.sqrt(2))) + 1


def strip_arms(bed, longest, depth, gap):
    """How many strips fit ONE plate as two arms sharing their corner."""
    return max(1, 2 * strip_arm(bed, longest, depth, gap) - 1)


def strip_band(bed, longest, depth, gap):
    """How many strips fit ONE plate as a single centred diagonal band: the
    strips sit at a common position along their length and are separated only
    across it, so their centres run the full half-width of the bed's diamond
    less the strip's own half-diagonal."""
    half = (bed - 2 * STRIP_MARGIN) / math.sqrt(2) \
        - strip_inset(longest, depth) * math.sqrt(2)
    if half < 0:
        return 1
    return int(2 * half / (depth + gap)) + 1


def strip_capacity(bed, longest, depth, gap):
    """How many strips fit ONE plate, whichever arrangement holds more. Two
    arms is not universally better: an arm advances by (depth+gap)*sqrt2 along
    a bed axis, so once a strip is thick relative to the bed a single arm
    holds one and the band more — Dominion's 270 x 27.80 first-riser holder
    is that case (band 2, arms 1)."""
    return max(strip_arms(bed, longest, depth, gap),
               strip_band(bed, longest, depth, gap))


# --- the bed ------------------------------------------------------------------


def profile(bed):
    return json.loads((PJ.PROFILES / f"{PJ.BEDS[bed][2]}.config").read_text())


def usable(bed, ps):
    """(width, depth) an object may occupy on `bed`. The bed, unless the
    printer declares per-extruder areas and the profile maps every filament
    to extruder 1 — the H2C, `filament_map` 1,1 — in which case extruder 1's
    reach: 325 of the 330. Studio holds an object to the reach of the
    extruder that prints it; the shipped 650 Sleeved lid stops at 324.8."""
    areas = ps.get("extruder_printable_area") or []
    if areas and all(str(m) == "1" for m in ps.get("filament_map", [])):
        pts = [tuple(map(float, q.split("x"))) for q in areas[0].split(",")]
        return max(x for x, _y in pts), max(y for _x, y in pts)
    return PJ.BEDS[bed][:2]


def fit_angle(w, d, uw, ud):
    """(angle in degrees, slack) that fits a w x d footprint into uw x ud with
    the most room to spare, searched between 30 and 60 degrees — for the
    object whose 45-degree span does not fit. Dominion 650 Sleeved's lid,
    343.9 x 111.3, spans 321.9 at 45 against an H2C's 320 of depth, and fits
    at 44 with 0.3 to spare on the 325 of usable width, which is where its
    shipped project has it (Allan, 2026-09-05: it fits, just, and prints).
    A negative slack means it does not fit at any angle."""
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
    angle with the margin reduced to whatever is left, down to nothing — for
    a bed the row forces, or when no bed passes the rule proper. Not for the
    ladder's own choice: a Dominion S box fits the A1 mini at 44 degrees with
    nothing to spare, and the Mini is an explicit choice, never something the
    ladder lands on (PIPELINE.md, "The Mini bed class")."""
    bw, bd = PJ.BEDS[bed][:2]
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
    bed, the smallest it fits relaxed (the 650 Sleeved's H2C); or `forced` —
    the row's `3D printer` column — which need only fit relaxed (Dominion 324
    Sleeved on its P1P, 4.3 mm from the edge) and is refused otherwise."""
    if forced:
        if forced not in PJ.BEDS:
            fail(f"unknown bed {forced!r}; one of {sorted(PJ.BEDS)}")
        if not fits(forced, objects, relaxed=True):
            fail(f"the forced bed {forced} does not fit every part at any angle")
        return forced
    for bed in PJ.BEDS:                    # smallest first
        if fits(bed, objects):
            return bed
    for bed in PJ.BEDS:
        if fits(bed, objects, relaxed=True):
            return bed
    fail("no candidate bed fits every part at any angle between 30 and 60 deg")


# --- the plates ---------------------------------------------------------------


def _dims(obj):
    return obj.size[0], obj.size[1]


def _gap(obj):
    """Thin strips pack tight; everything else keeps GAP."""
    return STRIP_GAP if role(obj.name) in ("Holder", "FirstHolder", "Topper") else GAP


def plate_groups(objects, bed):
    """[(plate name, [object indices])] in PLATE_SCHEME order, empty groups
    skipped, with the two splits described in the module docstring."""
    bw, bd = PJ.BEDS[bed][:2]
    side = min(bw, bd)
    groups = []
    for label, roles in PLATE_SCHEME:
        idxs = [i for i, o in enumerate(objects) if role(o.name) in roles]
        if not idxs:
            continue
        # A big object that must rotate fills its plate diagonally and leaves
        # no room for flat companions (the box's pushers on a P1): give the
        # companions their own plate.
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


# --- one plate ----------------------------------------------------------------


def pack_plate(objects, idxs, bed, exclude, turn=False, ps=None):
    """{index: (theta, cx, cy)} in plate coordinates and [(index, obb)], for
    the objects `idxs` on one plate of `bed`. `exclude` is the bed's exclude
    area as an obb, or None. `turn` packs everything a quarter turn round —
    the fallback when the tower has nowhere to go. Placements are validated
    by `validate`, which the caller runs once the plate is final."""
    bw, bd = PJ.BEDS[bed][:2]
    side = min(bw, bd)
    uw, ud = usable(bed, ps or profile(bed))
    quarter = math.pi / 2 if turn else 0.0
    dims = {i: (_dims(objects[i])[::-1] if turn else _dims(objects[i])) for i in idxs}
    rot_ids = [i for i in idxs if max(dims[i]) > side - BIG]
    # An object whose 45-degree span does not fit takes the angle that does,
    # with whatever margin is left (fit_angle) — alone on its plate, since the
    # strip packing below assumes 45 degrees and a shared pitch.
    tight = {}
    for i in rot_ids:
        if sum(dims[i]) / math.sqrt(2) > min(uw, ud) - STRIP_MARGIN:
            ang, slack = fit_angle(dims[i][0], dims[i][1], uw, ud)
            if slack < 0:
                fail(f"{objects[i].name} cannot fit the {bw:g}x{bd:g} bed at any "
                     f"angle between 30 and 60 degrees ({-slack:.1f} mm over)")
            tight[i] = ang
    if len(tight) > 1 or (tight and len(rot_ids) > 1):
        fail(f"{[objects[i].name for i in rot_ids]}: more than one object on the "
             f"plate needs the bed's whole diagonal")
    placements, placed = {}, []
    if tight:
        (i, ang), = tight.items()
        w, d = dims[i]
        th = math.radians(ang)
        cx, cy = uw / 2, ud / 2                 # centred in the USABLE area
        placements[i] = (th + quarter, cx, cy)
        placed.append((i, (cx, cy, w / 2, d / 2, th + quarter)))
        flat = [j for j in idxs if j != i]
        if flat:
            fail(f"{objects[i].name} takes its plate's whole diagonal; "
                 f"{[objects[j].name for j in flat]} cannot share it")
    elif rot_ids:
        # strips along two bed edges from a shared corner — a column down the
        # +x edge, then a row along the +y edge — or the centred band when
        # the arms cannot hold this plate's strips. Positions are relative to
        # a local origin and centred on the plate afterwards.
        sr = sorted(rot_ids, key=lambda i: -dims[i][1])
        longest = max(max(dims[i]) for i in sr)
        deep = max(min(dims[i]) for i in sr)
        gap = _gap(objects[sr[0]])

        def pitch(prev_d, i):
            """Centre-to-centre separation two neighbouring strips need
            ACROSS their width."""
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
        for i in sr:
            w, d = dims[i]
            cx, cy = rel[i][0] + dx, rel[i][1] + dy
            placements[i] = (ROT + quarter, cx, cy)
            placed.append((i, (cx, cy, w / 2, d / 2, ROT + quarter)))
        # everything else grid-searched into the free corners, largest first
        flat = sorted((i for i in idxs if i not in rot_ids),
                      key=lambda i: -dims[i][0] * dims[i][1])
        for i in flat:
            w, d = dims[i]
            spot, cy = None, bd - EDGE - d / 2
            while spot is None and cy >= EDGE + d / 2:
                cx = EDGE + w / 2
                while cx <= bw - EDGE - w / 2:
                    cand = (cx, cy, w / 2, d / 2, quarter)
                    if not (exclude and sat_overlap(cand, exclude, GAP)) \
                       and not any(sat_overlap(cand, ob, GAP) for _, ob in placed):
                        spot = cand
                        break
                    cx += GRID
                cy -= GRID
            if spot is None:
                fail(f"no room left for {objects[i].name}")
            placements[i] = (quarter, spot[0], spot[1])
            placed.append((i, (spot[0], spot[1], w / 2, d / 2, quarter)))
    else:
        # shelf rows, widest first, the rows centred on the plate
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
            return r if r in ("Holder", "FirstHolder", "Topper") else None

        # the tight gap between rows only when BOTH rows are the same strip
        # kind (topper to topper), else GAP
        rgaps = [STRIP_GAP if row_gap_role(a) and row_gap_role(a) == row_gap_role(b) else GAP
                 for a, b in zip(rows, rows[1:])]
        depths = [max(dims[i][1] for i in r) for r in rows]
        y0 = (bd - (sum(depths) + sum(rgaps))) / 2
        for j, (row, depth) in enumerate(zip(rows, depths)):
            widths = [dims[i][0] for i in row]
            x0 = (bw - (sum(widths) + GAP * (len(row) - 1))) / 2
            for i, w in zip(row, widths):
                d = dims[i][1]
                cx, cy = x0 + w / 2, y0 + depth / 2
                placements[i] = (quarter, cx, cy)
                placed.append((i, (cx, cy, w / 2, d / 2, quarter)))
                x0 += w + GAP
            y0 += depth + (rgaps[j] if j < len(rgaps) else 0.0)

    # nudge the whole plate off a corner exclude area if centring clipped it
    # (a near-bed-width box on a P1P, whose 18 x 28 bottom-left corner is
    # reserved): shift in x away from it by just enough, if all stays on the bed
    if exclude and placed:
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
            placed = [(i, (ob[0] + dx,) + ob[1:]) for i, ob in placed]
            for i, _ in placed:
                th, x, y = placements[i]
                placements[i] = (th, x + dx, y)

    return placements, placed


def validate(objects, placed, bed, exclude):
    """Every placed object on the bed, off the exclude area and CLEARANCE from
    its neighbours — or a refusal naming the first that is not."""
    bw, bd = PJ.BEDS[bed][:2]
    for k, (i, ob) in enumerate(placed):
        x0, y0, x1, y1 = obb_aabb(ob)
        if x0 < -1e-6 or y0 < -1e-6 or x1 > bw + 1e-6 or y1 > bd + 1e-6:
            fail(f"{objects[i].name} does not fit the bed "
                 f"({x0:.1f},{y0:.1f})-({x1:.1f},{y1:.1f})")
        if exclude and sat_overlap(ob, exclude, CLEARANCE):
            fail(f"{objects[i].name} enters the bed's exclude area")
        for j, ob2 in placed[:k]:
            if sat_overlap(ob, ob2, CLEARANCE):
                fail(f"{objects[i].name} overlaps {objects[j].name}")


def shifted(placements, placed, dx, dy):
    """The same plate moved by (dx, dy)."""
    return ({i: (th, x + dx, y + dy) for i, (th, x, y) in placements.items()},
            [(i, (ob[0] + dx, ob[1] + dy) + ob[2:]) for i, ob in placed])


def slides(placed, bed, exclude):
    """Where a plate's contents can be slid to open a corner for the tower:
    unmoved first, then hard against each of the four edges (clear of the
    exclude area by CLEARANCE) — the slack a centred layout splits between
    two sides is enough for a tower on one of them."""
    bw, bd = PJ.BEDS[bed][:2]
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


# --- the tower ----------------------------------------------------------------


def tower_bounds(ps):
    """The rectangle a prime tower must lie inside: the INTERSECTION of every
    extruder's printable area, not the bed. The H2C declares extruder 1 over
    x 0..325 and extruder 2 over 25..330, and every filament purges into the
    tower, so a tower legal for one nozzle can be unreachable for the other;
    Bambu notices only after slicing, and MakerWorld slices on upload.
    Single-nozzle printers declare no extruder_printable_area and get the bed."""
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


def tower(ps, bed, placed, exclude, start=(15.0, 200.0)):
    """Where the plate's prime tower goes: `start` if it is legal and clear,
    else the legal spot furthest from the bed's centre that clears the parts
    by WIPE_GAP, else by TIGHT_GAP — or None when no spot clears."""
    bw, bd = PJ.BEDS[bed][:2]
    w = float(ps.get("prime_tower_width", 35))
    tx0, ty0, tx1, ty1 = tower_bounds(ps)

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


# --- all of it ------------------------------------------------------------------


def layout(objects, bed=None):
    """(bed, [project.Plate], [project.Placement]) for `objects`."""
    bed = choose_bed(objects, bed)
    ps = profile(bed)
    ex = [tuple(map(float, p.split("x"))) for p in ps.get("bed_exclude_area", [])]
    exclude = (rect_obb(min(p[0] for p in ex), min(p[1] for p in ex),
                        max(p[0] for p in ex), max(p[1] for p in ex)) if ex else None)
    plates, placements = [], []
    for k, (name, idxs) in enumerate(plate_groups(objects, bed), start=1):
        where, placed, at = plate(objects, idxs, bed, ps, exclude, name)
        plates.append(PJ.Plate(name, at))
        for i, (th, cx, cy) in where.items():
            placements.append(PJ.Placement(i, k, cx, cy, math.degrees(th)))
    return bed, plates, placements


def plate(objects, idxs, bed, ps, exclude, name):
    """One plate packed WITH a home for its tower: as packed if the tower
    clears; else slid to an edge; else the whole plate a quarter turn round
    and the same again. Refuses when nothing works — a plate whose tower
    collides is not a plate to print."""
    for turn in (False, True):
        where, placed = pack_plate(objects, idxs, bed, exclude, turn=turn, ps=ps)
        for dx, dy in slides(placed, bed, exclude):
            w2, p2 = shifted(where, placed, dx, dy)
            try:
                validate(objects, p2, bed, exclude)
            except SystemExit:
                continue
            at = tower(ps, bed, p2, exclude)
            if at is not None:
                return w2, p2, at
    fail(f"plate {name}: no room for the prime tower, as packed or turned "
         f"a quarter round")
