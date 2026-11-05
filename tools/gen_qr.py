# -*- coding: utf-8 -*-
"""Generate QR codes (SVG) for Android/mobile-app resources.

Reads data/mobile_apps.json for the share_ids that must be link-free, pulls each
one's pan_url from content/folders/<slug>/index.md, and writes static/qr/<share_id>.svg.

Usage: python tools/gen_qr.py [--quiet]
"""
import argparse
import json
import os
import re
import sys

import qrcode
import qrcode.image.svg

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FOLDERS = os.path.join(ROOT, "content", "folders")
CONFIG = os.path.join(ROOT, "data", "mobile_apps.json")
OUT = os.path.join(ROOT, "static", "qr")


def field(txt, key):
    m = re.search(r"^%s:\s*\"?(.*?)\"?\s*$" % key, txt, re.M)
    return m.group(1) if m else ""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args()

    if not os.path.exists(CONFIG):
        print("ERROR: %s not found" % CONFIG)
        return 1
    ids = set(json.load(open(CONFIG, encoding="utf-8"))["ids"])

    os.makedirs(OUT, exist_ok=True)
    made, skipped = 0, []
    wanted = set()

    for name in sorted(os.listdir(FOLDERS)):
        p = os.path.join(FOLDERS, name, "index.md")
        if not os.path.isfile(p):
            continue
        txt = open(p, encoding="utf-8").read()
        sid = field(txt, "share_id")
        if sid not in ids:
            continue
        url = field(txt, "pan_url")
        if not url:
            skipped.append("%s (no pan_url)" % name)
            continue
        wanted.add(sid + ".svg")
        img = qrcode.make(
            url,
            image_factory=qrcode.image.svg.SvgPathImage,
            box_size=10,
            border=2,
        )
        img.save(os.path.join(OUT, sid + ".svg"))
        made += 1

    # drop stale codes for resources that are no longer flagged
    removed = 0
    for f in os.listdir(OUT):
        if f.endswith(".svg") and f not in wanted:
            os.remove(os.path.join(OUT, f))
            removed += 1

    missing = ids - {w[:-4] for w in wanted}
    if not args.quiet:
        print("qr: %d generated, %d stale removed" % (made, removed))
        if skipped:
            print("skipped: " + ", ".join(skipped))
        if missing:
            print("WARNING: %d ids had no matching page" % len(missing))
    return 0


if __name__ == "__main__":
    sys.exit(main())
