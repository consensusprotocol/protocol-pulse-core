"""Book Terminal registry: the curated, verified list of books the site shows and tracks.

data/books/registry.json is curated config committed with the code (Amazon US IDs, ISBN-13s
and authors verified 2026-11-24). It decides which books appear on /media and /books, which
Amazon IDs scripts/refresh_book_metrics.py fetches, and which books /api/books/metrics returns.
Its rank_nov24 values are a one-time observation: nothing here returns them.

Curated fields (version 3): categories (from the top-level list), description (one factual
line), subtitle, pathways (membership: pathway id, step, note), related_media (Protocol Pulse
series links already used on the site), free_resources (official free editions), pub_year and
pub_year_source (its parenthetical is the date the source gives: a full date or only the year;
pub_date() reads it), format ('Kindle' for a Kindle-only edition). _read() refuses a registry whose
fields break these rules, so a bad edit fails loudly instead of rendering half a page.
Stdlib only, so the collector script can import it without the Flask app.
"""
import json
import re
from datetime import datetime
from functools import lru_cache
from pathlib import Path

REGISTRY_PATH = Path(__file__).resolve().parent.parent / 'data' / 'books' / 'registry.json'
DEFAULT_TAG = 'protocolpulse-20'
_REQUIRED = ('slug', 'title', 'author', 'isbn13', 'amazon_id', 'description', 'categories')


def _https(url):
    return isinstance(url, str) and url.startswith('https://')


def _check_links(where, links, fields):
    if not isinstance(links, list) or not links:
        raise ValueError(f'{where}: must be a non-empty list')
    for link in links:
        if not isinstance(link, dict) or not all(isinstance(link.get(f), str) and link[f] for f in fields):
            raise ValueError(f'{where}: every entry needs {fields}')
        if not _https(link['url']):
            raise ValueError(f'{where}: {link["url"]!r} is not an https URL')


def _validate(path, data):
    books = data.get('books') if isinstance(data, dict) else None
    if not books:
        raise ValueError(f'{path}: no books')
    for book in books:
        missing = [k for k in _REQUIRED if not book.get(k)]
        if missing:
            raise ValueError(f'{path}: {book.get("slug") or book.get("title")!r} lacks {missing}')
    for key in ('slug', 'amazon_id', 'isbn13'):
        values = [book[key] for book in books]
        dupes = sorted({v for v in values if values.count(v) > 1})
        if dupes:
            raise ValueError(f'{path}: duplicate {key} {dupes}')

    categories = data.get('categories')
    if not isinstance(categories, list) or not categories or len(set(categories)) != len(categories):
        raise ValueError(f'{path}: categories must be a list of unique names')
    pathway_ids = [p.get('id') for p in data.get('pathways', [])]
    if any(not p.get('id') or not p.get('title') or not p.get('summary') for p in data.get('pathways', [])) \
            or len(set(pathway_ids)) != len(pathway_ids):
        raise ValueError(f'{path}: every pathway needs a unique id, a title and a summary')

    steps = {pid: [] for pid in pathway_ids}
    for book in books:
        where = f'{path}: {book["slug"]}'
        cats = book['categories']
        if not isinstance(cats, list) or len(set(cats)) != len(cats) or not set(cats) <= set(categories):
            raise ValueError(f'{where}: categories {cats!r} not a unique subset of {categories}')
        for member in book.get('pathways', []):
            if member.get('id') not in steps or not isinstance(member.get('step'), int) or not member.get('note'):
                raise ValueError(f'{where}: pathway entry {member!r} needs a known id, an int step and a note')
            steps[member['id']].append(member['step'])
        if 'related_media' in book:
            _check_links(f'{where} related_media', book['related_media'], ('kind', 'label', 'url'))
        if 'free_resources' in book:
            _check_links(f'{where} free_resources', book['free_resources'], ('label', 'url'))
        if 'publisher_link' in book and not _https(book['publisher_link']):
            raise ValueError(f'{where}: publisher_link is not an https URL')
        year = book.get('pub_year')
        if year is not None and (not isinstance(year, int) or not 1900 <= year <= 2100 or not book.get('pub_year_source')):
            raise ValueError(f'{where}: pub_year must be a year with a pub_year_source')
        exact = pub_date(book)
        if exact and exact.year != year:
            raise ValueError(f'{where}: pub_year_source gives {exact.isoformat()}, not a date in pub_year {year}')
    for pid, numbers in steps.items():
        if sorted(numbers) != list(range(1, len(numbers) + 1)) or len(numbers) < 2:
            raise ValueError(f'{path}: pathway {pid!r} steps {sorted(numbers)} are not 1..n (n >= 2)')

    featured = data.get('featured')
    if featured is not None and not any(b['slug'] == featured and b.get('pp_series') for b in books):
        raise ValueError(f'{path}: featured {featured!r} is not a Protocol Pulse series book')


