"""Book Terminal round 2: registry v3 fields, /books, /books/market, the illustrative data,
the market rules, the cover-map layout math and the /media #books script.

No network: sockets are refused. Pages render through the real blueprint and templates with
a stub base.html (the site's base needs the whole app). The layout math and the /media
script are the real JavaScript files, run under node (skipped if node is missing).

Run: python3 -m pytest -q tests/books/ -p no:cacheprovider
"""
import copy
import html
import importlib.util
import json
import re
import shutil
import socket
import subprocess
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
JS = Path(__file__).resolve().parent / 'js'
sys.path.append(str(ROOT / 'core'))

import book_market  # noqa: E402
import book_metrics  # noqa: E402
import books_registry  # noqa: E402

_spec = importlib.util.spec_from_file_location('make_illustrative_market', ROOT / 'scripts' / 'books' / 'make_illustrative_market.py')
generator = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(generator)

NODE = shutil.which('node')
AS_OF = date(2026, 11, 24)
NOW = datetime(2026, 11, 24, 12, 0, tzinfo=timezone.utc)
BANNER = 'Illustrative prototype — not live data.'
STUB_BASE = ('<!doctype html><html><head><title>{% block title %}{% endblock %}</title>{% block head %}{% endblock %}'
             '</head><body><main>{% block content %}{% endblock %}</main>{% block scripts %}{% endblock %}</body></html>')


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def refuse(*args, **kwargs):
        raise AssertionError('network access attempted in a book terminal test')
    monkeypatch.setattr(socket.socket, 'connect', refuse)
    monkeypatch.setattr(socket.socket, 'connect_ex', refuse)
    monkeypatch.setattr(socket, 'getaddrinfo', refuse)


@pytest.fixture(scope='module')
def client():
    from flask import Flask
    from jinja2 import ChoiceLoader, DictLoader, FileSystemLoader
    import routes_books
    app = Flask('book_terminal_test', template_folder=str(ROOT / 'templates'), static_folder=str(ROOT / 'static'))
    app.jinja_loader = ChoiceLoader([DictLoader({'base.html': STUB_BASE}), FileSystemLoader(str(ROOT / 'templates'))])
    app.register_blueprint(routes_books.books_bp)
    return app.test_client()


def visible_text(page):
    page = re.sub(r'<(script|style)\b.*?</\1>', ' ', page, flags=re.S | re.I)
    return html.unescape(re.sub(r'<[^>]+>', ' ', page))


def shown_books(page):
    """Slugs of the /books cards rendered without the hidden attribute."""
    return re.findall(r'<li class="bt-book" id="book-([a-z0-9-]+)"[^>]*?(?<!hidden)>', page)


def run_node(script, *args):
    if not NODE:
        pytest.skip('node is not installed')
    done = subprocess.run([NODE, str(script), *map(str, args)], capture_output=True, text=True, timeout=60)
    assert done.returncode == 0, done.stderr
    return json.loads(done.stdout)


# ── Registry v3 fields ───────────────────────────────────────────────────────

def test_registry_curated_fields():
    doc = json.loads((ROOT / 'data' / 'books' / 'registry.json').read_text(encoding='utf-8'))
    categories = set(doc['categories'])
    assert categories == {'Bitcoin', 'Money & Macro', 'Technology', 'History', 'Strategy', 'Economics'}
    pathway_ids = [p['id'] for p in doc['pathways']]
    steps = {pid: [] for pid in pathway_ids}
    for book in doc['books']:
        assert book['categories'] and set(book['categories']) <= categories, book['slug']
        d = book['description']
        assert '\n' not in d and 20 < len(d) <= 180 and d.endswith('.'), book['slug']
        assert not re.search('["“”]', d), f'{book["slug"]}: a description quotes no one'
        assert isinstance(book['pub_year'], int) and 1990 <= book['pub_year'] <= 2026, book['slug']
        assert re.match(r'(Open Library edition record|Amazon US product page) \(.+\), checked 2026-11-24$', book['pub_year_source'])
        for member in book.get('pathways', []):
            steps[member['id']].append(member['step'])
            assert member['note'].strip()
        for link in book.get('free_resources', []) + book.get('related_media', []):
            assert link['url'].startswith('https://') and link['label'].strip()
        assert 'publisher_link' not in book  # none verified (The Fiat Standard's store page answered 429)
    for pid, numbers in steps.items():
        assert sorted(numbers) == list(range(1, len(numbers) + 1)) and len(numbers) >= 2, pid
    featured = next(b for b in doc['books'] if b['slug'] == doc['featured'])
    assert featured['pp_series']


