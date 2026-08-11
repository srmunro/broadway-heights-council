#!/usr/bin/env python3
"""Mirror the mobile variant of each page into mirror/m/<path>/index.html.

Wix serves different HTML to mobile user agents, so a desktop-only mirror
renders the desktop layout on phones. We fetch both and let a small shim
pick the right one at runtime.
"""
import os
import re
import sys
import time
import urllib.request
from posixpath import relpath

ORIGIN = "https://www.broadwayheightscouncil.org"
OUT = "mirror"
UA = ("Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 "
      "(KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1")


def get(url, tries=3):
    for a in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=60) as r:
                return r.read().decode("utf-8", "replace")
        except Exception as e:
            if a == tries - 1:
                print(f"  FAILED {url}: {e}")
                return None
            time.sleep(2 * (a + 1))


# page keys from the desktop mirror we already built
keys = []
for root, dirs, files in os.walk(OUT):
    if "m" in root.split(os.sep):
        continue
    if "index.html" in files:
        rel = os.path.relpath(root, OUT).replace("\\", "/")
        keys.append("" if rel == "." else rel)
keys.sort()

pages = {k: ("m/index.html" if k == "" else f"m/{k}/index.html") for k in keys}
link_re = re.compile(r'(<a\b[^>]*?\bhref=")([^"]*)(")', re.I)

ok = fail = 0
for i, k in enumerate(keys, 1):
    url = ORIGIN + ("/" if not k else "/" + k)
    html = get(url)
    if html is None:
        fail += 1
        continue
    if 'wixMobileViewport' not in html:
        print(f"  WARN: {k or '/'} came back as desktop HTML")

    here = os.path.dirname(pages[k]) or "."

    def fix(m):
        head, href, tail = m.groups()
        for o in (ORIGIN, "https://broadwayheightscouncil.org",
                  "http://www.broadwayheightscouncil.org"):
            if href == o or href.startswith(o + "/"):
                t = href[len(o):].split("#")[0].split("?")[0].strip("/")
                frag = href[len(href.split("#")[0]):]
                if t in pages:
                    rel = relpath(pages[t], here)
                    if rel == "index.html":
                        rel = "./"
                    elif rel.endswith("/index.html"):
                        rel = rel[:-len("index.html")]
                    return head + rel + frag + tail
                return m.group(0)
        return m.group(0)

    html = link_re.sub(fix, html)

    dest = os.path.join(OUT, pages[k])
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    with open(dest, "w", encoding="utf-8") as f:
        f.write(html)
    ok += 1
    print(f"[{i}/{len(keys)}] {pages[k]} ({len(html)//1024} KB)")
    time.sleep(0.4)

print(f"\ndone: {ok} saved, {fail} failed")
