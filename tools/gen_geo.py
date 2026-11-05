# -*- coding: utf-8 -*-
"""Generate GEO / LLM-facing artifacts AFTER a Hugo build.

Hugo runs with --cleanDestinationDir, so this must run after hugo.exe::

    python tools/gen_geo.py

Outputs, all under public/:

    llms.txt                     llmstxt.org index, markdown links
    llms-full.txt                full plain-text dump of every page
    sitemap.md                   full-site sitemap in Markdown, markdown links
    sitemap-md.xml               XML sitemap of the Markdown mirror URLs
    index.md                     Markdown mirror of the home page
    index/index.md               Markdown mirror of the directory page
    folders/<slug>/index.md      Markdown mirror of every folder page

All URLs are absolute, read from baseURL in hugo.toml.

Privacy: pages listed in data/mobile_apps.json never expose pan_url anywhere,
matching the HTML templates (mobile apps are QR-code only).
"""
import json
import os
import re
import sys

try:
    import tomllib
except ImportError:  # Python < 3.11
    tomllib = None

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from apply_intros import real_screenshots  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONTENT = os.path.join(ROOT, "content", "folders")
PUBLIC = os.path.join(ROOT, "public")
CONFIG = os.path.join(ROOT, "hugo.toml")
MOBILE_APPS = os.path.join(ROOT, "data", "mobile_apps.json")

CAT_ORDER = ["软件工具", "设备与固件", "游戏与修改器", "学习资料", "影音媒体", "其他"]
CAT_DESC = {
    "软件工具": "桌面与移动端软件、开发工具、系统工具的安装包与便携版。",
    "设备与固件": "路由器固件、手机刷机包、设备驱动与系统镜像。",
    "游戏与修改器": "游戏本体、补丁、修改器与相关工具。",
    "学习资料": "考试资料、教程文档与电子书合集。",
    "影音媒体": "音视频、影视与媒体资源合集。",
    "其他": "未归入以上分类的网盘分享资源。",
}

INTRO = (
    "资源分享站 · 网盘资源索引（zh-CN）。本站收录整理自夸克网盘的公开分享，"
    "按文件夹归档：软件工具、设备与固件、游戏与修改器、学习资料、影音媒体等。"
    "每条资源一个独立页面，含简介、分类、体积、分享日期与网盘入口。"
    "资源仅供学习与交流使用，下载后请及时删除；如涉及版权问题请联系移除。"
)


def load_base_url():
    with open(CONFIG, "r", encoding="utf-8") as f:
        text = f.read()
    url = None
    if tomllib:
        try:
            url = tomllib.loads(text).get("baseURL")
        except tomllib.TOMLDecodeError:
            url = None
    if not url:
        m = re.search(r'^\s*baseURL\s*=\s*"([^"]+)"', text, re.M)
        url = m.group(1) if m else None
    if not url:
        raise SystemExit("ERROR: baseURL not found in hugo.toml")
    return url.rstrip("/") + "/"


def field(fm, key, default=""):
    m = re.search(r"^%s:\s*(.+?)\s*$" % re.escape(key), fm, re.M)
    if not m:
        return default
    value = m.group(1)
    if value.startswith('"'):
        try:
            return json.loads(value)
        except ValueError:
            return value.strip('"')
    return value


def md_text(text):
    return (text or "").replace("\\", "\\\\").replace("[", "\\[").replace("]", "\\]") \
        .replace("\r", " ").replace("\n", " ").strip()


def link(text, url):
    return "[%s](%s)" % (md_text(text), url)


def meta_suffix(page):
    parts = []
    if page["item_count"]:
        parts.append(page["item_count"])
    if page["date"]:
        parts.append("更新 " + page["date"])
    return "（%s）" % " · ".join(parts) if parts else ""


