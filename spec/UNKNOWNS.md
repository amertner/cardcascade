# The admitted unknowns

Every number in `cad/` is either derived, measured off a reference and
reproduced, or one of these: a constant that holds on the parameter sets it
was read from and whose origin in Onshape's terms is not known. Each is
recorded where it lives; this is the one list, so that none of them is
mistaken for a derived value and so that what would settle each is written
down. The rule that put them here (`cad/README.md`, "What the fit got
wrong"): a term no derived variable produces is the tell that a rule may be
reproducing the catalogue for the wrong reason.

| constant | where | value | holds on | what would settle it |
|---|---|---|---|---|
| `TRAIL` | `cad/parts/token_holder.py` | `0.0754` em | the tray's STEP to `5.70000` em, and all 18 cached trays to ±0.001 | How Onshape right-aligns a text box. It is not the left bearing and not either right bearing (`l` 0.019, `n` 0.053), and it is the same number under both — so a property of the box, not the string. One tray exported with a different final glyph would test the last hypothesis. |
| `CAP_TRAIL` | `cad/parts/holder.py` | `0.0646` em | five Holder references at em 3.9-10.0, to 0.001 em | The same question in Open Sans Bold, and a different answer (`d` bears 0.0776), so the two are not one rule. Settling `TRAIL` settles this. |
| `Z_BASE` | `cad/parts/topper.py` | `48.450` | all 48 cached toppers | Where the topper's underside sits in the assembly frame. Nothing in `derive.py` produces it; the Topper part studio's mate connector or plane definition would. |
| `BAND_HALF` | `cad/parts/topper.py` | `7.400` | two parameter sets | The front band's half width — "stays a hypothesis" (`spec/TOPPER.md`). A third topper size's STEP, or the sketch dimension. |
| `LIP_ROOM_RISE` | `cad/parts/topper.py` | `2.000` | two parameter sets | The notch floor above the topper's floor. The same STEP would settle both. |
| ~~the `2.600` width offset~~ | `spec/BOX.md`, "The label holders" | `1.600` on `-X`, `1.000` on `+X` | all nine Box references | Not unknown: the side label holder stands on the `-X` end only (`1.600`) and the closing bump on `+X` (`1.000`), and with both built the envelope matches every reference. Listed because BOX.md's "Still open" carried it after its own label-holder section had explained it. |
| the lip-rest residual | `spec/HOLDER.md`, "Chamfer lip rest" | about `±5` mm³ per holder | all ten Holder references, mixed in sign | The chamfer is modelled as `1.500` at 45° on the lower pair and leaves this much; a section through one reference at the rest would say whether it is the chamfer's angle, its edge pair, or the mesh. |
| `Middle` | `cad/parts/holder.py` | a construction plane for the side-slot mirror | — | "A guess, and written here as one" (`spec/HOLDER.md`): the feature carries no geometry of its own, so only the dialog in Onshape says what it is for. |
| `LID_RECESS_STEP` | `cad/lock.py` | `1.700` | every 7.0 lid | Not unknown — set on a test print, and marked *do not tune*. Listed so that no one derives it. |
| `_LSB_C`, `LOGO_MARGIN` | `cad/text.py` | `0.056` em, `0.12` | both Pusher references, all 34 pushers | The fitting rule's own knobs: `_LSB_C` is Orbitron's `C` left bearing read off the font, and the margin is the rule's, not Onshape's — the rule replaces a one-dimensional constraint (`cad/README.md`, "Text sizing is a rule"). Not unknown; a design choice. |
| `LOGO_WIDTH_FRACTION`, `LOGO_DEPTH_FRACTION` | `cad/parts/lid.py` | `0.600`, `0.850` | — | "Taste and not measurement" (`spec/LID.md`): the lid mark's fit is deliberately not Onshape's. Allan's to change. |
| `TWIST`, `NOMINAL_SIZE`, `ARM0` | `cad/marks.py` | `0.1039`, `20.8416`, `-46.14` | the two Innovation plain-mark drawings, to 0.019 mm | Fitted to Allan's drawings rather than read from a sketch. The Logo Flourishes sketch's own dimensions would replace them with expressions. |

Three of these are one question — how Onshape places the right end of a
right-aligned text box — and two are one STEP away.
