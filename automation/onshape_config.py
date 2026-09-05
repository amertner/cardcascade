"""Onshape document, Primary variable studio, and per-component part-studio
element ids for the Card Cascade master model.

All components live in ONE document/workspace. Component geometry is driven by
the Primary variable studio (set once per cascade — see set_variables.py), and
each component type is its OWN part studio, so each is a separate export
(translate + poll + download).

The user also has ASSEMBLIES containing all components; a future path could
export one assembly per parameter set instead of one export per part studio —
worth exploring to cut the export-call count. For now we export part studios.
"""

DID = "b6cb17a272a81e2049649d97"          # document
WID = "0d5e487a46c4ad6ff8cf268f"          # workspace

# Primary variable studio — POST the full Primary set here (1 call per cascade).
PRIMARY = "8aa4636cbb697a1091437161"

# Component type -> part-studio element id. Each is a separate part studio.
# TODO: Label (Compile) element id still needed.
ELEMENTS = {
    "Box":         "6a20c041a900d6b2fca960db",
    "Lid":         "1f5cc8c63b87dcf62f713af0",   # first test-exported studio
    "Holder":      "8b9578cb73a2958f625ee53d",
    "Pusher":      "c1fef5b25da6282bcdc20876",
    "Topper":      "46a8affed99afb21fa7202d8",   # configured per Expansion name
    "TokenHolder": "2d5e70091942133d994fd989",   # Dominion only
}

# Assembly holding all the MONOCHROME components (Box, Pusher, TokenHolder, and
# the first + default Holder instances), driven by the same Primary variable
# studio. Exporting this ONE element in one translation returns every monochrome
# component at once (see assembly_split.py) — far fewer API calls than one
# part-studio export per component.
#
# The Lid is NOT in this assembly: it can't be reconfigured per-game reliably,
# and its lettering body names would collide. It stays on the part-studio path.
ASSEMBLY = "f27edbc7a0f89c28092f18d4"

# Assembly holding all SIX Innovation toppers at once, driven by the same Primary
# variable studio. Toppers used to be six separate part-studio exports (one per
# Expansion configuration value) = six translate ops per (size, cards, sleeving);
# this collapses them to one, which is ~15 calls saved per parameter set and made
# toppers the largest single consumer of the Innovation budget.
#
# The six instances are the same part studio at six configuration values, so they
# all carry the SAME body names ("Topper", "Part 3"...) — nothing like the
# monochrome assembly, whose parts are named after their component type. Which
# instance is which expansion is recovered from the lettering geometry; see
# topper_split.py, which owns that and refuses rather than guessing.
# The first topper assembly (35aa82c92603710330ba2207) instanced the plate and
# the name inlays but NOT the logo inlay, so every topper split out of it printed
# with the logo as an empty recess in the white. The plate's logo recess was
# untouched — same vertex and triangle count as the studio export — and the
# splitter was lossless (44 objects in, 44 out), which is how the omission was
# traced to the assembly rather than to the export or the split. This element is
# the corrected assembly: 54 objects, +10 being Unseen's six-solid logo and one
# each for Cities, Echoes, Artifacts and Figures. Blank has no logo and is
# unchanged.
TOPPER_ASSEMBLY = "96b9b447b0cd4d8aef5f4c77"

# Which component types come from an assembly export vs a per-part-studio export.
# Membership decides how plan_exports/export route each component.
ASSEMBLY_SOURCED = frozenset({"Box", "Pusher", "Holder", "TokenHolder",
                              "HalfTokenHolder"})
TOPPER_SOURCED = frozenset({"Topper"})
STUDIO_SOURCED = frozenset({"Lid", "Label"})


