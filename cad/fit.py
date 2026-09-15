#!/usr/bin/env python3
"""Does a cascade actually fit? Interference and margins, from the B-reps.

    .venv/bin/python -m cad.fit --model S4.16.10.32-Un
    .venv/bin/python -m cad.fit --game Dominion --state all

This measures the MECHANISM — plate in channel, tab in cutout, bump in groove,
holder on rib — where every other check asserts one part at a time. Two tiers
(`spec/ASSEMBLY.md`, "What the fit test measures"): **interference**, the
exact common volume between two placed B-reps, where non-zero is a failure
full stop; and **margins**, the named fits reported against what
`LOCK_STANDARD.md` and the part modules say, where outside the band is a
warning with its number and never a pass. The Holder's rib and tread mates
are margins off the built mesh; its LIPS are intersected, and `lip_margins`
says where each sits in its rest when the cascade is open.
"""
import argparse
import sys
from pathlib import Path

from . import assembly as A
from . import derive as D
from . import lock as L
from . import revisions as R
from .parts import box as box_part
from .parts import holder as holder_part
from .parts import lid as lid_part
from .parts import pusher as pusher_part

ROOT = Path(__file__).resolve().parent.parent
CSV = ROOT / "automation" / "parts.csv"


class Margin:
    """One named fit: what was measured, and what it should have been."""

    def __init__(self, name, got, want, tol=0.001, note=""):
        self.name, self.got, self.want, self.tol, self.note = (
            name, got, want, tol, note)

    @property
    def ok(self):
        return self.want is None or abs(self.got - self.want) <= self.tol

    def __str__(self):
        want = "" if self.want is None else f" (want {self.want:.3f})"
        mark = "ok " if self.ok else "OFF"
        return (f"  {mark} {self.name:44s} {self.got:8.3f}{want}"
                + (f"  {self.note}" if self.note else ""))


def stored_pusher_margins(d):
    out = []
    y0, y1 = box_part.slot_band(d)
    pl = A.pusher_stored(d, 0)
    plate_back = pl((0, 0, 0))[1]
    plate_front = pl((0, 0, L.PLATE))[1]
    out.append(Margin("stored: plate in the 3.200 slot band, back",
                      y1 - plate_back, A.PLATE_SLOP))
    out.append(Margin("stored: plate in the 3.200 slot band, front",
                      plate_front - y0, A.PLATE_SLOP))
    top = pl((0, 0, 0))[2]
    out.append(Margin("stored: pusher top at the rim", top, d.BoxHeight))
    out.append(Margin("stored: tab fills the rim cutout, top",
                      top, d.BoxHeight))
    out.append(Margin("stored: tab fills the rim cutout, bottom",
                      pl((L.TAB_L, 0, 0))[2], box_part.RIM_CUTOUT_Z))
    out.append(Margin("stored: rest below the pusher's own bottom",
                      pl((d.calPusherTotalHeight, 0, 0))[2]
                      - box_part.pusher_rest(d), None,
                      note="a catch, not a shelf"))
    _cls, s = L.lock_class(d.calPusherTotalDepth)
    centre = box_part.pusher_slots(d)[0]
    tab = pl((0, -d.calPusherTotalDepth / 2 + s, 0))[0]
    out.append(Margin("stored: tab centre on the cutout's",
                      abs(tab - centre), s, note="+- s from the slot centre"))
    return out


def socketed_pusher_margins(d):
    out = []
    s_i = A.play_sockets(d)[0]
    x = lid_part.socket_centres(d)[s_i]
    cx = A.lid_under(d)((x, 0.0, 0.0))[0]
    pl = A.pusher_socketed(d, s_i)
    face_a, face_b = pl((0, 0, 0))[0], pl((0, 0, L.PLATE))[0]
    lo, hi = min(face_a, face_b), max(face_a, face_b)
    out.append(Margin("play: plate in the 3.300 channel, +X",
                      cx + L.LID_CHANNEL_W / 2 - hi,
                      (L.LID_CHANNEL_W - L.PLATE) / 2))
    out.append(Margin("play: plate in the 3.300 channel, -X",
                      lo - (cx - L.LID_CHANNEL_W / 2),
                      (L.LID_CHANNEL_W - L.PLATE) / 2))
    tip = pl((0, 0, L.PLATE + L.TAB_PROUD))[0]
    floor = cx - L.LID_CHANNEL_W / 2 - L.LID_RECESS_STEP
    out.append(Margin("play: tab tip to the recess floor", tip - floor, None,
                      note=f"standard's play is {L.LID_RECESS_STEP - L.TAB_PROUD:.3f} "
                           "with the plate hard over"))
    _y0, y1 = lid_part.socket_span(d)
    under = A.lid_under(d)
    out.append(Margin("play: pusher overhangs its socket, back",
                      pl((0, 0, 0))[1] - under((0, y1, 0))[1],
                      L.LID_SOCKET_CLEARANCE / 2))
    out.append(Margin("play: pusher stands on the lid floor",
                      pl((0, 0, 0))[2], 0.0))
    return out


