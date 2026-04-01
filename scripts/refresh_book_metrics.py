#!/usr/bin/env python3
"""
refresh_book_metrics.py — Daily BSR refresh for Sovereign Book Library.
NON-DESTRUCTIVE: preserves last-known-good data on scrape failure.
ATOMIC writes via tempfile + os.replace.
CANONICAL bsr_change_pct function — single source of truth.

Cron: 17 6 * * * cd /home/ultron/protocol_pulse && python3 scripts/refresh_book_metrics.py >> logs/book_metrics.log 2>&1
"""
import json, os, sys, time, logging, random, tempfile
from datetime import datetime, timezone
from pathlib import Path

logging.basicConfig(level=logging.INFO, format='%(asctime)s [BSR] %(message)s')
log = logging.getLogger(__name__)

DATA_DIR = Path(__file__).resolve().parent.parent / 'data'
METRICS_FILE = DATA_DIR / 'book_metrics.json'
HISTORY_FILE = DATA_DIR / 'book_metrics_history.jsonl'

PP_ASINS = ['B0DVTCVX8J', '9916697191', '0241360846', 'B0CQLMQRH7']

TRACKED_ASINS = {
    'B0DVTCVX8J': {'title': 'The Big Print', 'author': 'Lawrence Lepard', 'category': 'Economics', 'cover_url': '/static/images/books/big_print.jpg', 'published': '2025-12-15'},
    '9916697191': {'title': 'Everything Divided by 21 Million', 'author': 'Knut Svanholm', 'category': 'Bitcoin', 'cover_url': '/static/images/books/everything_21m.jpg', 'published': '2024-03-01'},
    '0241360846': {'title': 'Daylight Robbery', 'author': 'Dominic Frisby', 'category': 'Economics', 'cover_url': '/static/images/books/daylight_robbery.jpg', 'published': '2019-11-07'},
    'B07FCGQ672': {'title': 'The Bitcoin Standard', 'author': 'Saifedean Ammous', 'category': 'Bitcoin', 'cover_url': '/static/images/books/bitcoin_standard.jpg', 'published': '2018-03-23'},
    'B09WFDTX49': {'title': 'Broken Money', 'author': 'Lyn Alden', 'category': 'Economics', 'cover_url': '/static/images/books/broken_money.jpg', 'published': '2023-08-01'},
    'B0CQLMQRH7': {'title': 'The Genesis Book', 'author': 'Aaron van Wirdum', 'category': 'Bitcoin', 'cover_url': '/static/images/books/genesis_book.jpg', 'published': '2024-01-03'},
    '1098150090': {'title': 'Mastering Bitcoin', 'author': 'Andreas Antonopoulos & David Harding', 'category': 'Technical', 'cover_url': '/static/images/books/mastering_bitcoin.jpg', 'published': '2023-12-01'},
    '1544526474': {'title': 'The Fiat Standard', 'author': 'Saifedean Ammous', 'category': 'Economics', 'cover_url': 'https://covers.openlibrary.org/b/isbn/9781544526478-L.jpg', 'published': '2021-11-16'},
    '0684832720': {'title': 'The Sovereign Individual', 'author': 'James Dale Davidson', 'category': 'Economics', 'cover_url': 'https://covers.openlibrary.org/b/isbn/9780684832722-L.jpg', 'published': '1999-08-26'},
    '006236250X': {'title': 'Digital Gold', 'author': 'Nathaniel Popper', 'category': 'Bitcoin', 'cover_url': 'https://covers.openlibrary.org/b/isbn/9780062362506-L.jpg', 'published': '2016-05-24'},
    '1736110519': {'title': 'Layered Money', 'author': 'Nik Bhatia', 'category': 'Economics', 'cover_url': 'https://covers.openlibrary.org/b/isbn/9781736110515-L.jpg', 'published': '2021-01-18'},
    '1260026671': {'title': 'Cryptoassets', 'author': 'Chris Burniske & Jack Tatar', 'category': 'Investing', 'cover_url': 'https://covers.openlibrary.org/b/isbn/9781260026672-L.jpg', 'published': '2017-10-03'},
    '1999257405': {'title': 'The Price of Tomorrow', 'author': 'Jeff Booth', 'category': 'Economics', 'cover_url': 'https://covers.openlibrary.org/b/isbn/9781999257408-L.jpg', 'published': '2020-01-14'},
    '1097476922': {'title': 'Inventing Bitcoin', 'author': 'Yan Pritzker', 'category': 'Bitcoin', 'cover_url': 'https://covers.openlibrary.org/b/isbn/9781097476922-L.jpg', 'published': '2019-05-01'},
    '1697526349': {'title': '21 Lessons', 'author': 'Gigi', 'category': 'Bitcoin', 'cover_url': 'https://covers.openlibrary.org/b/isbn/9781697526349-L.jpg', 'published': '2019-10-21'},
}

AFFILIATE_TAG = os.environ.get('AMAZON_AFFILIATE_TAG', 'protocolpulse-20')

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