def load_pages(base):
    mobile = set()
    if os.path.exists(MOBILE_APPS):
        with open(MOBILE_APPS, "r", encoding="utf-8") as f:
            mobile = set(json.load(f).get("ids", []))

    pages = []
    for slug in sorted(os.listdir(CONTENT)):
        path = os.path.join(CONTENT, slug, "index.md")
        if not os.path.isfile(path):
            continue
        with open(path, "r", encoding="utf-8") as f:
            text = f.read()
        if not text.startswith("---\n"):
            continue
        end = text.index("\n---", 4)
        fm, body = text[4:end], text[end + 4:].lstrip("\n")

        try:
            cats = json.loads(field(fm, "categories")) or []
        except ValueError:
            cats = []
        share_id = field(fm, "share_id")
        url = base + "folders/" + slug + "/"
        pages.append({
            "slug": slug,
            "title": field(fm, "title") or slug,
            "date": field(fm, "date"),
            "description": field(fm, "description"),
            "summary": field(fm, "summary") or field(fm, "description"),
            "categories_raw": field(fm, "categories"),
            "categories": cats or ["其他"],
            "category": cats[0] if cats else "其他",
            "tags_raw": field(fm, "tags"),
            "item_count": field(fm, "item_count"),
            "pan_url": "" if share_id in mobile else field(fm, "pan_url"),
            "share_id": share_id,
            "body": body.strip(),
            "screenshots": real_screenshots(fm),
            "url": url,
            "md_url": url + "index.md",
            "md_path": os.path.join(PUBLIC, "folders", slug, "index.md"),
            "lastmod": (field(fm, "date") or "")[:10],
        })
    pages.sort(key=lambda p: (p["date"], p["slug"]), reverse=True)
    return pages


def grouped(pages):
    out = []
    for cat in CAT_ORDER:
        group = [p for p in pages if p["category"] == cat]
        if group:
            out.append((cat, group))
    for cat in sorted({p["category"] for p in pages} - set(CAT_ORDER)):
        out.append((cat, [p for p in pages if p["category"] == cat]))
    return out


def build_md_sitemap_xml(base, pages):
    ns = "http://www.sitemaps.org/schemas/sitemap/0.9"
    X = [
        '<?xml version="1.0" encoding="utf-8" standalone="yes"?>',
        '<urlset xmlns="%s">' % ns,
    ]

    def url_entry(url, lastmod=""):
        X.append("  <url>")
        X.append("    <loc>%s</loc>" % url.replace("&", "&amp;").replace("<", "&lt;"))
        if lastmod:
            X.append("    <lastmod>%s</lastmod>" % lastmod)
        X.append("    <changefreq>weekly</changefreq>")
        X.append("    <priority>0.5</priority>")
        X.append("  </url>")

    url_entry(base + "index.md")
    url_entry(base + "index/index.md")
    url_entry(base + "sitemap.md")
    url_entry(base + "llms.txt")
    url_entry(base + "llms-full.txt")
    for p in pages:
        url_entry(p["md_url"], p["lastmod"])
    X.append("</urlset>")
    return X


def write(path, lines):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines).rstrip("\n") + "\n")


def build_llms_txt(base, pages):
    L = [
        "# DL / INDEX",
        "",
        "> " + INTRO,
        "",
        "## 站点入口",
        "",
        "- " + link("首页", base) + " — 站点介绍与免责声明。",
        "- " + link("资源目录", base + "index/") + " — %d 条资源的搜索与分类筛选。" % len(pages),
        "- " + link("全站地图（HTML）", base + "sitemap/") + " — 人可读的全站页面清单。",
        "- " + link("全站地图（Markdown）", base + "sitemap.md") + " — 全站 Markdown 超链接清单。",
        "- " + link("Sitemap.xml", base + "sitemap.xml") + " — 搜索引擎 XML sitemap。",
        "- " + link("全文镜像 llms-full.txt", base + "llms-full.txt") + " — 全部页面正文的纯文本合集。",
        "",
        "## 说明",
        "",
        "- 每条资源页另有同路径的 `index.md` 镜像（即 `<资源页 URL>index.md`），供 LLM 直接抓取；HTML 页为人工阅读版本。",
        "- 手机版软件（安卓 App / APK）按站点策略不输出网盘链接，只在 HTML 页提供扫码获取。",
        "- 内容由 `tools/gen_folders.py` 从 `qsave share ls --json` 生成，文案源为 `tools/intros.json`，slug 稳定不变。",
        "- 资源仅供学习与交流使用，下载后请及时删除；如涉及版权问题请联系移除。",
        "",
        "## 资源列表（按分类 · 分类内按分享时间倒序，共 %d 条）" % len(pages),
        "",
    ]
    for cat, group in grouped(pages):
        L += ["### %s（%d）" % (cat, len(group)), "", CAT_DESC.get(cat, ""), ""]
        for p in group:
            L.append("- %s: %s%s · %s" % (
                link(p["title"], p["url"]),
                md_text(p["summary"]),
                meta_suffix(p),
                link("Markdown", p["md_url"]),
            ))
        L.append("")
    return L