@lru_cache(maxsize=4)
def _read(path):
    with open(path, encoding='utf-8') as f:
        data = json.load(f)
    _validate(path, data)
    return json.dumps(data)  # cached as text: every caller gets fresh objects


def _doc(path=REGISTRY_PATH):
    return json.loads(_read(str(path)))


def load_registry(path=REGISTRY_PATH):
    """The registry's books in file order. The file is read once; each call returns fresh copies."""
    return _doc(path)['books']


def by_id(amazon_id, path=REGISTRY_PATH):
    """The registry book with this Amazon ID, or None."""
    for book in load_registry(path):
        if book['amazon_id'] == amazon_id:
            return book
    return None


_SOURCE_DATE = re.compile(r'\(([^()]*)\)')
_DATE_FORMATS = ('%Y-%m-%d', '%B %d, %Y', '%b %d, %Y')


def pub_date(book):
    """The exact publication date of the tracked edition, when its pub_year_source records one, else None.

    'Amazon US product page (February 3, 2025), checked ...' -> date(2025, 2, 3);
    'Open Library edition record (2020), checked ...' -> None (the source gives only the year).
    """
    m = _SOURCE_DATE.search(book.get('pub_year_source') or '')
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(m.group(1).strip(), fmt).date() if m else None
        except ValueError:
            continue
    return None


def pub_date_label(book):
    """'Feb 3, 2025' when the exact date is recorded; '2020 (exact date not recorded)' otherwise."""
    exact = pub_date(book)
    if exact:
        return f'{exact:%b} {exact.day}, {exact.year}'
    return f"{book['pub_year']} (exact date not recorded)" if book.get('pub_year') else 'Not recorded'


def amazon_url(book, tag=DEFAULT_TAG):
    """Amazon US product link for a registry book, with the affiliate tag."""
    url = f"https://www.amazon.com/dp/{book['amazon_id']}"
    return f'{url}?tag={tag}' if tag else url


def purchase_label(book):
    """Text of the Amazon button: the tracked edition's format, never just an icon."""
    return 'Kindle on Amazon' if book.get('format') == 'Kindle' else 'Buy on Amazon'


def free_alt(book):
    """URL of the book's first official free edition, or None."""
    resources = book.get('free_resources') or []
    return resources[0]['url'] if resources else None


def series_link(book):
    """(url, label) of the book's Protocol Pulse series, or (None, None)."""
    for media in book.get('related_media') or []:
        if media['kind'] == 'series':
            return media['url'], media['label']
    return None, None


# Covers the site serves itself (static/images/books/).
_LOCAL_COVERS = {
    'the-big-print': 'big_print.jpg',
    'everything-divided-by-21-million': 'everything_21m.jpg',
    'daylight-robbery': 'daylight_robbery.jpg',
    'the-genesis-book': 'genesis_book.jpg',
    'the-bitcoin-standard': 'bitcoin_standard.jpg',
    'broken-money': 'broken_money.jpg',
    'mastering-bitcoin': 'mastering_bitcoin.jpg',
}
# Open Library had no cover for these ISBN-13s on 2026-11-24 (?default=false answered 404):
# use Amazon's image for the registry ID, as the API already did for Digital Gold.
_AMAZON_COVERS = {'digital-gold', 'softwar', 'the-money-revolution'}


