"""Book Terminal pages: /books (The Sovereign Library) and /books/market (Book Market).

Both are prototypes on the book-terminal branch: every response from this blueprint sends
X-Robots-Tag: noindex, and both templates carry <meta name="robots" content="noindex">.

/books renders data/books/registry.json only: titles, authors, descriptions, covers,
purchase and free links. No rank numbers and no sales wording. Search (?q=) and category
(?cat=) filter on the server too, so the page works without JavaScript; static/js/books.js
applies the same rules in the browser (fold() below is the shared normalisation).

Registered with one line in core/routes.py.
"""
import os
import unicodedata

from flask import Blueprint, render_template, request

import books_registry

books_bp = Blueprint('books', __name__)
ASSET_VERSION = '20261124r2'


def _tag():
    return os.environ.get('AMAZON_AFFILIATE_TAG', books_registry.DEFAULT_TAG)


def fold(text):
    """Lowercase without accents: 'Wírdum' -> 'wirdum'. books.js does the same with NFD."""
    return ''.join(c for c in unicodedata.normalize('NFD', text or '').lower()
                   if unicodedata.category(c) != 'Mn')


def search_text(entry):
    """What the search box matches: title, subtitle, author, description, categories."""
    return fold(' '.join([entry['title'], entry.get('subtitle') or '', entry['author'],
                          entry['description'], ' '.join(entry['categories'])]))


def matches(entry, q, cat):
    """Every word of q appears in the book's search text, and the book is in cat (if any)."""
    haystack = search_text(entry)
    return (not cat or cat in entry['categories']) and all(term in haystack for term in fold(q).split())


@books_bp.after_request
def _noindex(response):
    response.headers['X-Robots-Tag'] = 'noindex'
    return response


@books_bp.route('/books')
def library():
    lib = books_registry.library(_tag())
    q = (request.args.get('q') or '').strip()[:100]
    # The form sends the current category as a hidden field and a chip's value after it:
    # the last value wins. Unknown categories mean "all".
    cats = request.args.getlist('cat')
    cat = cats[-1] if cats and cats[-1] in lib['categories'] else ''
    view = 'list' if request.args.get('view') == 'list' else 'grid'
    shown = 0
    for entry in lib['series'] + lib['essential']:
        entry['search'] = search_text(entry)
        entry['match'] = matches(entry, q, cat)
        shown += entry['match']
    return render_template('books/library.html', lib=lib, q=q, cat=cat, view=view, shown=shown,
                           asset_version=ASSET_VERSION)
