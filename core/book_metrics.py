"""Book Terminal API payload: the registry's books joined with the collector's metrics file.

/api/books/metrics (core/routes_api.py) returns metrics_response(). Every book in
data/books/registry.json appears once, in registry order; metrics rows for IDs outside the
registry are dropped. data_status per book:
  'ok'      last successful fetch less than 48 h ago
  'stale'   older: the rank is kept and marked, with last_successful_fetch as its date
  'no_data' never fetched (or no valid rank): bsr, bsr_change and rank_score are null
bsr_change is the collector's plain measurement against its previous good fetch. Nothing here
turns it into a momentum label: the previous-fetch 'rising' rule is retired (no 'rising' list,
no is_rising field, no RISING featured badge); the frozen candidate rule lives in
core/book_signal_rules.py and is not published. is_breakout only comes from 'ok' rows.
Stdlib only, so the tests need no Flask app.
"""
import json
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path

import books_registry

log = logging.getLogger(__name__)

_DATA = Path(__file__).resolve().parent.parent / 'data'
METRICS_PATH = _DATA / 'book_metrics.json'
FEATURED_PATH = _DATA / 'featured_book.json'
FRESH_HOURS = 48


def _parse_ts(value):
    try:
        ts = datetime.fromisoformat(value)
    except (TypeError, ValueError):
        return None
    return ts if ts.tzinfo else ts.replace(tzinfo=timezone.utc)


def data_status(row, now):
    """'ok', 'stale' or 'no_data' for one metrics row ({} for a book the collector never wrote)."""
    bsr = row.get('bsr')
    fetched = _parse_ts(row.get('last_successful_fetch'))
    if fetched is None or not isinstance(bsr, int) or bsr <= 0:
        return 'no_data'
    return 'ok' if now - fetched < timedelta(hours=FRESH_HOURS) else 'stale'


def book_rows(metrics, now, tag=books_registry.DEFAULT_TAG):
    """One row per registry book with its rank data and data_status."""
    books = metrics.get('books', [])
    if not isinstance(books, list):
        raise ValueError('metrics "books" is not a list')
    by_asin = {r.get('asin'): r for r in books if isinstance(r, dict)}
    rows = []
    for book in books_registry.load_registry():
        m = by_asin.get(book['amazon_id'], {})
        status = data_status(m, now)
        ranked = status != 'no_data'
        fresh = status == 'ok'
        score = m.get('rank_score', m.get('velocity')) if ranked else None
        rows.append({
            'slug': book['slug'],
            'title': book['title'],
            'author': book['author'],
            'asin': book['amazon_id'],
            'isbn13': book['isbn13'],
            'format': book.get('format'),
            'pp_series': bool(book.get('pp_series')),
            'cover_url': books_registry.cover_url(book),
            'amazon_url': books_registry.amazon_url(book, tag),
            'purchase_label': books_registry.purchase_label(book),
            'free_alt': books_registry.free_alt(book),
            'data_status': status,
            'bsr': m['bsr'] if ranked else None,
            'bsr_previous': m.get('bsr_previous') if ranked else None,
            'bsr_change': m.get('bsr_change') if ranked else None,
            'rank_category': m.get('rank_category') if ranked else None,
            'rank_score': score,
            'velocity': score,  # deprecated alias of rank_score: remove after one release
            'is_breakout': bool(m.get('is_breakout')) if fresh else False,
            'fetch_status': m.get('fetch_status'),
            'fetch_error': m.get('fetch_error'),
            'last_successful_fetch': m.get('last_successful_fetch') if ranked else None,
        })
    return rows


def _featured(cfg, rows, now):
    """featured_book.json while it runs; else the best-ranked fresh book, PP series first."""
    if cfg:
        end_date = cfg.get('end_date')
        end = _parse_ts(end_date) if end_date else None
        if end_date and end is None:
            log.warning('featured_book.json end_date %r unreadable; using the fallback', end_date)
        elif end is None or now <= end:
            return cfg
    fresh = [r for r in rows if r['data_status'] == 'ok']
    pp = [r for r in fresh if r['pp_series']]
    if pp:
        pick, badge = min(pp, key=lambda r: r['bsr']), 'PROTOCOL PULSE SERIES'
    elif fresh:
        pick, badge = min(fresh, key=lambda r: r['bsr']), 'TOP RANKED'
    else:
        return None
    where = f" in {pick['rank_category']}" if pick['rank_category'] else ''
    # The series button on /media renders only when the registry has a series link for the pick.
    series_url, series_label = books_registry.series_link(books_registry.by_id(pick['asin']) or {})
    return {
        'title': pick['title'],
        'author': pick['author'],
        'format': pick['format'],
        'cover_url': pick['cover_url'],
        'amazon_url': pick['amazon_url'],
        'purchase_label': pick['purchase_label'],
        'series_url': series_url,
        'series_label': series_label,
        'headline': pick['title'],
        'body_text': f"by {pick['author']} · Amazon US Best Sellers Rank #{pick['bsr']:,}{where}",
        'badge': badge,
    }


def build_payload(metrics, featured_cfg, now, tag=books_registry.DEFAULT_TAG):
    rows = book_rows(metrics, now, tag)
    counts = {s: sum(1 for r in rows if r['data_status'] == s) for s in ('ok', 'stale', 'no_data')}
    last_updated = metrics.get('last_updated') or None
    updated = _parse_ts(last_updated)
    return {
        'status': 'ok',
        'source': 'amazon_scrape',
        'marketplace': 'US',
        'last_updated': last_updated,
        'stale': updated is None or now - updated > timedelta(hours=FRESH_HOURS),
        'stale_after_hours': FRESH_HOURS,
        # last_run: the collector's own counts for its last run; the rest count the books below.
        'fetch_health': {'last_run': metrics.get('fetch_health') or None, 'books': len(rows), **counts},
        'featured': _featured(featured_cfg, rows, now),
        'books': rows,
    }


def _read_featured(path):
    """featured_book.json is optional: missing -> None; unreadable -> None, logged."""
    try:
        with open(path, encoding='utf-8') as f:
            cfg = json.load(f)
    except FileNotFoundError:
        return None
    except (OSError, ValueError) as e:
        log.warning('featured book config unreadable (%s): %s', path, e)
        return None
    return cfg if isinstance(cfg, dict) else None


def metrics_response(metrics_path=METRICS_PATH, featured_path=FEATURED_PATH, now=None,
                     tag=books_registry.DEFAULT_TAG):
    """(payload, http_status) for /api/books/metrics. Any failure is a 503 with an empty book list."""
    try:
        with open(metrics_path, encoding='utf-8') as f:
            metrics = json.load(f)
        if not isinstance(metrics, dict):
            raise ValueError('metrics file is not a JSON object')
        now = now or datetime.now(timezone.utc)
        return build_payload(metrics, _read_featured(featured_path), now, tag), 200
    except Exception as e:
        log.exception('book metrics unavailable')
        return {'error': f'book metrics unavailable ({type(e).__name__})', 'books': []}, 503
