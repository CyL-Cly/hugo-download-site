# -*- coding: utf-8 -*-
"""Build data/device_meta.json from folder page titles.

Only infers what the *title* actually states (brand / model / device type).
Version numbers are NOT inferred: the share listing carries no file names, so
the real firmware build is unknown until someone opens the share. Pages say so
explicitly instead of guessing.

Run after gen_folders.py when pages change:

    python tools/gen_device_meta.py            # report only
    python tools/gen_device_meta.py --write    # update data/device_meta.json

The JSON is hand-editable; keep existing entries and only fill gaps with
--write (so manual corrections survive regeneration).
"""
import argparse
import json
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FOLDERS = os.path.join(ROOT, "content", "folders")
OUT = os.path.join(ROOT, "data", "device_meta.json")
TARGET_CATEGORY = "设备与固件"

BRANDS = [
    ("一加", ["一加", "OnePlus", "oneplus"]),
    ("Netgear", ["RAX"]),
    ("微软", ["Windows"]),
    ("小米", ["小米", "Redmi", "红米"]),
    ("三星", ["三星", "Samsung"]),
    ("华为", ["华为", "Honor", "荣耀"]),
    ("苹果", ["iPhone", "iPad"]),
]

# tablet / router / system-image detection on the title tail
TYPES = [
    ("平板", ["Pad"]),
    ("路由器", ["RAX", "OpenWrt", "oenwrt"]),
    ("系统镜像", ["Windows", "镜像"]),
]


def field(fm, key):
    m = re.search(r"^%s:\s*(.+?)\s*$" % re.escape(key), fm, re.M)
    if not m:
        return ""
    v = m.group(1).strip()
    if v.startswith('"'):
        try:
            return json.loads(v)
        except ValueError:
            return v.strip('"')
    return v


def detect_brand(title):
    for name, keys in BRANDS:
        if any(k in title for k in keys):
            return name
    return ""


def detect_type(title):
    for name, keys in TYPES:
        if any(k in title for k in keys):
            return name
    return "手机" if detect_brand(title) == "一加" else ""


def model_of(title, brand):
    """Strip brand words and noise, keep the model part of the title."""
    t = title
    for noise in ("一加", "OnePlus", "oneplus", "ONEPLUS"):
        t = t.replace(noise, " ")
    t = re.sub(r"\s+", " ", t).strip(" -_")
    if brand == "Netgear":
        m = re.search(r"RAX\s*\d+\s*[A-Za-z]*", t, re.I)
        if m:
            return re.sub(r"\s+", "", m.group(0)).upper().replace("RAXM", "RAX")
    return t


def screenshots_none(_):
    return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args()

    existing = {}
    if os.path.exists(OUT):
        with open(OUT, "r", encoding="utf-8") as f:
            existing = json.load(f)
        existing.pop("_comment", None)

    rows, meta = [], dict(existing)
    for name in sorted(os.listdir(FOLDERS)):
        p = os.path.join(FOLDERS, name, "index.md")
        if not os.path.isfile(p):
            continue
        txt = open(p, encoding="utf-8").read()
        fm = txt[4:txt.index("\n---", 4)]
        if TARGET_CATEGORY not in field(fm, "categories"):
            continue
        title = field(fm, "title")
        share_id = field(fm, "share_id")
        brand = detect_brand(title)
        dtype = detect_type(title)
        model = model_of(title, brand)
        rows.append((share_id, title, brand, model, dtype))
        if share_id and share_id not in meta:
            meta[share_id] = {"brand": brand, "model": model, "type": dtype}

    print("firmware pages: %d | in data file: %d" % (len(rows), len(meta)))
    print("%-10s %-30s %-8s %-18s %s" % ("share", "title", "brand", "model", "type"))
    for sid, title, brand, model, dtype in rows:
        mark = "" if sid in existing else "  <- new"
        print("%-10s %-30s %-8s %-18s %s%s"
              % (sid[:8], title[:30], brand or "-", model or "-", dtype or "-", mark))

    # prune entries whose page left the 设备与固件 category
    live = {r[0] for r in rows}
    stale = [k for k in meta if k not in live]
    for k in stale:
        del meta[k]
    if stale:
        print("\npruned %d stale entries (page no longer 设备与固件)" % len(stale))

    if args.write:
        payload = {
            "_comment": "设备与固件页的结构化字段（品牌/机型/类型），按 share_id。"
                        "只填标题能确证的信息；版本号无法从分享列表取得，页面会提示自行核对。"
                        "可手工修正，重跑 gen_device_meta.py 只补缺失项。",
        }
        payload.update({k: meta[k] for k in sorted(meta)})
        os.makedirs(os.path.dirname(OUT), exist_ok=True)
        with open(OUT, "w", encoding="utf-8", newline="\n") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
            f.write("\n")
        print("\nwrote %s (%d entries)" % (OUT, len(meta)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
