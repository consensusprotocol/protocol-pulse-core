"""
network.py — Resilient HTTP utility for assembler_v2.
All external API calls route through http_get() and http_post().
Provides retry with exponential backoff + jitter.
Never raises — returns None on all failures.
"""
import time, random, logging
logger = logging.getLogger(__name__)


def http_get(url: str, params=None, headers=None, timeout=10,
             max_attempts=3, backoff_base=1.5):
    """GET with retry/backoff. Returns response object or None on failure."""
    import requests
    for attempt in range(1, max_attempts + 1):
        try:
            r = requests.get(url, params=params, headers=headers, timeout=timeout)
            if r.status_code == 429:
                retry_after = int(r.headers.get('Retry-After', backoff_base ** attempt))
                logger.warning(f"[network] 429 on {url} — waiting {retry_after}s")
                time.sleep(retry_after + random.uniform(0, 1))
                continue
            r.raise_for_status()
            return r
        except Exception as e:
            wait = (backoff_base ** attempt) + random.uniform(0, 1)
            if attempt < max_attempts:
                logger.warning(f"[network] attempt {attempt}/{max_attempts} failed for {url}: {e} — retry in {wait:.1f}s")
                time.sleep(wait)
            else:
                logger.error(f"[network] all {max_attempts} attempts failed for {url}: {e}")
    return None


def http_post(url: str, json_body=None, headers=None, timeout=30,
              max_attempts=3, backoff_base=1.5):
    """POST with retry/backoff. Returns response object or None on failure."""
    import requests
    for attempt in range(1, max_attempts + 1):
        try:
            r = requests.post(url, json=json_body, headers=headers, timeout=timeout)
            if r.status_code == 429:
                retry_after = int(r.headers.get('Retry-After', backoff_base ** attempt))
                logger.warning(f"[network] 429 on {url} — waiting {retry_after}s")
                time.sleep(retry_after + random.uniform(0, 1))
                continue
            r.raise_for_status()
            return r
        except Exception as e:
            wait = (backoff_base ** attempt) + random.uniform(0, 1)
            if attempt < max_attempts:
                logger.warning(f"[network] attempt {attempt}/{max_attempts} failed for {url}: {e} — retry in {wait:.1f}s")
                time.sleep(wait)
            else:
                logger.error(f"[network] all {max_attempts} attempts failed for {url}: {e}")
    return None
