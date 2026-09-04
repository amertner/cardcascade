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
| `BAND_HALF` | `cad/parts/topper.py` | `7.400` | all eight parameter sets | INPUT. The `Divider` sketch maps onto the holder's imported `Top slant angle` triangle (Allan, 2026-09-04), and that fixes the DIAGONAL — its top leg is `sliderDistance - 1.2`, `7.2` on the 15-card unsleeved set and `5.2` to `10.95` across the eight — not the band, which is `14.800` on all of them. The band belongs to `Remove most of front` and its companions, which take the front wall away over `calSlotwidth - 2 * 7.4` centred on each slot; that sketch's own width or margin expression is the number. |
| `TWIST`, `NOMINAL_SIZE`, `ARM0` | `cad/marks.py` | `0.1039`, `20.8416`, `-46.14` | the two Innovation plain-mark drawings, to 0.019 mm | WORK. The Logo Flourishes sketch is on file (`logos/Innovation/sketch/Logo Flourishes.dxf`, 2026-09-04) and agrees where compared — `LINE_WIDTH` `0.600`, the annulus bore within `0.003` of the font's `I`, arms `0.600 x 3.000`. Reading `TWIST` and `ARM0` off its five arm rectangles, and `NOMINAL_SIZE` off the annulus, replaces three fitted numbers with the sketch's; the same sketch is the material for generating the Ultimate mark instead of drawing it. |

Both are work here, not input: a holder point to name and a sketch to read.

## Settled, and where the record is

Not repeated here; each spec carries its own. The `2.600` box width offset
(`spec/BOX.md`, "The label holders"); the Holder's lip-rest residual
(`spec/HOLDER.md`, "`Lip Rest` is the lip's own LENGTH"); `Middle`, a mate
connector, unused (`spec/HOLDER.md`); `TRAIL` and `CAP_TRAIL`, a quarter of
the font's space advance — what an Onshape text box does at its right edge,
read off two right-aligned samples in four lines and three fonts
(`cad/text.box_trail`, `spec/TOKENHOLDER.md`); `Z_BASE`, the holder's slant
top plus the topper's rear thickness, and `LIP_ROOM_RISE`, the holder's
`SLANT_STEP` (`spec/TOPPER.md`); the Ultimate mark's scale-1 export
(`spec/LID.md`). Design knobs that were never unknowns —
`LID_RECESS_STEP`, set on a test print; the text rule's `_LSB_C` and
`LOGO_MARGIN`; the lid fit's two fractions — are documented where they live.
