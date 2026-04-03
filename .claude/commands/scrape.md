Trigger a specific social scraper.

Source: $ARGUMENTS
- "x" or "twitter" or "nitter": `python3 services/nitter_scraper.py`
- "nostr": `python3 cron/nostr_cron.py`
- "spaces": `python3 x_spaces_scraper/run_scraper.py`
- "media" or "rss": `python3 scripts/sync_media_feeds.py`
- "all": run all scrapers sequentially
- If blank: show status of all scrapers (last run time, data freshness)

After scraping, report: items collected, data freshness, any errors.