def test_related_media_only_for_series_books_and_only_urls_already_in_the_repo():
    routes_pages = (ROOT / 'core' / 'routes_pages.py').read_text(encoding='utf-8')
    with_media = [b for b in books_registry.load_registry() if b.get('related_media')]
    assert {b['slug'] for b in with_media} == {b['slug'] for b in books_registry.load_registry() if b.get('pp_series')}
    for book in with_media:
        for media in book['related_media']:
            key = re.search(r'(?:v=|list=)([A-Za-z0-9_-]+)', media['url']).group(1)
            assert key in routes_pages, f'{book["slug"]}: {media["url"]} is not a link the site already uses'


def test_free_editions_and_formats():
    by_slug = {b['slug']: b for b in books_registry.load_registry()}
    assert books_registry.free_alt(by_slug['softwar']) == 'https://hdl.handle.net/1721.1/153030'
    assert books_registry.purchase_label(by_slug['the-fiat-standard']) == 'Kindle on Amazon'
    assert [s for s, b in by_slug.items() if books_registry.purchase_label(b) != 'Buy on Amazon'] == ['the-fiat-standard']


@pytest.mark.parametrize('breakage, message', [
    (lambda d: d['books'][0]['categories'].append('Crypto'), 'categories'),
    (lambda d: d['books'][0].update(description=''), 'lacks'),
    (lambda d: next(b for b in d['books'] if b['slug'] == 'mastering-bitcoin')['pathways'][0].update(step=7), 'steps'),
    (lambda d: next(b for b in d['books'] if b['slug'] == 'softwar')['free_resources'][0].update(url='http://hdl.handle.net/1721.1/153030'), 'https'),
    (lambda d: d.update(featured='softwar'), 'featured'),
    (lambda d: d['books'][0].pop('pub_year_source'), 'pub_year'),
])
def test_registry_loader_refuses_a_broken_registry(tmp_path, breakage, message):
    doc = json.loads((ROOT / 'data' / 'books' / 'registry.json').read_text(encoding='utf-8'))
    broken = copy.deepcopy(doc)
    breakage(broken)
    path = tmp_path / 'registry.json'
    path.write_text(json.dumps(broken), encoding='utf-8')
    with pytest.raises(ValueError, match=message):
        books_registry.load_registry(path)


def test_library_view_comes_from_the_registry():
    lib = books_registry.library('protocolpulse-20')
    registry = books_registry.load_registry()
    assert [e['slug'] for e in lib['series']] == [b['slug'] for b in registry if b.get('pp_series')]
    assert len(lib['series']) + len(lib['essential']) == lib['count'] == len(registry) == 18
    assert lib['featured']['slug'] == 'the-big-print' and lib['featured']['series_url'].startswith('https://www.youtube.com/')
    for p in lib['pathways']:
        assert [s['step'] for s in p['steps']] == list(range(1, len(p['steps']) + 1))
    entry = json.dumps(lib)
    assert 'rank' not in entry.lower().replace('rank_nov24', '') and 'bestseller' not in entry.lower()


# ── /books ───────────────────────────────────────────────────────────────────

def test_books_page_renders_every_title_without_rank_numbers(client):
    resp = client.get('/books')
    assert resp.status_code == 200
    assert resp.headers['X-Robots-Tag'] == 'noindex'
    page = resp.get_data(as_text=True)
    assert '<meta name="robots" content="noindex">' in page
    for book in books_registry.load_registry():
        assert html.escape(book['title'], quote=False) in page, book['title']
    text = visible_text(page)
    assert not re.search(r'#\s?\d', text), 'a rank number on /books'
    for word in ('bestseller', 'best seller', 'rank', 'bsr'):
        assert word not in text.lower(), word
    assert len(shown_books(page)) == 18
    assert text.count('Kindle on Amazon') == 1 and text.count('Buy on Amazon') == 18  # featured card + 17 cards
    assert 'Kindle edition' in text
    assert page.count('?tag=protocolpulse-20') == 19
    for url in ('https://hdl.handle.net/1721.1/153030', 'https://21lessons.com/', 'https://github.com/bitcoinbook/bitcoinbook'):
        assert url in page
    assert len(re.findall(r'<article class="bt-path"', page)) == 5


