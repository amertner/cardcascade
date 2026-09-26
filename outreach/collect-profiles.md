# Instructions for collecting the MakerWorld print-profile links

Paste everything below this line into a Claude session that can browse
makerworld.com. It needs no repository access. Paste its answer back here.

---

I need the id of every print profile on four MakerWorld model pages,
matched to a list of card boxes. Each model page lists its print profiles
(the "Print Profiles" panel, one card per profile, each with a title such as
"Dominion 324 Card Unsleeved (M6.21.10.45-Un)"). Every profile has its own
URL: the model URL followed by `#profileId-<number>`. You can get it from
the profile card's share button, or from the page's data, where the
profiles are listed as "instances" with an "id" and a "title".

For each row below, find the profile whose title contains the row's model
code (the code in brackets, like `M6.21.10.45-Un`), once for the unsleeved
code and once for the sleeved one, and record its profile id number.
Match on the model code, not on the card count, because several boxes
share a count. A model code in a profile title may spell the flags with
dots or hyphens (`M4.21.10.32-M-Un` or `M4.21.10.32-M.Un`), and a profile
title may omit the `-M`: then match on the rest of the code AND the word
"Mat" in the title. Where you cannot find a profile for a code, say so
rather than guessing; where a page holds two profiles for one code (for
instance one per printer), give both ids and their titles.

Answer with ONE JSON object in this exact shape, and nothing else, so it
can be pasted into a file. Keys are the strings in the first column,
copied exactly; values are the profile id numbers as strings:

```json
{
  "Dominion/168 Card": {"Un": "1234567", "Sl": "1234568"},
  "FCM/144 Card": {"Un": "…", "Sl": "…"}
}
```

After the JSON, list separately any row you could not match, and any
profile on the four pages that matched no row (its title and id), so the
list can be checked against the pages.

The four model pages and the rows on each:

### Dominion: https://makerworld.com/en/models/2957494-card-cascade-dominion-store-play-system

| Key (copy exactly) | Unsleeved model code | Sleeved model code |
|---|---|---|
| `Dominion/168 Card` | `S4.16.10.32-Un` | `S4.16.10.32-Sl` |
| `Dominion/202 Card (Mat)` | `M4.21.10.32-M-Un` | `M4.21.10.45-M-Sl` |
| `Dominion/244 Card` | `M4.21.10.32-Un` | `M4.21.10.45-Sl` |
| `Dominion/246 Card` | `S2.40.12-30.32-Un` | `S2.40.12-30.45-Sl` |
| `Dominion/290 Card (Mat)` | `M6.21.10-12.45-M-Un` | `M6.21.10-12.62-M-Sl` |
| `Dominion/300 Card` | `S5.40.12.45-Un` | `S5.40.12.62-Sl` |
| `Dominion/324 Card` | `M6.21.10.45-Un` | `M6.21.10.62-Sl` |
| `Dominion/333 Card` | `S9.21.10.62-Un` | `S9.21.10.62-Sl` |
| `Dominion/400 Card (Mat)` | `M8.40.10.62-M-Un` | `M8.40.10.62-M-Sl` |
| `Dominion/472 Card` | `M2.60.18-40.45-Un` | `M2.60.18-40.62-Sl` |
| `Dominion/560 Card` | `L6.40.12.45-Un` | `L6.40.12.62-Sl` |
| `Dominion/650 Card` | `L8.50.10.62-Un` | `L8.50.10.62-Sl` |

### Food Chain Magnate: https://makerworld.com/en/models/3053860-food-chain-magnate-card-cascade-system

| Key (copy exactly) | Unsleeved model code | Sleeved model code |
|---|---|---|
| `FCM/144 Card` | `M5.6.6.20-Un` | `M5.6.6.32-Sl` |
| `FCM/180 Card` | `L3.18.6.20-Un` | `L3.18.6.20-Sl` |
| `FCM/264 Card` | `M4.18.12.32-Un` | `M4.18.12.45-Sl` |
| `FCM/198 Card` | `S4.18.12.32-Un` | `S4.18.12.45-Sl` |

### Innovation: https://makerworld.com/en/models/3192197-card-cascade-for-innovation-ultimate

| Key (copy exactly) | Unsleeved model code | Sleeved model code |
|---|---|---|
| `Innovation/3 Ages 5 Expansions` | `S5.15.15.45-Un` | `S5.15.15.62-Sl` |
| `Innovation/4 Ages 5 Expansions` | `M5.15.15.45-Un` | `M5.15.15.62-Sl` |
| `Innovation/Single Set` | `S3.15.10.20-Un` | `S3.15.10.32-Sl` |
| `Innovation/Single Mini` | `XS5.15.10.32-Un` | `XS5.15.10.45-Sl` |
| `Innovation/3 Later Ages 5 Expansions` | `S5.10.10.32-Un` | `S5.10.10.45-Sl` |
| `Innovation/4 Later Ages 5 Expansions` | `M5.10.10.32-Un` | `M5.10.10.45-Sl` |
| `Innovation/Three Expansions` | `M8.16.10-16.45-Un` | `M8.16.10-16.62-Sl` |

### Compile: https://makerworld.com/en/models/3042334-compile-main-aux-system-card-cascade

| Key (copy exactly) | Unsleeved model code | Sleeved model code |
|---|---|---|
| `Compile/105 Card` | `S4.7.7.20-Un` | `S4.7.7.32-Sl` |
| `Compile/126 Card` | `S5.7.7.20-Un` | `S5.7.7.45-Sl` |
| `Compile/210 Card` | `L5.7.7.20-Un` | `L5.7.7.45-Sl` |
