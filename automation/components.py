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
        "extras": ["TokenHolder"],
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
        "pushers": {"S": 2, "M": 2, "L": 3},   # Innovation M uses 2, not 3

        # 6 toppers: one per expansion + a blank; same dims, different text.
        # ONE whole-studio Onshape export per sleeving yields all of them.
        # TODO confirm the exact expansion labels.
        "toppers": ["Cities", "Echoes", "Artifacts", "Figures", "Unseen",
                    "Blank"],
    },
}

# Pusher count by box size: 2 for S, 3 for M and L. Innovation is the exception
# — its M box also uses 2. Games override the default via their spec's "pushers"
# map; use pushers_for(spec, size).
PUSHERS_BY_SIZE = {"S": 2, "M": 3, "L": 3}


def pushers_for(spec, size):
    return spec.get("pushers", PUSHERS_BY_SIZE).get(size, 3)


def game_by_name(name):
    """Resolve a CLI game argument to (canonical_name, spec) by full name or
    folder code (e.g. 'FCM')."""
    if name in GAMES:
        return name, GAMES[name]
    for gname, spec in GAMES.items():
        if spec["folder"].lower() == name.lower():
            return gname, spec
    return None, None
