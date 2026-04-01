#!/usr/bin/env python3
"""
refresh_book_metrics.py — Weekly BSR (Best Sellers Rank) refresh for Sovereign Book Library.
Scrapes Amazon product pages for BSR data, falls back to stored JSON on failure.

Cron: 0 6 * * 1 python3 ~/protocol_pulse/scripts/refresh_book_metrics.py
"""
import json
import os
import sys
import time
import logging
import random
from datetime import datetime, timezone
from pathlib import Path

logging.basicConfig(level=logging.INFO, format='%(asctime)s [BSR] %(message)s')
log = logging.getLogger(__name__)

DATA_DIR = Path(__file__).resolve().parent.parent / 'data'
METRICS_FILE = DATA_DIR / 'book_metrics.json'

# ASINs to track (Protocol Pulse series + rivals)
TRACKED_ASINS = {
    'B0DVTCVX8J': {'title': 'The Big Print', 'author': 'Lawrence Lepard', 'category': 'Economics',
                    'cover_url': '/static/images/books/big_print.jpg', 'published': '2025-12-15'},
    '9916697191': {'title': 'Everything Divided by 21 Million', 'author': 'Knut Svanholm', 'category': 'Bitcoin',
                    'cover_url': '/static/images/books/everything_21m.jpg', 'published': '2024-03-01'},
    '0241360846': {'title': 'Daylight Robbery', 'author': 'Dominic Frisby', 'category': 'Economics',
                    'cover_url': '/static/images/books/daylight_robbery.jpg', 'published': '2019-11-07'},
    'B07FCGQ672': {'title': 'The Bitcoin Standard', 'author': 'Saifedean Ammous', 'category': 'Bitcoin',
                    'cover_url': '/static/images/books/bitcoin_standard.jpg', 'published': '2018-03-23'},
    'B09WFDTX49': {'title': 'Broken Money', 'author': 'Lyn Alden', 'category': 'Economics',
                    'cover_url': '/static/images/books/broken_money.jpg', 'published': '2023-08-01'},
    'B0CQLMQRH7': {'title': 'The Genesis Book', 'author': 'Aaron van Wirdum', 'category': 'Bitcoin',
                    'cover_url': '/static/images/books/genesis_book.jpg', 'published': '2024-01-03'},
    '1098150090': {'title': 'Mastering Bitcoin', 'author': 'Andreas Antonopoulos & David Harding', 'category': 'Technical',
                    'cover_url': '/static/images/books/mastering_bitcoin.jpg', 'published': '2023-12-01'},
    '1544526474': {'title': 'The Fiat Standard', 'author': 'Saifedean Ammous', 'category': 'Economics',
                    'cover_url': 'https://covers.openlibrary.org/b/isbn/9781544526478-L.jpg', 'published': '2021-11-16'},
    '0684832720': {'title': 'The Sovereign Individual', 'author': 'James Dale Davidson & Lord William Rees-Mogg', 'category': 'Economics',
                    'cover_url': 'https://covers.openlibrary.org/b/isbn/9780684832722-L.jpg', 'published': '1999-08-26'},
    '006236250X': {'title': 'Digital Gold', 'author': 'Nathaniel Popper', 'category': 'Bitcoin',
                    'cover_url': 'https://covers.openlibrary.org/b/isbn/9780062362506-L.jpg', 'published': '2016-05-24'},
    '1736110519': {'title': 'Layered Money', 'author': 'Nik Bhatia', 'category': 'Economics',
                    'cover_url': 'https://covers.openlibrary.org/b/isbn/9781736110515-L.jpg', 'published': '2021-01-18'},
    '1260026671': {'title': 'Cryptoassets', 'author': 'Chris Burniske & Jack Tatar', 'category': 'Investing',
                    'cover_url': 'https://covers.openlibrary.org/b/isbn/9781260026672-L.jpg', 'published': '2017-10-03'},
    '1999257405': {'title': 'The Price of Tomorrow', 'author': 'Jeff Booth', 'category': 'Economics',
                    'cover_url': 'https://covers.openlibrary.org/b/isbn/9781999257408-L.jpg', 'published': '2020-01-14'},
    '1097476922': {'title': 'Inventing Bitcoin', 'author': 'Yan Pritzker', 'category': 'Bitcoin',
                    'cover_url': 'https://covers.openlibrary.org/b/isbn/9781097476922-L.jpg', 'published': '2019-05-01'},
    '1697526349': {'title': '21 Lessons', 'author': 'Gigi', 'category': 'Bitcoin',
                    'cover_url': 'https://covers.openlibrary.org/b/isbn/9781697526349-L.jpg', 'published': '2019-10-21'},
}