def holder_margins(d, holders=None):
    """The holder on its rib. `holders` maps `(first, rear)` to the slot and
    width measured off the mesh an assembly actually places. Keyed on the deep
    flag and NOT shared: a FirstHolder is DEEPER, so its side slot — centred
    on its own depth — sits somewhere else entirely."""
    out = []
    for j, first in A.holders(d):
        info = (holders or {}).get((first, A.rear_of(d, j)))
        if info is None:
            out.append(Margin(f"holder {j}: rib in the side slot",
                              float("nan"), None,
                              note="slot not found on the mesh — not checked"))
            continue
        slot_lo, slot_hi = info["slot"]
        want = (slot_hi - slot_lo - box_part.SLIDER_W) / 2
        rib0, rib1 = box_part.slider_ribs(d)[j]
        pl = A.holder_closed(d, j)
        lo, hi = pl((0, slot_lo, 0))[1], pl((0, slot_hi, 0))[1]
        out.append(Margin(f"holder {j}: rib in the side slot, back",
                          hi - rib1, want))
        out.append(Margin(f"holder {j}: rib in the side slot, front",
                          rib0 - lo, want))
    plain = (holders or {}).get((False, False)) or next(iter((holders or {}).values()), None)
    if plain:
        inner = box_part.box_width(d) / 2 - D.WallThickness
        out.append(Margin("holder: clearance in the box, each side",
                          inner - plain["width"] / 2, None))
    return out


def tread_margins(d):
    """The holder's footprint on the pusher's tread — the play state's own fit.
    The offset between a tread's centre and its rib's is a CONSTANT 0.150 on
    every cascade and eats that much of the rib's slack in the holder's slot
    (`spec/ASSEMBLY.md`, "The finding")."""
    out = []
    drops = pusher_part.slider_drops(d)
    W = d.calPusherTotalDepth
    oy = A.pusher_socketed(d, A.play_sockets(d)[0]).origin[1]
    for j, first in A.holders(d):
        k = d.RisingSliders - j
        back = oy - (W - sum(drops[:k]))
        front = oy - (W - sum(drops[:k - 1]))
        pl = A.holder_play(d, j)
        depth = holder_part.holder_depth(d, first)
        out.append(Margin(f"holder {j}: on its tread, back",
                          back - pl.origin[1], None))
        out.append(Margin(f"holder {j}: on its tread, front",
                          (pl.origin[1] - depth) - front, None))
    return out


