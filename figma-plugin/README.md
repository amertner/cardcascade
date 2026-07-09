# CC Poster Export (private Figma plugin)

Exports every variable-mode combination of the poster Card as
correctly-named PNGs, zipped — no duplicated frames, no manual
configure/export/rename loop.

## Install (once)

1. Have this folder on your machine (it's in the repo).
2. Figma **desktop** app → Menu → Plugins → Development →
   **Import plugin from manifest…** → pick `figma-plugin/manifest.json`.

## Use

1. Open the poster file and **select the Card** (the frame/section that
   carries the variable modes).
2. Run Plugins → Development → **CC Poster Export**.
3. Tick the variable collections to iterate (e.g. *Box Sizes* and
   *Sleeves*) — the plugin exports the cartesian product of their modes.
4. Set the filename pattern:
   - `{Box Sizes}` / `{Sleeves}` (any collection name) → the mode's name,
     e.g. `CC {Box Sizes}{Sleeves}` → `CC 202S.png` if the modes are
     named `202` and `S`.
   - `{text:Model ref}` → the contents of the text layer named
     `Model ref` *after* the modes are applied — useful to put the full
     model number in the filename.
5. **Export all combinations** → **Download zip**.

"Settle ms" is a short pause between flipping modes and rendering; raise
it if exports ever show a half-updated card. The Card's original modes
are restored when the run finishes.

For a file that instead contains one ready frame per poster, the REST
export script `../figma_export.py` downloads and names them all in one
command without opening Figma.
