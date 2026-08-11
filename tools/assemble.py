#!/usr/bin/env python3
"""Assemble the publishable tree.

  /            exact desktop mirror of broadwayheightscouncil.org
  /m/          exact mobile mirror (Wix serves different HTML per user agent)
  /custom/     BHCC-built pages, carried over from the repo unchanged
  /assets/     stylesheets for the custom pages

Run from the repo root, after build_mirror.py and build_mobile.py have
written ./mirror/. Output lands in ./newrepo/.
"""
import os
import re
import shutil
from posixpath import relpath

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MIRROR = os.path.join(REPO, "mirror")
OUT = os.path.join(REPO, "newrepo")

# Carried over from the repo as-is. Everything else in the output tree is
# generated from the mirror.
CARRY = ["custom", "assets", "tools", "README.md", ".nojekyll"]


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
# 2. Carry the hand-built pages across untouched
# --------------------------------------------------------------------------

def copy_authored():
    for name in CARRY:
        src = os.path.join(REPO, name)
        if not os.path.exists(src):
            print(f"  skipped {name} (not present)")
            continue
        dst = os.path.join(OUT, name)
        if os.path.isdir(src):
            shutil.copytree(src, dst)
        else:
            shutil.copy2(src, dst)
        print(f"carried {name}")


def main():
    if os.path.exists(OUT):
        shutil.rmtree(OUT)
    os.makedirs(OUT)
    copy_mirror()
    copy_authored()
    print("\nassembled ->", OUT)


if __name__ == "__main__":
    main()