def compute_velocity(bsr: int) -> int:
    """0-100 velocity score from BSR. Lower BSR = higher velocity."""
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


def scrape_bsr(asin: str):
    """Scrape BSR from Amazon. Returns int or None on any failure."""
    import re
    try:
        import requests
        from bs4 import BeautifulSoup
    except ImportError:
        log.warning('requests/bs4 not installed')
        return None

    url = f'https://www.amazon.com/dp/{asin}'
    headers = {
        'User-Agent': random.choice(USER_AGENTS),
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate',
    }
    try:
        resp = requests.get(url, headers=headers, timeout=15)
        if resp.status_code != 200:
            log.warning(f'[{asin}] HTTP {resp.status_code}')
            return None
        soup = BeautifulSoup(resp.text, 'html.parser')
        # Method 1: detail bullets
        detail = soup.find('div', id='detailBulletsWrapper_feature_div')
        if detail:
            m = re.search(r'Best Sellers Rank.*?#([\d,]+)', detail.get_text())
            if m: return int(m.group(1).replace(',', ''))
        # Method 2: product table
        for th in soup.find_all('th'):
            if 'Best Sellers Rank' in th.get_text():
                td = th.find_next_sibling('td')
                if td:
                    m = re.search(r'#([\d,]+)', td.get_text())
                    if m: return int(m.group(1).replace(',', ''))
        # Method 3: regex on full page
        m = re.search(r'Best Sellers Rank.*?#([\d,]+)', resp.text)
        if m: return int(m.group(1).replace(',', ''))
        log.warning(f'[{asin}] BSR not found in page')
        return None
    except Exception as e:
        log.warning(f'[{asin}] scrape error: {e}')
        return None


def load_existing():
    if METRICS_FILE.exists():
        try:
            with open(METRICS_FILE) as f:
                return json.load(f)
        except Exception:
            pass
    return {'last_updated': None, 'books': []}


def refresh():
    existing = load_existing()
    existing_map = {b['asin']: b for b in existing.get('books', [])}
    now_iso = datetime.now(timezone.utc).isoformat()

    updated_books = []
    success_count = 0
    fail_count = 0

    for asin, meta in TRACKED_ASINS.items():
        prev = existing_map.get(asin, {})
        prev_bsr = prev.get('bsr') or prev.get('bsr_current') or 50000
        last_good = prev.get('last_successful_fetch')

        new_bsr = scrape_bsr(asin)
        time.sleep(random.uniform(3, 7))

        if new_bsr is not None and new_bsr > 0:
            # SUCCESS — use new data
            bsr = new_bsr
            fetch_status = 'ok'
            fetch_error = None
            last_good = now_iso
            success_count += 1
        else:
            # FAILURE — preserve existing BSR, never zero out
            bsr = prev_bsr
            fetch_status = 'error'
            fetch_error = 'scrape_failed'
            fail_count += 1
            log.warning(f'[{asin}] keeping prev BSR={prev_bsr}')

        # Canonical change calculation
        chg = compute_bsr_change_pct(prev_bsr, bsr)

        # Initial breakout detection (was unranked, now has rank)
        was_unranked = (prev_bsr == 50000 and not prev.get('last_successful_fetch'))
        is_rising = (chg is not None and chg <= -10.0) or (was_unranked and new_bsr is not None)
        is_breakout = was_unranked and new_bsr is not None

        # Append to history JSONL
        try:
            with open(HISTORY_FILE, 'a') as hf:
                hf.write(json.dumps({'asin': asin, 'bsr': bsr, 'ts': now_iso}) + '\n')
        except Exception:
            pass

        updated_books.append({
            'title': meta['title'],
            'author': meta['author'],
            'asin': asin,
            'cover_url': meta['cover_url'],
            'amazon_url': f'https://www.amazon.com/dp/{asin}?tag={AFFILIATE_TAG}',
            'bsr': bsr,
            'bsr_previous': prev_bsr,
            'bsr_change': chg if chg is not None else 0.0,
            'category': meta['category'],
            'is_rising': is_rising,
            'is_breakout': is_breakout,
            'velocity': compute_velocity(bsr),
            'published': meta['published'],
            'fetch_status': fetch_status,
            'fetch_error': fetch_error,
            'last_successful_fetch': last_good,
        })

    # Stale-data guard: only write if >50% succeeded OR first run
    first_run = not any(b.get('last_successful_fetch') for b in existing.get('books', []))
    if success_count > len(TRACKED_ASINS) * 0.5 or first_run:
        updated_books.sort(key=lambda b: b['bsr'])
        atomic_write_json(METRICS_FILE, {
            'last_updated': now_iso,
            'fetch_health': {'success': success_count, 'failed': fail_count, 'total': len(TRACKED_ASINS)},
            'books': updated_books,
        })
        log.info(f'Written: {success_count} ok, {fail_count} preserved')
    else:
        log.error(f'STALE-DATA GUARD: only {success_count}/{len(TRACKED_ASINS)} succeeded — not overwriting')


if __name__ == '__main__':
    refresh()
