#!/usr/bin/env python3
"""Does a cascade actually fit? Interference and margins, from the B-reps.

    .venv/bin/python -m cad.fit --model S4.16.10.32-Un
    .venv/bin/python -m cad.fit --game Dominion --state all

The point of assembling a cascade. Every clearance in the design is asserted
one part at a time today, against a reference that only ever shows that part;
this measures the MECHANISM — plate in channel, tab in cutout, bump in groove,
holder on rib.

Two tiers, because the parts do not all come from the same place
(`spec/ASSEMBLY.md`):

* **interference** — exact `common volume` between two placed B-reps, for the
  parts `cad/` builds from source. That is Box, Lid, Pusher and TokenHolder,
  which is the whole of the lock. Non-zero is a failure, full stop.
* **margins** — the named fits, each computed from the placements and reported
  against what `LOCK_STANDARD.md` and the part modules say it should be. A
  margin outside its band is a warning with its number, never a pass.

The Holder is not intersected, though it could be now that
`cad/parts/holder.py` is finished: an assembly places the CACHED mesh by
default, because `individual/` is what shipped, and its mates are checked as
margins off that same mesh. Intersecting the source Holder against a cached
everything-else would measure the difference between the two rather than a
fit.
"""
import argparse
import sys
from pathlib import Path

from . import assembly as A
from . import derive as D
from . import lock as L
from . import params
from .parts import box as box_part
from .parts import holder as holder_part
from .parts import lid as lid_part
from .parts import pusher as pusher_part
from .parts import token_holder as th_part

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


def stored_pusher_margins(p, d):
    """The pusher in the box's rear storage."""
    out = []
    y0, y1 = box_part.slot_band(p, d)
    pl = A.pusher_stored(p, d, 0)
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
                      - box_part.pusher_rest(p, d), None,
                      note="a catch, not a shelf"))
    _cls, s = L.lock_class(d.calPusherTotalDepth)
    centre = box_part.pusher_slots(p, d)[0]
    tab = pl((0, -d.calPusherTotalDepth / 2 + s, 0))[0]
    out.append(Margin("stored: tab centre on the cutout's",
                      abs(tab - centre), s, note="+- s from the slot centre"))
    return out


def socketed_pusher_margins(p, d):
    """The pusher in the lid's socket."""
    out = []
    s_i = A.play_sockets(p, d)[0]
    x = lid_part.socket_centres(p, d)[s_i]
    cx = A.lid_under(p, d)((x, 0.0, 0.0))[0]
    pl = A.pusher_socketed(p, d, s_i)
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
    y0, y1 = lid_part.socket_span(p, d)
    under = A.lid_under(p, d)
    out.append(Margin("play: pusher overhangs its socket, back",
                      pl((0, 0, 0))[1] - under((0, y1, 0))[1],
                      L.LID_SOCKET_CLEARANCE / 2))
    out.append(Margin("play: pusher stands on the lid floor",
                      pl((0, 0, 0))[2], 0.0))
    return out


def holder_margins(p, d, cached=None):
    """The holder on its rib.

    `cached` maps `first` to the slot and width measured off the mesh an
    assembly actually places, because that is the part in the box. It is keyed
    on `first` and not shared: **a FirstHolder is DEEPER** — its depth is
    `calFirstSliderDistance - 0.400` — so its side slot, which is centred on
    its own depth, sits somewhere else entirely. Measuring every riser against
    the standard holder's slot is what the first version of this did, and the
    catalogue pass caught it on all six first-riser rows and nowhere else.

    A row whose FirstHolder has never been exported (`Holder M-21-r6-Un
    (first)` does not exist) gets its standard risers checked and that one
    reported, rather than the whole cascade skipped.
    """
    out = []
    for j, first in A.holders(p, d):
        info = (cached or {}).get(first)
        if info is None:
            out.append(Margin(f"holder {j}: rib in the side slot",
                              float("nan"), None,
                              note="no cached mesh — not checked"))
            continue
        slot_lo, slot_hi = info["slot"]
        want = (slot_hi - slot_lo - box_part.SLIDER_W) / 2
        rib0, rib1 = box_part.slider_ribs(p, d)[j]
        pl = A.holder_closed(p, d, j)
        lo, hi = pl((0, slot_lo, 0))[1], pl((0, slot_hi, 0))[1]
        out.append(Margin(f"holder {j}: rib in the side slot, back",
                          hi - rib1, want))
        out.append(Margin(f"holder {j}: rib in the side slot, front",
                          rib0 - lo, want))
    plain = (cached or {}).get(False)
    if plain:
        inner = box_part.box_width(p, d) / 2 - D.WallThickness
        out.append(Margin("holder: clearance in the box, each side",
                          inner - plain["width"] / 2, None))
    return out


