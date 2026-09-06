# Every Card Cascade in one table - and how to find one that fits your game

I get asked "will this work for *my* game?" quite often, and the honest answer is
that it very often will, even when the game is nowhere in the model name. Card
sizes are fairly standard, and there are now 24 published Cascade designs to
choose from. A Cascade doesn't actually know what game it's for - it knows how
wide a card is, how tall it is, how many piles it has to keep apart, and how deep
each pile is allowed to get.

So here is the whole catalogue in one place, sorted by the thing that actually
decides whether it will work for you: card width. Print it for whatever you like
- they're all free on MakerWorld.

## The three things that decide whether a Cascade fits your game

**1. Card width.** This is the one that either works or doesn't. Every design is
cut for a specific card width, and a card that is too wide simply will not go in.
Going the other way is fine: a narrower card sits in a wider compartment quite
happily, it just has a bit of side-to-side play.

In the CAD each game has a single card width, and the card compartment in the
sliding holders is cut 1.4 mm wider than that. So the real number - the widest
card that will physically go in - is:

|Group|Designed for|Card width|Compartment, unsleeved|Compartment, sleeved|
|:-|:-|-:|-:|-:|
|A|Dominion, FCM|60 mm|61.4 mm|63.4 mm|
|B|Innovation|64 mm|65.4 mm|67.4 mm|
|C|Compile|65 mm|66.4 mm|68.4 mm|

Group A is the "euro" card, around 59 x 91 mm. Groups B and C comfortably take
the standard/poker card at 63.5 x 88 mm.

**One trap worth knowing about:** a poker-sized card does *not* fit a Group A
box, not even the sleeved version. 63.5 mm of card against a 63.4 mm
compartment - it misses by a tenth of a millimetre. If your cards are
poker-sized, you want Group B or C, and an unsleeved Group B box (65.4 mm) will
take them with room to spare.

Measure your own cards rather than trusting the game name, and compare against
the compartment column.

**2. Card height.** Every Cascade in the catalogue is built around a 92 mm card,
and the pocket is 88.5 mm deep, so the top few mm of the card always stands proud
where you can see and grab it. Anything up to 92 mm tall is fine - shorter cards
just sit a little lower. Tarot-size cards are not going to work.

**3. Depth per pile.** Each pile gets a slot of a fixed depth, so what really
matters is millimetres, not card counts. There's a formula further down for
converting the card counts in the table to your own cards.

## Reading the model number

Every design has a model number like **M6.21.10**, which is the whole
specification of the box:

* **M** = how many card slots across. XS = 2, S = 3, **M = 4**, L = 5.
* **6** = how many sliding card holders there are behind the front pocket.
* **21** = how many cards fit in each compartment of the fixed front pocket.
* **10** = how many cards fit in each slot of each sliding holder.

So an M6.21.10 has 4 columns, a front pocket 21 cards deep and 6 sliders behind
it holding 10 cards each: 4 x 21 + 4 x 6 x 10 = 324 cards in 4 x 7 = 28 separate
piles.

Two suffixes turn up in the tables below:

* **-30** as in **S2.40.12-30**: the first slider is a different depth from the
  rest (30 cards instead of 12), for a set with one unusually thick pile.
* **-M** as in **M4.21.10-M**: two front compartments are merged into one wide
  one to hold player mats instead of cards, so the box holds two fewer piles
  than the numbers alone suggest.

On the files themselves you'll also see two more fields - the side label width in
mm, and Un or Sl for unsleeved or sleeved - so the full names of those two are
`M6.21.10.45-Un` and `M4.21.10.45-M-Sl`. I've left both off the tables to keep
them readable.

## The tables

**Cards** and **Front / slider** are for the game the box was designed for; scale
them to your own cards with the formula below. **Piles** is the number of
compartments that keep cards apart, which is usually the number that decides
whether a box suits your game. **Closed size** is the footprint of the closed
Cascade in mm; every one of them is 106.6 mm tall. **Bed** is the print bed you need: Mini
= A1 mini (180 mm), 256 = P1P/P1S/X1C/A1, 350 = H2C/H2D. Where two are listed,
the unsleeved version fits the smaller bed and the sleeved one doesn't.

**Group A - cards up to 61.4 mm wide (63.4 mm in the sleeved boxes)**

|Model|Game|Cards|Piles|Front / slider|Closed size, unsl / sleeved|Bed|Originally for|
|:-|:-|-:|-:|:-|:-|:-|:-|
|**M5.6.6**|FCM|144|24|6 / 6|271x40 / 279x48|256|FCM Milestones|
|**S4.16.10**|Dominion|168|15|16 / 10|208x45 / 214x57.3|256|Dominion: Alchemy, Cornucopia, Guilds|
|**L3.18.6**|FCM|180|20|18 / 6|334x35 / 344x42.9|350|FCM Occupations, box 2 of 2|
|**S4.18.12**|FCM|198|15|18 / 12|208x48.8 / 214x63.3|256|FCM Occupations, 1-box alternative|
|**M4.21.10-M**|Dominion|202|18|21 / 10|271x47 / 279x60.3|256|Half a 400-card set, with mat pocket|
|**M4.21.10**|Dominion|244|20|21 / 10|271x46.9 / 279x60.3|256|Half of Adventures / Nocturne / Plunder|
|**S2.40.12-30**|Dominion|246|9|40 / 12 (1st 30)|208x50 / 214x68.1|256|Dominion base cards, thick piles|
|**M4.18.12**|FCM|264|20|18 / 12|271x48.8 / 279x63.3|256|FCM Occupations, box 1 of 2|
|**S5.40.12**|Dominion|300|18|40 / 12|208x64.1 / 214x86.1|256|Half the Dominion base set|
|**M6.21.10**|Dominion|324|28|21 / 10|271x59.3 / 279x77.1|256|A standard Dominion expansion|
|**S9.21.10**|Dominion|333|30|21 / 10|208x77.9 / 214x102.3|256|A big set on a 256 mm bed|
|**M8.40.10-M**|Dominion|400|34|40 / 10|271x78.9 / 279x105.3|256 / 350|Dominion sets with mats|
|**M2.60.18-40**|Dominion|472|12|60 / 18 (1st 40)|271x63.7 / 279x89.7|256 / 350|Dominion base cards, 6 players|
|**L6.40.12**|Dominion|560|35|40 / 12|334x71 / 344x95.7|350|The whole Dominion base set|
|**L8.50.10**|Dominion|650|45|50 / 10|334x82.7 / 344x111.3|350|Dominion's biggest sets|

