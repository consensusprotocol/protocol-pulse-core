"""Book Terminal: registry, /api/books/metrics payload, collector history lines, rank parsing.

No network: an autouse fixture refuses sockets, the collector gets a fake fetch, and every
file the collector writes goes to tmp_path. The HTML fixtures are hand-written snippets in
the shape of Amazon product pages, not saved pages.

Run: python3 -m pytest -q tests/books/ -p no:cacheprovider
"""
import importlib.util
import json
import logging
import socket
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
FIXTURES = Path(__file__).resolve().parent / 'fixtures'
sys.path.append(str(ROOT / 'core'))

import books_registry  # noqa: E402
import book_metrics  # noqa: E402

_spec = importlib.util.spec_from_file_location('refresh_book_metrics', ROOT / 'scripts' / 'refresh_book_metrics.py')
collector = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(collector)

# IDs the site used before the registry: 404 on Amazon or the wrong book.
DEAD_IDS = ['B07FCGQ672', 'B09WFDTX49', '1097476922', '1642790622', '1916294216',
            '1416532194', '0470181552', '1544542895', 'B0BW3MTQG6', '1544526474']
CRYPTOASSETS_ID = '1260026671'
NOW = datetime(2026, 11, 24, 12, 0, tzinfo=timezone.utc)


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def refuse(*args, **kwargs):
        raise AssertionError('network access attempted in a book terminal test')
    monkeypatch.setattr(socket.socket, 'connect', refuse)
    monkeypatch.setattr(socket.socket, 'connect_ex', refuse)
    monkeypatch.setattr(socket, 'getaddrinfo', refuse)


def isbn13_ok(isbn):
    if len(isbn) != 13 or not isbn.isdigit():
        return False
    total = sum(int(d) * (1 if i % 2 == 0 else 3) for i, d in enumerate(isbn[:12]))
    return (10 - total % 10) % 10 == int(isbn[12])


def page(name):
    return (FIXTURES / name).read_text(encoding='utf-8')


# ── Registry and the Media Hub list ──────────────────────────────────────────

def test_registry_loads_18_titles_with_unique_ids_and_valid_isbn13():
    books = books_registry.load_registry()
    assert len(books) == 18
    for key in ('slug', 'title', 'amazon_id', 'isbn13'):
        assert len({b[key] for b in books}) == 18, key
    assert [b['isbn13'] for b in books if not isbn13_ok(b['isbn13'])] == []
    assert not isbn13_ok('9781097476922')  # the old Inventing Bitcoin cover number is no ISBN-13


def test_no_cryptoassets_and_no_dead_ids():
    books = books_registry.load_registry()
    assert not any('cryptoassets' in b['title'].lower() for b in books)
    assert {b['amazon_id'] for b in books}.isdisjoint(DEAD_IDS + [CRYPTOASSETS_ID])
    assert set(collector.TRACKED_ASINS) == {b['amazon_id'] for b in books}


def test_softwar_is_lowerys_book_with_the_verified_id():
    book = books_registry.by_id('B0BW358F37')
    assert (book['title'], book['author']) == ('Softwar', 'Jason P. Lowery')
    our, recommended = books_registry.media_hub_lists()
    [softwar] = [b for b in our + recommended if b['title'] == 'Softwar']
    assert softwar['author'] == 'Jason P. Lowery'
    assert softwar['amazon_url'] == 'https://www.amazon.com/dp/B0BW358F37?tag=protocolpulse-20'
    assert softwar['free_alt'] == 'https://hdl.handle.net/1721.1/153030'
    assert 'Ellison' not in json.dumps(our + recommended)


def test_media_hub_lists_come_from_the_registry():
    registry = books_registry.load_registry()
    our, recommended = books_registry.media_hub_lists('protocolpulse-20')
    assert [b['title'] for b in our] == [b['title'] for b in registry if b.get('pp_series')]
    assert [b['title'] for b in recommended] == [b['title'] for b in registry if not b.get('pp_series')]
    assert (len(our), len(recommended)) == (4, 14)
    for entry in our + recommended:
        assert entry['title'] and entry['author'] and entry['description'] and entry['cover_url']
        assert entry['amazon_url'].endswith('?tag=protocolpulse-20')
    assert all(isinstance(b['essential'], bool) for b in recommended)
    assert not any('bestseller' in b for b in our + recommended)  # an editorial pick, not a sales claim
    blob = json.dumps(our + recommended)
    assert [d for d in DEAD_IDS + [CRYPTOASSETS_ID] if d in blob] == []
    assert 'The Money Revolution' in blob and 'The Truth About Money' not in blob


def test_media_hub_lists_are_fresh_dicts():
    our, _ = books_registry.media_hub_lists()
    our[0]['title'] = 'changed by a caller'  # the /media route adds keys to these dicts
    assert books_registry.media_hub_lists()[0][0]['title'] != 'changed by a caller'