def tread_margins(p, d):
    """The holder's footprint on the pusher's tread — the play state's own fit.

    The offset between a tread's centre and its rib's is a CONSTANT `0.150` on
    every cascade, and it is the finding this whole exercise was built to make:
    it eats that much of the `0.400` the rib has in the holder's slot. Derived
    rather than measured — every parameter cancels.
    """
    out = []
    drops = pusher_part.slider_drops(p, d)
    W = d.calPusherTotalDepth
    oy = A.pusher_socketed(p, d, A.play_sockets(p, d)[0]).origin[1]
    for j, _first in A.holders(p, d):
        k = p.RisingSliders - j
        back = oy - (W - sum(drops[:k]))
        front = oy - (W - sum(drops[:k - 1]))
        pl = A.holder_play(p, d, j)
        depth = holder_part.holder_depth(p, d, _first)
        out.append(Margin(f"holder {j}: on its tread, back",
                          back - pl.origin[1], None))
        out.append(Margin(f"holder {j}: on its tread, front",
                          (pl.origin[1] - depth) - front, None))
    return out


def lid_margins(p, d):
    """The lid over the box, and the box in the lid."""
    out = []
    z0, _z1 = lid_part.groove_span(d)
    pl = A.lid_closed(p, d)
    out.append(Margin("closed: groove floor on the box's bump top",
                      pl((0, 0, z0))[2], lid_part.BUMP_TOP))
    inner = lid_part.lid_width(p, d) / 2 - D.WallThickness
    out.append(Margin("lid over box: width, each side",
                      inner - box_part.box_width(p, d) / 2,
                      (lid_part.WIDTH_OVER_BOX - 2 * D.WallThickness) / 2))
    lid_inner_back = A.lid_under(p, d)((0, lid_part.lid_depth(d) / 2
                                       - D.WallThickness, 0))[1]
    box_back = box_part.box_depth(p, d) / 2 + box_part.REAR_DEPTH
    out.append(Margin("lid over box: behind the rear storage",
                      lid_inner_back - box_back, None))
    lid_inner_front = A.lid_under(p, d)((0, -lid_part.lid_depth(d) / 2
                                        + D.WallThickness, 0))[1]
    out.append(Margin("lid over box: in front of the front wall",
                      -box_part.box_depth(p, d) / 2 - lid_inner_front, None))
    return out


def cached_holders(p, d, folder):
    """`{first: {slot, width}}` for the holders an assembly places, measured
    off their meshes. A key is absent when that mesh is not on disk."""
    out = {}
    for first in {f for _j, f in A.holders(p, d)}:
        info = cached_holder(p, d, folder, first)
        if info is not None:
            out[first] = info
    return out


