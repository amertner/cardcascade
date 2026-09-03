# Bundled typefaces

All from [Google Fonts](https://fonts.google.com/), all under the SIL Open
Font License 1.1, which allows redistribution with the licence text. Kept in
the repository rather than fetched, so a build needs no network and cannot
silently pick up a different release of a face the geometry was fitted to.

| file | used by | for |
|---|---|---|
| `Orbitron-Bold.ttf` | `cad/text.py`, `labelmaker.py` | the product name and version engraved on the parts |
| `OpenSans-Bold.ttf` | `cad/text.py` | the detail line |
| `NotoSerif-Regular.ttf` | `cad/marks.py` | the Innovation wordmark |
| `NotoSerif-Bold.ttf` | `cad/parts/topper.py` | the Topper's expansion names |
| `NotoSerif-BoldItalic.ttf` | — | `Ultimate`, when that mark is rebuilt too |
| `Inter-Regular.ttf`, `DMMono-*.ttf` | `labelmaker.py` | the printed labels |

`NotoSerif-Regular.ttf` and `NotoSerif-BoldItalic.ttf` are static instances cut
from Google's variable fonts (`NotoSerif[wdth,wght]` at `wght 400 / wdth 100`,
and the Italic at `wght 700`) with `fontTools.varLib.instancer` — upstream
ships only the variable files, and build123d's `Text` wants a static face.
`OFL-NotoSerif.txt` is their licence; the others carry the same one.

**`NotoSerif-Bold.ttf` came a different way** and it is worth saying so: it was
served by the Google Fonts CSS API (`fonts.gstatic.com`) rather than cut here,
because the variable font lives on GitHub and this session's GitHub access is
scoped to one repository. It is the **same release, 2.015**, as the Regular
beside it, with the same `unitsPerEm` and `sCapHeight`, but it is SUBSET —
3178 glyphs against the Regular's 3830. That is ample for six English
expansion names and would not be for anything else. Re-cut it from the
variable font if this ever needs to set text outside basic Latin.

**Which face a mark is set in is a measurement, not a choice** — see
`cad/text.py` for Orbitron and Open Sans, and `spec/LID.md` for Noto Serif,
which was confirmed against Allan's own drawing to `0.019 mm` over 109 mm of
wordmark before anything was built with it.