def test_local_cover_files_exist():
    for book in books_registry.load_registry():
        url = books_registry.cover_url(book)
        if url.startswith('/static/'):
            assert (ROOT / url.lstrip('/')).is_file(), url


def test_media_hub_title_block_is_plain_text():
    from jinja2 import Environment, FileSystemLoader
    template = Environment(loader=FileSystemLoader(str(ROOT / 'templates'))).get_template('media_hub.html')
    title = ''.join(template.blocks['title'](template.new_context({})))
    assert title == 'Bitcoin Media Command Center — Protocol Pulse'


def test_vendored_chartjs_is_4_4_7():
    js = (ROOT / 'static' / 'vendor' / 'chart.umd.min.js').read_bytes()
    assert len(js) > 150_000
    assert b'Chart.js v4.4.7' in js[:1000] and b'MIT License' in js[:1000]


# ── /api/books/metrics payload ───────────────────────────────────────────────

def _iso(dt):
    return dt.isoformat()


def _row(asin, bsr, fetched, **extra):
    row = {'asin': asin, 'bsr': bsr, 'bsr_previous': None, 'bsr_change': None,
           'fetch_status': 'ok' if fetched else 'error',
           'fetch_error': None if fetched else 'HTTP 404',
           'last_successful_fetch': _iso(fetched) if fetched else None}
    row.update(extra)
    return row


FIXTURE_METRICS = {
    'last_updated': _iso(NOW - timedelta(hours=2)),
    'fetch_health': {'success': 2, 'failed': 2, 'total': 4},
    'books': [
        # ok, written by the old collector (score under 'velocity', no rank_score)
        _row('0684832720', 10230, NOW - timedelta(hours=2), bsr_previous=7975, bsr_change=28.28, velocity=72),
        # stale: last good fetch 5 days ago, flagged rising back then
        _row('B0DVTCVX8J', 50373, NOW - timedelta(days=5), bsr_change=-12.5, rank_score=59, is_rising=True),
        # a seeded number that was never fetched: no_data
        _row('1119473861', 3210, None, velocity=85),
        # Cryptoassets: not in the registry
        _row(CRYPTOASSETS_ID, 247482, NOW - timedelta(hours=2), velocity=20),
    ],
}


def _response(tmp_path, metrics, featured=None):
    metrics_path = tmp_path / 'book_metrics.json'
    metrics_path.write_text(json.dumps(metrics), encoding='utf-8')
    featured_path = tmp_path / 'featured_book.json'
    if featured is not None:
        featured_path.write_text(json.dumps(featured), encoding='utf-8')
    return book_metrics.metrics_response(metrics_path=metrics_path, featured_path=featured_path, now=NOW)


def test_api_data_status_ok_stale_no_data(tmp_path):
    payload, status = _response(tmp_path, FIXTURE_METRICS)
    assert status == 200
    books = {b['asin']: b for b in payload['books']}
    assert len(payload['books']) == len(books) == 18
    assert CRYPTOASSETS_ID not in books

    ok = books['0684832720']
    assert (ok['data_status'], ok['bsr'], ok['bsr_change']) == ('ok', 10230, 28.28)
    assert ok['rank_score'] == ok['velocity'] == 72

    stale = books['B0DVTCVX8J']
    assert (stale['data_status'], stale['bsr']) == ('stale', 50373)
    assert stale['last_successful_fetch'] == _iso(NOW - timedelta(days=5))
    assert stale['is_rising'] is False  # momentum only from fresh ranks
    assert stale['rank_score'] == stale['velocity'] == 59

    for asin in ('1119473861', 'B0BW358F37'):  # seeded number / no row at all
        book = books[asin]
        assert book['data_status'] == 'no_data'
        assert book['bsr'] is None and book['bsr_change'] is None
        assert book['rank_score'] is None and book['velocity'] is None

    assert payload['fetch_health'] == {'last_run': {'success': 2, 'failed': 2, 'total': 4},
                                       'books': 18, 'ok': 1, 'stale': 1, 'no_data': 16}
    assert payload['stale'] is False
    assert not any('rank_nov24' in b for b in payload['books'])


@pytest.mark.parametrize('age_hours, expected', [(0, 'ok'), (47.9, 'ok'), (48.1, 'stale'), (720, 'stale')])
def test_data_status_48h_boundary(age_hours, expected):
    row = {'bsr': 1234, 'last_successful_fetch': _iso(NOW - timedelta(hours=age_hours))}
    assert book_metrics.data_status(row, NOW) == expected