@pytest.mark.parametrize('query, expected', [
    ('q=lowery', ['softwar']),
    ('q=W%C3%8DRDUM', ['the-genesis-book']),                      # case and accents folded
    ('cat=History', ['daylight-robbery', 'the-genesis-book', 'digital-gold', 'the-blocksize-war']),
    ('cat=History&cat=Strategy', ['the-sovereign-individual', 'softwar']),  # last value wins
    ('cat=Crypto', None),                                          # unknown category: all books
    ('q=money&cat=Money+%26+Macro', ['the-big-print', 'broken-money', 'the-fiat-standard', 'layered-money', 'the-money-revolution']),
])
def test_books_search_and_category_work_without_javascript(client, query, expected):
    page = client.get('/books?' + query).get_data(as_text=True)
    shown = shown_books(page)
    if expected is None:
        assert len(shown) == 18
    else:
        assert sorted(shown) == sorted(expected)
    assert f'Showing {len(shown)} of 18 books' in page


# ── /books/market ────────────────────────────────────────────────────────────

def test_market_page_is_bannered_noindex_and_illustrative(client):
    resp = client.get('/books/market')
    assert resp.status_code == 200
    assert resp.headers['X-Robots-Tag'] == 'noindex'
    page = resp.get_data(as_text=True)
    assert '<meta name="robots" content="noindex">' in page
    assert BANNER in page and 'Not for publication.' in page
    assert page.index(BANNER) < page.index('Book Market Map')  # the banner opens the page
    view = book_market.view(books_registry.load_registry(), book_market.load())
    stats = re.findall(r'<span class="bt-stat-n">(\d+)</span>', page)
    assert stats == [str(view['stats'][k]) for k in ('tracked', 'live', 'stale', 'unavailable')]
    assert len(re.findall(r'<tr data-title=', page)) == 18
    assert 'sustained 7-day improvement &ge; 20% with sufficient history' in page
    assert 'Not plotted:' in page and 'The Fiat Standard (Kindle edition, Kindle Store rank)' in page
    map_data = json.loads(re.search(r'<script type="application/json" id="btMapData">(.*?)</script>', page, re.S).group(1))
    assert 1 <= len(map_data['books']) <= 8
    assert 'the-fiat-standard' not in {b['slug'] for b in map_data['books']}
    assert 'bestseller' not in visible_text(page).lower()


# ── Illustrative data ────────────────────────────────────────────────────────

def test_illustrative_json_is_flagged_everywhere_and_matches_its_generator():
    path = ROOT / 'data' / 'books' / 'market_illustrative.json'
    data = json.loads(path.read_text(encoding='utf-8'))
    assert data['illustrative'] is True and 'Not observed data' in data['note']
    assert all(r['illustrative'] is True for r in data['records'])
    assert [r['slug'] for r in data['records']] == [b['slug'] for b in books_registry.load_registry()]
    assert all(len(r['series']) == data['window_days'] for r in data['records'])
    assert path.read_text(encoding='utf-8') == generator.dumps(generator.build())  # committed file = a fresh run


@pytest.mark.parametrize('unflag', [lambda d: d.update(illustrative=False), lambda d: d['records'][3].pop('illustrative')])
def test_market_refuses_data_not_flagged_illustrative(tmp_path, unflag):
    data = json.loads((ROOT / 'data' / 'books' / 'market_illustrative.json').read_text(encoding='utf-8'))
    unflag(data)
    path = tmp_path / 'market.json'
    path.write_text(json.dumps(data), encoding='utf-8')
    with pytest.raises(ValueError, match='illustrative'):
        book_market.load(path)


# ── Market rules ─────────────────────────────────────────────────────────────

def test_states_and_seven_day_change():
    assert book_market.metrics([None] * 30, AS_OF)['state'] == 'unavailable'
    live = book_market.metrics([100] * 29 + [None], AS_OF)              # seen yesterday
    assert (live['state'], live['change_7d'], live['last_observed']) == ('live', 0.0, '2026-11-23')
    stale = book_market.metrics([100] * 28 + [None, None], AS_OF)       # seen 2 days ago
    assert (stale['state'], stale['change_7d'], stale['rank']) == ('stale', None, 100)
    gap = book_market.metrics([100] * 22 + [None] + [90] * 7, AS_OF)    # nothing 7 days before
    assert (gap['state'], gap['change_7d'], gap['momentum']) == ('live', None, None)
    moved = book_market.metrics([1000] * 22 + [1000, 990, 980, 970, 960, 950, 940, 800], AS_OF)
    assert (moved['change_7d'], moved['momentum']) == (-20.0, 20.0)


