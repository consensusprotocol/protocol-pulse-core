"""Book Market prototype (/books/market): what the page shows, derived from ILLUSTRATIVE data.

data/books/market_illustrative.json is synthetic (scripts/books/make_illustrative_market.py):
nothing in it was observed. This module applies the rules real data will need later, so the
prototype shows honest states:

  state        'live' (observed on the dataset date or the day before, the API's 48 h rule),
               'stale' (observed earlier in the window), 'unavailable' (never observed).
  change_7d    % change of the rank number between the latest observation and the one 7 days
               before it; None unless the book is live and both days were observed. Negative =
               rank improved. momentum = -change_7d (up = improving), used by the map.
  rising       rising_star_candidate_v1, the frozen candidate rule (core/book_signal_rules.py),
               applied to the illustrative series as observations: the page shows the rule and
               says it ran on illustrative data. No observed rank is ever scored here.
  map          only books ranked in the same Amazon list and format (Books, print), live, with
               a 7-day change and a verified pub_year; at most MAP_MAX, strongest rank first.
               Kindle Store ranks (The Fiat Standard) are listed as excluded, never mixed in.
  sparkline    observed points only; a missing day breaks the line.
  map points   also carry what the detail view shows: edition, the exact publication date when
               the registry's source records one, rank list, observed days and the sparkline.

Stdlib only; the tests use it without Flask.
"""
import json
import math
from datetime import date, timedelta
from pathlib import Path

import book_signal_rules
import books_registry

ILLUSTRATIVE_PATH = Path(__file__).resolve().parent.parent / 'data' / 'books' / 'market_illustrative.json'
LIVE_MAX_AGE_DAYS = 1
MAP_MAX = 8
MAP_LIST, MAP_FORMAT = 'Books', 'print'
STATE_ORDER = {'live': 0, 'stale': 1, 'unavailable': 2}


def load(path=ILLUSTRATIVE_PATH):
    """The illustrative dataset, refused unless it and every record say illustrative: true."""
    with open(path, encoding='utf-8') as f:
        data = json.load(f)
    if data.get('illustrative') is not True:
        raise ValueError(f'{path}: not flagged illustrative')
    window = data['window_days']
    for rec in data['records']:
        if rec.get('illustrative') is not True or len(rec['series']) != window:
            raise ValueError(f'{path}: record {rec.get("slug")!r} not flagged illustrative or wrong length')
    return data


def is_rising(series, as_of):
    """rising_star_candidate_v1 on the dataset date, the series' days read as observations."""
    days = len(series)
    dated = {as_of - timedelta(days=days - 1 - i): v for i, v in enumerate(series) if v is not None}
    return book_signal_rules.evaluate(dated, as_of)['qualifies']


def metrics(series, as_of):
    """Per-book derived values from one illustrative series (oldest first, None = no observation)."""
    seen = [i for i, v in enumerate(series) if v is not None]
    if not seen:
        return {'state': 'unavailable', 'rank': None, 'change_7d': None, 'momentum': None,
                'observed_days': 0, 'last_observed': None, 'rising': False}
    last = seen[-1]
    age = len(series) - 1 - last
    state = 'live' if age <= LIVE_MAX_AGE_DAYS else 'stale'
    change = None
    if state == 'live' and last >= 7 and series[last - 7] is not None:
        change = round((series[last] - series[last - 7]) / series[last - 7] * 100, 1)
    return {
        'state': state,
        'rank': series[last],
        'change_7d': change,
        'momentum': -change if change is not None else None,
        'observed_days': len(seen),
        'last_observed': (as_of - timedelta(days=age)).isoformat(),
        'rising': is_rising(series, as_of),
    }


def sparkline(series, width=120, height=30, pad=3):
    """(path d, isolated points) for an SVG sparkline of the observed values only.

    Log scale, better (smaller) rank drawn higher. Each run of consecutive observed days is
    one 'M ... L ...' segment, so a missing day is a gap in the line; a run of one day has no
    line and is returned as a point instead.
    """
    observed = [v for v in series if v is not None]
    if not observed:
        return '', []
    lo, hi = math.log(min(observed)), math.log(max(observed))
    span = (hi - lo) or 1.0
    step = (width - 2 * pad) / max(len(series) - 1, 1)

    def xy(i, v):
        return round(pad + i * step, 1), round(pad + (math.log(v) - lo) / span * (height - 2 * pad), 1)

    parts, points, run = [], [], []
    for i, v in enumerate(series + [None]):
        if v is not None:
            run.append(xy(i, v))
            continue
        if len(run) == 1:
            points.append(run[0])
        elif run:
            parts.append('M' + ' L'.join(f'{x} {y}' for x, y in run))
        run = []
    return ' '.join(parts), points