def build_llms_full(base, pages):
    L = [
        "# DL / INDEX — 全文镜像",
        "",
        "> " + INTRO,
        "",
        "> 共 %d 条资源。每条含规范页面、Markdown 镜像、分类、简介与正文。" % len(pages),
        "",
        "## 站点入口",
        "",
        "- " + link("首页", base),
        "- " + link("资源目录", base + "index/"),
        "- " + link("全站地图", base + "sitemap/"),
        "- " + link("全站地图（Markdown）", base + "sitemap.md"),
        "- " + link("llms.txt", base + "llms.txt"),
        "",
        "## 资源全文",
        "",
    ]
    for p in pages:
        L += [
            "### " + p["title"],
            "",
            "- 规范页面：" + link(p["url"], p["url"]),
            "- Markdown 镜像：" + link(p["md_url"], p["md_url"]),
            "- 分类：" + p["category"],
        ]
        if p["item_count"]:
            L.append("- 内容：" + p["item_count"])
        if p["date"]:
            L.append("- 更新日期：" + p["date"])
        L += ["", "简介：" + md_text(p["summary"]), ""]
        if p["body"]:
            L += [p["body"], ""]
        if p["pan_url"]:
            L += ["网盘入口：" + link("打开网盘文件夹", p["pan_url"]), ""]
        for s in p["screenshots"]:
            L += ["截图：" + link(s.get("caption") or "查看图片", base + s["src"]), ""]
        L += ["---", ""]
    return L


def build_sitemap_md(base, pages):
    M = [
        "---",
        'title: "全站地图"',
        'description: "DL / INDEX 全站页面清单，含首页、资源目录与全部资源页的 Markdown 超链接。"',
        "canonical: " + base + "sitemap/",
        "---",
        "",
        "# 全站地图",
        "",
        "> 本站共 %d 个页面：首页、资源目录、全站地图，以及 %d 个资源详情页。所有链接均为 Markdown 超链接。" % (len(pages) + 3, len(pages)),
        "",
        "## 主要页面",
        "",
        "- " + link("首页", base),
        "- " + link("资源目录", base + "index/"),
        "- " + link("全站地图（HTML）", base + "sitemap/"),
        "- " + link("全站地图（Markdown）", base + "sitemap.md") + "（本页）",
        "- " + link("llms.txt", base + "llms.txt"),
        "- " + link("llms-full.txt", base + "llms-full.txt"),
        "- " + link("Sitemap.xml", base + "sitemap.xml"),
        "",
        "## 资源详情页（%d，分类内按分享时间倒序）" % len(pages),
        "",
    ]
    for cat, group in grouped(pages):
        M += ["### %s（%d）" % (cat, len(group)), "", CAT_DESC.get(cat, ""), ""]
        for p in group:
            M.append("- %s · %s%s" % (
                link(p["title"], p["url"]),
                link("Markdown", p["md_url"]),
                meta_suffix(p),
            ))
        M.append("")
    return M


def build_home_md(base, pages):
    return [
        "---",
        'title: "DL / INDEX"',
        'description: "资源分享站 · 网盘资源索引"',
        "canonical: " + base,
        "---",
        "",
        "# DL / INDEX",
        "",
        INTRO,
        "",
        "## 导航",
        "",
        "- " + link("资源目录", base + "index/") + " — %d 条资源" % len(pages),
        "- " + link("全站地图（HTML）", base + "sitemap/"),
        "- " + link("全站地图（Markdown）", base + "sitemap.md"),
        "- " + link("llms.txt", base + "llms.txt"),
        "- " + link("llms-full.txt", base + "llms-full.txt"),
        "- " + link("Sitemap.xml", base + "sitemap.xml"),
        "",
        "## 免责声明",
        "",
        "资源仅供学习与交流使用，请在下载后及时删除；如涉及版权问题，请联系移除。",
        "",
    ]


