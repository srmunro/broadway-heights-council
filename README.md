# Broadway Heights Community Council — site copy

A static copy of [broadwayheightscouncil.org](https://www.broadwayheightscouncil.org),
published at <https://srmunro.github.io/broadway-heights-council/>.

The live site is built on Wix. Every page here is the actual HTML Wix serves,
saved as-is, so the copy renders identically — styles, images, fonts and scripts
still load from the Wix CDNs at runtime.

Snapshot taken **2026-08-10**.

## Layout

| Path | What it is |
| --- | --- |
| `/` | Desktop pages — 57 of them, matching the live URL structure (`/events/`, `/ourstory/`, `/event-details-registration/<slug>/`, …) |
| `/m/` | Mobile pages. Wix serves different HTML to phones, so both variants are mirrored; a few lines of JS in each page's `<head>` sends visitors to the right one based on user agent |
| `/custom/` | Pages built for BHCC that don't exist on the Wix site, restyled to match it |
| `/assets/` | Stylesheet for the `/custom/` pages |
| `/tools/` | The scripts that produced the mirror |

### The custom pages

| Page | Purpose |
| --- | --- |
| [`custom/events.html`](custom/events.html) | Events list with upcoming/archive tabs, driven by a JS array at the bottom of the file |
| [`custom/register.html`](custom/register.html) | Event sign-up form (`?event=<id>` selects the event) |
| [`custom/event-template.html`](custom/event-template.html) | Starting point for a new event detail page |
| [`custom/mexican-independence-day-2026.html`](custom/mexican-independence-day-2026.html) | Event detail page for the September 2026 celebration |

They share `assets/bhcc.css` (site chrome — header, footer, type, colour) and
`assets/bhcc-pages.css` (components), both built from the live site's own
Montserrat / Open Sans / Poppins type and its `#2c5c7a` / `#a45f53` / `#f9f7f4`
palette.

## What works and what doesn't

Everything you can *read* is exact: text, layout, images, page structure, and the
event listings as they stood when the snapshot was taken.

Anything that talks back to Wix's servers does not work, because those endpoints
only answer requests from the real domain:

- contact, newsletter and event-registration forms
- ticketing and the booking calendar
- donations
- member login

Two deliberate additions to the mirrored HTML, both small and both marked in
`tools/assemble.py`:

- the desktop/mobile redirect described above
- a fallback nav drawer on mobile pages — Wix's own menu button depends on a
  same-origin web worker that can't start here, so the hamburger would otherwise
  do nothing

The copy also doesn't update itself. When the live site changes, re-run the
scripts.

## Refreshing the snapshot

```bash
python3 tools/build_mirror.py mirror   # desktop pages, from the site's sitemaps
python3 tools/build_mobile.py          # mobile variants
python3 tools/assemble.py              # -> newrepo/, ready to publish
```

`build_mirror.py` reads `pages-sitemap.xml`, `event-pages-sitemap.xml` and
`booking-services-sitemap.xml`, so pages added in Wix are picked up
automatically. It rewrites internal links to relative paths and leaves CDN
assets pointing at Wix.