def lip_margins(d):
    """Every lip in its rest, in play — the fit 7.2e (`rev.seated_lips`) is
    for (`spec/HOLDER.md`, "Lips that seat"). Reported at EVERY release:
    before the flag the numbers say what was wrong. Three readings — a rear
    lip's underside above the rest floor of the holder behind, its tip past
    that holder's front wall, and the same two for the Box's lip."""
    out = []
    hs = A.holders(d)
    rest = (holder_part.rest_depth(d) if d.rev.seated_lips
            else holder_part.SLANT_STEP)
    # `REST_CLEARANCE`, or more where the box lip made the rest deeper
    # (`holder.rest_depth`): one notch depth per cascade.
    want = rest - holder_part.SLANT_STEP if d.rev.seated_lips else None
    seen = set()
    for (jb, fb), (jf, ff) in zip(hs, hs[1:]):
        if (fb, ff) in seen:
            continue
        seen.add((fb, ff))
        pb, pf = A.holder_play(d, jb), A.holder_play(d, jf)
        under = pf.origin[2] + holder_part.lip_band_z(d, ff, 0.0, lower=True)
        floor = (pb.origin[2]
                 + holder_part.slant_z(d, fb, pf.origin[1] - pb.origin[1]) - rest)
        who = f"holder {jf}{' (deep)' if ff else ''} in holder {jb}{' (deep)' if fb else ''}"
        out.append(Margin(f"play: {who}, lip above the rest floor",
                          under - floor, want))
        wall_in = (pb.origin[1] - holder_part.holder_depth(d, fb)
                   + holder_part.WALL)
        out.append(Margin(f"play: {who}, lip tip past the wall's inner face",
                          pf.origin[1] + holder_part.lip_reach_y(d, ff) - wall_in,
                          0.0 if d.rev.seated_lips else None))
    jf, ff = hs[-1]
    pf = A.holder_play(d, jf)
    who = f"box lip in holder {jf}{' (deep)' if ff else ''}"
    out.append(Margin(f"play: {who}, lip above the rest floor",
                      rest - A.box_lip_seat(d), None,
                      note=f"must be >= {holder_part.REST_CLEARANCE:.3f}"
                           if d.rev.seated_lips else "must be > 0"))
    m = box_part.lip_slope(d)
    if d.rev.ribs_forward:
        reach = box_part.lip_reach(d)
    elif d.rev.seated_lips:
        reach = A.front_holder_gap(d) + holder_part.WALL
    else:
        reach = box_part.LIP_DEPTH * m / (1.0 + m * m) ** 0.5
    wall_face = pf.origin[1] - holder_part.holder_depth(d, ff)
    if d.rev.ribs_forward:
        # From 7.2f the lip BITES the wall by LIP_BITE, inside the rib slack,
        # rather than filling it (`box.lip_reach`).
        out.append(Margin(f"play: {who}, lip's bite into the wall",
                          box_part.pocket_span(d)[2] + reach - wall_face,
                          box_part.LIP_BITE))
    else:
        out.append(Margin(f"play: {who}, lip tip past the wall's inner face",
                          box_part.pocket_span(d)[2] + reach - (wall_face + holder_part.WALL),
                          0.0 if d.rev.seated_lips else None))
    # Closed, a holder's rear lips are above the front wall of the holder
    # behind, which is what lets the holders go in back to front down their
    # ribs.
    if len(hs) > 1:
        (jb, fb), (jf, ff2) = hs[0], hs[1]
        pb, pf2 = A.holder_closed(d, jb), A.holder_closed(d, jf)
        y_tip = pf2.origin[1] + holder_part.lip_reach_y(d, ff2)
        under = pf2.origin[2] + holder_part.lip_band_z(d, ff2, holder_part.lip_reach_y(d, ff2), lower=True)
        wall_top = pb.origin[2] + holder_part.slant_z(d, fb, y_tip - pb.origin[1])
        out.append(Margin("closed: rear lips above the wall of the holder behind",
                          under - wall_top, None, note="must be > 0: holders go in back to front"))
    return out


def insertion(d, built=None, step=0.5, above=30.0):
    """The front holder lowered down its ribs onto its seat, against the box,
    as B-reps: [(shift, worst mm3)] for the holder centred on its rib and at
    the BACK of its rib slack. From 7.2f the lip bites LIP_BITE, which the
    slack absorbs, so the SHIFTED sweep must be clean (`spec/BOX.md`)."""
    from .parts import box as bp
    built = {} if built is None else built
    box = _once(built, "Box", lambda: bp.build(d))
    hs = A.holders(d)
    j, first = hs[-1]
    rear = A.rear_of(d, j)
    key = f"Holder{'-deep' if first else ''}{'-rear' if rear else ''}"
    holder = _once(built, key,
                   lambda f=first, r=rear: holder_part.build(d, f, text=False, rear=r))
    closed = A.holder_closed(d, j)
    slack = (holder_part.SLOT_W - bp.SLIDER_W) / 2
    out = []
    for shift in (0.0, slack):
        worst = 0.0
        dz = 0.0
        while dz <= above:
            pl = A.Place(origin=(closed.origin[0], closed.origin[1] + shift,
                                 closed.origin[2] + dz))
            c = box & (pl.location() * holder)
            worst = max(worst, c.volume if c is not None else 0.0)
            dz += step
        out.append((shift, worst))
    return out


