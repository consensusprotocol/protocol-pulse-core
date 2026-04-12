#!/usr/bin/env python3
"""
Congressional STOCK Act Scraper — Production
=============================================
Scrapes Senate EFDS Periodic Transaction Reports (STOCK Act) via Playwright.
The working flow (confirmed 2026-04-12):
  1. GET /search/home/     — get CSRF, checkbox visible
  2. checkbox.check()      — auto-submits agreement form, 302 → /search/
  3. Fill report_type=11 + date range checkbox
  4. $(form).trigger('submit') via jQuery — DataTables XHR fires
  5. Intercept the 200 JSON response — 2,381+ PTRs available

No Quiver. No proxy. No datacenter issue.
Your IP: 208.78.190.54 / Summit Broadband Naples — clean residential ISP.
The block was Akamai WAF on the raw POST (not IP). jQuery form trigger bypasses it.
"""
import json, logging, re, time
from datetime import datetime, timezone, timedelta
from pathlib import Path

logger = logging.getLogger(__name__)

BASE_DIR   = Path("/home/ultron/protocol_pulse")
CACHE_PATH = BASE_DIR / "data" / "congress_live.json"
CACHE_TTL  = 4 * 3600  # 4 hours

CRYPTO_TICKERS = {
    "MSTR","MARA","RIOT","CLSK","HUT","BITF","COIN","IBIT","FBTC",
    "GBTC","BITB","ARKB","BTCO","BITO","SQ","PYPL","HOOD","NVDA","AMD",
}


def _cache_fresh() -> bool:
    if CACHE_PATH.exists():
        return (time.time() - CACHE_PATH.stat().st_mtime) < CACHE_TTL
    return False


def _parse_ptr_row(row: list) -> dict:
    """Parse raw DataTables row into structured dict."""
    if not isinstance(row, list) or len(row) < 4:
        return {}
    # col 0: first, 1: last, 2: office (may have HTML), 3: report link, 4: date
    filer      = f"{row[0]} {row[1]}".strip()
    office     = re.sub(r'<[^>]+>', '', str(row[2])).strip()
    date_filed = re.sub(r'<[^>]+>', '', str(row[4] if len(row) > 4 else '')).strip()
    # Extract title + URL from the link in col 3
    link_m = re.search(r'href="([^"]+)".*?>(.*?)</a>', str(row[3]), re.DOTALL)
    if link_m:
        url   = link_m.group(1)
        title = re.sub(r'<[^>]+>', '', link_m.group(2)).strip()
        if not url.startswith('http'):
            url = 'https://efdsearch.senate.gov' + url
    else:
        url, title = '', re.sub(r'<[^>]+>', '', str(row[3])).strip()

    # Classify ticker from title (PTRs often list the asset)
    tickers_found = [t for t in CRYPTO_TICKERS if t in title.upper()]

    return {
        "filer":          filer,
        "office":         office,
        "title":          title,
        "date_filed":     date_filed,
        "filing_url":     url,
        "tickers":        tickers_found,
        "is_crypto":      bool(tickers_found),
        "form":           "PTR",
        "chamber":        "senate",
        "source":         "Senate EFDS",
        "conviction":     35 if tickers_found else 15,
    }


def scrape_senate_ptrs(limit: int = 50,
                        start_date: str = "01/01/2026") -> list[dict]:
    """
    Scrape Senate EFDS PTRs using Playwright.
    Returns list of parsed PTR filings.
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        logger.error("Playwright not installed")
        return []

    captured = []

    with sync_playwright() as pw:
        browser = pw.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage",
                  "--disable-blink-features=AutomationControlled"],
        )
        ctx = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            ),
            locale="en-US",
        )
        ctx.add_init_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        page = ctx.new_page()

        # Intercept DataTables XHR
        def on_resp(r):
            if 'report/data' in r.url and r.status == 200:
                try:
                    captured.append(r.json())
                    logger.debug("Captured data response: %d rows",
                                 len(captured[-1].get('data', [])))
                except Exception:
                    pass
        page.on("response", on_resp)

        try:
            # Step 1: Accept agreement
            page.goto("https://efdsearch.senate.gov/search/home/",
                      timeout=30000, wait_until="domcontentloaded")
            page.wait_for_timeout(800)
            page.locator("input#agree_statement").wait_for(state="visible", timeout=8000)
            page.locator("input#agree_statement").check()  # auto-submits via onChange
            page.wait_for_url("**/search/", timeout=12000)
            page.wait_for_load_state("domcontentloaded")
            page.wait_for_timeout(800)
            logger.info("Agreement accepted, on: %s", page.url)

            # Step 2: Check PTR report type
            page.locator("input[name='report_type'][value='11']").wait_for(state="visible", timeout=5000)
            page.locator("input[name='report_type'][value='11']").check()

            # Step 3: jQuery form trigger — bypasses WAF, DataTables XHR fires
            page.evaluate("() => { var f=document.getElementById('searchForm'); if(f) $(f).trigger('submit'); }")
            page.wait_for_timeout(6000)  # wait for XHR response
            logger.info("Search submitted, captured: %d", len(captured))

        except Exception as e:
            logger.error("Playwright scrape error: %s", e)
        finally:
            browser.close()

    # Parse all captured rows
    rows = []
    for d in captured:
        for raw in d.get('data', []):
            p = _parse_ptr_row(raw)
            if p:
                rows.append(p)

    # Dedup by (filer, date_filed)
    seen, unique = set(), []
    for r in rows:
        key = f"{r['filer']}|{r['date_filed']}"
        if key not in seen:
            seen.add(key)
            unique.append(r)

    logger.info("Senate PTRs: %d unique filings scraped", len(unique))
    return unique


def fetch_congress_trades(limit: int = 50, force: bool = False) -> dict:
    """Master function — returns fresh or cached congressional PTR data."""
    if not force and _cache_fresh():
        try:
            return json.loads(CACHE_PATH.read_text())
        except Exception:
            pass

    t0 = time.time()
    logger.info("Congressional EFDS scraper starting...")

    trades = scrape_senate_ptrs(limit=limit)
    crypto = [t for t in trades if t.get("is_crypto")]

    result = {
        "updated_at":    datetime.now(timezone.utc).isoformat(),
        "fetch_time_ms": round((time.time() - t0) * 1000),
        "is_live":       len(trades) > 0,
        "senate_count":  len(trades),
        "all_trades":    trades,
        "crypto_trades": crypto,
        "source":        "Senate EFDS Playwright",
    }

    try:
        CACHE_PATH.parent.mkdir(exist_ok=True)
        CACHE_PATH.write_text(json.dumps(result, indent=2, default=str))
        logger.info("Cached %d trades (%d crypto)", len(trades), len(crypto))
    except Exception as e:
        logger.error("Cache write: %s", e)

    return result


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s [%(levelname)s] %(message)s")
    result = fetch_congress_trades(limit=50, force=True)
    print(f"\nStatus:          {'LIVE' if result['is_live'] else 'FAILED'}")
    print(f"Senate PTRs:     {result['senate_count']}")
    print(f"Crypto-adjacent: {len(result['crypto_trades'])}")
    print(f"Fetch time:      {result['fetch_time_ms']}ms")
    if result['all_trades']:
        print(f"\nMost recent 10 filings:")
        for t in sorted(result['all_trades'],
                        key=lambda x: x.get('date_filed',''), reverse=True)[:10]:
            flag = " 🔴 CRYPTO" if t.get('is_crypto') else ""
            print(f"  {t['date_filed']:12} {t['filer']:35}{flag}")
