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

Nothing is open. The last row — `TWIST`, `NOMINAL_SIZE` and `ARM0` in
`cad/marks.py` — closed 2026-09-05 when the Logo Flourishes sketch was read:
`TWIST` `0.1041` and `ARM0` `-46.1442` are now the sketch's own (one offset
fits all five arms' twenty corners to `0.00002`), and the annulus confirms
`NOMINAL_SIZE` to `0.06 %` without bettering the letters' fit
(`spec/LID.md`, "The Innovation mark, rebuilt"). The same sketch is what the
generated Ultimate mark is built from.

## Settled, and where the record is

Not repeated here; each spec carries its own. The `2.600` box width offset
(`spec/BOX.md`, "The label holders"); the Holder's lip-rest residual
(`spec/HOLDER.md`, "`Lip Rest` is the lip's own LENGTH"); `Middle`, a mate
connector, unused (`spec/HOLDER.md`); `TRAIL` and `CAP_TRAIL`, a quarter of
the font's space advance — what an Onshape text box does at its right edge,
read off two right-aligned samples in four lines and three fonts
(`cad/text.box_trail`, `spec/TOKENHOLDER.md`); `Z_BASE`, the holder's slant
top plus the topper's rear thickness, `LIP_ROOM_RISE`, the holder's
`SLANT_STEP`, and `BAND_HALF`, the front opening's `6` from the pocket's end
plus the pocket's `1.400` inset (`spec/TOPPER.md`); the Ultimate mark's scale-1 export
and the star's `TWIST` and `ARM0` (`spec/LID.md`). Design knobs that were never unknowns —
`LID_RECESS_STEP`, set on a test print; the text rule's `_LSB_C` and
`LOGO_MARGIN`; the lid fit's two fractions — are documented where they live.
