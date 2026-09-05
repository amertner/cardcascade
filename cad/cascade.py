"""A cascade from its parts.csv row: which parts, and the project they make.

The composition rules are `automation/PIPELINE.md`'s ("Component composition")
and `automation/components.py`'s per-game policy, restated here in terms of
`cad.build`'s file names — the names that ARE a part's identity, being what is
engraved on it — so nothing has to be planned or deduplicated: two cascades
that need the same holder ask for the same file.

    from cad import cascade as CC
    objects = CC.objects(row, p, d)        # [project.Obj], from build/<Game>/
"""
import sys
from pathlib import Path

from . import build as B, project as PJ, tables as TB

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "automation"))
import components as C                                   # noqa: E402

BUILD = ROOT / "build"


def parts(row, p, d):
    """[(object name, filename under build/<Game>/)] — every printed thing
    the cascade `row` (with its sleeving already in `p`) is made of, in the
    order the plate scheme lists them.

    * one Box, `calPusherSlots` Pushers (`#calPusherSlots` is the studio's
      count of rear slots: 2 for Innovation and for S boxes, 3 for M and L);
    * `RisingSliders` Holders — one of them the deeper FirstHolder when the row
      overrides the first slot's capacity;
    * one Lid;
    * Dominion: a TokenHolder where the row's `TokenHolder` column says `full`,
      and a HalfTokenHolder as well on a merged (Mat) row — the two are
      alternatives for one pocket, and the cascade ships both;
    * Innovation: the six Toppers, one per expansion plus Blank, except on
      the rows `components.no_toppers` names (a box built for ONE set has
      nothing for a topper to say).
    """
    out = [("Box", B.box_file(d))]
    out += [("Pusher", B.pusher_file(p))] * d.calPusherSlots
    if p.isFirstSlidingSlotOverride:
        out.append(("FirstHolder", B.holder_file(d, first=True)))
        out += [("Holder", B.holder_file(d))] * (p.RisingSliders - 1)
    else:
        out += [("Holder", B.holder_file(d))] * p.RisingSliders
    out.append((PJ.object_name("Lid", p, d), B.lid_file(d)))
    if p.GameName == "Dominion" and (row.get("TokenHolder") or "").strip().lower() == "full":
        out.append(("TokenHolder", B.token_holder_file(d, half=False)))
        if p.MatPocket:
            out.append(("HalfTokenHolder", B.token_holder_file(d, half=True)))
    spec = C.GAMES.get(p.GameName) or {}
    short = (row.get("Short name") or "").strip()
    if p.GameName == "Innovation" and short not in spec.get("no_toppers", set()):
        for exp in TB.TOPPER_EXPANSIONS + ("Blank",):
            out.append((f"Topper {exp}", B.topper_file(p, d, exp)))
    return out


def objects(row, p, d, root=BUILD):
    """The parts as `project.Obj`s, read from `root/<Game>/`. A missing file
    is named rather than guessed around — build it first."""
    folder = root / p.GameName
    missing = sorted({fn for _n, fn in parts(row, p, d) if not (folder / fn).exists()})
    if missing:
        raise SystemExit(f"REFUSING: not built under {folder}: {missing} — "
                         f"run python -m cad.build --part all")
    cache = {}
    out = []
    for name, fn in parts(row, p, d):
        if fn not in cache:
            cache[fn] = PJ.Obj.from_file(name, folder / fn)
        obj = cache[fn]
        out.append(PJ.Obj(name, obj.parts))
    return out


def title(row, p, d):
    """The project's name, `components.cascade_filename` without the suffix:
    `Dominion 168 Card Unsleeved (S4.16.10.32-Un)`. The model code is the
    row's own per-sleeving column, as the shipped names have it."""
    model = (row.get("Sleeved model" if p.isSleeved else "Unsl Model") or "").strip()
    return C.cascade_filename((row.get("Game") or p.GameName).strip(),
                              (row.get("Short name") or "").strip(),
                              "Sl" if p.isSleeved else "Un", model)[:-len(".3mf")]