CLIMB = [1000] * 22 + [1000, 950, 900, 850, 800, 780, 760, 750]   # -25% over 7 days, never worse


@pytest.mark.parametrize('series, rising', [
    (CLIMB, True),
    (CLIMB[:23] + [1050] + CLIMB[24:], False),                          # worse than the start on the way
    ([None] * 16 + CLIMB[16:], True),                                   # exactly 14 observed days: enough
    ([None] * 17 + CLIMB[17:], False),                                  # 13 observed days: not enough
    (CLIMB[:22] + [1000, None, None, 850, 800, 780, 760, 750], True),   # 6 of the last 8 days: enough
    (CLIMB[:22] + [1000, None, None, None, 800, 780, 760, 750], False), # 5 of the last 8: not enough
    (CLIMB[:22] + [1000, 990, 980, 970, 960, 950, 940, 810], False),    # 19% is not 20%
    (CLIMB[:-1] + [None], True),                                        # seen yesterday is still live
    (CLIMB[:-2] + [None, None], False),                                 # stale
])
def test_rising_rule(series, rising):
    assert len(series) == 30
    assert book_market.metrics(series, AS_OF)['rising'] is rising


def test_sparkline_draws_observed_points_only():
    path, points = book_market.sparkline([100, 200, None, 150, None, None, 120, 130], width=80, height=30)
    assert path.count('M') == 2           # two runs of consecutive days
    assert len(points) == 1               # the lone day is a dot, not a line through the gap
    first = [float(v) for v in path.split('L')[0][1:].split()]
    second = [float(v) for v in path.split('L')[1].split('M')[0].split()]
    assert first[1] < second[1]           # rank 100 (better) is drawn above rank 200
    assert book_market.sparkline([None] * 30) == ('', [])


def test_map_never_mixes_lists_or_formats():
    registry = books_registry.load_registry()
    data = json.loads((ROOT / 'data' / 'books' / 'market_illustrative.json').read_text(encoding='utf-8'))
    climb = [500 + 10 * i for i in range(30)][::-1]     # strongest, live, improving
    for rec in data['records']:
        if rec['slug'] == 'the-fiat-standard':
            rec['series'] = list(climb)
    view = book_market.view(registry, data)
    plotted = {b['slug'] for b in view['map']['books']}
    assert 'the-fiat-standard' not in plotted
    assert {'title': 'The Fiat Standard', 'format': 'Kindle', 'rank_list': 'Kindle Store'} in view['excluded_lists']
    rows = {r['slug']: r for r in view['rows']}
    for slug in plotted:
        r = rows[slug]
        assert (r['rank_list'], r['format'], r['state']) == ('Books', 'print', 'live')
        assert r['change_7d'] is not None and r['pub_year']
    strengths = sorted(view['map']['books'], key=lambda b: b['rank'])
    assert strengths[0]['strength'] == 1.0 and strengths[-1]['strength'] == 0.0
    assert len(plotted) <= book_market.MAP_MAX
    ranks = [r['rank'] for r in view['rows']]
    assert ranks == sorted(ranks, key=lambda v: (v is None, v or 0))  # rank ascending, no rank last


# ── Layout math (static/js/book_market.js under node) ────────────────────────

def test_cover_area_follows_rank_strength_and_keeps_the_cover_shape():
    out = run_node(JS / 'layout_check.js', ROOT / 'static' / 'js' / 'book_market.js')
    for c in out['coverSize']:
        assert c['area'] == pytest.approx(1000 + 8000 * c['s'], rel=1e-12)
        assert c['w'] / c['h'] == pytest.approx(c['aspect'], rel=1e-12)
        assert c['w'] * c['h'] == pytest.approx(c['area'], rel=1e-12)
    assert out['coverClamp'] == [1000, 9000]