def strength(ranks):
    """Normalised rank strength in [0, 1] for each rank of the set: log scale, best rank -> 1."""
    logs = [math.log(r) for r in ranks]
    lo, hi = min(logs), max(logs)
    return [1.0 if hi == lo else round((hi - v) / (hi - lo), 4) for v in logs]


def view(registry, data, tag=books_registry.DEFAULT_TAG):
    """Everything /books/market renders: stats, rows (all tracked books), map, rising."""
    as_of = date.fromisoformat(data['as_of'])
    books = {b['slug']: b for b in registry}
    rows = []
    for rec in data['records']:
        book = books.get(rec['slug'])
        if book is None:  # a record for a book no longer in the registry
            continue
        m = metrics(rec['series'], as_of)
        path, points = sparkline(rec['series'])
        seen = date.fromisoformat(m['last_observed']) if m['last_observed'] else None
        rows.append(dict(m, slug=book['slug'], title=book['title'], author=book['author'],
                         last_label=f'{seen:%b} {seen.day}' if seen else None,
                         state_order=STATE_ORDER[m['state']],
                         pub_year=book.get('pub_year'), format=rec['format'], rank_list=rec['rank_list'],
                         cover_url=books_registry.cover_url(book), amazon_url=books_registry.amazon_url(book, tag),
                         purchase_label=books_registry.purchase_label(book), spark_path=path, spark_points=points,
                         illustrative=True))
    # Rank ascending, books without a rank last: the order the table header's aria-sort states.
    rows.sort(key=lambda r: (r['rank'] is None, r['rank'] or 0, r['title']))

    comparable = [r for r in rows if r['rank_list'] == MAP_LIST and r['format'] == MAP_FORMAT]
    eligible = [r for r in comparable if r['state'] == 'live' and r['change_7d'] is not None and r['pub_year']]
    plotted = sorted(eligible, key=lambda r: r['rank'])[:MAP_MAX]
    map_books = []
    for r, s in zip(plotted, strength([r['rank'] for r in plotted]) if plotted else []):
        book = books[r['slug']]
        exact = books_registry.pub_date(book)
        map_books.append({k: r[k] for k in ('slug', 'title', 'author', 'pub_year', 'rank', 'change_7d', 'momentum', 'cover_url',
                                            'rank_list', 'observed_days', 'spark_path', 'spark_points')}
                         | {'strength': s, 'pub_date': exact.isoformat() if exact else None,
                            'published': books_registry.pub_date_label(book),
                            'edition': f"{'Kindle' if r['format'] == 'Kindle' else 'Print'} edition, ISBN-13 {book['isbn13']}"})
    years = [b['pub_year'] for b in map_books] or [as_of.year]
    bound = max([10.0] + [math.ceil(abs(b['momentum']) / 10.0) * 10.0 for b in map_books])
    excluded_lists = [r for r in rows if r not in comparable]
    not_plotted = [r for r in comparable if r not in plotted]
    return {
        'as_of': data['as_of'],
        'note': data['note'],
        'window_days': data['window_days'],
        'stats': {'tracked': len(rows), 'live': sum(r['state'] == 'live' for r in rows),
                  'stale': sum(r['state'] == 'stale' for r in rows),
                  'unavailable': sum(r['state'] == 'unavailable' for r in rows)},
        'rows': rows,
        'rising': [r for r in rows if r['rising']],
        'map': {'books': map_books, 'x': {'min': min(years), 'max': max(years)}, 'as_of_year': as_of.year,
                'window_days': data['window_days'],
                'y': {'min': -bound, 'max': bound}, 'list': MAP_LIST, 'format': MAP_FORMAT,
                'max_books': MAP_MAX, 'cap_fraction': 0.06},
        'excluded_lists': [{'title': r['title'], 'format': r['format'], 'rank_list': r['rank_list']} for r in excluded_lists],
        'not_plotted': [{'title': r['title'], 'reason': _why_not(r, plotted)} for r in not_plotted],
        'rules': {'live_max_age_days': LIVE_MAX_AGE_DAYS, 'rising': dict(book_signal_rules.RISING_STAR_RULE)},
    }


def _why_not(row, plotted):
    if row['state'] != 'live':
        return 'no live rank' if row['state'] == 'stale' else 'no data'
    if row['change_7d'] is None:
        return 'no 7-day change (missing day)'
    if not row['pub_year']:
        return 'no verified publication year'
    return f'outside the {MAP_MAX} strongest ranks'
