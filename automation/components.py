"""Per-game component specification for the Card Cascade export planner.

Components are NEVER shared across games, so every identity is namespaced by
game and files live under individual/<Game folder>/. A component's `key` is
what makes it unique WITHIN a game — two cascades sharing a key share ONE
export — and is also its set of Onshape configuration inputs (PIPELINE.md,
"Dedup identity keys"). A cascade "context" (plan_exports.py) exposes: game,
folder, short_name, base_model, model, size, risers, cards_per_slot,
first_riser, front_capacity, horizontal, merged, sleeved, sl, pushers.
"""

# Holder identity = (game, #cards held, sleeved) for ALL games; holder_spans
# marks the games whose holder spans `Horizontal` slots of that capacity.
GAMES = {
    "Compile": {
        "folder": "Compile",
        "holder_spans": True,
        "extras": [],
        # the logo label is drawn by labelmaker.py, not in Onshape
        "onshape_label": False,
    },
    "Dominion": {
        "folder": "Dominion",
        # Token holders are per-row (parts.csv 'TokenHolder').
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
        # Innovation uses 2 pushers at EVERY size: `isOnlyTwoPusherSlots` is
        # per-GAME, and a per-size map would let `XS` fall through to 3.
        "pushers": 2,

        # 6 toppers on one plate: ONE assembly export yields all six
        "toppers": ["Cities", "Echoes", "Artifacts", "Figures", "Unseen",
                    "Blank"],

        # Rows that carry NO toppers, by Short name: a box built for ONE set
        # has nothing for a topper to say. It lives here rather than as
        # `--count Topper=0` because compose() is what refresh_cascades diffs
        # against, so a row listing toppers the project lacks would make
        # build_swap SKIP the cascade for ever. These track parts.csv.
        "no_toppers": {"Single Set", "Single Mini"},
    },
}

# Pusher count by box size; a game overrides with its spec's "pushers".
PUSHERS_BY_SIZE = {"XS": 2, "S": 2, "M": 3, "L": 3}


def pushers_for(spec, size):
    """How many pushers a box of this size takes. This table and the CAD are
    two copies of one fact and the CAD is the authority (`verify.py`)."""
    over = spec.get("pushers")
    if isinstance(over, int):
        return over
    return (over or PUSHERS_BY_SIZE).get(size, 3)


def game_by_name(name):
    """A CLI game argument to (canonical_name, spec), by name or folder."""
    if name in GAMES:
        return name, GAMES[name]
    for gname, spec in GAMES.items():
        if spec["folder"].lower() == name.lower():
            return gname, spec
    return None, None


def cascade_filename(game, short_name, sleeved, model, version, label=None):
    """Canonical output name for an assembled cascade project:

        "<Game> <Short name> <Sleeved|Unsleeved> v<version> (<model>).3mf"
        e.g. "Compile 126 Card Sleeved v7.0 (S5.7.7.45-Sl).3mf"

    The Short name need not be a card count. `sleeved` is "Sl"/"Un"; `model`
    is the row's per-sleeving model code.

    `version` is what the name PROMISES about the parts inside. The argument
    is not optional, but `None` is a legal, deliberate answer — "no version in
    this name" — and is what the TRACKED trees pass (see `tracked_name`;
    PIPELINE.md, "A name is an identity, a version is a release"). On the
    Onshape path it is the cascade's GENERATION, that table not being uniform;
    on the cad path every part really is built at one version.

    `label` is parts.csv's `Project label` and switches to the FCM form,
    "FCM Occ 2S v7.0 (180 Card L3-18-6-20-Sl).3mf" — *the 2nd box for
    Occupations, sleeved*, which the canonical form cannot say. The sleeving
    letter joins the label directly when it ends in a digit and after a space
    otherwise; the game is its folder code, the card count moves inside the
    bracket, and the model's dots fold to dashes."""
    ver = f" v{version}" if version else ""
    if label:
        folder = (GAMES.get(game) or {}).get("folder", game)
        sl = "S" if sleeved == "Sl" else "U"
        sep = "" if label[-1:].isdigit() else " "
        name = (f"{folder} {label}{sep}{sl}{ver} "
                f"({short_name} {model.replace('.', '-')}).3mf")
    else:
        slv = "Sleeved" if sleeved == "Sl" else "Unsleeved"
        name = f"{game} {short_name} {slv}{ver} ({model}).3mf"
    # a model code may carry a '/' — a path separator — so fold it and the
    # other filesystem-hostile chars to '-', as legacy names did
    for ch in "/\\:":
        name = name.replace(ch, "-")
    return name


def tracked_name(game, short_name, sleeved, model, label=None):
    """The name a cascade project has IN THE REPO — `cascade_filename` with no
    version. The one place that policy is stated, for both pipelines.

    A name in the repo is an identity: git follows a path, so a version in it
    renames the whole catalogue on every release. What a file IS stays
    readable from it — the version is in the 3MF `Title` and engraved on the
    parts. It goes into the NAME only for the tree that leaves the repo, whose
    reader has nothing else to go on: `cad.cascade --publish`."""
    return cascade_filename(game, short_name, sleeved, model, None, label)
