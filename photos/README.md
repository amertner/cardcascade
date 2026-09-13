# photos/ — the pictures the description posters carry

One folder per game, holding POSTER-READY pictures only: a cascade on a
transparent background (RGBA PNG), or on a plain white one that
`make_posters.py` knocks out. The raw phone photos stay where they are
(`cascades/<Game>/Pictures`, `cascades/Innovation/Photos`); what is here is
the chosen, cut version.

`make_posters.py` finds a row's picture by name, so most rows need no
mapping at all:

1. `photos/<Game>/<Short name> <Sleeved|Unsleeved>.png` (or .jpg/.jpeg)
   — when the two sleevings have their own photo;
2. `photos/<Game>/<Short name>.png` — one photo for both;
3. the row's `photo` entry in `posters.json`, `{"Un": "<path>", "Sl":
   ["<path>", <threshold>]}` — any path, which is how a sleeved photo serves
   its unsleeved twin WITHOUT a copy (a photo of a full sleeved cascade
   beats a render of the unsleeved one), and how a knockout threshold is
   tuned for one photo;
4. a cached render under `build/posters/<Game>/`;
5. with `--render`, a fresh Blender render of the open cascade with its
   card stacks;
6. a grey placeholder saying so.

FCM's rows answer to their `Project label` (`Occ 1`, `Alt`, ...) as well as
their Short name. A photo is never duplicated between rows: reuse is a
`photo` line in the spec, so a re-cut photo updates every poster that
shows it.