def build_dir_md(base, pages):
    D = [
        "---",
        'title: "资源目录"',
        'description: "DL / INDEX 全部 %d 条资源的 Markdown 目录。"' % len(pages),
        "canonical: " + base + "index/",
        "---",
        "",
        "# 资源目录",
        "",
        "> 共 %d 个文件夹，按分享时间倒序。每条给出 HTML 页与 Markdown 镜像两种链接。" % len(pages),
        "",
        "- " + link("全站地图（HTML）", base + "sitemap/"),
        "- " + link("全站地图（Markdown）", base + "sitemap.md"),
        "- " + link("llms.txt", base + "llms.txt"),
        "",
    ]
    for cat, group in grouped(pages):
        D += ["## %s（%d）" % (cat, len(group)), ""]
        for p in group:
            D.append("- %s — %s · %s%s" % (
                link(p["title"], p["url"]),
                md_text(p["summary"]),
                link("Markdown", p["md_url"]),
                meta_suffix(p),
            ))
        D.append("")
    return D


def build_page_md(base, page, related):
    B = [
        "---",
        "title: %s" % json.dumps(page["title"], ensure_ascii=False),
        "date: %s" % page["date"],
        "description: %s" % json.dumps(page["description"], ensure_ascii=False),
        "summary: %s" % json.dumps(page["summary"], ensure_ascii=False),
        "categories: %s" % page["categories_raw"],
        "tags: %s" % page["tags_raw"],
        "item_count: %s" % json.dumps(page["item_count"], ensure_ascii=False),
        "canonical: " + page["url"],
        "markdown: " + page["md_url"],
        "---",
        "",
        "# " + page["title"],
        "",
        md_text(page["summary"]),
        "",
    ]
    if page["body"]:
        B += [page["body"], ""]
    B += [
        "## 页面信息",
        "",
        "- 分类：" + link(page["category"], base + "sitemap/"),
    ]
    if page["item_count"]:
        B.append("- 内容：" + page["item_count"])
    B += [
        "- 更新日期：" + page["date"],
        "- 规范页面（HTML）：" + link(page["url"], page["url"]),
        "- Markdown 镜像：" + link(page["md_url"], page["md_url"]),
        "- 所属目录：" + link("资源目录", base + "index/") + " · " + link("目录 Markdown", base + "index/index.md"),
        "- 全站地图：" + link("HTML", base + "sitemap/") + " · " + link("Markdown", base + "sitemap.md") + " · " + link("llms.txt", base + "llms.txt"),
        "",
    ]
    if page["pan_url"]:
        B += ["网盘入口：" + link("打开网盘文件夹 ↗", page["pan_url"]), ""]
    else:
        B += ["网盘入口：手机版软件按站点策略不直接提供链接，请在规范页面扫码获取。", ""]
    if page["screenshots"]:
        B += ["## 截图", ""]
        for s in page["screenshots"]:
            B.append("- " + link(s.get("caption") or "查看图片", base + s["src"]))
        B.append("")
    if related:
        B += ["## 同类资源", ""]
        for r in related:
            B.append("- %s · %s" % (link(r["title"], r["url"]), link("Markdown", r["md_url"])))
        B.append("")
    return B


def main():
    base = load_base_url()
    pages = load_pages(base)
    if not pages:
        raise SystemExit("ERROR: no folder pages found in content/folders")
    if not os.path.isdir(PUBLIC):
        raise SystemExit("ERROR: public/ not found; run hugo first")

    write(os.path.join(PUBLIC, "llms.txt"), build_llms_txt(base, pages))
    write(os.path.join(PUBLIC, "llms-full.txt"), build_llms_full(base, pages))
    write(os.path.join(PUBLIC, "sitemap.md"), build_sitemap_md(base, pages))
    write(os.path.join(PUBLIC, "sitemap-md.xml"), build_md_sitemap_xml(base, pages))
    write(os.path.join(PUBLIC, "index.md"), build_home_md(base, pages))
    write(os.path.join(PUBLIC, "index", "index.md"), build_dir_md(base, pages))

    same_cat = {}
    for p in pages:
        same_cat.setdefault(p["category"], []).append(p)
    mirrors = 0
    for p in pages:
        related = [r for r in same_cat[p["category"]] if r["slug"] != p["slug"]][:3]
        write(p["md_path"], build_page_md(base, p, related))
        mirrors += 1

    missing = [p["slug"] for p in pages if not os.path.isfile(p["md_path"])]
    if missing:
        raise SystemExit("ERROR: %d mirrors not written: %s" % (len(missing), missing[:5]))
    print("geo: %d pages -> llms.txt, llms-full.txt, sitemap.md, index.md,"
          " index/index.md, %d Markdown mirrors" % (len(pages), mirrors))
    return 0


if __name__ == "__main__":
    sys.exit(main())