AFFILIATE_TAG = os.environ.get('AMAZON_AFFILIATE_TAG', 'protocolpulse-20')

USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 14_5) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Safari/605.1.15',
    'Mozilla/5.0 (X11; Linux x86_64; rv:128.0) Gecko/20100101 Firefox/128.0',
]


def scrape_bsr(asin: str) -> int | None:
    """Scrape BSR from Amazon product page. Returns BSR int or None on failure."""
    import re
    try:
        import requests
        from bs4 import BeautifulSoup
    except ImportError:
        log.warning("requests/bs4 not installed — skipping scrape")
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
            log.warning(f"[{asin}] HTTP {resp.status_code}")
            return None

        soup = BeautifulSoup(resp.text, 'html.parser')

        # Method 1: Product details table
        detail_bullets = soup.find('div', id='detailBulletsWrapper_feature_div')
        if detail_bullets:
            text = detail_bullets.get_text()
            match = re.search(r'Best Sellers Rank.*?#([\d,]+)', text)
            if match:
                return int(match.group(1).replace(',', ''))

        # Method 2: Product information table
        for th in soup.find_all('th'):
            if 'Best Sellers Rank' in th.get_text():
                td = th.find_next_sibling('td')
                if td:
                    match = re.search(r'#([\d,]+)', td.get_text())
                    if match:
                        return int(match.group(1).replace(',', ''))

        # Method 3: Regex on full page
        match = re.search(r'Best Sellers Rank.*?#([\d,]+)', resp.text)
        if match:
            return int(match.group(1).replace(',', ''))

        log.warning(f"[{asin}] BSR not found in page")
        return None

    except Exception as e:
        log.warning(f"[{asin}] scrape error: {e}")
        return None


def load_existing() -> dict:
    """Load existing metrics file."""
    if METRICS_FILE.exists():
        with open(METRICS_FILE) as f:
            return json.load(f)
    return {'last_updated': None, 'books': []}


def compute_velocity(bsr: int) -> int:
    """Compute a 0-100 velocity score from BSR (lower BSR = higher velocity)."""
    if bsr <= 1000:
        return 95
    elif bsr <= 5000:
        return 85
    elif bsr <= 15000:
        return 70
    elif bsr <= 30000:
        return 55
    elif bsr <= 50000:
        return 40
    else:
        return max(20, 100 - bsr // 1000)


def refresh():
    """Main refresh: scrape BSR for all tracked ASINs, update metrics file."""
    existing = load_existing()
    existing_map = {b['asin']: b for b in existing.get('books', [])}

    updated_books = []
    scrape_count = 0

    for asin, meta in TRACKED_ASINS.items():
        prev = existing_map.get(asin, {})
        prev_bsr = prev.get('bsr', 50000)

        # Scrape fresh BSR
        new_bsr = scrape_bsr(asin)
        if new_bsr is not None:
            scrape_count += 1
            bsr = new_bsr
        else:
            # Keep existing BSR if scrape failed
            bsr = prev_bsr

        bsr_change = round(((bsr - prev_bsr) / prev_bsr) * 100, 1) if prev_bsr else 0
        is_rising = bsr_change < -10  # BSR dropped >10% = rising in sales

        updated_books.append({
            'title': meta['title'],
            'author': meta['author'],
            'asin': asin,
            'cover_url': meta['cover_url'],
            'amazon_url': f'https://www.amazon.com/dp/{asin}?tag={AFFILIATE_TAG}',
            'bsr': bsr,
            'bsr_previous': prev_bsr,
            'bsr_change': bsr_change,
            'category': meta['category'],
            'is_rising': is_rising,
            'velocity': compute_velocity(bsr),
            'published': meta['published'],
        })

        # Be polite — random delay between requests
        time.sleep(random.uniform(2, 5))

    # Sort by BSR ascending (best sellers first)
    updated_books.sort(key=lambda b: b['bsr'])

    output = {
        'last_updated': datetime.now(timezone.utc).isoformat(),
        'books': updated_books,
    }

    with open(METRICS_FILE, 'w') as f:
        json.dump(output, f, indent=2)

    log.info(f"Refreshed {len(updated_books)} books ({scrape_count} scraped successfully)")


if __name__ == '__main__':
    refresh()
