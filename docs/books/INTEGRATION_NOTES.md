# Book Terminal: integration notes (round 3, 2026-11-25)

This branch owns `/books`, `/books/market`, the `#books` section and podcast thumbnails of `/media`, the books
API and collector, and the files listed at the end. Shared files are not edited here: `templates/base.html`,
the site nav and footer, `static/css/pp-*.css`, `static/css/protocol-pulse-tokens.css` and the logo belong to
Homepage Reforge. The items below need a change in those files, or an owner decision, when this branch is
integrated.

## 1. Logo: replace the untracked PNG with Reforge's inline SVG

`templates/base.html:131` (nav) and `:370` (footer) load `static/img/brand/pp_pulse_line_500.png`:

```html
<img src="{{ url_for('static', filename='img/brand/pp_pulse_line_500.png') }}" alt="Protocol Pulse" class="pp-nav__logo" style="height:36px;">
<img src="{{ url_for('static', filename='img/brand/pp_pulse_line_500.png') }}" alt="Protocol Pulse" class="pp-footer__brand-logo">
```

That PNG was never committed: commit db6ca41c7 added the references but not the file. It exists only untracked in
the live tree (94,916 bytes), so protocolpulse.io serves it, while every worktree and preview gets a 404. At
integration, both `<img>` tags must be replaced by Homepage Reforge's tracked inline SVG logo. The source is
`homepage-reforge:docs/homepage_reforge/prototypes/D/index.html`:

- line 371: `<symbol id="i-logo" viewBox="0 0 48 32">` with one stroked path (`stroke="#e31b1b"`, `stroke-width="3.4"`);
- lines 402-403: `<a class="brand" href="https://protocolpulse.io/" aria-label="Protocol Pulse home"><svg aria-hidden="true"><use href="#i-logo"/></svg><span class="word">Protocol<span>Pulse</span></span></a>`;
- lines 66-69: the `.brand` CSS (34 x 22 px mark, 19 px wordmark, "Pulse" in the red text colour).

Reforge's own brief says the same (`docs/homepage_reforge/08_D_LIVING_NEWSROOM_BRIEF.md:419`: "Replace with the
inline SVG logo used by A/B/C"). Committing the PNG instead would make the live tree's `git merge --ff-only`
refuse, because the identical file is untracked there.

