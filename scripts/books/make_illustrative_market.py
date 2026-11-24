#!/usr/bin/env python3
"""Illustrative data for the /books/market prototype. NOT observed data. NOT for publication.

Every rank, gap, state and trend in the output is synthetic: a seeded random walk per book,
so the page can be designed and reviewed against realistic shapes (missing days, stale rows,
books with no data, a few sustained climbers) without publishing real rank analytics.
Deterministic: the same registry and seed give byte-identical output (tests/books checks the
committed file against a fresh run).

Taken from data/books/registry.json and not synthetic: the slug, the tracked format (print or
Kindle) and the name of the Amazon list the rank belongs to ("Books" / "Kindle Store", from
the suffix of the registry's one-time rank_nov24 note; its number is never read).

Output (data/books/market_illustrative.json): top-level illustrative=true, as_of, window_days,
seed, note; one record per registry book with illustrative=true, slug, format, rank_list and
series: window_days daily values, oldest first, null = no observation that day.
Derived views (live/stale/unavailable, 7-day change, rising rule) are computed by
core/book_market.py at render time, not stored here.

Run: python3 scripts/books/make_illustrative_market.py [--out PATH]
"""
import argparse
import hashlib
import json
import math
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REGISTRY = ROOT / 'data' / 'books' / 'registry.json'
OUT = ROOT / 'data' / 'books' / 'market_illustrative.json'

SEED = 'book-terminal-illustrative-v1'
AS_OF = '2026-11-24'
WINDOW = 30
N_UNAVAILABLE = 3   # books with no observation at all
N_STALE = 2         # last observation 4-9 days before AS_OF
N_SURGE = 2         # sustained climbers over the last 10 days
N_SPARSE = 1        # observed on roughly a third of the days
NOTE = ('Synthetic values from a seeded generator (scripts/books/make_illustrative_market.py). '
        'Not observed data. Not for publication.')


def _digest(slug, salt):
    return hashlib.sha256(f'{SEED}:{salt}:{slug}'.encode('utf-8')).hexdigest()


def _rank_list(book):
    note = book.get('rank_nov24') or ''
    return note.split(' in ', 1)[1].strip() if ' in ' in note else 'Books'


def _series(slug, profile):
    rng = random.Random(_digest(slug, 'series'))
    log_rank = rng.uniform(math.log(6_000), math.log(2_500_000))
    drift = rng.uniform(-0.02, 0.02)
    noise = rng.uniform(0.03, 0.10)
    values = []
    for day in range(WINDOW):
        mu, sigma = drift, noise
        if profile == 'surge' and day >= WINDOW - 10:
            mu, sigma = -0.05, 0.015
        log_rank = min(max(log_rank + rng.gauss(mu, sigma), math.log(1_500)), math.log(4_000_000))
        values.append(int(math.exp(log_rank)))
    seen_p = 0.35 if profile == 'sparse' else 0.9
    seen = [rng.random() < seen_p for _ in range(WINDOW)]
    if profile == 'surge':
        seen[WINDOW - 9:] = [True] * 9
    if profile == 'stale':
        last = WINDOW - 1 - rng.randint(4, 9)
        seen = [s and day < last for day, s in enumerate(seen)]
        seen[last] = True
    else:
        seen[-1] = True  # live: observed on AS_OF
    return [v if s else None for v, s in zip(values, seen)]


def build(registry_path=REGISTRY):
    books = json.loads(Path(registry_path).read_text(encoding='utf-8'))['books']
    order = sorted((b['slug'] for b in books), key=lambda s: _digest(s, 'profile'))
    profiles = {}
    cut = [N_UNAVAILABLE, N_STALE, N_SURGE, N_SPARSE]
    names = ['unavailable', 'stale', 'surge', 'sparse']
    i = 0
    for name, n in zip(names, cut):
        for slug in order[i:i + n]:
            profiles[slug] = name
        i += n
    records = []
    for book in books:
        profile = profiles.get(book['slug'], 'steady')
        series = [None] * WINDOW if profile == 'unavailable' else _series(book['slug'], profile)
        records.append({
            'slug': book['slug'],
            'illustrative': True,
            'format': 'Kindle' if book.get('format') == 'Kindle' else 'print',
            'rank_list': _rank_list(book),
            'series': series,
        })
    return {
        'illustrative': True,
        'note': NOTE,
        'generator': 'scripts/books/make_illustrative_market.py',
        'seed': SEED,
        'as_of': AS_OF,
        'window_days': WINDOW,
        'records': records,
    }


def dumps(data):
    return json.dumps(data, indent=1) + '\n'


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--out', type=Path, default=OUT)
    args = parser.parse_args(argv)
    args.out.write_text(dumps(build()), encoding='utf-8')
    print(f'wrote {args.out}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