def source_element(comp_type):
    """The Onshape element a component is exported FROM: the shared assembly for
    monochrome parts, the per-type part studio otherwise.

    --adopt must record the same id the export path writes, or a part that came
    out of an assembly split is misattributed to a studio it never came from.
    ELEMENTS carries a standalone studio for Box/Holder/Pusher/TokenHolder as
    well, so keying off it alone silently produces that wrong answer."""
    if comp_type in ASSEMBLY_SOURCED:
        return ASSEMBLY
    if comp_type in TOPPER_SOURCED:
        return TOPPER_ASSEMBLY
    return ELEMENTS.get(comp_type, "")

# Object names inside the assembly export map 1:1 to component types. A distinct
# first-riser holder is named "FirstHolder" (separate from the default "Holder");
# older exports name both "Holder" and are told apart by height — see
# assembly_split.py.
ASSEMBLY_ROLE_NAMES = {"Box", "Pusher", "Holder", "FirstHolder", "TokenHolder",
                       "HalfTokenHolder"}

# The Topper PART STUDIO uses a CONFIGURATION input for the embossed expansion
# name. That was the old export path — one call per expansion. TOPPER_ASSEMBLY
# above replaces it, so nothing in the export path sets this any more; it is kept
# because it documents the studio and is what a one-off manual export would need.
#
# Toppers vary by (expansion, size, CARDS PER SLIDING SLOT, sleeved). The
# cards-per-slot axis was missing until the 10-card boxes were designed: the
# embossed text sits in the topper's depth, which is 2.00 mm + one card thickness
# per card, so a 15-card topper is 8.00 mm (Un) and a 10-card one 6.00 mm, and
# the text scales to 65%. A 15-card topper does not fit a 10-card slot.
#
# Confirmed from the studio's Configuration table: a single list input with 6
# options — Echoes, Cities, Unseen, Artifacts, Figures, Blank (matches
# components.py). Each drives a "Text 1" string; Blank has its text suppressed
# (prints a nameless plate). The API needs the input's internal parameterId
# (not the display label) — get it once via GET /configuration and set it here.
TOPPER_CONFIG_PARAM = "List_xRR7r3rgtnzkvq"   # parameterId of the Expansion list
TOPPER_OPTIONS = ["Echoes", "Cities", "Unseen", "Artifacts", "Figures", "Blank"]

# A component's part studio can contain three kinds of part:
#   - the MAIN part, named like the component ("Topper", "Lid", ...);
#   - "letter" parts (Part 3, Part 4, ...) — the embossed expansion/version text
#     as SEPARATE solids (letters aren't contiguous). These DO belong in the
#     export (multi-colour); their count varies per configuration/expansion.
#   - IMPORTED reference parts named like ANOTHER component (the Topper studio
#     imports a Holder for positioning). These must be EXCLUDED.
# So the exporter exports the WHOLE studio, then drops parts that are imports,
# keeping the main part + all letters — stripping locally rather than fetching
# partIds per config (the letter set changes per expansion). The Lid studio
# follows the same pattern (main lid + version letters + an import).


def is_imported(part_name, component_type):
    """A part named after a DIFFERENT component type is an imported reference to
    exclude from a whole-studio export; the main part (== component_type) and
    the letter parts (Part N) are kept."""
    return part_name in ELEMENTS and part_name != component_type


