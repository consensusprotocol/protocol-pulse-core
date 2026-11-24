"""Book Terminal registry: the curated, verified list of books the site shows and tracks.

data/books/registry.json is curated config committed with the code (Amazon US IDs, ISBN-13s
and authors verified 2026-11-24). It decides which books appear on /media, which Amazon IDs
scripts/refresh_book_metrics.py fetches, and which books /api/books/metrics returns.
Its rank_nov24 values are a one-time observation: nothing here returns them.
Stdlib only, so the collector script can import it without the Flask app.
"""
import json
from functools import lru_cache
from pathlib import Path

REGISTRY_PATH = Path(__file__).resolve().parent.parent / 'data' / 'books' / 'registry.json'
DEFAULT_TAG = 'protocolpulse-20'
_REQUIRED = ('slug', 'title', 'author', 'isbn13', 'amazon_id')


@lru_cache(maxsize=4)
def _read(path):
    with open(path, encoding='utf-8') as f:
        data = json.load(f)
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
    return tuple(books)


def load_registry(path=REGISTRY_PATH):
    """The registry's books in file order. The file is read once; each call returns fresh copies."""
    return [dict(book) for book in _read(str(path))]


def by_id(amazon_id, path=REGISTRY_PATH):
    """The registry book with this Amazon ID, or None."""
    for book in load_registry(path):
        if book['amazon_id'] == amazon_id:
            return book
    return None


def amazon_url(book, tag=DEFAULT_TAG):
    """Amazon US product link for a registry book, with the affiliate tag."""
    url = f"https://www.amazon.com/dp/{book['amazon_id']}"
    return f'{url}?tag={tag}' if tag else url


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


# Media Hub card text by registry slug: (one-line description, ESSENTIAL badge).
# Descriptions carried over from the old hard-coded list where the book is unchanged.
_CARDS = {
    'the-big-print': ('An exposé revealing how the Federal Reserve and financial elites engineered wealth extraction through monetary policy.', False),
    'everything-divided-by-21-million': ('A philosophical deep dive into Bitcoin\'s relationship to time, money, freedom, and human progress through mathematical scarcity.', False),
    'daylight-robbery': ('The hidden history of how taxation has shaped human civilization from ancient empires to modern governments.', False),
    'the-genesis-book': ('The definitive history of Bitcoin\'s ideological origins — from Austrian economics to the cypherpunk movement.', False),
    'the-bitcoin-standard': ('The essential guide to understanding Bitcoin as sound money and the history of monetary systems.', True),
    'broken-money': ('A comprehensive analysis of the global monetary system and why Bitcoin matters.', True),
    'mastering-bitcoin': ('The technical guide to understanding and programming Bitcoin at a deep level. Third Edition.', True),
    'the-fiat-standard': ('A companion to The Bitcoin Standard examining our current fiat monetary system.', True),
    'the-sovereign-individual': ('A prescient 1997 book predicting the rise of digital money and the transformation of society.', True),
    'digital-gold': ('A reported history of Bitcoin\'s early years and the people who built it, by New York Times journalist Nathaniel Popper.', False),
    'layered-money': ('An accessible introduction to how money works in layers, from gold to Bitcoin.', False),
    'the-price-of-tomorrow': ('Why deflation is the key to an abundant future in a technologically advancing world.', False),
    'inventing-bitcoin': ('A concise technical and economic introduction to how Bitcoin works and why it matters.', True),
    '21-lessons': ('What falling down the Bitcoin rabbit hole taught one developer about philosophy, economics, and technology.', False),
    'thank-god-for-bitcoin': ('A faith-oriented perspective on Bitcoin as a tool for freedom and stewardship.', False),
    'the-blocksize-war': ('The inside story of the battle over Bitcoin\'s block size and the future of the protocol.', False),
    'softwar': ('Jason Lowery\'s theory of proof-of-work as power projection and its national strategic significance, from his MIT thesis.', False),
    'the-money-revolution': ('Richard Duncan on how credit creation now drives the US economy and how it could finance the next American century.', False),
}


def media_hub_lists(tag=DEFAULT_TAG, path=REGISTRY_PATH):
    """(our_books, recommended_books) for the Media Hub: registry pp_series books, then the rest.

    Entries carry title, author, description, cover_url, amazon_url, plus bestseller on
    recommended books and free_alt where the registry has one. New dicts on every call.
    """
    our_books, recommended_books = [], []
    for book in load_registry(path):
        description, essential = _CARDS.get(book['slug'], ('', False))
        entry = {
            'title': book['title'],
            'author': book['author'],
            'description': description,
            'cover_url': cover_url(book),
            'amazon_url': amazon_url(book, tag),
        }
        if book.get('free_alt'):
            entry['free_alt'] = book['free_alt']
        if book.get('pp_series'):
            our_books.append(entry)
        else:
            entry['bestseller'] = essential
            recommended_books.append(entry)
    return our_books, recommended_books