@pytest.mark.parametrize('row', [
    {},
    {'bsr': 1234, 'last_successful_fetch': None},
    {'bsr': None, 'last_successful_fetch': '2026-11-24T10:00:00+00:00'},
    {'bsr': 1234, 'last_successful_fetch': 'not a date'},
])
def test_data_status_no_data(row):
    assert book_metrics.data_status(row, NOW) == 'no_data'


def test_rising_and_featured_use_only_fresh_ranks(tmp_path):
    metrics = {'last_updated': _iso(NOW - timedelta(hours=3)), 'books': [
        _row('006236250X', 282953, NOW - timedelta(hours=3), bsr_change=-61.19, is_rising=True, rank_score=20),
        _row('B0DVTCVX8J', 50373, NOW - timedelta(days=5), bsr_change=-30.0, is_rising=True, rank_score=59),
        _row('1119473861', 3210, None),
    ]}
    payload, status = _response(tmp_path, metrics)  # no featured_book.json: fallback
    assert status == 200
    assert [b['asin'] for b in payload['rising']] == ['006236250X']
    assert payload['featured']['title'] == 'Digital Gold'
    assert payload['featured']['badge'] == 'RISING'
    assert '#282,953' in payload['featured']['body_text']


def test_featured_without_any_fresh_rank_is_none(tmp_path):
    payload, status = _response(tmp_path, {'last_updated': None, 'books': [_row('1119473861', 3210, None)]})
    assert status == 200
    assert payload['featured'] is None and payload['stale'] is True


def test_configured_featured_book_runs_until_its_end_date(tmp_path):
    cfg = {'title': 'The Big Print', 'author': 'Lawrence Lepard', 'end_date': '2026-12-31',
           'amazon_url': 'https://www.amazon.com/dp/B0DVTCVX8J?tag=protocolpulse-20'}
    payload, _ = _response(tmp_path, FIXTURE_METRICS, featured=cfg)
    assert payload['featured'] == cfg
    payload, _ = _response(tmp_path, FIXTURE_METRICS, featured=dict(cfg, end_date='2026-06-01'))
    assert payload['featured']['title'] == 'The Sovereign Individual'  # the only fresh rank


@pytest.mark.parametrize('content', ['{"books": [', '[1, 2, 3]', '{"books": {"0684832720": {}}}'])
def test_api_unreadable_metrics_is_503(tmp_path, caplog, content):
    path = tmp_path / 'book_metrics.json'
    path.write_text(content, encoding='utf-8')
    payload, status = book_metrics.metrics_response(metrics_path=path, featured_path=tmp_path / 'none.json', now=NOW)
    assert status == 503
    assert payload['books'] == [] and payload['error'].startswith('book metrics unavailable')
    assert 'book metrics unavailable' in caplog.text  # logged, not silent


def test_api_missing_metrics_file_is_503(tmp_path):
    payload, status = book_metrics.metrics_response(metrics_path=tmp_path / 'missing.json',
                                                    featured_path=tmp_path / 'none.json', now=NOW)
    assert (status, payload['books']) == (503, [])


def test_api_registry_failure_is_503(tmp_path, monkeypatch):
    def broken(*args, **kwargs):
        raise ValueError('registry unreadable')
    monkeypatch.setattr(books_registry, 'load_registry', broken)
    payload, status = _response(tmp_path, FIXTURE_METRICS)
    assert (status, payload['books']) == (503, [])


# ── Collector: parsing and history ───────────────────────────────────────────

def test_parse_rank_captures_category_from_detail_bullets():
    assert collector.parse_rank(page('amazon_dp_books_detail_bullets.html')) == (51009, 'Books')


def test_parse_rank_captures_category_from_product_table():
    assert collector.parse_rank(page('amazon_dp_kindle_product_table.html')) == (1540887, 'Kindle Store')


@pytest.mark.parametrize('html, expected', [
    ('<div id="detailBulletsWrapper_feature_div"><span>Best Sellers Rank:</span> #1,234 Paid in Kindle Store '
     '(See Top 100 Paid in Kindle Store)</div>', (1234, 'Kindle Store (Paid)')),
    # raw-line method: a CSS colour after the label must not read as a rank
    ('<p><b>Best Sellers Rank:</b><span style="color:#333"> #2,345 in Books (See Top 100 in Books)</span></p>',
     (2345, 'Books')),
    ('<p>Best Sellers Rank: #777</p>', (777, None)),
    ("<html><body><h1>Sorry, we just need to make sure you're not a robot.</h1></body></html>", (None, None)),
])
def test_parse_rank_variants(html, expected):
    assert collector.parse_rank(html) == expected


