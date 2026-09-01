"""Per-game component specification for the Card Cascade export planner.

Components are NEVER shared across games (each game has its own card
dimensions/thickness in Onshape), so every identity is namespaced by game and
files live under individual/<Game folder>/.

For each component, `key` lists the parameters that make it unique WITHIN a
game — two cascades whose components share the same key share ONE Onshape
export. `key` is also (will be) the set of Onshape configuration inputs to set,
so it does double duty. Values marked TODO need confirming against the actual
Onshape configuration inputs.

A cascade "context" (built in plan_exports.py) exposes these parameters:
  game, folder, short_name, base_model, model (per-sleeving, e.g.
  S5.15.15.45-Un), size (S/M/L), risers, cards_per_slot, first_riser (or None),
  front_capacity, horizontal, merged (bool), sleeved (Un/Sl), sl (U/S),
  pushers (2 or 3).
"""

# Holder identity = (game, #cards the holder holds, sleeved) for ALL games;
# there is no separate "size" axis. For per-slot games the capacity is
# Cards/Riser slot. For Compile the holder spans `Horizontal` protocols of
# Cards/Riser slot (=7) each, so Horizontal is what varies it (S=3x7, L=5x7);
# set holder_spans=True for those.
GAMES = {
    "Compile": {
        "folder": "Compile",
        "holder_spans": True,
        "extras": [],
        "onshape_label": True,   # Compile's logo label comes from Onshape
    },
    "Dominion": {
        "folder": "Dominion",
        # Token holders are per-row now (parts.csv 'TokenHolder' column:
        # none/full/full+half) — only sets whose expansions need them carry one.
        "extras": [],
        "onshape_label": False,  # labels via labelmaker.py
    },
    "Food Chain Magnate": {
        "folder": "FCM",
        "extras": [],
        "onshape_label": False,
    },
    "Innovation": {
        "folder": "Innovation",
        "holder_spans": True,     # holder spans HorizontalSlots (3 wide=S, 4=M)
        "extras": ["Toppers"],
        "onshape_label": False,
        # Innovation uses 2 pushers at EVERY size, which is what the CAD says:
        # `isOnlyTwoPusherSlots` is a per-GAME variable, not a per-size one, and
        # every Innovation box on disk has 2 slots (countable from its rim
        # cutouts). A per-size map was the wrong shape and had two holes: `L`,
        # which no Innovation row reaches, and `XS`, which one does — Single
        # Mini fell through to the default 3 against a box with 2 slots.
        "pushers": 2,

        # 6 toppers: one per expansion + a blank; same plate, different text.
        # ONE Onshape ASSEMBLY export per parameter set yields all six
        # (onshape_config.TOPPER_ASSEMBLY, split by topper_split.py).
        "toppers": ["Cities", "Echoes", "Artifacts", "Figures", "Unseen",
                    "Blank"],

        # Rows that carry NO toppers, by Short name. A topper names which
        # expansion a riser holds, so a box built for ONE set — either single
        # box — has nothing for it to say. This has to live here rather than
        # being handled with `--count Topper=0` at build time: compose() is what
        # refresh_cascades diffs a project against, so a row listing toppers the
        # project does not have makes build_swap report them as unfillable and
        # SKIP the cascade on every future refresh.
        #
        # These are SHORT NAMES from parts.csv and must track it: the XS row was
        # listed here as "Inno 130" while parts.csv called it "Single Mini", so
        # the entry never matched and the XS cascades composed 12 toppers that do
        # not exist and that its projects have no slot for — ~38 wasted API calls
        # on any full-game export.
        "no_toppers": {"Single Set", "Single Mini"},
    },
}

# Pusher count by box size: 2 for XS and S, 3 for M and L. Innovation is the
# exception and takes 2 at every size. Games override via their spec's
# "pushers", an int or a per-size dict; use pushers_for(spec, size).
PUSHERS_BY_SIZE = {"XS": 2, "S": 2, "M": 3, "L": 3}


def pushers_for(spec, size):
    """How many pushers a box of this size takes.

    A game's `pushers` override may be an INT (the count at every size, which is
    what Innovation needs) or a per-size dict. Cross-check against a box with
    `verify.py --boxes`, which counts the rim cutouts: this table and the CAD
    are two copies of one fact, and the CAD is the authority."""
    over = spec.get("pushers")
    if isinstance(over, int):
        return over
    return (over or PUSHERS_BY_SIZE).get(size, 3)


def game_by_name(name):
    """Resolve a CLI game argument to (canonical_name, spec) by full name or
    folder code (e.g. 'FCM')."""
    if name in GAMES:
        return name, GAMES[name]
    for gname, spec in GAMES.items():
        if spec["folder"].lower() == name.lower():
            return gname, spec
    return None, None


def cascade_filename(game, short_name, sleeved, model):
    """Canonical output name for an assembled cascade project:

        "<Game> <Short name> <Sleeved|Unsleeved> (<model>).3mf"
        e.g. "Compile 126 Card Sleeved (S5.7.7.45-Sl).3mf"

    The Short name need not be a card count — Innovation's rows are named for
    what a box holds ("3 Ages 5 Expansions"), which is what its buyers look for.

    `sleeved` is "Sl"/"Un" (as in the cascade context); `model` is the row's
    per-sleeving model code (e.g. "M8.40.10.62-Sl")."""
    slv = "Sleeved" if sleeved == "Sl" else "Unsleeved"
    name = f"{game} {short_name} {slv} ({model}).3mf"
    # Some model codes carry a '/' (e.g. S2.40.12/30.32-Un) — a path separator,
    # so fold it and other filesystem-hostile chars to '-' (as legacy names did).
    for ch in "/\\:":
        name = name.replace(ch, "-")
    return name