**Group B - cards up to 65.4 mm wide (67.4 mm in the sleeved boxes)**

|Model|Game|Cards|Piles|Front / slider|Closed size, unsl / sleeved|Bed|Originally for|
|:-|:-|-:|-:|:-|:-|:-|:-|
|**XS5.15.10**|Innovation|130|12|15 / 10|153x58.5 / 157x68.4|Mini|One Innovation set, A1 mini|
|**S3.15.10**|Innovation|135|12|15 / 10|220x39.3 / 226x50.6|256|One Innovation set|
|**S5.10.10**|Innovation|180|18|10 / 10|220x50.1 / 226x65.1|256|Innovation Ultimate, 3 later ages|
|**M5.10.10**|Innovation|240|24|10 / 10|287x50.1 / 295x65.1|256|Innovation Ultimate, 4 later ages|
|**S5.15.15**|Innovation|270|18|15 / 15|220x62.1 / 226x84.6|256|Innovation Ultimate, 3 ages|
|**M5.15.15**|Innovation|360|24|15 / 15|287x62.1 / 295x84.6|256 / 350|Innovation Ultimate, 4 ages|

**Group C - cards up to 66.4 mm wide (68.4 mm in the sleeved boxes)**

|Model|Game|Cards|Piles|Front / slider|Closed size, unsl / sleeved|Bed|Originally for|
|:-|:-|-:|-:|:-|:-|:-|:-|
|**S4.7.7**|Compile|105|15|7 / 7|222.9x37.7 / 228.9x51.7|256|Compile main + 1 aux|
|**S5.7.7**|Compile|126|18|7 / 7|222.9x42.9 / 228.9x59.7|256|Compile main 2, aux 1 and 2|
|**L5.7.7**|Compile|210|30|7 / 7|359x42.9 / 369x59.7|350|All 10 Compile sets|

## Working out the capacity for your own cards

The card counts above assume the card thickness of the game each box was designed
for. The slot is a fixed depth in mm, so if your cards are thinner you fit more,
and if they're thicker you fit fewer. The assumed thickness is:

|Designed for|Unsleeved|Sleeved|
|:-|-:|-:|
|Dominion, FCM|0.38 mm|0.60 mm|
|Innovation|0.40 mm|0.65 mm|
|Compile|0.40 mm|0.80 mm|

So the depth of a slot is `cards x thickness`. An M6.21.10 unsleeved has a
21 x 0.38 = 8.0 mm front pocket and 10 x 0.38 = 3.8 mm slider slots. If your own
cards are 0.30 mm thick, that same box takes 26 per front compartment and 12 per
slider slot - about 390 cards rather than 324.

Sleeves vary a lot, so measure a stack of ten of yours and divide by ten. If you
land within about 10% of the number in the table, it'll be fine.

## Some starting points

* **Lots of small piles**: L5.7.7 (30 piles) and L3.18.6 (20 piles, and only
  35 mm deep closed) are the ones shaped for a game with many little decks.
* **A few very deep piles**: S2.40.12-30 (9 piles) and M2.60.18-40 (12 piles).
* **The biggest**: L8.50.10, 650 cards in 45 piles.
* **The smallest printer**: XS5.15.10 is the only one that fits an A1 mini.
* **Player mats or boards**: the -M models have a wide pocket at the front for
  them.

## Where to download

Everything is free on MakerWorld. Each game's page has every model for that game
as separate print profiles, sleeved and unsleeved:

* [Card Cascade for Dominion](https://makerworld.com/en/models/2957494-dominion-store-play-system-card-cascade)
* [Card Cascade for Innovation Ultimate](https://makerworld.com/en/models/3192197-card-cascade-for-innovation-ultimate)
* [Card Cascade for Food Chain Magnate](https://makerworld.com/en/models/3053860-food-chain-magnate-card-cascade-system)
* [Card Cascade for Compile](https://makerworld.com/en/models/3042334-compile-main-aux-system-card-cascade)

The game name on the page is just where the design started - the box doesn't care.
The one thing that is game-specific is the logo on the lid, and the labels, which
you can generate blank if you'd rather.

If you print one, please like, rate and boost the model so others can find it.

## Tell me what you fit into them

This is the part I'm actually curious about. If you've used a Cascade for
something that isn't Dominion, Innovation, FCM or Compile, please post it in
[r/cardcascade](https://www.reddit.com/r/cardcascade/) with the game and the model
number you used. If a few of the same requests come up I'm happy to cut new sizes
- the design is parametric, so a new one is mostly a matter of picking the
numbers.

What game would you want one for? :)