# Per-studio design version. Bump the entry for a studio you have edited in
# Onshape; components exported at an older version go stale and are re-exported
# (see provenance.py). No API calls — you control these.
# The embossed version number comes from set_variables.build_primary, NOT from
# this table, and the two are only equal by hand — see PIPELINE.md, "The
# engraved version is not the recorded version". verify.check_stamp now reads
# the engraving off the exported bytes and refuses a component whose stamp
# disagrees with the generation it is being built at. The Box
# and Holder studios changed at 6.5, so both are 6.5. The Lid is 6.5 as well, but
# for a fix that reached exactly ONE file: a singularity in the CAD stopped
# Onshape extruding the pusher slot out of the lid's foot, so the sleeved FCM 180
# lid printed with that foot solid and no channel for the pusher to slot into.
# Every other lid was checked against that defect's signature — the slot's cut
# faces are simply absent when the extrude fails — and all 33 carry their full
# cut, so they were adopted at 6.5 rather than re-exported (they already match
# the studio). Pushers were ASSUMED to emboss nothing, hence to be version-
# independent, and were left at their own design version — see the 6.6 note
# below, where measuring one showed that assumption was false.
#
# Token holders were in that same "version-independent" group until 6.5, when
# the design narrowed them (Dominion 168 sleeved: 74.80 -> 63.10 mm wide) and
# narrowed the box's front pocket to match. That is a real geometry change, not
# an embossed version string, so both token-holder types move to 6.5 and every
# one still on 6.3 is genuinely stale — a 6.3 holder is too wide for a 6.5
# pocket. Token holders are Dominion-only, so this marks nothing stale in the
# other three games.
#
# 6.6 fixes a defect in the holder: every holder is 0.4 mm thicker than at 6.5.
# Only the Holder studio changed SHAPE, but the whole MONOCHROME set moves to
# 6.6 — Box, Pusher, Holder and both token holders. They share one assembly
# export, so re-exporting them costs nothing beyond the parameter sets the
# holders already need, and it puts 6.6 on the boxes rather than leaving a 6.6
# holder inside a box embossed 6.5.
#
# "Everything but the Holder is only a version bump" was checked rather than
# assumed, by diffing the first export of the run (Compile 105 Un) against its
# predecessor vertex by vertex:
#   Box     every face identical to 0.0000 mm; the ONLY changed geometry is a
#           0.97 x 1.18 x 0.40 mm blob at x=82, z=1.2..1.6 — one version glyph.
#   Holder  Y-min moves exactly -0.4000 mm and nothing else does. X is identical;
#           Y-max +0.046 and Z-max -0.010 are tessellation of curved faces, which
#           is why the SPAN reads +0.446 rather than +0.400. The fix lands
#           entirely on one face.
#   Pusher  bounding box identical on every axis, yet 353 vertices changed inside
#           a 2.5 x 15.6 x 0.4 mm strip — a raised version string. So pushers DO
#           emboss the version and the note above was wrong; because VERSIONS
#           pinned them at 6.3 they were never re-exported, and every pusher on
#           disk still read 6.4. Including them here is what fixes that, and is
#           why Pusher now tracks the design version like the rest.
# The LID is deliberately left at 6.5 (Allan's call), so a refreshed cascade has
# a box reading 6.6 under a lid that still embosses 6.4 — the adopted-lid
# discrepancy PIPELINE.md records under `--changed Lid`.
# 7.0 is the lock catalogue (see LOCK_STANDARD.md). Box, Lid and Pusher all
# carry lock geometry — the pusher's tabs and notch, the lid's recesses and key
# rib, the box's rim cutouts — so all three move together and a cascade must be
# built from one version of the three. Holders and toppers carry no lock feature
# and stay where they are. Confirmed against the meshes before bumping: the CAD
# embosses "7.0" on Box, Lid and Pusher alike, read off the exported parts.
#
# The Lid moving is what closes the adopted-lid discrepancy noted below: it sat
# at 6.5 while everything else went to 6.6, so a refreshed cascade carried a box
# and a lid reading different versions. At 7.0 they agree again.
# A GENERATION is one self-consistent set of per-type versions — what "a v7
# cascade" or "a v6 cascade" actually means, spelled out. A cascade is built at
# one generation and never a mixture, because the 7.0 lock spans three
# components: a pusher, a lid and a box must come from the same version.
#
# parts.csv's `Build` column names the generation a row is built at; blank means
# CURRENT. That is how "these cascades move to 7.0, the rest stay at 6.x for now"
# is expressed, and it replaces reading a rule off box depth.
#
# CAUTION — components dedup ACROSS cascades, so a generation is not free to
# pick per cascade. A pusher's key is (risers, cards, sleeved), so one file
# serves up to three cascades; if one of them is pinned to 6.6 and another
# builds at 7.0, the single file on disk cannot be both. plan_exports reports
# those as generation conflicts rather than silently giving one of them the
# wrong part. Box and Lid are keyed per model, so they never conflict.
GENERATIONS = {
    "7.0": {
        "Box": "7.0", "Lid": "7.0", "Holder": "6.6", "Pusher": "7.0",
        "Topper": "6.6", "TokenHolder": "6.6", "HalfTokenHolder": "6.6",
        "Label": "6.3",
    },
    # Everything as it stood before the lock catalogue. Kept so a cascade can be
    # held back deliberately, and so what "v6" means stays written down rather
    # than being recoverable only from git history.
    "6.6": {
        "Box": "6.6", "Lid": "6.5", "Holder": "6.6", "Pusher": "6.6",
        "Topper": "6.6", "TokenHolder": "6.6", "HalfTokenHolder": "6.6",
        "Label": "6.3",
    },
}
CURRENT = "7.0"

