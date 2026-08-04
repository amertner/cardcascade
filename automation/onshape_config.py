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
# TODO: TokenHolder (Dominion) and Label (Compile) element ids still needed.
ELEMENTS = {
    "Box":    "6a20c041a900d6b2fca960db",
    "Lid":    "1f5cc8c63b87dcf62f713af0",   # the studio we first test-exported
    "Holder": "8b9578cb73a2958f625ee53d",
    "Pusher": "c1fef5b25da6282bcdc20876",
    "Topper": "46a8affed99afb21fa7202d8",   # configured per Expansion name
}

# The Topper studio uses a CONFIGURATION input for the embossed expansion name,
# so toppers export one-per-expansion (via configurationencodings, like
# onshape_test.py --set), NOT one whole-studio export. This changes the topper
# cost model in plan_exports/export (currently one shared key per sleeving).
# TODO: confirm the configuration parameter id via a /configuration GET.
TOPPER_CONFIG_PARAM = None                 # e.g. "Expansion"


def part_url(eid):
    return f"https://cad.onshape.com/documents/{DID}/w/{WID}/e/{eid}"
