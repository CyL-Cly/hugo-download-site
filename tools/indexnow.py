# -*- coding: utf-8 -*-
"""Submit the built site's URLs to IndexNow (Bing / Yandex / Seznam / Naver).

Reads absolute <loc> values from public/sitemap.xml and public/sitemap-md.xml
(HTML pages + their Markdown mirrors) and POSTs them to the IndexNow endpoint
in batches. The key file must already be published at
https://<host>/<key>.txt, so run this *after* the deploy when possible; the
script only reports the response and never fails the build.

Usage:
    python tools/indexnow.py              # submit everything in the sitemap
    python tools/indexnow.py --dry-run    # show what would be sent
    python tools/indexnow.py --limit 50   # only the first N URLs
"""
import argparse
import json
import os
import sys
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG = os.path.join(ROOT, "tools", "indexnow.json")
SITEMAP = os.path.join(ROOT, "public", "sitemap.xml")
MD_SITEMAP = os.path.join(ROOT, "public", "sitemap-md.xml")
BATCH = 10000


def load_urls(host, path):
    if not os.path.exists(path):
        return []
    ns = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    tree = ET.parse(path)
    urls = []
    for loc in tree.getroot().findall(".//s:url/s:loc", ns):
        u = (loc.text or "").strip()
        if not u:
            continue
        if u.startswith("/"):
            u = "https://%s%s" % (host, u)
        if u.startswith("https://") or u.startswith("http://"):
            urls.append(u)
    return urls


def submit(endpoint, payload):
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        endpoint,
        data=body,
        method="POST",
        headers={
            "Content-Type": "application/json; charset=utf-8",
            "User-Agent": "hugo-download-site/indexnow",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.status, resp.read().decode("utf-8", "replace")[:300]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()

    if not os.path.exists(CONFIG):
        print("ERROR: %s not found" % CONFIG)
        return 1
    cfg = json.load(open(CONFIG, encoding="utf-8"))
    urls = []
    seen = set()
    for sitemap in (SITEMAP, MD_SITEMAP):
        for u in load_urls(cfg["host"], sitemap):
            if u not in seen:
                seen.add(u)
                urls.append(u)
    if args.limit:
        urls = urls[: args.limit]
    if not urls:
        print("indexnow: sitemap has no absolute URLs, nothing submitted")
        return 0

    print("indexnow: %d URLs for %s" % (len(urls), cfg["host"]))
    if args.dry_run:
        for u in urls[:5]:
            print("  " + u)
        print("  ...")
        return 0

    ok = 0
    for i in range(0, len(urls), BATCH):
        chunk = urls[i: i + BATCH]
        payload = {
            "host": cfg["host"],
            "key": cfg["key"],
            "keyLocation": cfg["keyLocation"],
            "urlList": chunk,
        }
        try:
            status, text = submit(cfg["endpoint"], payload)
            print("  batch %d: HTTP %s %s" % (i // BATCH + 1, status, text))
            if 200 <= status < 300:
                ok += len(chunk)
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", "replace")[:300]
            print("  batch %d: HTTP %s %s" % (i // BATCH + 1, e.code, detail))
            if e.code in (403, 422):
                print("  hint: key file may not be deployed yet -> "
                      "https://%s/%s.txt" % (cfg["host"], cfg["key"]))
        except Exception as e:  # noqa: BLE001 - network errors must not break the build
            print("  batch %d: %s" % (i // BATCH + 1, e))

    print("indexnow: %d/%d URLs accepted" % (ok, len(urls)))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
