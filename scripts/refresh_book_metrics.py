#!/usr/bin/env python3
"""
refresh_book_metrics.py — Daily Amazon US Best Sellers Rank refresh for the Book Terminal.
TRACKED: exactly the books in data/books/registry.json (core/books_registry.py), by Amazon ID.
NON-DESTRUCTIVE: the metrics file keeps each book's last good rank, flagged by fetch_status.
HISTORY: one line per book per run; a failed fetch is written as bsr null, never a carried value.
ATOMIC writes via tempfile + os.replace.
CANONICAL bsr_change_pct function — single source of truth.

Cron: 17 6 * * * cd /home/ultron/protocol_pulse && python3 scripts/refresh_book_metrics.py >> logs/book_metrics.log 2>&1
"""
import html as html_lib
import json, os, sys, time, logging, random, re, tempfile
from datetime import datetime, timezone
from pathlib import Path

logging.basicConfig(level=logging.INFO, format='%(asctime)s [BSR] %(message)s')
log = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / 'data'
METRICS_FILE = DATA_DIR / 'book_metrics.json'
HISTORY_FILE = DATA_DIR / 'book_metrics_history.jsonl'
MARKETPLACE = 'US'

sys.path.append(str(ROOT / 'core'))
import books_registry  # noqa: E402  (stdlib-only module in core/)

# Amazon ID -> registry book. The registry is the only list of tracked books.
TRACKED_ASINS = {b['amazon_id']: b for b in books_registry.load_registry()}

USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 14_5) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Safari/605.1.15',
    'Mozilla/5.0 (X11; Linux x86_64; rv:128.0) Gecko/20100101 Firefox/128.0',
]


def compute_bsr_change_pct(previous: int, current: int):
    """CANONICAL BSR change calculation — single source of truth.
    Negative = rank improved (book selling better).
    Positive = rank declined (book selling worse).
    """
    if not previous or previous <= 0 or not current or current <= 0:
        return None
    return round(((current - previous) / previous) * 100.0, 2)


