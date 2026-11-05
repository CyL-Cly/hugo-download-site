# -*- coding: utf-8 -*-
"""Split the 215 folder pages into batches for intro writing.

Reads every content/folders/<slug>/index.md front matter and writes
tools/intros/batch-NN.json  (input for writers)
plus prints a summary.

Usage: python tools/build_intro_batches.py [--size 44]
"""
import argparse
import json
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FOLDERS = os.path.join(ROOT, "content", "folders")
OUT = os.path.join(ROOT, "tools", "intros")


def field(txt, key):
    m = re.search(r"^%s:\s*\"?(.*?)\"?\s*$" % key, txt, re.M)
    return m.group(1).strip().strip('"') if m else ""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--size", type=int, default=44)
    args = ap.parse_args()

    items = []
    for name in sorted(os.listdir(FOLDERS)):
        p = os.path.join(FOLDERS, name, "index.md")
        if not os.path.isfile(p):
            continue
        txt = open(p, "r", encoding="utf-8").read()
        items.append({
            "slug": name,
            "share_id": field(txt, "share_id"),
            "title": field(txt, "title"),
            "category": field(txt, "categories").strip("[]"),
            "item_count": field(txt, "item_count"),
            "size": field(txt, "size"),
            "date": field(txt, "date"),
        })

    os.makedirs(OUT, exist_ok=True)
    for f in os.listdir(OUT):
        if f.startswith("batch-"):
            os.remove(os.path.join(OUT, f))

    n = 0
    for i in range(0, len(items), args.size):
        chunk = items[i:i + args.size]
        n += 1
        path = os.path.join(OUT, "batch-%02d.json" % n)
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            json.dump(chunk, f, ensure_ascii=False, indent=2)
        print("batch-%02d.json  %d items" % (n, len(chunk)))
    print("total %d items in %d batches" % (len(items), n))


if __name__ == "__main__":
    main()