def lid_margins(d, holders=None):
    """The lid over the box, and the box in the lid; `holders` is
    `built_holders`' reading."""
    out = []
    z0, _z1 = lid_part.groove_span(d)
    pl = A.lid_closed(d)
    out.append(Margin("closed: groove floor on the box's bump top",
                      pl((0, 0, z0))[2], lid_part.BUMP_TOP))
    # What bounds a box's height: the sockets hang from the closed lid's floor
    # over the card compartments, and the tallest thing under them is a card
    # on the holder's pocket floor, or a holder taller than its cards.
    card_floor = (box_part.floor_top(d) + holder_part.half_height(d)
                  + holder_part.pocket_z(d)[0] - holder_part.FLOOR_DROP)
    out.append(Margin("closed: socket underside over the card top",
                      (d.BoxHeight - lid_part.SOCKET_H)
                      - (card_floor + d.CardHeight), None,
                      note=f"CardHeight {d.CardHeight:.0f}; must be > 0"))
    # ... and over the tallest HOLDER, read off the built meshes: a deep holder
    # at the back rises above the card tops.
    tops = [info["top"] for info in (holders or {}).values() if "top" in info]
    if tops:
        out.append(Margin("closed: socket underside over the tallest holder",
                          (d.BoxHeight - lid_part.SOCKET_H)
                          - (box_part.floor_top(d) + holder_part.half_height(d)
                             + max(tops)), None, note="must be > 0"))
    inner = lid_part.lid_width(d) / 2 - D.WallThickness
    out.append(Margin("lid over box: width, each side",
                      inner - box_part.box_width(d) / 2,
                      (lid_part.WIDTH_OVER_BOX - 2 * D.WallThickness) / 2))
    lid_inner_back = A.lid_under(d)((0, lid_part.lid_depth(d) / 2
                                       - D.WallThickness, 0))[1]
    box_back = box_part.box_depth(d) / 2 + box_part.REAR_DEPTH
    out.append(Margin("lid over box: behind the rear storage",
                      lid_inner_back - box_back, None))
    lid_inner_front = A.lid_under(d)((0, -lid_part.lid_depth(d) / 2
                                        + D.WallThickness, 0))[1]
    out.append(Margin("lid over box: in front of the front wall",
                      -box_part.box_depth(d) / 2 - lid_inner_front, None))
    return out


def built_holders(d, folder, out_dir=None):
    """`{(first, rear): {slot, width, top}}` for the holders an assembly places
    (`assembly.holder_kinds`), measured off their meshes in `out_dir` and
    built first where missing. A key is absent when the slot is not found."""
    out = {}
    for (first, rear), _js in A.holder_kinds(d):
        info = built_holder(d, folder, first, out_dir, rear)
        if info is not None:
            out[(first, rear)] = info
    return out


def built_holder(d, folder, first=False, out_dir=None, rear=False):
    """The slot, width and top of one built holder, off its mesh; `None` when
    the slot is not found."""
    import numpy as np
    from . import assemble, build as B
    _n, verts, _t = assemble.holder_mesh(d, out_dir or B.out_for(d.Version),
                                         folder, first, rear)
    v = np.asarray(verts)
    x_lo, x_hi = v[:, 0].min(), v[:, 0].max()
    end = v[(v[:, 0] <= x_lo + holder_part.END_BLOCK + 1e-6)]
    ys = np.unique(np.round(end[:, 1], 3))
    # The side slot's two walls are the pair `SLOT_W` apart AND centred on the
    # holder's mid-depth. BOTH conditions are needed: an outer face and a lip
    # chamfer can match the width alone.
    mid = -holder_part.holder_depth(d, first) / 2
    walls = sorted(((abs((a + b) / 2 - mid), (float(a), float(b)))
                    for i, a in enumerate(ys) for b in ys[i + 1:]
                    if abs((b - a) - holder_part.SLOT_W) < 0.05))
    if not walls or walls[0][0] > 0.05:
        return None
    return {"slot": walls[0][1], "width": float(x_hi - x_lo),
            "top": float(v[:, 2].max())}


def _once(built, key, make):
    """`built[key]`, made on first asking: `--state all` builds each once."""
    if key not in built:
        built[key] = make()
    return built[key]