def compute_rank_score(bsr: int) -> int:
    """0-100 score derived only from the Best Sellers Rank: lower rank = higher score.
    A step function of rank (formerly 'velocity'): not a sales count or a sales rate."""
    if bsr <= 1000: return 95
    elif bsr <= 5000: return 85
    elif bsr <= 15000: return 72
    elif bsr <= 30000: return 58
    elif bsr <= 50000: return 42
    else: return max(20, 100 - bsr // 1200)


def atomic_write_json(path: Path, payload: dict):
    """Write JSON atomically via temp file + os.replace. Never partial writes."""
    dir_name = path.parent
    fd, tmp_path = tempfile.mkstemp(dir=str(dir_name), suffix='.tmp')
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            json.dump(payload, f, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, str(path))
        log.info(f'Atomic write OK: {path}')
    except Exception as e:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
        raise e


def fetch_page(asin: str):
    """GET the Amazon US product page for an ID. Returns (http_status, html); raises on network errors."""
    import requests
    url = f'https://www.amazon.com/dp/{asin}'
    headers = {
        'User-Agent': random.choice(USER_AGENTS),
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate',
    }
    resp = requests.get(url, headers=headers, timeout=15)
    return resp.status_code, resp.text


_RANK = re.compile(r'#\s?([\d,]+)')
# What follows the first rank number: '#51,009 in Books (See Top 100...' / '#1,234 Paid in Kindle Store'
_RANK_LIST = re.compile(r'\s+(?:(Paid|Free)\s+)?in\s+([^()#<>]+?)\s*(?:\(|#|<|$)')


def _first_rank(text: str):
    """(rank, category) of the first '#N in Category' after 'Best Sellers Rank' in text."""
    text = ' '.join(html_lib.unescape(text).split())
    start = text.find('Best Sellers Rank')
    if start < 0:
        return None, None
    m = _RANK.search(text, start)
    if not m:
        return None, None
    rank = int(m.group(1).replace(',', ''))
    listed = _RANK_LIST.match(text, m.end())
    if not listed:
        return rank, None
    category = listed.group(2).strip()[:80]
    if listed.group(1):
        category = f'{category} ({listed.group(1)})'
    return rank, category or None


def parse_rank(page_html: str):
    """(rank, category) for the first Best Sellers Rank on an Amazon product page, else (None, None).
    category is the list the rank is in, as the page writes it: 'Books', 'Kindle Store'."""
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(page_html, 'html.parser')
    # Method 1: detail bullets
    detail = soup.find('div', id='detailBulletsWrapper_feature_div')
    if detail:
        rank, category = _first_rank(detail.get_text(' '))
        if rank:
            return rank, category
    # Method 2: product details table
    for th in soup.find_all('th'):
        if 'Best Sellers Rank' in th.get_text():
            td = th.find_next_sibling('td')
            if td:
                rank, category = _first_rank('Best Sellers Rank ' + td.get_text(' '))
                if rank:
                    return rank, category
    # Method 3: the raw page line that carries the label, tags stripped
    m = re.search(r'Best Sellers Rank[^\n]*', page_html)
    if m:
        return _first_rank(re.sub(r'<[^>]+>', ' ', m.group(0)))
    return None, None


def scrape_bsr(asin: str, fetch=fetch_page):
    """Fetch and parse one product page. Returns (rank, category, error); error is None on success."""
    try:
        status, page = fetch(asin)
    except ImportError:
        return None, None, 'requests not installed'
    except Exception as e:
        return None, None, f'scrape error: {type(e).__name__}: {e}'[:200]
    if status != 200:
        return None, None, f'HTTP {status}'
    try:
        rank, category = parse_rank(page)
    except ImportError:
        return None, None, 'bs4 not installed'
    except Exception as e:
        return None, None, f'parse error: {type(e).__name__}: {e}'[:200]
    if not rank:
        return None, None, 'BSR not found in page'
    return rank, category, None


def history_line(asin: str, rank, category, error, ts: str) -> dict:
    """One history record. A failed fetch is bsr None: never the carried value."""
    ok = error is None
    return {
        'asin': asin,
        'bsr': rank if ok else None,
        'ts': ts,
        'status': 'ok' if ok else 'error',
        'error': error,
        'category': category if ok else None,
        'marketplace': MARKETPLACE,
    }


def append_history(line: dict) -> bool:
    """Append one line to the history file. A failed write is logged, never swallowed."""
    try:
        with open(HISTORY_FILE, 'a', encoding='utf-8') as hf:
            hf.write(json.dumps(line) + '\n')
        return True
    except OSError as e:
        log.error(f"[{line['asin']}] history write failed ({HISTORY_FILE}): {e}")
        return False


def load_existing():
    if METRICS_FILE.exists():
        try:
            with open(METRICS_FILE) as f:
                return json.load(f)
        except Exception as e:
            log.error(f'cannot read {METRICS_FILE} ({e}); starting without previous values')
    return {'last_updated': None, 'books': []}


def _pause():
    time.sleep(random.uniform(3, 7))


def refresh(fetch=fetch_page, pause=_pause):
    existing = load_existing()
    existing_map = {b.get('asin'): b for b in existing.get('books', [])}
    now_iso = datetime.now(timezone.utc).isoformat()

    updated_books = []
    success_count = 0
    fail_count = 0
    history_errors = 0

    for asin, book in TRACKED_ASINS.items():
        prev = existing_map.get(asin, {})
        prev_rank = prev.get('bsr')
        # A last good value exists only if a fetch once succeeded; seeded or carried numbers do not count.
        had_good = bool(prev.get('last_successful_fetch')) and isinstance(prev_rank, int) and prev_rank > 0
        last_good_bsr = prev_rank if had_good else None

        rank, category, error = scrape_bsr(asin, fetch)
        pause()

        if error is None:
            # SUCCESS — new rank; change measured against the last good rank only
            chg = compute_bsr_change_pct(last_good_bsr, rank)
            row = {
                'bsr': rank,
                'bsr_previous': last_good_bsr,
                'bsr_change': chg,
                'rank_category': category,
                'is_rising': chg is not None and chg <= -10.0,
                'fetch_status': 'ok',
                'fetch_error': None,
                'last_successful_fetch': now_iso,
            }
            success_count += 1
        else:
            # FAILURE — keep the last good snapshot as it was; never invent a rank
            log.warning(f'[{asin}] {error}')
            if had_good:
                log.warning(f'[{asin}] keeping prev BSR={last_good_bsr}')
            row = {
                'bsr': last_good_bsr,
                'bsr_previous': prev.get('bsr_previous') if had_good else None,
                'bsr_change': prev.get('bsr_change') if had_good else None,
                'rank_category': prev.get('rank_category') if had_good else None,
                'is_rising': bool(prev.get('is_rising')) if had_good else False,
                'fetch_status': 'error',
                'fetch_error': error,
                'last_successful_fetch': prev.get('last_successful_fetch') if had_good else None,
            }
            fail_count += 1

        if not append_history(history_line(asin, rank, category, error, now_iso)):
            history_errors += 1

        updated_books.append({
            'asin': asin,
            'title': book['title'],
            'author': book['author'],
            **row,
            'rank_score': compute_rank_score(row['bsr']) if row['bsr'] else None,
            # A page without a rank counts as a failed fetch, so "was unranked, now ranked"
            # cannot be observed: never claim a breakout (the old 50000 default made every
            # newly tracked ID look like one).
            'is_breakout': False,
        })

    # Stale-data guard: only write if >50% succeeded OR first run
    written = False
    first_run = not any(b.get('last_successful_fetch') for b in existing.get('books', []))
    if success_count > len(TRACKED_ASINS) * 0.5 or first_run:
        updated_books.sort(key=lambda b: (b['bsr'] is None, b['bsr'] or 0))
        atomic_write_json(METRICS_FILE, {
            'last_updated': now_iso,
            'marketplace': MARKETPLACE,
            'fetch_health': {'success': success_count, 'failed': fail_count, 'total': len(TRACKED_ASINS)},
            'books': updated_books,
        })
        written = True
        log.info(f'Written: {success_count} ok, {fail_count} failed (last good rank kept)')
    else:
        log.error(f'STALE-DATA GUARD: only {success_count}/{len(TRACKED_ASINS)} succeeded — not overwriting')
    if history_errors:
        log.error(f'{history_errors} history line(s) not written to {HISTORY_FILE}')
    return {'success': success_count, 'failed': fail_count, 'history_errors': history_errors, 'written': written}


if __name__ == '__main__':
    refresh()