# The default generation's table, kept under its old name: every caller that has
# no cascade in hand (and every existing reader) still sees the current set.
VERSIONS = GENERATIONS[CURRENT]
# The Innovation lid + toppers changed at 6.4. Toppers moved again at 6.6, and
# it is a real geometry change, not an embossed string: the expansion name is no
# longer preceded by a logo body, the plate's depth now tracks
# CardsPerSlidingSlot (2.00 mm + a card thickness per card), and the text scales
# with it. Every 6.4 topper is therefore genuinely stale.
#
# The Blank topper used to be exempt at 6.3, because the 6.4 change was "add an
# expansion logo" and Blank has no expansion to name. That reasoning ends at 6.6:
# no topper carries a logo now, and Blank is no longer the 6 mm taller odd one
# out (45.20 mm, same as its siblings). It is an ordinary topper again, so the
# exemption is gone and expected_version() is a plain lookup.


def generation_name(name):
    """Validate a generation name; blank means CURRENT. Fails here, at planning
    time, rather than after calls have been spent on a typo."""
    g = (name or "").strip() or CURRENT
    if g not in GENERATIONS:
        raise KeyError(f"unknown generation {g!r} in parts.csv `Build`; "
                       f"known: {sorted(GENERATIONS)}")
    return g


def generation(name):
    """The per-type version table for a generation name; CURRENT if blank."""
    return GENERATIONS[generation_name(name)]


def generation_for(build, sleeved):
    """Resolve a parts.csv `Build` cell for ONE sleeving.

    A row's two sleevings are separate cascades and move independently — the
    broken-eleven wave is mostly the UNSLEEVED halves — so the cell may be
    per-sleeving. Accepted forms:

        ''              both sleevings at CURRENT
        '6.6'           both sleevings at 6.6
        'Un:6.6'        unsleeved at 6.6, sleeved at CURRENT
        'Un:6.6 Sl:7.0' each named explicitly (comma or space separated)

    `sleeved` is 'Un' or 'Sl'.
    """
    text = (build or "").strip()
    if ":" not in text:
        return generation_name(text)
    for part in text.replace(",", " ").split():
        tag, _, val = part.partition(":")
        if tag.strip().lower() == sleeved.lower():
            return generation_name(val)
    return CURRENT


def expected_version(comp_type, files, gen=None):
    """The version a component of `comp_type` SHOULD be at, in generation `gen`
    (CURRENT when omitted), plus any per-file exemptions (there are none at
    present; see the 6.6 note above).

    This must be the ONE place the rule lives. It is read when deciding whether
    a component is stale (plan_exports.needs_export) AND when writing a
    provenance row (export._record, --adopt); if those two disagree, a component
    is recorded at a version the staleness check never expects and goes stale
    the instant it is written. `files` — the component's file name, or the set of
    files sharing its key — is what an exemption would key on, and is kept in the
    signature so reinstating one stays a change to this function alone.
    """
    return generation(gen).get(comp_type)


def part_url(eid):
    return f"https://cad.onshape.com/documents/{DID}/w/{WID}/e/{eid}"
