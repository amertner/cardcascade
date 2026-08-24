# CC Poster Export (private Figma plugin)

Exports variable-mode combinations of the poster Card as correctly-named
PNGs, zipped — no duplicated frames, no manual configure/export/rename
loop.

## Install (once)

1. Have this folder on your machine (it's in the repo).
2. Figma **desktop** app → Menu → Plugins → Development →
   **Import plugin from manifest…** → pick `figma-plugin/manifest.json`.

## Use

1. Open the poster file and **select the Card** (the frame/section that
   carries the variable modes).
2. Run Plugins → Development → **CC Poster Export**.
3. Pick the modes to iterate. Every mode starts ticked, so *export
   everything* is just open-and-go. Click a collection's name (or its
   twisty) to unfold its modes and pick a subset — `none` then tick the
   two sizes you want. The button counts the run before you start it
   (`Export 4 combinations`), which is the guard against firing off a
   200-PNG export by accident.

   A collection reads one of three ways:

   | Collection | Meaning |
   |---|---|
   | all modes ticked | iterate all of them |
   | some ticked | iterate just those |
   | one ticked | **pinned** to that mode for the whole run |
   | none ticked (`not iterated`) | left at whatever the Card already has |

   So "every size, sleeved only" is Box Sizes = all, Sleeves = just
   `Sleeved`. The picks and the output settings are remembered per file,
   and a remembered subset is unfolded on open so you can see what you
   are about to get.
4. Set the filename pattern:
   - `{Box Sizes}` / `{Sleeves}` (any collection name) → the mode's name,
     e.g. `CC {Box Sizes}{Sleeves}` → `CC 202S.png` if the modes are
     named `202` and `S`.
   - `{Sleeves:Sleeved=S,Unsleeved=U}` → the mode name mapped through
     the given `name=value` pairs (unmapped modes fall back to their
     name), so `CC {Box Sizes}{Sleeves:Sleeved=S,Unsleeved=U}` →
     `CC 202S.png` without renaming any modes.
   - `{text:Model ref}` → the contents of the text layer named
     `Model ref` *after* the modes are applied — useful to put the full
     model number in the filename.

   A placeholder for a collection that isn't being iterated is left
   in the filename as-is; pin the collection to one mode to resolve it.
5. **Export** → **Download zip**.

"Settle ms" is a short pause between flipping modes and rendering; raise
it if exports ever show a half-updated card. The Card's modes are
restored when the run finishes — collections that had no explicit mode
beforehand are cleared rather than left pinned.

## Test

`node figma-plugin/test_ui.js` drives `ui.html`'s selection logic against
a stub DOM (no Figma, no browser, no dependencies) and checks the
tri-states, the combination count, and the clientStorage round-trip
including modes that were deleted since they were remembered.

For a file that instead contains one ready frame per poster, the REST
export script `../figma_export.py` downloads and names them all in one
command without opening Figma.