def test_separation_respects_the_displacement_cap():
    out = run_node(JS / 'layout_check.js', ROOT / 'static' / 'js' / 'book_market.js')
    assert len(out['separate']) == 80
    assert sum(s['overlaps_before'] for s in out['separate']) > 50       # the cases do collide
    for s in out['separate']:
        assert s['every_node_within_cap'] and s['maxDx'] <= s['capX'] + 1e-9 and s['maxDy'] <= s['capY'] + 1e-9
        assert s['sizes_kept'] and s['repeatable']
    assert sum(s['overlaps_after'] for s in out['separate']) < sum(s['overlaps_before'] for s in out['separate']) / 2
    assert out['apart'] == {'maxDx': 0, 'maxDy': 0, 'iterations': 1, 'converged': True}
    assert out['pair']['overlaps'] == 0 and out['pair']['dx'][0] == -out['pair']['dx'][1] < 0
    assert out['tight']['overlaps'] == 1 and out['tight']['maxDx'] <= 5 and out['tight']['maxDy'] <= 5


def test_recency_scale_and_year_labels():
    out = run_node(JS / 'layout_check.js', ROOT / 'static' / 'js' / 'book_market.js')
    assert out['recency'] == sorted(out['recency']) and len(set(out['recency'])) == len(out['recency'])
    years = [y for y, _ in out['ticks']]
    xs = sorted(x for _, x in out['ticks'])
    assert 2025 in years and 1999 in years
    assert all(b - a >= 34 for a, b in zip(xs, xs[1:]))


# ── /media #books: the page's own script under node ──────────────────────────

def _render_media(tmp_path, payload):
    path = tmp_path / 'payload.json'
    path.write_text(json.dumps(payload), encoding='utf-8')
    return run_node(JS / 'media_books_harness.js', ROOT / 'templates' / 'media_hub.html', path)


def _metrics():
    def row(asin, bsr, hours_ago, **extra):
        fetched = NOW - timedelta(hours=hours_ago)
        return dict({'asin': asin, 'bsr': bsr, 'bsr_previous': None, 'bsr_change': None, 'fetch_status': 'ok',
                     'last_successful_fetch': fetched.isoformat()}, **extra)
    return {'last_updated': (NOW - timedelta(hours=2)).isoformat(), 'books': [
        row('B0DVTCVX8J', 50373, 2, bsr_change=-5.6, rank_score=59),     # The Big Print (series book)
        row('0684832720', 10230, 2, bsr_change=28.28, rank_score=72),
        row('B0HR576L3M', 1540887, 2, rank_category='Kindle Store'),      # The Fiat Standard, Kindle
        row('1119473861', 34197, 24 * 5),                                  # stale
    ]}


def test_media_grid_labels_every_book_honestly(tmp_path):
    payload, status = book_metrics.metrics_response(metrics_path=_write(tmp_path, 'm.json', _metrics()),
                                                    featured_path=tmp_path / 'none.json', now=NOW)
    assert status == 200
    out = _render_media(tmp_path, payload)
    cards = re.findall(r'<article class="bk-card".*?</article>', out['libraryGrid'], re.S)
    assert len(cards) == 18 and out['libraryCount'] == '18 books'
    unranked = [c for c in cards if 'data-status="no_data"' in c]
    assert len(unranked) == 14
    for card in unranked:
        assert 'No rank yet' in card and not re.search(r'#\d', card)
    everything = json.dumps(out).lower()
    assert 'bestseller' not in everything and 'best seller' not in everything.replace('best sellers rank', '')
    assert sum('Kindle on Amazon' in c for c in cards) == 1 and sum('Buy on Amazon' in c for c in cards) == 17
    assert all('rel="sponsored noopener"' in c and 'target="_blank"' in c and '(opens in a new tab)' in c for c in cards)
    for book in books_registry.load_registry():  # each buy link's accessible name says which book
        assert f': {html.escape(book["title"], quote=False)} (opens in a new tab)' in out['libraryGrid'], book['title']
    assert '>#1<' not in out['libraryGrid']  # no list-position badge
    assert out['chartCardDisplay'] == 'none'  # no Chart.js in the harness: the card hides, the grid stays