def interference(d, state, tokens=False, built=None):
    """[(a, b, mm3)] for every pair of SOURCE-built parts, placed: Box, Lid,
    Pusher, the TokenHolder where `tokens`, and every Holder built without its
    text. Anything non-zero is a defect."""
    from .parts import box as bp, lid as lp, pusher as pp, token_holder as tp
    built = {} if built is None else built
    solids = [("Box", _once(built, "Box", lambda: bp.build(d)), A.box(d))]
    for j, first in A.holders(d):
        rear = A.rear_of(d, j)
        key = f"Holder{'-deep' if first else ''}{'-rear' if rear else ''}"
        solid = _once(built, key,
                      lambda f=first, r=rear: holder_part.build(d, f, text=False, rear=r))
        place = A.holder_play(d, j) if state == A.PLAY else A.holder_closed(d, j)
        solids.append((f"Holder@{j}", solid, place))
    pusher = _once(built, "Pusher", lambda: pp.build(d))
    lid = lambda: _once(built, "Lid", lambda: lp.build(d))       # noqa: E731
    if state == A.PLAY:
        solids += [(f"Pusher@{s}", pusher, A.pusher_socketed(d, s))
                   for s in A.play_sockets(d)]
        solids.append(("Lid", lid(), A.lid_under(d)))
    else:
        solids += [(f"Pusher[{k}]", pusher, A.pusher_stored(d, k))
                   for k in A.pushers(d)]
        if state == A.CLOSED_LID:
            solids.append(("Lid", lid(), A.lid_closed(d)))
    if tokens:
        solids.append(("TokenHolder",
                       _once(built, "TokenHolder", lambda: tp.build(d, False)),
                       A.token_holder(d)))

    placed = [(n, pl.location() * s) for n, s, pl in solids]
    out = []
    for i, (na, sa) in enumerate(placed):
        for nb, sb in placed[i + 1:]:
            common = sa & sb
            out.append((na, nb, common.volume if common is not None else 0.0))
    return out


def report(d, folder, state, solids=True, tokens=False, built=None):
    """Print one cascade's fit in one state; True if everything passed.
    `built` carries the cascade's parts from state to state."""
    print(f"\n{folder}/{d.calModelName}  [{state}]")
    built = {} if built is None else built
    holders = _once(built, "holders", lambda: built_holders(d, folder))
    margins = list(lid_margins(d, holders))
    if state == A.PLAY:
        margins += socketed_pusher_margins(d) + tread_margins(d) + lip_margins(d)
    else:
        margins += stored_pusher_margins(d)
    margins += holder_margins(d, holders)
    for m in margins:
        print(m)
    ok = all(m.ok for m in margins)
    if solids:
        print("  -- interference, source-built parts --")
        for a, b, v in interference(d, state, tokens, built):
            flag = "ok " if v <= 1e-6 else "HIT"
            if v > 1e-6:
                ok = False
            print(f"  {flag} {a + ' / ' + b:44s} {v:10.4f} mm3")
        if state == A.CLOSED:
            print("  -- the front holder lowered onto its seat --")
            for shift, v in insertion(d, built):
                at_back = shift > 0
                bad = v > 1e-6 and at_back
                if bad:
                    ok = False
                flag = "HIT" if bad else "ok "
                where = "at the back of its rib slack" if at_back else "centred on its rib"
                print(f"  {flag} {'front holder past the box lip, ' + where:44s} {v:10.4f} mm3"
                      + ("" if at_back else "  (the lip's bite; must clear when shifted back)"))
    return ok


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--game")
    ap.add_argument("--model")
    ap.add_argument("--state", choices=A.STATES + ("all",), default=A.CLOSED)
    ap.add_argument("--csv", default=CSV, type=Path)
    ap.add_argument("--version", default=R.CURRENT, choices=R.RELEASES,
                    help=f"the release to measure (default {R.CURRENT}); a "
                         "release can change a part (cad/revisions.py)")
    ap.add_argument("--no-solids", action="store_true",
                    help="margins only — seconds, where a B-rep pass is minutes")
    args = ap.parse_args(argv)

    from . import assemble
    rows = assemble.catalogue(args.csv, args.game, args.model, args.version)
    states = A.STATES if args.state == "all" else (args.state,)
    ok = True
    for folder, d, tokens, _toppers in rows:
        built = {}
        for state in states:
            ok &= report(d, folder, state, solids=not args.no_solids,
                         tokens=tokens, built=built)
    print("\nPASS" if ok else "\nFAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