def cover_url(book):
    """Cover image URL for a registry book: local file, Amazon image, or Open Library by ISBN-13.

    default=false makes Open Library answer 404 instead of a blank image when it has no cover,
    so the page's <img onerror> fallback can take over.
    """
    local = _LOCAL_COVERS.get(book['slug'])
    if local:
        return f'/static/images/books/{local}'
    if book['slug'] in _AMAZON_COVERS:
        return f"https://m.media-amazon.com/images/P/{book['amazon_id']}.01.L.jpg"
    return f"https://covers.openlibrary.org/b/isbn/{book['isbn13']}-L.jpg?default=false"


# Media Hub server list: books that carry the ESSENTIAL mark there. An editorial pick, not a
# sales claim (this flag was called 'bestseller' before round 2; templates/media_hub.html
# never renders it).
_ESSENTIAL = frozenset({'the-bitcoin-standard', 'broken-money', 'mastering-bitcoin', 'the-fiat-standard',
                        'the-sovereign-individual', 'inventing-bitcoin'})


def media_hub_lists(tag=DEFAULT_TAG, path=REGISTRY_PATH):
    """(our_books, recommended_books) for the Media Hub: registry pp_series books, then the rest.

    Entries carry title, author, description, cover_url, amazon_url, plus essential on
    recommended books and free_alt where the registry has a free edition. New dicts on every call.
    """
    our_books, recommended_books = [], []
    for book in load_registry(path):
        entry = {
            'title': book['title'],
            'author': book['author'],
            'description': book['description'],
            'cover_url': cover_url(book),
            'amazon_url': amazon_url(book, tag),
        }
        if free_alt(book):
            entry['free_alt'] = free_alt(book)
        if book.get('pp_series'):
            our_books.append(entry)
        else:
            entry['essential'] = book['slug'] in _ESSENTIAL
            recommended_books.append(entry)
    return our_books, recommended_books


def library_entry(book, tag=DEFAULT_TAG):
    """One /books card: registry text and links only. No rank, no sales wording."""
    series_url, series_label = series_link(book)
    return {
        'slug': book['slug'],
        'title': book['title'],
        'subtitle': book.get('subtitle'),
        'author': book['author'],
        'description': book['description'],
        'categories': list(book['categories']),
        'pub_year': book.get('pub_year'),
        'cover_url': cover_url(book),
        'amazon_url': amazon_url(book, tag),
        'purchase_label': purchase_label(book),
        'format_note': 'Kindle edition' if book.get('format') == 'Kindle' else None,
        'free_resources': list(book.get('free_resources') or []),
        'series_url': series_url,
        'series_label': series_label,
        'pp_series': bool(book.get('pp_series')),
    }


def library(tag=DEFAULT_TAG, path=REGISTRY_PATH):
    """Everything /books renders, from the registry alone.

    {'categories', 'featured', 'series', 'essential', 'pathways', 'count'}: series = the
    Protocol Pulse series books, essential = the rest, both in registry order; pathways in
    registry order, each with its books sorted by step.
    """
    doc = _doc(path)
    entries = [library_entry(book, tag) for book in doc['books']]
    by_slug = {e['slug']: e for e in entries}
    pathways = []
    for p in doc.get('pathways', []):
        steps = sorted(((m['step'], m['note'], book['slug']) for book in doc['books']
                        for m in book.get('pathways', []) if m['id'] == p['id']))
        pathways.append({'id': p['id'], 'title': p['title'], 'summary': p['summary'],
                         'steps': [{'step': n, 'note': note, 'book': by_slug[slug]} for n, note, slug in steps]})
    return {
        'categories': list(doc['categories']),
        'featured': by_slug.get(doc.get('featured')),
        'series': [e for e in entries if e['pp_series']],
        'essential': [e for e in entries if not e['pp_series']],
        'pathways': pathways,
        'count': len(entries),
    }