**Preview only:** for the round 3 screenshots this worktree holds an untracked copy of the live PNG at
`static/img/brand/pp_pulse_line_500.png` (sha256 d1ce4f0c…46feb, the same bytes as the live tree's), so the
captures match what production serves today. It is not committed and must never be.

## 2. Third-party favicon request on /media

Round 2's console showed `net::ERR_BLOCKED_BY_RESPONSE.NotSameOrigin` for
`https://bitcoinmagazine.com/wp-content/uploads/2024/09/cropped-Bitcoin-Magazine-glyph-black-01-32x32.png`.
The request came from the podcast column of `templates/media_hub.html`, which rendered each episode's
`thumbnail_url` as an `<img>`. For 10 Bitcoin Magazine episodes, that URL is the publisher's WordPress site icon
(the RSS channel image), not episode artwork.

- Fixed in this branch (`templates/media_hub.html` is a file this workstream owns): the `feed_thumb()` macro renders the
  feed's initials (a local text glyph, `aria-hidden`) for any thumbnail that is a site icon: `favicon` or
  `apple-touch-icon` in the URL, Google's `/s2/favicons`, a `.ico`, or a WordPress `cropped-…-32x32` /
  `180x180` / `192x192` / `270x270` icon. Episode artwork renders as before. The round 3 browser check records no
  request to bitcoinmagazine.com (`~/book_terminal_work/shots/round3/console.txt`).
- Not changed (shared): `services/media_feed_service.py` stores the feed's channel image as the episode thumbnail.
  The feed service owner may prefer to drop site icons at ingest.

## 3. Robots and noindex

What the prototypes send now, measured on the preview (127.0.0.1:5077, 2026-11-25):

| Path | `X-Robots-Tag` header | Robots metas in the HTML |
|---|---|---|
| `/books` | `noindex` | base.html's `index, follow, max-snippet:-1, …` and `googlebot: index, follow` |
| `/books/market` | `noindex` | the same two base.html metas |
| `/media` | none | the same two base.html metas (a production page: indexable, unchanged) |

The prototypes use exactly one noindex mechanism, the `X-Robots-Tag: noindex` header that
`core/routes_books.py` sends on every response of its blueprint. The templates no longer add their own
`<meta name="robots" content="noindex">` and googlebot meta, which only put a second, contradicting meta into
the page. Search engines apply the most restrictive directive across header and metas, so noindex holds. The
markup still says `index, follow`, though, because base.html hard-codes it (`templates/base.html:19-20`) and a
page cannot replace it.

**Required base.html change (Homepage Reforge):** wrap the two metas in a block that defaults to today's values,
so a prototype can override it:

```jinja
{% block robots %}
<meta name="robots" content="index, follow, max-snippet:-1, max-image-preview:large, max-video-preview:-1">
<meta name="googlebot" content="index, follow">
{% endblock %}
```

Then `templates/books/library.html` and `templates/books/market.html` add
`{% block robots %}<meta name="robots" content="noindex">{% endblock %}`, and the page and header agree.

**noindex is not access control.** Anyone who can reach the server can open `/books` and `/books/market`; noindex
only asks search engines not to list them, and links or shared URLs still work. Keeping the prototypes out of
production depends on not deploying these routes (they register with one line in `core/routes.py`), or gating
them behind a login or a feature flag, until they are approved.

## 4. Retired previous-fetch "Rising" rule

Retired in this branch: the collector no longer writes `is_rising` (rank ≥ 10% better than the previous fetch);
the API has no `rising` list, `is_rising` field or `RISING` featured badge; `/media #books` has no Rising Stars
section, legend entry, chart class or tooltip flag. The frozen, unpublished candidate rule is
`core/book_signal_rules.py` (`docs/books/RISING_STAR_CANDIDATE.md`). For integration:

- The live `data/book_metrics.json` still carries `is_rising` from earlier collector runs until the new collector
  runs. The API ignores the field.
- These files still contain the old Rising Stars code, but nothing serves them. They were left in place for an
  owner decision rather than deleted silently. Flask's `template_folder` is the root `templates/`, and no
  blueprint loads `core/templates/`:
  `core/templates/media_hub.html` (last changed 2026-04-01), `templates/media_hub.html.bak.1776487159`,
  `templates/media_hub_old_backup.html.archived`, `core/routes_api.py.bak.1776487159`. Recommendation: delete
  them at integration.
- The `/media` chart still plots `bsr_change`, each book's rank change since its previous fetch. It is labelled as a
  plain measurement ("Rank change since the previous fetch"), not a momentum or rising signal. If the owner wants
  every previous-fetch comparison gone, that axis is the remaining one.

## 5. Data notes for the owner

- **The Money Revolution** (Amazon ID 1119856264, ISBN-13 978-1119856269): the Amazon US product page fetched
  2026-11-25 lists "Publication date: January 31, 2022", Wiley, 1st edition. The registry's `pub_year` 2021 comes
  from the Open Library edition record. It was not changed. The illustrative map plots it at 2021, and the detail
  view says "2021 (exact date not recorded)".
- **Digital Gold**: the Amazon US page lists May 24, 2016 (the registry's year is 2016). It could become the
  recorded exact date.
- **Exact dates:** 13 of 18 registry books record an exact publication date in `pub_year_source`
  (`books_registry.pub_date()`). The other 5 record only the year, and the detail view says so.
- **Purchase links** (`~/book_terminal_work/round3/purchase_links.txt`): 13 of 21 URLs were verified on
  2026-11-25. The other 8 are Amazon URLs that returned Amazon's robot-check page on both passes (HTTP 200, title
  "Amazon.com"). They are unverified today, not broken. The round 1 check on 2026-11-24 recorded HTTP 200 and the
  matching product title for all 8.

## 6. Site chrome the pages work around (no shared file changed)

- `main#ppMainContent.pp-main` carries a `transform` (computed `matrix(1, 0, 0, 1, 0, 0)`), which makes it the
  containing block of any `position: fixed` descendant. The phone detail sheet on `/books/market` is therefore
  re-parented by `static/js/book_market.js` into a `.bt` host under `<body>`. If that transform goes, the host is
  still harmless.
- `static/css/books.css` neutralises the global traps inside `.bt` only: `.fab` (pp-style.css:1486), `header`
  (pp-coindesk.css:12), and the teal `a:hover` (pp-main.css:201). The mobile rule
  `* { animation-duration: .3s !important; transition-duration: .3s !important }` (pp-style.css:3270-3271)
  stays in force: on phones the market's settle and its Map | Table fade both run 300 ms (within the 400 ms limit).
- The fixed mobile Commander banner (`#ppMobileBanner`, 39 px measured at 390 x 844) covers the bottom of every phone screen.
  The round 3 layouts keep the first shelf covers (`/books`) and the detail sheet (`/books/market`) above it.

## 7. Files this branch owns (book terminal)

`core/book_market.py`, `core/book_metrics.py`, `core/book_signal_rules.py`, `core/books_registry.py`,
`core/routes_books.py` (and its one registration line in `core/routes.py`), `data/books/registry.json`,
`data/books/market_illustrative.json`, `scripts/books/*.py`, `scripts/refresh_book_metrics.py`,
`templates/books/*.html`, `templates/media_hub.html` (the `#books` section and the podcast thumbnails),
`static/css/books.css`, `static/js/books.js`, `static/js/book_market.js`, `static/fonts/fraunces/`,
`static/vendor/chart.umd.min.js`, `tests/books/`, `docs/books/`. Run: `python3 -m pytest -q tests/books/ -p no:cacheprovider`.
Never commit `data/book_metrics.json` or `data/featured_book.json`; they are runtime data.
