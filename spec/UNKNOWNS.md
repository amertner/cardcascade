# What is still unknown

Every number in `cad/` is either derived, or measured off a reference and
reproduced, or one of these: a constant that holds on the parameter sets it
was read from and whose origin in Onshape's terms is not known. This is the
one list of them, kept to what is STILL OPEN — an entry leaves when it is
derived or explained, and the spec that settled it carries the record. The
rule that puts a number here (`cad/README.md`, "What the fit got wrong"): a
term no derived variable produces is the tell that a rule may reproduce the
catalogue for the wrong reason.

Each row says what would settle it, and whether that is a file from Onshape
(INPUT) or a piece of work here (WORK).

| constant | where | value | holds on | what would settle it |
|---|---|---|---|---|
| `TRAIL` | `cad/parts/token_holder.py` | `0.0754` em | three tray STEPs, `l` and `n` endings, and all 18 cached trays | INPUT. It is a property of the right-aligned text box and not of the last glyph (settled 2026-09-04), but what Onshape does with `0.0754` em is not known. A plate with two right-aligned strings of known size and different last glyphs, exported as a STEP, would say. |
| `CAP_TRAIL` | `cad/parts/holder.py` | `0.0646` em | five Holder references at em 3.9-10.0 | INPUT — the same question in Open Sans Bold, and a different number (`d` bears `0.0776`), so the two are not one rule. The same plate, with an Open Sans string on it, settles both. |
| `Z_BASE` | `cad/parts/topper.py` | `48.450` | all 48 cached toppers and the four S references | INPUT. Where the topper's underside sits in the assembly frame; nothing in `derive.py` produces it. The Topper's mate connector definition in Onshape, or the Holder and its Topper exported together from the assembly, would let it be derived from the holder's features. |
| `BAND_HALF` | `cad/parts/topper.py` | `7.400` | three parameter sets, M and S | INPUT. Constant across sizes; whether it IS `#FootDistanceFromWall` (`spec/TOPPER.md`) only the `Divider` sketch's own dimension can say. |
| `LIP_ROOM_RISE` | `cad/parts/topper.py` | `2.000` | three parameter sets, M and S | INPUT. `#LipHeight` in the same sketch would name it. |
| `Middle` | `cad/parts/holder.py` | a construction plane for the side-slot mirror | — | INPUT. "A guess, and written here as one" (`spec/HOLDER.md`): the feature carries no geometry, so only its dialog in Onshape says what it is for. A screenshot settles it. |
| `TWIST`, `NOMINAL_SIZE`, `ARM0` | `cad/marks.py` | `0.1039`, `20.8416`, `-46.14` | the two Innovation plain-mark drawings, to 0.019 mm | WORK. The Logo Flourishes sketch is on file (`logos/Innovation/sketch/Logo Flourishes.dxf`, 2026-09-04) and agrees where compared — `LINE_WIDTH` `0.600`, the annulus bore within `0.003` of the font's `I`, arms `0.600 x 3.000`. Reading `TWIST` and `ARM0` off its five arm rectangles, and `NOMINAL_SIZE` off the annulus, replaces three fitted numbers with the sketch's; the same sketch is the material for generating the Ultimate mark instead of drawing it. |

Two of these are one question — how Onshape places the right end of a
right-aligned text box — and two more are one sketch's dimensions.

## Settled, and where the record is

Not repeated here; each spec carries its own. The `2.600` box width offset
(`spec/BOX.md`, "The label holders"); the Holder's lip-rest residual
(`spec/HOLDER.md`, "`Lip Rest` is the lip's own LENGTH"); `TRAIL`'s
independence from the last glyph (`spec/TOKENHOLDER.md`); the Ultimate mark's
scale-1 export (`spec/LID.md`). Design knobs that were never unknowns —
`LID_RECESS_STEP`, set on a test print; the text rule's `_LSB_C` and
`LOGO_MARGIN`; the lid fit's two fractions — are documented where they live.
