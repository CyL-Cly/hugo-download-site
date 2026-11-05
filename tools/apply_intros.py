# -*- coding: utf-8 -*-
"""Apply descriptions from tools/intros.json to every folder page.

For each content/folders/<slug>/index.md this rewrites the front matter with a
clean field order, sets `summary` from the intro data, replaces the body text
with the longer intro, and drops the old "no screenshot yet" placeholder block.
Real screenshots (entries with a non-empty src) are preserved.

Usage:
    python tools/apply_intros.py            # apply
    python tools/apply_intros.py --dry-run  # report only
"""
import argparse
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FOLDERS = os.path.join(ROOT, "content", "folders")
INTROS = os.path.join(ROOT, "tools", "intros.json")

FIELD_ORDER = [
    "title", "date", "description", "summary", "categories", "tags",
    "item_count", "pan_url", "share_id", "size",
]


def q(s):
    return json.dumps(s, ensure_ascii=False)


def split_front_matter(txt):
    if not txt.startswith("---\n"):
        raise ValueError("missing front matter")
    end = txt.index("\n---", 4)
    return txt[4:end], txt[end + 4:].lstrip("\n")


def get_field(fm, key):
    m = re.search(r"^%s:\s*(.+?)\s*$" % key, fm, re.M)
    if not m:
        return ""
    v = m.group(1)
    if v.startswith('"') and v.endswith('"'):
        try:
            return json.loads(v)
        except ValueError:
            return v.strip('"')
    return v


def real_screenshots(fm):
    """Collect screenshot entries that actually point at an image."""
    out = []
    lines = fm.split("\n")
    i, n = 0, len(lines)
    while i < n:
        if re.match(r"^screenshots:\s*$", lines[i]):
            i += 1
            cur = {}
            while i < n and (lines[i].startswith((" ", "\t", "-")) or not lines[i].strip()):
                s = lines[i].strip()
                mc = re.match(r'^-?\s*caption:\s*"?(.*?)"?$', s)
                ms = re.match(r'^-?\s*src:\s*"?(.*?)"?$', s)
                if mc:
                    if cur:
                        out.append(cur)
                    cur = {"caption": mc.group(1)}
                elif ms:
                    if cur is None:
                        cur = {}
                    cur["src"] = ms.group(1)
                i += 1
            if cur:
                out.append(cur)
            continue
        i += 1
    return [s for s in out if s.get("src")]


def build_page(slug, fm, intro):
    vals = {k: get_field(fm, k) for k in FIELD_ORDER}
    vals["title"] = vals["title"] or slug
    vals["summary"] = intro["summary"]

    lines = ["---"]
    for k in FIELD_ORDER:
        v = vals.get(k, "")
        if k in ("categories", "tags"):
            lines.append("%s: %s" % (k, v or "[]"))
        elif k == "date":
            lines.append("%s: %s" % (k, v))
        else:
            lines.append("%s: %s" % (k, q(v)))

    shots = real_screenshots(fm)
    if shots:
        lines.append("screenshots:")
        for s in shots:
            lines.append("  - caption: %s" % q(s.get("caption", "")))
            lines.append("    src: %s" % q(s["src"]))

    lines.append("---")
    lines.append("")
    body = (intro.get("intro") or intro["summary"]).strip()
    lines.append(body)
    lines.append("")
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    with open(INTROS, "r", encoding="utf-8") as f:
        intros = json.load(f)

    by_slug = {}
    by_share = {}
    for k, v in intros.items():
        by_share[k] = v
        if v.get("slug"):
            by_slug[v["slug"]] = v

    changed = missing = kept_shots = 0
    for name in sorted(os.listdir(FOLDERS)):
        p = os.path.join(FOLDERS, name, "index.md")
        if not os.path.isfile(p):
            continue
        txt = open(p, "r", encoding="utf-8").read()
        fm, _ = split_front_matter(txt)
        share_id = get_field(fm, "share_id")
        intro = by_share.get(share_id) or by_slug.get(name)
        if not intro:
            print("MISSING intro: %s" % name)
            missing += 1
            continue
        if real_screenshots(fm):
            kept_shots += 1
        new = build_page(name, fm, intro)
        if new != txt:
            changed += 1
            if not args.dry_run:
                with open(p, "w", encoding="utf-8", newline="\n") as f:
                    f.write(new)

    print("rewrote %d pages, missing %d, kept real screenshots on %d"
          % (changed, missing, kept_shots))
    return 1 if missing else 0


if __name__ == "__main__":
    sys.exit(main())