def test_scrape_bsr_says_why_it_failed():
    assert collector.scrape_bsr('X', fetch=lambda a: (404, '')) == (None, None, 'HTTP 404')
    assert collector.scrape_bsr('X', fetch=lambda a: (200, '<p>captcha</p>')) == (None, None, 'BSR not found in page')

    def timeout(asin):
        raise TimeoutError('read timed out')
    rank, category, error = collector.scrape_bsr('X', fetch=timeout)
    assert (rank, category) == (None, None) and error.startswith('scrape error: TimeoutError')
    ok = collector.scrape_bsr('X', fetch=lambda a: (200, page('amazon_dp_books_detail_bullets.html')))
    assert ok == (51009, 'Books', None)


@pytest.fixture
def collector_files(tmp_path, monkeypatch):
    metrics = tmp_path / 'book_metrics.json'
    history = tmp_path / 'book_metrics_history.jsonl'
    monkeypatch.setattr(collector, 'METRICS_FILE', metrics)
    monkeypatch.setattr(collector, 'HISTORY_FILE', history)
    return metrics, history


def test_collector_history_and_metrics_on_failure(collector_files):
    metrics_path, history_path = collector_files
    prev_good, never_fetched, riser, new_id = '0684832720', '1119473861', 'B0DVTCVX8J', '1119856264'
    prev_ts = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
    metrics_path.write_text(json.dumps({'last_updated': prev_ts, 'books': [
        {'asin': prev_good, 'bsr': 10230, 'bsr_previous': 7975, 'bsr_change': 28.28, 'is_rising': False,
         'fetch_status': 'ok', 'last_successful_fetch': prev_ts},
        {'asin': riser, 'bsr': 60000, 'fetch_status': 'ok', 'last_successful_fetch': prev_ts},
        {'asin': never_fetched, 'bsr': 3210, 'fetch_status': 'error', 'last_successful_fetch': None},
        {'asin': CRYPTOASSETS_ID, 'bsr': 247482, 'fetch_status': 'ok', 'last_successful_fetch': prev_ts},
    ]}), encoding='utf-8')
    ok_page = page('amazon_dp_books_detail_bullets.html')  # #51,009 in Books

    def fake_fetch(asin):
        return (404, 'Not Found') if asin in (prev_good, never_fetched) else (200, ok_page)

    result = collector.refresh(fetch=fake_fetch, pause=lambda: None)
    assert result == {'success': 16, 'failed': 2, 'history_errors': 0, 'written': True}

    lines = [json.loads(line) for line in history_path.read_text(encoding='utf-8').splitlines()]
    assert len(lines) == 18
    by_asin = {line['asin']: line for line in lines}
    for asin in (prev_good, never_fetched):
        line = by_asin[asin]
        assert (line['status'], line['error'], line['marketplace']) == ('error', 'HTTP 404', 'US')
        assert line['bsr'] is None and line['category'] is None  # never the carried 10230 or the seeded 3210
    good = by_asin[riser]
    assert set(good) == {'asin', 'bsr', 'ts', 'status', 'error', 'category', 'marketplace'}
    assert (good['status'], good['bsr'], good['category'], good['error']) == ('ok', 51009, 'Books', None)

    rows = {b['asin']: b for b in json.loads(metrics_path.read_text(encoding='utf-8'))['books']}
    assert set(rows) == set(collector.TRACKED_ASINS)  # Cryptoassets row dropped
    kept = rows[prev_good]  # metrics file: last good value kept and flagged
    assert (kept['bsr'], kept['fetch_status'], kept['fetch_error']) == (10230, 'error', 'HTTP 404')
    assert kept['last_successful_fetch'] == prev_ts and kept['bsr_change'] == 28.28
    never = rows[never_fetched]
    assert never['bsr'] is None and never['rank_score'] is None and never['last_successful_fetch'] is None
    rose = rows[riser]
    assert rose['bsr_previous'] == 60000 and rose['is_rising'] is True
    assert rose['bsr_change'] == collector.compute_bsr_change_pct(60000, 51009) < -10
    assert rose['rank_category'] == 'Books' and rose['rank_score'] == collector.compute_rank_score(51009)
    first = rows[new_id]  # first fetch of a newly tracked ID: no change, not rising
    assert (first['bsr'], first['bsr_change'], first['is_rising']) == (51009, None, False)
    assert not any(r['bsr'] == 50000 for r in rows.values())
    assert not any(r['is_breakout'] for r in rows.values())


def test_collector_logs_a_failed_history_write(collector_files, caplog):
    metrics_path, history_path = collector_files
    history_path.mkdir()  # appending to a directory raises IsADirectoryError
    ok_page = page('amazon_dp_books_detail_bullets.html')
    with caplog.at_level(logging.ERROR):
        result = collector.refresh(fetch=lambda asin: (200, ok_page), pause=lambda: None)
    assert result['history_errors'] == 18 and result['written'] is True
    assert 'history write failed' in caplog.text
    assert json.loads(metrics_path.read_text(encoding='utf-8'))['fetch_health']['success'] == 18
