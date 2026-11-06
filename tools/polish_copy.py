# -*- coding: utf-8 -*-
"""Strip speculation from resource copy (tools/intros.json).

Review feedback: many one-liners read like guesses ("可能是…", "从名字看…",
"应该和文档有关"). The share listing carries no file names, so such guesses can
never be checked. This script rebuilds the copy from the fields that ARE known —
title, category, file count, size, share date, plus brand/model for device
pages — and states openly what the share does not say.

    python tools/polish_copy.py --report out.txt   # review the diff
    python tools/polish_copy.py --write            # rewrite tools/intros.json
    python tools/apply_intros.py                   # push into content pages
"""
import argparse
import json
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FOLDERS = os.path.join(ROOT, "content", "folders")
INTROS = os.path.join(ROOT, "tools", "intros.json")
DEVICE_META = os.path.join(ROOT, "data", "device_meta.json")

HEDGES = [
    "从名字看", "看名字", "从命名", "按命名", "需要打开文件才知道", "具体是哪一个",
    "应是", "应属", "可能是", "大概率", "据说", "大概", "不确定", "按原始标题",
    "疑似", "看上去", "推测", "判断", "应该", "应能", "多半", "或许",
    "没有更多说明", "需下载后确认", "看不出", "一般指", "不妨先", "需自行",
    "可能", "估计", "大概率", "无法判断", "不好判断", "只能", "结合",
    "以应用里显示", "先打开看看", "需解压后", "自行确认", "再做判断",
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


def load_facts():
    out = {}
    for name in os.listdir(FOLDERS):
        p = os.path.join(FOLDERS, name, "index.md")
        if not os.path.isfile(p):
            continue
        txt = open(p, encoding="utf-8").read()
        fm = txt[4:txt.index("\n---", 4)]
        sid = field(fm, "share_id")
        cat = field(fm, "categories").strip("[]").replace('"', "").strip()
        out[sid] = {
            "slug": name,
            "title": field(fm, "title"),
            "date": field(fm, "date"),
            "size": field(fm, "size"),
            "item_count": field(fm, "item_count"),
            "cat": cat,
        }
    return out


def load_device_meta():
    if not os.path.exists(DEVICE_META):
        return {}
    d = json.load(open(DEVICE_META, encoding="utf-8"))
    d.pop("_comment", None)
    return d


def has_hedge(text):
    return any(h in text for h in HEDGES)


def tidy(text):
    text = text.strip()
    text = re.sub(r"\s+", " ", text)
    # drop empty clauses left by conditional joins
    text = re.sub(r"[，、；]{2,}", "，", text).strip("，、；")
    if text and text[-1] not in "。！？":
        text += "。"
    return text


def file_clause(f):
    n = f["item_count"].split(" ")[0] or "1"
    return "分享内共 %s 个文件" % n


def size_clause(f, skip=False):
    if f["size"] in ("", "未知"):
        return "分享未提供体积"
    return "" if skip else "体积 %s" % f["size"]


def join(*parts):
    return "，".join(p for p in parts if p)


def has_size_word(text):
    return re.search(r"\d+(\.\d+)?\s*(B|KB|MB|GB|TB)", text) is not None


def rewrite(old_summary, f, dm):
    title, cat = f["title"], f["cat"]

    # --- device / firmware: brand + model are stated by the title itself ---
    if dm.get("brand") and dm.get("model"):
        name = "%s %s" % (dm["brand"], dm["model"])
        kind = dm.get("type") or "设备"
        summary = tidy("%s %s相关资源，%s，分享于 %s" % (
            name, kind, size_clause(f), f["date"]))
        body = tidy("%s。标题只给出机型（%s），未标注系统版本、适用区域与刷机方式。"
                    "下载后请先打开文件夹核对版本与机型，确认无误再动手。" % (
                        join(file_clause(f), size_clause(f), "分享日期 " + f["date"]),
                        name))
        return summary, body

    # --- everything else: reuse the summary only when it states no guess ---
    known = bool(old_summary) and len(old_summary) >= 15 and not has_hedge(old_summary)
    if known:
        summary = tidy(old_summary)
    else:
        summary = tidy("「%s」（%s），%s，分享于 %s" % (
            title, cat, size_clause(f), f["date"]))

    body = tidy("%s。标题未标注具体版本号与更多说明，以网盘内文件名与版本为准。" % (
        join(file_clause(f), size_clause(f, skip=has_size_word(summary)),
             "分享日期 " + f["date"])))
    return summary, body


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--report", help="write a human-readable diff report here")
    args = ap.parse_args()

    fmap, dmeta = load_facts(), load_device_meta()
    intros = json.load(open(INTROS, encoding="utf-8"))
    report = []
    changed = 0

    for sid, entry in intros.items():
        f = fmap.get(sid)
        if not f:
            continue
        old_s = entry.get("summary", "")
        old_i = entry.get("intro", "")
        if not (has_hedge(old_s) or has_hedge(old_i)):
            continue
        new_s, new_i = rewrite(old_s, f, dmeta.get(sid, {}))
        if new_s == old_s and new_i == old_i:
            continue
        entry["summary"], entry["intro"] = new_s, new_i
        changed += 1
        report.append((f["title"], old_s, new_s, old_i, new_i))

    lines = ["entries flagged: %d | rewritten: %d" % (len(report), changed)]
    for title, os_, ns, oi, ni in report:
        lines += ["", "### " + title,
                  "  summary: " + os_, "        -> " + ns,
                  "  intro  : " + oi, "        -> " + ni]
    if args.report:
        with open(args.report, "w", encoding="utf-8", newline="\n") as fh:
            fh.write("\n".join(lines) + "\n")
    print(lines[0])

    if args.write and changed:
        with open(INTROS, "w", encoding="utf-8", newline="\n") as fh:
            json.dump(intros, fh, ensure_ascii=False, indent=2, sort_keys=True)
            fh.write("\n")
        print("wrote", INTROS)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
