# -*- coding: utf-8 -*-
"""Merge writer outputs (tools/intros/out-*.json) into tools/intros.json.

Validates coverage against the batch manifests and reports suspicious entries
(missing text, too short/long, duplicated sentences, repeated openings).

Usage: python tools/merge_intros.py
"""
import glob
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIR = os.path.join(ROOT, "tools", "intros")
OUT = os.path.join(ROOT, "tools", "intros.json")


def load(path):
    with open(path, "r", encoding="utf-8-sig") as f:
        return json.load(f)


def main():
    batches = {}
    for p in sorted(glob.glob(os.path.join(DIR, "batch-*.json"))):
        for it in load(p):
            batches[it["share_id"]] = it

    merged, problems, seen_text = {}, [], {}
    for p in sorted(glob.glob(os.path.join(DIR, "out-*.json"))):
        try:
            data = load(p)
        except ValueError as e:
            problems.append("%s: invalid JSON (%s)" % (os.path.basename(p), e))
            continue
        for row in data:
            sid = (row.get("share_id") or "").strip()
            summary = (row.get("summary") or "").strip()
            intro = (row.get("intro") or "").strip()
            if sid not in batches:
                problems.append("unknown share_id %r in %s" % (sid, os.path.basename(p)))
                continue
            if sid in merged:
                problems.append("duplicate share_id %s" % sid)
                continue
            if not summary or not intro:
                problems.append("empty text for %s" % sid)
                continue
            if len(summary) < 10:
                problems.append("summary too short (%d) %s" % (len(summary), sid))
            if len(intro) < 25:
                problems.append("intro too short (%d) %s" % (len(intro), sid))
            if intro in seen_text:
                problems.append("intro duplicated between %s and %s" % (seen_text[intro], sid))
            seen_text[intro] = sid
            src = batches[sid]
            merged[sid] = {
                "slug": src["slug"],
                "title": src["title"],
                "category": src["category"].strip('"'),
                "summary": summary,
                "intro": intro,
            }

    missing = [s for s in batches if s not in merged]
    for s in missing:
        problems.append("missing %s (%s)" % (s, batches[s]["title"]))

    with open(OUT, "w", encoding="utf-8", newline="\n") as f:
        json.dump(merged, f, ensure_ascii=False, indent=2, sort_keys=True)

    print("batches: %d, merged: %d, missing: %d" % (len(batches), len(merged), len(missing)))

    # repeated opening characters across entries (template smell)
    heads = {}
    for v in merged.values():
        heads[v["summary"][:3]] = heads.get(v["summary"][:3], 0) + 1
    common = sorted(heads.items(), key=lambda kv: -kv[1])[:5]
    print("most common summary openings:", common)

    if problems:
        print("\nPROBLEMS (%d):" % len(problems))
        for p in problems[:40]:
            print("  " + p)
        return 1
    print("all clean")
    return 0


if __name__ == "__main__":
    sys.exit(main())
