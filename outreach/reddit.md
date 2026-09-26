# Reddit: the launch post, and where to put it

Drafts for the first round of posts. Nothing here is posted by a script;
copy, adjust, post. **No post links GitHub** (Allan, 2026-09-26): the
catalogue the posts point at is the PINNED POST on r/cardcascade, whose
text is `outreach/catalogue-reddit.md`, written by `make_catalogue.py
--reddit` from the same data as `CATALOGUE.md`. Once it is posted, put its
URL where the drafts say `<pinned post>`.

## The plan

1. **Home base is r/cardcascade.** Post the catalogue there first, pinned,
   so every other post can link ONE place that stays current: the
   subreddit, which links the catalogue, which links MakerWorld. Cross-posts
   go stale; the pinned post does not.
2. **One post per community, written for that community**, not one text
   everywhere. Reddit's spam filter and most mods treat identical text in
   several subs as spam, and each audience cares about a different thing:
   the mechanism (3D printing subs), the game (game subs), the print
   (Bambu sub).
3. **Space them out, a few days apart**, and answer every comment for the
   first day. Engagement in the first hours is what the ranking rewards.
4. **Lead with a photo or the GIF, not a link.** Image posts and native
   video outrank link posts nearly everywhere. Put the links in the first
   comment where a sub bans them in the body.

## Where, and each sub's rules to check before posting

| Subreddit | Why | What to check first |
|---|---|---|
| r/cardcascade | Home base: the pinned catalogue post | Nothing, it is yours |
| r/functionalprint | The best fit: a mechanism that does a job, free files. Big and receptive to organisers | Requires a photo of the PRINTED thing in use, and the files link in a comment |
| r/3Dprinting | Largest audience. Weekend threads bury posts; post midweek, morning US time | Self-promotion rule: the files must be free, and the post must be about the print, not the download |
| r/BambuLab | Every cascade is a Bambu Studio project with plates and filaments set; the H2-series lids are a talking point | Flair the post "Model"; MakerWorld links are welcome there |
| r/boardgames | The people with the games. Strict about self-promotion (the 10:1 rule: nine ordinary comments for every post that promotes your own thing) | Post it as a "look what I made for my collection" with a photo; put the links in a reply, not the body |
| r/dominion | The game with the most cascades and the most cards to store. A sizing table per expansion is exactly what that sub asks about | Small and friendly; a text post with the Dominion table inline works |
| r/boardgameorganizers, r/tabletopgamedesign | Smaller, on-topic subs. Organisers is the more useful of the two | Read the last month of posts and match their tone |

Innovation, Compile and FCM have no subreddit worth a post of their own;
they get a mention in the r/boardgames post and a row in the catalogue.

## Post 1: r/cardcascade (pinned)

**Title:** Does a Card Cascade fit your game? Every size by card width and slot depth

**Body:** the whole of `outreach/catalogue-reddit.md`, pasted as a text
post in Reddit's markdown editor (switch the editor to Markdown first, or
the tables flatten). Regenerate it with `make_catalogue.py --reddit` and
edit the post whenever a cascade is added. Pin it, and put its URL in the
subreddit's sidebar.

## Post 2: r/functionalprint

**Title:** Store-and-play card box: closed it's a labelled box, open it
cascades every pile into view. Free files for four games, fits many more.

**Post type:** image or video (the open/close GIF), files link in the
first comment.

**Body (or first comment):**

I got tired of card games that live in a big box and need ten minutes of
setup, so I designed this. The sliding holders ride on ribs in the box; lift
the front and the whole stack rises in a staircase, every pile with its top
card showing. Push it back down, lid on, it's a box with a slide-in label.

Details for the print-minded: two-colour projects for Bambu Studio (white
plus black for the logo and lettering), no supports anywhere, the seam is
placed on a rib so it never touches a sliding face, and the holders are
printed as thin strips at 45° to pack a plate. A full cascade is 3 to 5
plates depending on size. Sizes for 256 mm beds and for the 325 mm H2
series.

Designed so far for Dominion (all expansions), Innovation, Compile and Food
Chain Magnate, but the slots are cut for the card size, not the game, so if
your game uses 59x91, 63x88, 65x92 or 41x63 mm cards there is probably a
box that fits. Table of all of them with sizes, capacities and links:
<pinned post> on r/cardcascade.

Files: https://makerworld.com/en/collections/33559137-card-cascades

## Post 3: r/dominion

**Title:** A 3D-printed box for every Dominion expansion that opens straight
into play (free files, sizing table inside)

**Body:**

[photo]

I've been printing these for my collection for a while and finally have
one for every expansion, sleeved and unsleeved. Closed, each expansion is a
labelled box the size of a paperback. Open, the Kingdom piles rise in a
staircase with the base cards in front, so setup is "take the box out,
lift". Randomisers fit, mats have their own slot in the sets that need
them, and there is a token holder.

Which box for which expansion (a 256 mm bed needs a pair for the biggest
sets):

[paste the two Dominion expansion tables from CATALOGUE.md, "Dominion: which cascade for which expansion"]

All free on MakerWorld, with labels for every set as a separate project:
https://makerworld.com/en/collections/33559137-card-cascades

Every size in one table, and requests: <pinned post> on r/cardcascade

## Post 4: r/BambuLab

**Title:** Card Cascade: two-colour store-and-play card boxes, a full Studio
project per size, incl. sizes for the H2 series

**Body:**

Plates, filaments and process settings are all in the project, so it's
open, pick the plate, print. White in slot 1 and black in slot 2 for the
lettering and logo; no supports; the seam sits on a rib so the sliding
faces stay clean. Four games so far, and a table of every size so you can
check your own game's cards: <pinned post> on r/cardcascade.

Files: https://makerworld.com/en/collections/33559137-card-cascades

## Post 5: r/boardgames

**Title:** I designed a card box that opens into a cascade of every pile
for Dominion, Innovation, Compile and FCM, and made the files free

Image post, links in a comment. Keep the body to the photo and two lines:
what it is, and that the files are free. Answer the "does it fit X" replies
with the pinned post's link.

## Pictures to use

- `cascades/Dominion/Card Cascade Dominion Landscape Hero.png`: the
  store/lift/play triptych, the best single image.
- `cascades/Innovation/IU Opening.gif`, `cascades/Innovation/IU demo.gif`:
  the open/close motion for r/functionalprint.
- `cascades/Dominion/CC Demo.mp4`: native video for r/3Dprinting.
- `cascades/<Game>/<cascade>.png`: the per-cascade posters, for a reply
  about one size.

## Things to settle before posting

- The four MakerWorld project URLs, so the catalogue links a family to its
  own page rather than to the collection (`catalogue.json`, `makerworld`).
- The Mini Cards cascades (41 x 63 mm) are not published yet and are kept
  out of the catalogue (`catalogue.json`, `hidden`). They are the generic
  offer, the one a stranger with a mini-card game would want: when they go
  on MakerWorld, remove them from `hidden` and add the model URL.
- r/cardcascade's sidebar: a one-line description, the collection link and
  the catalogue link, so a visitor from a cross-post finds both.