def test_media_series_button_only_when_the_data_has_a_series_link(tmp_path):
    metrics_path = _write(tmp_path, 'm.json', _metrics())
    payload, _ = book_metrics.metrics_response(metrics_path=metrics_path, featured_path=tmp_path / 'none.json', now=NOW)
    assert payload['featured']['title'] == 'The Big Print'
    out = _render_media(tmp_path, payload)
    url, label = books_registry.series_link(books_registry.by_id('B0DVTCVX8J'))
    assert out['featuredHidden'] is False
    assert out['featured'].count('bk-btn-ghost') == 1 and f'href="{url}"' in out['featured'] and label in out['featured']
    assert 'Big Print Series' not in out['featured'] and 'youtube.com/@ProtocolPulse' not in out['featured']

    cfg = {'title': 'The Big Print', 'author': 'Lawrence Lepard', 'end_date': '2026-12-31', 'badge': 'FEATURED',
           'amazon_url': 'https://www.amazon.com/dp/B0DVTCVX8J?tag=protocolpulse-20', 'cover_url': '/static/x.jpg'}
    payload, _ = book_metrics.metrics_response(metrics_path=metrics_path, featured_path=_write(tmp_path, 'f.json', cfg), now=NOW)
    out = _render_media(tmp_path, payload)
    assert 'bk-btn-ghost' not in out['featured'] and 'series' not in out['featured'].lower()
    assert 'Buy on Amazon' in out['featured']

    payload, _ = book_metrics.metrics_response(metrics_path=metrics_path,
                                               featured_path=_write(tmp_path, 'f2.json', dict(cfg, series_url='/podcasts#series')),
                                               now=NOW)
    out = _render_media(tmp_path, payload)
    assert 'href="/podcasts#series"' in out['featured'] and 'The Big Print series' in out['featured']  # label from the data


def _write(tmp_path, name, obj):
    path = tmp_path / name
    path.write_text(json.dumps(obj), encoding='utf-8')
    return path


DISCLOSURE = 'As an Amazon Associate, Protocol Pulse earns from qualifying purchases.'
SITE_ICON = 'https://bitcoinmagazine.com/wp-content/uploads/2024/09/cropped-Bitcoin-Magazine-glyph-black-01-32x32.png'


def render_media(client, podcasts=()):
    from flask import render_template
    with client.application.test_request_context('/media'):
        return render_template('media_hub.html', feed_matrix={'podcasts': list(podcasts), 'videos': [], 'kol': []},
                               feed_stats={}, ticker_items=[])


def test_media_has_no_previous_fetch_rising_stars(client, tmp_path):
    page = render_media(client)
    assert 'rising' not in page.lower()           # no section, legend entry, script step or label
    legend = re.search(r'<ul class="bk-legend"[^>]*>(.*?)</ul>', page, re.S).group(1)
    assert re.findall(r'</span>([^<]+)</li>', legend) == ['PP Series', 'Other']
    metrics = _metrics()
    metrics['books'][1].update(bsr_change=-61.0, is_rising=True)  # an old collector row with the flag set
    payload, _ = book_metrics.metrics_response(metrics_path=_write(tmp_path, 'm.json', metrics),
                                               featured_path=tmp_path / 'none.json', now=NOW)
    assert 'rising' not in json.dumps(payload).lower()
    assert 'rising' not in json.dumps(_render_media(tmp_path, payload)).lower()


def test_media_books_section_carries_the_affiliate_disclosure(client):
    page = render_media(client)
    books = page[page.index('<div id="books"'):]
    assert books.count(DISCLOSURE) == 1
    assert books.index(DISCLOSURE) < books.index('id="featuredBookBanner"') < books.index('id="libraryGrid"')


@pytest.mark.parametrize('thumb, initials', [
    (SITE_ICON, 'BM'),
    ('https://example.org/favicon.ico?v=3', 'BM'),
    ('https://example.org/wp-content/uploads/cropped-site-icon-192x192.png', 'BM'),
    ('https://cdn.example.org/art/show-3000x3000.jpg', None),     # episode artwork: requested as before
    ('', None),
])
def test_media_never_requests_a_feed_site_icon(client, thumb, initials):
    ep = {'feed_name': 'Bitcoin Magazine Podcast', 'title': 'An episode', 'thumbnail_url': thumb,
          'source_url': 'https://example.org/ep', 'signal_score': 0}
    page = render_media(client, [ep])
    feed = page[page.index('id="podFeed"'):page.index('id="vidCol"')]
    shown = re.findall(r'<span class="fi-thumb fi-initials" aria-hidden="true">([^<]*)</span>', feed)
    imgs = re.findall(r'<img class="fi-thumb" src="([^"]*)"', feed)
    if initials:
        assert shown == [initials] and imgs == []
    else:
        assert shown == [] and imgs == ([thumb] if thumb else [])
    assert 'bitcoinmagazine.com' not in feed