def cached_holder(p, d, folder, first=False):
    """The slot and width of one cached holder, measured off its mesh.
    `None` when it is not on disk."""
    import numpy as np
    from . import assemble
    try:
        _n, verts, _t = assemble.holder_mesh(p, d, folder, first)
    except Exception:
        return None
    v = np.asarray(verts)
    x_lo, x_hi = v[:, 0].min(), v[:, 0].max()
    end = v[(v[:, 0] <= x_lo + holder_part.END_BLOCK + 1e-6)]
    ys = np.unique(np.round(end[:, 1], 3))
    # The side slot's two walls are the pair `SLOT_W` apart AND centred on the
    # holder's mid-depth. Both conditions are needed: on `Holder S-16-r4-Un`
    # the pair (-5.800, -3.908) is 1.892 apart and matches the width alone to
    # 0.008, and it is the outer face and a lip chamfer, not the slot.
    mid = -holder_part.holder_depth(p, d, first) / 2
    walls = sorted(((abs((a + b) / 2 - mid), (float(a), float(b)))
                    for i, a in enumerate(ys) for b in ys[i + 1:]
                    if abs((b - a) - holder_part.SLOT_W) < 0.05))
    if not walls or walls[0][0] > 0.05:
        return None
    return {"slot": walls[0][1], "width": float(x_hi - x_lo)}


def interference(p, d, state):
    """[(a, b, mm3)] for every pair of SOURCE-built parts, placed.

    Box, Lid, Pusher and TokenHolder — the whole of the lock mechanism, and the
    only parts `cad/` can hand a B-rep for. Anything non-zero is a defect.
    """
    from .parts import box as bp, lid as lp, pusher as pp, token_holder as tp
    solids = [("Box", bp.build(p), A.box(p, d))]
    pusher = pp.build(p)
    if state == A.PLAY:
        solids += [(f"Pusher@{s}", pusher, A.pusher_socketed(p, d, s))
                   for s in A.play_sockets(p, d)]
        solids.append(("Lid", lp.build(p), A.lid_under(p, d)))
    else:
        solids += [(f"Pusher[{k}]", pusher, A.pusher_stored(p, d, k))
                   for k in A.pushers(p, d)]
        if state == A.CLOSED_LID:
            solids.append(("Lid", lp.build(p), A.lid_closed(p, d)))
    if p.GameName == "Dominion":
        solids.append(("TokenHolder", tp.build(p, False), A.token_holder(p, d)))

    placed = [(n, pl.location() * s) for n, s, pl in solids]
    out = []
    for i, (na, sa) in enumerate(placed):
        for nb, sb in placed[i + 1:]:
            common = sa & sb
            out.append((na, nb, common.volume if common is not None else 0.0))
    return out


def report(p, d, folder, state, solids=True):
    """Print one cascade's fit in one state. True if everything passed."""
    print(f"\n{folder}/{d.calModelName}  [{state}]")
    cached = cached_holders(p, d, folder)
    margins = list(lid_margins(p, d))
    if state == A.PLAY:
        margins += socketed_pusher_margins(p, d) + tread_margins(p, d)
    else:
        margins += stored_pusher_margins(p, d)
    margins += holder_margins(p, d, cached)
    for m in margins:
        print(m)
    ok = all(m.ok for m in margins)
    if solids:
        print("  -- interference, source-built parts --")
        for a, b, v in interference(p, d, state):
            flag = "ok " if v <= 1e-6 else "HIT"
            if v > 1e-6:
                ok = False
            print(f"  {flag} {a + ' / ' + b:44s} {v:10.4f} mm3")
    return ok


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--game")
    ap.add_argument("--model")
    ap.add_argument("--state", choices=A.STATES + ("all",), default=A.CLOSED)
    ap.add_argument("--csv", default=CSV, type=Path)
    ap.add_argument("--no-solids", action="store_true",
                    help="margins only — seconds, where a B-rep pass is minutes")
    args = ap.parse_args(argv)

    from . import assemble
    rows = assemble.catalogue(args.csv, args.game, args.model)
    states = A.STATES if args.state == "all" else (args.state,)
    ok = True
    for folder, p, _tokens, _sn in rows:
        d = D.derive(p)
        for state in states:
            ok &= report(p, d, folder, state, solids=not args.no_solids)
    print("\nPASS" if ok else "\nFAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
