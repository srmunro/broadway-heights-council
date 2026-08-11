#!/usr/bin/env python3
"""Assemble the new repo tree.

  /            exact desktop mirror of broadwayheightscouncil.org
  /m/          exact mobile mirror (Wix serves different HTML per user agent)
  /custom/     the hand-built BHCC pages, restyled to match the live site
  /assets/     shared stylesheet for the custom pages
"""
import os
import re
import shutil
from posixpath import relpath

SCRATCH = os.path.dirname(os.path.abspath(__file__))
MIRROR = os.path.join(SCRATCH, "mirror")
SRC = os.path.join(SCRATCH, "broadway-heights-council")
OUT = os.path.join(SCRATCH, "newrepo")

LOGO = ("https://static.wixstatic.com/media/9b9e6e_5f356153803e43d98a8f513104c6b454~mv2.png/"
        "v1/fill/w_92,h_92,al_c,q_85,usm_0.66_1.00_0.01,enc_avif,quality_auto/Logo.png")


# --------------------------------------------------------------------------
# 1. Copy the mirror over, injecting the desktop/mobile user-agent shim
# --------------------------------------------------------------------------

SHIM = (
    '<script>(function(){try{'
    'if(!/Mobi|Android|iPhone|iPad|iPod|IEMobile|Opera Mini/i.test(navigator.userAgent))return;'
    'location.replace("%s"+location.search+location.hash);'
    '}catch(e){}})();</script>'
)
SHIM_BACK = (
    '<script>(function(){try{'
    'if(/Mobi|Android|iPhone|iPad|iPod|IEMobile|Opera Mini/i.test(navigator.userAgent))return;'
    'location.replace("%s"+location.search+location.hash);'
    '}catch(e){}})();</script>'
)


# Wix's mobile menu is opened by its client bundle, which can't boot off the
# original domain (its web worker is same-origin only). The links are already
# in the DOM, so bind a plain fallback drawer to the existing hamburger and
# only use it if Wix's own menu hasn't opened.
MOBILE_MENU = """<style>
#bhccFallbackMenu{position:fixed;inset:0;z-index:99999;background:#2c5c7a;display:none;flex-direction:column;padding:26px 28px;overflow:auto}
#bhccFallbackMenu.open{display:flex}
#bhccFallbackMenu a{font-family:montserrat,'Montserrat',sans-serif;font-size:20px;color:#fff;text-decoration:none;padding:14px 0;border-bottom:1px solid rgba(255,255,255,.18)}
#bhccFallbackClose{align-self:flex-end;background:none;border:0;color:#fff;font-size:34px;line-height:1;padding:0 4px 14px;cursor:pointer}
</style>
<script>
(function () {
  function build() {
    var toggle = document.getElementById('MENU_AS_CONTAINER_TOGGLE');
    var source = document.getElementById('MENU_AS_CONTAINER');
    if (!toggle || !source || document.getElementById('bhccFallbackMenu')) return;

    var nav = document.createElement('nav');
    nav.id = 'bhccFallbackMenu';
    var close = document.createElement('button');
    close.id = 'bhccFallbackClose';
    close.type = 'button';
    close.innerHTML = '&times;';
    close.setAttribute('aria-label', 'Close menu');
    close.onclick = function () { nav.classList.remove('open'); };
    nav.appendChild(close);

    var links = source.querySelectorAll('a');
    if (!links.length) return;
    for (var i = 0; i < links.length; i++) {
      var a = document.createElement('a');
      a.href = links[i].getAttribute('href');
      a.textContent = links[i].textContent.trim();
      nav.appendChild(a);
    }
    document.body.appendChild(nav);

    toggle.addEventListener('click', function () {
      setTimeout(function () {
        var c = document.getElementById('MENU_AS_CONTAINER');
        var s = c && getComputedStyle(c);
        if (!s || s.display === 'none' || s.visibility === 'hidden') nav.classList.add('open');
      }, 250);
    });
    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape') nav.classList.remove('open');
    });
  }
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', build);
  } else {
    build();
  }
})();
</script>"""


def append_body(html, snippet):
    """Add a snippet just before </body>."""
    i = html.lower().rfind("</body>")
    if i == -1:
        return html + snippet
    return html[:i] + snippet + html[i:]


def inject(html, snippet):
    """Put the shim first thing in <head> so it runs before Wix boots."""
    m = re.search(r"<head[^>]*>", html, re.I)
    if not m:
        return snippet + html
    return html[:m.end()] + snippet + html[m.end():]


def copy_mirror():
    desktop = []
    for root, dirs, files in os.walk(MIRROR):
        if "index.html" not in files:
            continue
        rel = os.path.relpath(root, MIRROR).replace(os.sep, "/")
        rel = "" if rel == "." else rel
        if rel == "m" or rel.startswith("m/"):
            continue
        desktop.append(rel)

    for rel in sorted(desktop):
        src = os.path.join(MIRROR, rel, "index.html") if rel else os.path.join(MIRROR, "index.html")
        dst = os.path.join(OUT, rel, "index.html") if rel else os.path.join(OUT, "index.html")
        here = rel or "."
        target = relpath(f"m/{rel}/" if rel else "m/", here)
        if not target.endswith("/"):
            target += "/"
        html = open(src, encoding="utf-8").read()
        html = inject(html, SHIM % target)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        open(dst, "w", encoding="utf-8").write(html)

        # mobile counterpart
        msrc = os.path.join(MIRROR, "m", rel, "index.html") if rel else os.path.join(MIRROR, "m", "index.html")
        if os.path.exists(msrc):
            mdst = os.path.join(OUT, "m", rel, "index.html") if rel else os.path.join(OUT, "m", "index.html")
            mhere = f"m/{rel}" if rel else "m"
            mtarget = relpath(f"{rel}/" if rel else ".", mhere)
            if not mtarget.endswith("/"):
                mtarget += "/"
            mhtml = open(msrc, encoding="utf-8").read()
            mhtml = inject(mhtml, SHIM_BACK % mtarget)
            mhtml = append_body(mhtml, MOBILE_MENU)
            os.makedirs(os.path.dirname(mdst), exist_ok=True)
            open(mdst, "w", encoding="utf-8").write(mhtml)
    print(f"mirror: {len(desktop)} desktop pages + mobile counterparts")


