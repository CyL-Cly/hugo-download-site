# -*- coding: utf-8 -*-
"""Generate Hugo folder pages from qsave `share ls --json` output.

Usage:
    python tools/gen_folders.py --input .tmp-shares.json

Creates content/folders/<slug>/index.md for each ACTIVE share.
Re-running is safe: it regenerates the same deterministic slugs, so any
summary or screenshot edits you made in the front matter are preserved.
"""
import argparse
import json
import os
import re
import sys
import datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CATEGORY_RULES = os.path.join(ROOT, "tools", "category-rules.json")
OUT_DIR = os.path.join(ROOT, "content", "folders")
INTROS = os.path.join(ROOT, "tools", "intros.json")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from apply_intros import real_screenshots  # noqa: E402

CATEGORIES = ["软件工具", "设备与固件", "游戏与修改器", "学习资料", "影音媒体", "其他"]


def load_rules():
    with open(CATEGORY_RULES, "r", encoding="utf-8") as f:
        return json.load(f)


def slugify(title, share_id):
    """Deterministic, filesystem-safe slug: pinyin-free, use shareId prefix."""
    ascii_part = re.sub(r"[^a-zA-Z0-9]+", "-", title).strip("-").lower()
    ascii_part = ascii_part[:40]
    suffix = share_id[:8]
    if not ascii_part:
        return "share-" + suffix
    return "%s-%s" % (ascii_part, suffix)


def human_size(n):
    """Empty string when the share does not report a size.

    The API returns size=0 for a few shares. Printing "未知" reads like a defect
    on the page, so callers omit the field instead and say the size was not
    provided.
    """
    if not n or n <= 0:
        return ""
    units = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    v = float(n)
    while v >= 1024 and i < len(units) - 1:
        v /= 1024
        i += 1
    return "%.1f %s" % (v, units[i])


def iso_date(ms):
    if not ms:
        return "2026-01-01"
    try:
        return datetime.datetime.fromtimestamp(
            ms / 1000, datetime.timezone.utc).strftime("%Y-%m-%d")
    except (ValueError, OSError, OverflowError):
        return "2026-01-01"


def categorize(title, rules):
    order = ["学习资料", "影音媒体", "设备与固件", "游戏与修改器", "软件工具"]
    for cat in order:
        for kw in rules.get(cat, []):
            if kw.lower() in title.lower():
                return cat
    for cat, keywords in rules.items():
        if cat in order:
            continue
        for kw in keywords:
            if kw.lower() in title.lower():
                return cat
    return "其他"


def yaml_str(s):
    """Quote a TOML/YAML-ish string safely for front matter."""
    return json.dumps(s, ensure_ascii=False)


def summary_for(it, cat, size):
    base = {
        "软件工具": "软件工具与安装包，来自夸克网盘分享。",
        "设备与固件": "设备相关资源（固件 / 刷机包 / 系统镜像），来自夸克网盘分享。",
        "游戏与修改器": "游戏本体、补丁与修改器资源，来自夸克网盘分享。",
        "学习资料": "学习资料与文档合集，来自夸克网盘分享。",
        "影音媒体": "音视频与媒体资源，来自夸克网盘分享。",
        "其他": "网盘分享资源，来自夸克网盘。",
    }[cat]
    return "%s 体积 %s。" % (base, size) if size else "%s 该分享未提供体积。" % base


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    ap.add_argument("--out", default=OUT_DIR, help="target dir (default: content/folders)")
    ap.add_argument("--active-only", action="store_true", default=True)
    args = ap.parse_args()
    out_dir = args.out

    rules = load_rules()
    intro_map = {}
    if os.path.exists(INTROS):
        with open(INTROS, "r", encoding="utf-8") as f:
            intro_map = json.load(f)
        print("loaded %d intros from tools/intros.json" % len(intro_map))
    else:
        print("WARNING: tools/intros.json not found, falling back to generic text")
    with open(args.input, "rb") as f:
        data = f.read()
    if data.startswith(b"\xff\xfe") or data.startswith(b"\xfe\xff"):
        raw = data.decode("utf-16")
    elif data.startswith(b"\xef\xbb\xbf"):
        raw = data.decode("utf-8-sig")
    else:
        raw = data.decode("utf-8", errors="replace")
    envelope = json.loads(raw)
    items = envelope["data"]["items"]

    # De-duplicate by firstId (same file shared multiple times) keeping newest.
    seen = {}
    for it in items:
        if args.active_only and not it.get("active", True):
            continue
        key = it.get("firstId") or it.get("url")
        if key not in seen or it.get("created", 0) > seen[key].get("created", 0):
            seen[key] = it
    uniq = list(seen.values())
    uniq.sort(key=lambda x: x.get("created", 0), reverse=True)

    if os.path.isdir(out_dir):
        for name in os.listdir(out_dir):
            p = os.path.join(out_dir, name)
            if os.path.isdir(p):
                for f in os.listdir(p):
                    os.remove(os.path.join(p, f))
                os.rmdir(p)
    os.makedirs(out_dir, exist_ok=True)

    counts = {}
    for it in uniq:
        title = (it.get("title") or "未命名分享").strip()
        cat = categorize(title, rules)
        size = human_size(it.get("size", 0))
        slug = slugify(title, it.get("shareId", ""))
        folder = os.path.join(out_dir, slug)
        os.makedirs(folder, exist_ok=True)
        existing = os.path.join(folder, "index.md")
        custom_summary = ""
        custom_shots = []
        if os.path.exists(existing):
            txt = open(existing, "r", encoding="utf-8").read()
            m = re.search(r"^summary:\s*(.+)$", txt, re.M)
            if m:
                custom_summary = m.group(1).strip().strip('"')
            custom_shots = real_screenshots(txt)
        preset = (intro_map.get(it.get("shareId", "")) or {})
        default_summary = summary_for(it, cat, size)
        preset_summary = preset.get("summary", "")
        # A summary that differs from both the generator default and the copy in
        # intros.json was edited by hand -> keep it.
        if custom_summary and custom_summary not in (default_summary, preset_summary):
            summary = custom_summary
        else:
            summary = preset_summary or default_summary
        body = preset.get("intro") or summary
        date = iso_date(it.get("created"))
        url = it.get("url", "")
        file_num = it.get("fileNum", 1)
        lines = [
            "---",
            "title: %s" % yaml_str(title),
            "date: %s" % date,
            "description: %s" % yaml_str("夸克网盘分享 · %s" % cat),
            "summary: %s" % yaml_str(summary),
            "categories: [%s]" % yaml_str(cat),
            "tags: [%s]" % yaml_str("夸克"),
            "item_count: %s" % yaml_str(
                "%d 个文件 · %s" % (file_num, size) if size else "%d 个文件" % file_num),
            "pan_url: %s" % yaml_str(url),
            "share_id: %s" % yaml_str(it.get("shareId", "")),
            "size: %s" % yaml_str(size),
        ]
        if custom_shots:
            lines.append("screenshots:")
            for s in custom_shots:
                lines.append("  - caption: %s" % yaml_str(s.get("caption", "")))
                lines.append("    src: %s" % yaml_str(s["src"]))
        lines += ["---", "", body.strip(), ""]
        with open(os.path.join(folder, "index.md"), "w", encoding="utf-8", newline="\n") as f:
            f.write("\n".join(lines))
        counts[cat] = counts.get(cat, 0) + 1

    print("generated %d folder pages" % len(uniq))
    for c in CATEGORIES:
        if counts.get(c):
            print("  %-14s %d" % (c, counts[c]))


if __name__ == "__main__":
    sys.exit(main())
