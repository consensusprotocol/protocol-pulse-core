# F-P3-2: Jurisdiction Regulatory Intelligence Engine — Foundation Document

## Purpose
50-jurisdiction legislative monitoring with NLP keyword classification and 24h update latency.

## Data Sources (all free RSS/public)
- BIS: https://www.bis.org/rss.htm
- ECB: https://www.ecb.europa.eu/rss/news.rss
- Federal Reserve: https://www.federalreserve.gov/feeds/press_all.xml
- IMF Blog: https://www.imf.org/en/Blogs/rss
- CoinDesk: https://www.coindesk.com/arc/outboundfeeds/rss/
- Bitcoin Magazine: https://bitcoinmagazine.com/.rss/full/

## NLP Classification (Rule-Based Keyword Matching)
- HOSTILE: ban, prohibit, illegal, restrict, seize, freeze, AML, enforcement
- FRIENDLY: legal tender, regulate, approve, license, ETF, approved, framework
- NEUTRAL: everything else
- Confidence threshold: keyword_count / total_words > 0.01

## Output Schema (SentinelState.regulatory)
```json
{
  "recent_alerts": [],
  "jurisdiction_updates": [],
  "threat_level": "LOW|MEDIUM|HIGH",
  "last_hostile_event": null,
  "last_friendly_event": null,
  "updated_at": 0.0
}
```

## Integration
- Load via importlib.util in sentinel.py
- Run every 30 minutes
- Display in SOVEREIGN LAYER panel
