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
| `TRAIL` | `cad/parts/token_holder.py` | `0.0754` em | three tray STEPs, `l` and `n` endings, and all 18 cached trays | INPUT. What Onshape's text box does at its right edge: the INK ends this far short of the box's edge, whatever the last glyph. Allan's right-aligned sample (`spec/reference/Text right-aligned sample.step`, three lines in three fonts, boxes 10 tall with one shared right edge at `x 110.135`) CONFIRMS the mechanism and the Open Sans number — see `CAP_TRAIL` — but its Orbitron line reads `0.0677` em, and its ink run is 1.4 % short of Orbitron BOLD's, kerning being only `+0.005` em, so that line is almost certainly Orbitron Regular and does not speak to the parts' Bold. No font metric is `0.0754` or `0.0646` (nearest: a quarter of the space advance, `0.0765` and `0.0649`, which puts the tray's em at `5.69917` against `5.70000` read two ways). Still wanted: the same sample line in **Orbitron Bold**. |
| `CAP_TRAIL` | `cad/parts/holder.py` | `0.0646` em | five Holder references at em 3.9-10.0, and the right-aligned sample | SETTLED AS A FACT, not yet as a formula. The sample's `Open Sans Bold` line, right-aligned in a 10-tall box to `x 110.135`, ends its ink `0.0646` em short of it — the holder's constant to four decimals, with the same last glyph `d`. So this IS what an Onshape text box in Open Sans Bold does at its right edge. What the number is in font terms is unknown; it is not the `d`'s right bearing (`0.0776`) nor any table metric. The same STEP also fixes Onshape's box HEIGHT at `0.72` em for Open Sans, which is not its cap height (`0.7339`). |
| `BAND_HALF` | `cad/parts/topper.py` | `7.400` | three parameter sets, M and S | WORK. The `Divider` sketch has no dimensions and maps onto points imported from the holder (Allan, 2026-09-04), so `7.400` is some holder point's distance from the slot's centre; finding which — the lip's plan, the scallop, the end block — derives it. |
| `TWIST`, `NOMINAL_SIZE`, `ARM0` | `cad/marks.py` | `0.1039`, `20.8416`, `-46.14` | the two Innovation plain-mark drawings, to 0.019 mm | WORK. The Logo Flourishes sketch is on file (`logos/Innovation/sketch/Logo Flourishes.dxf`, 2026-09-04) and agrees where compared — `LINE_WIDTH` `0.600`, the annulus bore within `0.003` of the font's `I`, arms `0.600 x 3.000`. Reading `TWIST` and `ARM0` off its five arm rectangles, and `NOMINAL_SIZE` off the annulus, replaces three fitted numbers with the sketch's; the same sketch is the material for generating the Ultimate mark instead of drawing it. |

`TRAIL` and `CAP_TRAIL` are one question — what an Onshape text box's right
edge is, in font terms — now confirmed as a mechanism and measured for Open
Sans Bold; the other two are reading a holder point and a sketch.

## Settled, and where the record is

Not repeated here; each spec carries its own. The `2.600` box width offset
(`spec/BOX.md`, "The label holders"); the Holder's lip-rest residual
(`spec/HOLDER.md`, "`Lip Rest` is the lip's own LENGTH"); `Middle`, a mate
connector, unused (`spec/HOLDER.md`); `TRAIL`'s independence from the last
glyph (`spec/TOKENHOLDER.md`); `Z_BASE`, the holder's slant top plus the
topper's rear thickness, and `LIP_ROOM_RISE`, the holder's `SLANT_STEP`
(`spec/TOPPER.md`); the Ultimate mark's scale-1 export (`spec/LID.md`). Design knobs that were never unknowns —
`LID_RECESS_STEP`, set on a test print; the text rule's `_LSB_C` and
`LOGO_MARGIN`; the lid fit's two fractions — are documented where they live.