# --------------------------------------------------------------------------
# 2. Rebuild the custom pages with the live site's chrome
# --------------------------------------------------------------------------

NAV = [
    ("../", "Home", "home"),
    ("../ourstory/", "Our Story", "ourstory"),
    ("events.html", "Events", "events"),
    ("../join-the-council/", "Join the Council", "join"),
    ("../copy-of-contact-us/", "Contact Us", "contact"),
    ("../donate/", "Donate", "donate"),
]


def header(active):
    links = "\n".join(
        '      <a href="{}"{}>{}</a>'.format(
            href, ' aria-current="page"' if key == active else "", label)
        for href, label, key in NAV
    )
    return f"""<header class="bh-header" id="top">
  <div class="bh-header__inner">
    <a class="bh-brand" href="../">
      <img src="{LOGO}" alt="Broadway Heights Community Council logo" width="46" height="46">
      <span>Broadway Heights Community Council</span>
    </a>
    <button class="bh-burger" type="button" aria-label="Menu" aria-expanded="false" aria-controls="bh-nav">
      <span></span><span></span><span></span>
    </button>
    <nav class="bh-nav" id="bh-nav">
{links}
    </nav>
  </div>
</header>"""


FOOTER = """<footer class="bh-footer">
  <div class="bh-footer__inner">
    <h2>Let's Collaborate | Stay Updated with the Latest News and Developments</h2>
    <form action="../copy-of-contact-us/" method="get">
      <input type="email" name="email" placeholder="Enter your email here" aria-label="Email address">
      <button type="submit" class="bh-btn">Submit</button>
    </form>
    <p>Broadway Heights Community Council is a registered 501(c)(3) nonprofit. EIN: 90-0893585</p>
    <p>A safe, inclusive, and united neighborhood voice, working for over two decades to strengthen
       community pride and ensure a better quality of life for all.</p>
    <p><a href="#top">Back to Top</a></p>
    <div class="bh-footer__meta">&copy; Broadway Heights Community Council 2024</div>
  </div>
</footer>

<script>
  (function () {
    var burger = document.querySelector('.bh-burger');
    var nav = document.getElementById('bh-nav');
    if (!burger || !nav) return;
    burger.addEventListener('click', function () {
      var open = nav.classList.toggle('is-open');
      burger.setAttribute('aria-expanded', open ? 'true' : 'false');
    });
  })();
</script>"""


PAGES = {
    "events.html": "events",
    "register.html": "events",
    "event-template.html": "events",
    "mexican-independence-day-2026.html": "events",
}


def rebuild_custom():
    os.makedirs(os.path.join(OUT, "custom"), exist_ok=True)
    for name, active in PAGES.items():
        html = open(os.path.join(SRC, name), encoding="utf-8").read()

        title = re.search(r"<title>(.*?)</title>", html, re.S).group(1).strip()
        desc_m = re.search(r'<meta name="description" content="([^"]*)"', html)
        desc = desc_m.group(1) if desc_m else ""

        after_header = html.split("</header>", 1)[1]
        content = after_header.split('<footer class="site-footer">', 1)[0].strip()
        tail = after_header.split("</footer>", 1)[1]
        scripts = tail.split("</body>", 1)[0].strip()

        # links: these pages now live one level down, alongside each other
        content = content.replace('href="../events.html"', 'href="events.html"')
        scripts = scripts.replace(
            'detailPage: "event-details-registration/',
            'detailPage: "../event-details-registration/')
        scripts = re.sub(
            r'(detailPage: "\.\./event-details-registration/[^"]+)\.html"',
            r'\1/"', scripts)

        page = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{title}</title>
  <meta name="description" content="{desc}">
  <link rel="icon" href="https://static.wixstatic.com/media/9b9e6e_311f91ce3d684f748ac00eaab46b407a~mv2.png/v1/fill/w_32,h_32,lg_1,usm_0.66_1.00_0.01/9b9e6e_311f91ce3d684f748ac00eaab46b407a~mv2.png" type="image/png">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link rel="stylesheet" href="../assets/bhcc.css">
  <link rel="stylesheet" href="../assets/bhcc-pages.css">
</head>
<body>

{header(active)}

{content}

{FOOTER}

<script>
{scripts.replace('<script>', '').replace('</script>', '').strip()}
</script>

</body>
</html>
"""
        open(os.path.join(OUT, "custom", name), "w", encoding="utf-8").write(page)
        print(f"custom/{name}")


def main():
    if os.path.exists(OUT):
        shutil.rmtree(OUT)
    os.makedirs(OUT)
    copy_mirror()
    shutil.copytree(os.path.join(SCRATCH, "assets"), os.path.join(OUT, "assets"))
    rebuild_custom()
    open(os.path.join(OUT, ".nojekyll"), "w").close()
    print("\nassembled ->", OUT)


if __name__ == "__main__":
    main()
