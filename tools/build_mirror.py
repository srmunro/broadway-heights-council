#!/usr/bin/env python3
"""Build a static mirror of broadwayheightscouncil.org.

Downloads every page listed in the site's sitemaps, saves each at
<path>/index.html so URLs match the live site, and rewrites internal
<a href> links to relative paths so the copy is self-contained.
Assets (CSS/JS/images) stay on the Wix CDNs, which is what makes the
copy render identically.
"""
import os
import re
import sys
import time
import urllib.request
import urllib.error
from posixpath import relpath

ORIGIN = "https://www.broadwayheightscouncil.org"
OUT = sys.argv[1] if len(sys.argv) > 1 else "mirror"
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

SITEMAPS = [
    "/pages-sitemap.xml",
    "/event-pages-sitemap.xml",
    "/booking-services-sitemap.xml",
]


def get(url, tries=3):
    for attempt in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=60) as r:
                return r.read().decode("utf-8", "replace")
        except Exception as e:
            if attempt == tries - 1:
                print(f"  FAILED {url}: {e}")
                return None
            time.sleep(2 * (attempt + 1))


def collect_urls():
    urls = set()
    for sm in SITEMAPS:
        xml = get(ORIGIN + sm)
        if not xml:
            continue
        urls.update(re.findall(r"<loc>([^<]+)</loc>", xml))
    urls.add(ORIGIN)
    return sorted(urls)


def path_for(url):
    """Local file path (relative to OUT) for a site URL."""
    p = url.replace(ORIGIN, "").replace("https://broadwayheightscouncil.org", "")
    p = p.split("#")[0].split("?")[0].strip("/")
    return "index.html" if not p else f"{p}/index.html"


def main():
    urls = collect_urls()
    print(f"{len(urls)} pages to mirror")

    # map: site path (no leading slash, '' for home) -> local file path
    pages = {}
    for u in urls:
        pages[u.replace(ORIGIN, "").split("#")[0].split("?")[0].strip("/")] = path_for(u)

    link_re = re.compile(r'(<a\b[^>]*?\bhref=")([^"]*)(")', re.I)

    ok = fail = 0
    for i, url in enumerate(urls, 1):
        dest = os.path.join(OUT, path_for(url))
        html = get(url)
        if html is None:
            fail += 1
            continue

        here = os.path.dirname(path_for(url)) or "."

        def fix(m):
            head, href, tail = m.groups()
            for origin in (ORIGIN, "https://broadwayheightscouncil.org",
                           "http://www.broadwayheightscouncil.org"):
                if href == origin or href.startswith(origin + "/"):
                    target = href[len(origin):].split("#")[0].split("?")[0].strip("/")
                    frag = href[len(href.split("#")[0]):]
                    if target in pages:
                        rel = relpath(pages[target], here)
                        return head + rel + frag + tail
                    # not mirrored (e.g. a page outside the sitemaps) -> leave live
                    return m.group(0)
            return m.group(0)

        html = link_re.sub(fix, html)

        os.makedirs(os.path.dirname(dest), exist_ok=True)
        with open(dest, "w", encoding="utf-8") as f:
            f.write(html)
        ok += 1
        print(f"[{i}/{len(urls)}] {path_for(url)}  ({len(html)//1024} KB)")
        time.sleep(0.4)

    print(f"\ndone: {ok} saved, {fail} failed")


if __name__ == "__main__":
    main()
