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

# The Topper studio uses a CONFIGURATION input for the embossed expansion name,
# so each topper is a separate export (one per expansion, via
# configurationencodings like onshape_test.py --set). Toppers vary by
# (expansion, size, sleeved) only — modeled that way in plan_exports/export.
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
# (see provenance.py). No API calls — you control these. Defaults to the current
# CC 6.3 design.
VERSIONS = {
    "Box": "6.3", "Lid": "6.3", "Holder": "6.3", "Pusher": "6.3",
    "Topper": "6.3", "TokenHolder": "6.3", "Label": "6.3",
}


def part_url(eid):
    return f"https://cad.onshape.com/documents/{DID}/w/{WID}/e/{eid}"
