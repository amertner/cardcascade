#!/usr/bin/env python3
"""Fetch the Dominion set glyphs the posters draw, from the Dominion
Strategy wiki, into logos/Dominion/sets/<Set>.png.

One alpha PNG per set, named as cc.cfg spells it, so labels and posters share
a vocabulary. The PNGs are committed and a build never touches the network.
The wiki's HTML sits behind a bot challenge but its files do not, and a
MediaWiki path follows from the file name: images/<md5[0]>/<md5[0:2]>/<File>.

    .venv/bin/python fetch_set_icons.py [--force] [Set ...]
"""
import argparse
import hashlib
import os
import sys
import urllib.request

REPO = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(REPO, "logos", "Dominion", "sets")
WIKI = "https://wiki.dominionstrategy.com/images"

# set name (cc.cfg / posters.json) -> the wiki's file name
ICONS = {
    "Base Set": "Dominion_icon.png",
    "Intrigue": "Intrigue_icon.png",
    "Seaside": "Seaside_icon.png",
    "Alchemy": "Alchemy_icon.png",
    "Prosperity": "Prosperity_icon.png",
    "Cornucopia": "Cornucopia_icon.png",
    "Hinterlands": "Hinterlands_icon.png",
    "Dark Ages": "Dark_Ages_icon.png",
    "Guilds": "Guilds_icon.png",
    "Adventures": "Adventures_icon.png",
    "Empires": "Empires_icon.png",
    "Nocturne": "Nocturne_icon.png",
    "Renaissance": "Renaissance_icon.png",
    "Menagerie": "Menagerie_(expansion)_icon.png",
    "Allies": "Allies_icon.png",
    "Plunder": "Plunder_(expansion)_icon.png",
    "Rising Sun": "Rising_Sun_icon.png",
    "Promo": "Promo_icon.png",
}


def url(filename):
    h = hashlib.md5(filename.encode()).hexdigest()
    return f"{WIKI}/{h[0]}/{h[:2]}/{filename}"


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("sets", nargs="*", help="default: every set in ICONS")
    ap.add_argument("--force", action="store_true", help="re-download existing files")
    args = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)
    wanted = args.sets or list(ICONS)
    bad = [s for s in wanted if s not in ICONS]
    if bad:
        sys.exit(f"unknown set(s): {bad}; known: {list(ICONS)}")
    for s in wanted:
        dest = os.path.join(OUT, f"{s}.png")
        if os.path.exists(dest) and not args.force:
            print(f"  kept     {dest}")
            continue
        req = urllib.request.Request(url(ICONS[s]), headers={"User-Agent": "cardcascade/1.0"})
        with urllib.request.urlopen(req, timeout=30) as r:
            data = r.read()
        if not data.startswith(b"\x89PNG"):
            sys.exit(f"{s}: not a PNG from {url(ICONS[s])}")
        with open(dest, "wb") as f:
            f.write(data)
        print(f"  fetched  {dest}  ({len(data)} bytes)")


if __name__ == "__main__":
    main()
