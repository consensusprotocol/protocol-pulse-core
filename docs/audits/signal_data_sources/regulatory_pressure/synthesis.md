# MASTER DATA SOURCE REPORT: Bitcoin Regulatory Pressure Signal

---

## SECTION 1: UNANIMOUS SOURCES (All 3 Models Agreed)

These sources appeared across Gemini, GPT-4o, and Grok — highest confidence tier.

| Source | Exact URL | Auth | Rate Limit | Key Fields | Update Freq | Consensus Quality |
|--------|-----------|------|------------|------------|-------------|-------------------|
| Congress.gov API | `https://api.congress.gov/v3/bill?format=json` | API Key (Free at api.congress.gov/sign-up) | 1,000 req/hr | `title`, `latestAction.text`, `policyArea.name`, `sponsors`, `cosponsors.count` | Daily | 9/10 |
| SEC EDGAR Full-Text | `https://efts.sec.gov/LATEST/search-index` | None | ~10 req/sec (be conservative) | Filing text, `form` type (S-1, 19b-4, 497), `accessionNumber`, `cik` | Near real-time | 8/10 |
| Federal Register API | `https://www.federalregister.gov/api/v1/documents.json` | None | Generous, undocumented | `title`, `publication_date`, `agencies.name`, `abstract`, `html_url`, `document_number` | Daily | 9/10 |
| CFTC Press Releases | `https://www.cftc.gov/rss/PressRoom.xml` | None | N/A (RSS) | `title`, `link`, `pubDate`, `description` | As-needed | 7/10 |
| iShares IBIT ETF | `https://www.ishares.com/us/products/333011/ishares-bitcoin-trust` | None | Undocumented | `Shares Outstanding`, `Market Price`, `Net Assets`, `As of Date` | Daily | 9/10 |
| Fidelity FBTC Data | `https://institutional.fidelity.com/app/proxy/content?literatureURL=/9899221.PDF` | None | Undocumented | Holdings, inflows/outflows | Daily | 8/10 |
| BIS Research Papers | `https://www.bis.org/doclist/rss/cbspeeches.xml` | None | N/A (RSS) | `title`, `link`, speech author, institution, date | Weekly | 8/10 |

---

## SECTION 2: MAJORITY SOURCES (2 of 3 Models Agreed)

| Source | Exact URL | Auth | Rate Limit | Key Fields | Update Freq | Models | Quality |
|--------|-----------|------|------------|------------|-------------|--------|---------|
| SEC Data Submissions API | `https://data.sec.gov/submissions/CIK{NUMBER}.json` | None (User-Agent header required) | 10 req/sec | `filings.recent.form`, `filings.recent.accessionNumber`, `filings.recent.filingDate`, `entityType` | Daily | Gemini + Grok | 9/10 |
| DOJ Cybercrime RSS | `https://www.justice.gov/opa/rss.xml?field_pr_topic_tid=4531` | None | N/A (RSS) | `title`, `description`, keywords: 'seizure', 'virtual currency', 'indictment' | As-needed | Gemini + Grok | 9/10 |
| OFAC SDN Sanctions | `https://sanctionssearch.ofac.treas.gov/api/search` | None | Undocumented | `Name`, `Programs`, `SourceListURL`, Bitcoin addresses flagged | As-needed | Gemini only (critical miss by others) | 10/10 |
| ARK ARKB ETF CSV | `https://ark-funds.com/wp-content/uploads/funds-etf-csv/ARKB.csv` | None | Undocumented | Daily holdings, shares, weight | Daily | GPT-4o + Grok | 8/10 |
| Farside ETF Aggregator | `https://farside.co.uk/?p=997` | None | Undocumented | All ETF daily flows in one HTML table | Daily | Gemini + implicit Grok | 10/10 |
| IMF Data API | `https://www.imf.org/external/datamapper/api/v1` | None | Undocumented | Economic indicators, financial stability flags | Quarterly | GPT-4o + Grok | 7/10 |
| World Bank API | `https://api.worldbank.org/v2/country/all/indicator/NY.GDP.MKTP.CD?format=json` | None | Undocumented | Macro economic stress indicators by country | Quarterly | GPT-4o + Grok | 6/10 |
| EU EUR-Lex (MiCA) | `https://eur-lex.europa.eu/search.html?qid=&text=bitcoin&scope=EURLEX` | None | Undocumented | MiCA regulation texts, amendments, enforcement dates | Monthly | GPT-4o unique partial | 8/10 |

---

## SECTION 3: UNIQUE FINDINGS BY MODEL

### What GEMINI Found That Others Missed

| Unique Source | Exact URL | Why It Matters | Quality |
|---------------|-----------|----------------|---------|
| **OFAC SDN Sanctions Search** | `https://sanctionssearch.ofac.treas.gov/api/search` | Direct Bitcoin address blacklisting — strongest regulatory enforcement signal possible. When OFAC adds a BTC address, it's a 10-alarm fire for exchange compliance teams. Immediate price-relevant event. | 10/10 |
| **Treasury OFAC SDN XML bulk** | `https://www.treasury.gov/ofac/downloads/sdn.xml` | Full bulk download of all sanctioned entities. Cross-reference against known exchange wallets. | 9/10 |
| **SEC EDGAR CIK-specific filings** | `https://data.sec.gov/submissions/CIK0001990422.json` | Direct filing-level tracking per entity (e.g. BlackRock Bitcoin Trust CIK). More precise than full-text search. | 9/10 |

### What GPT-4O Found That Others Missed

| Unique Source | Exact URL | Why It Matters | Quality |
|---------------|-----------|----------------|---------|
| **EU EUR-Lex MiCA texts** | `https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX%3A32023R1114` | MiCA is the world's first comprehensive crypto regulatory framework. Direct text access for parsing enforcement timelines, asset classification changes. | 8/10 |
| **IMF Financial Stability API** | `https://www.imf.org/external/datamapper/api/v1/NGDP_RPCH` | Global financial stress correlates with Bitcoin regulatory crackdowns historically (2022 Terra/Luna, 2023 banking crisis). Leading indicator. | 7/10 |
| **World Bank Financial Inclusion** | `https://api.worldbank.org/v2/country/all/indicator/FX.OWN.TOTL.ZS?format=json` | Countries with low banking access adopt Bitcoin faster, creating regulatory conflict zones (Nigeria, Turkey, Argentina). | 6/10 |

### What GROK Found That Others Missed

| Unique Source | Exact URL | Why It Matters | Quality |
|---------------|-----------|----------------|---------|
| **ARK ARKB Daily CSV** | `https://ark-funds.com/wp-content/uploads/funds-etf-csv/ARKB.csv` | Direct machine-readable ETF flow data. No scraping required. ARK is a leading indicator of retail regulatory sentiment. | 8/10 |
| **FinCEN Enforcement Actions** | `https://www.fincen.gov/news-room/rss.xml` | FinCEN actions on crypto exchanges (e.g. Binance $4.3B fine). Direct AML/KYC regulatory pressure signal. | 9/10 |
| **State-Level Regulatory Tracker (NMLS)** | `https://www.nmlsconsumeraccess.org/` | BitLicense equivalents by state. NY, CA, TX regulatory divergence creates arbitrage signals. | 7/10 |

---

## SECTION 4: PRIORITY RANKINGS

### P0 — CRITICAL (Implement Immediately, Highest Alpha)

| Source | URL | Rationale |
|--------|-----|-----------|
| OFAC SDN Sanctions | `https://sanctionssearch.ofac.treas.gov/api/search` | Real-time enforcement. Exchange delistings follow within hours. |
| DOJ Cybercrime RSS | `https://www.justice.gov/opa/rss.xml?field_pr_topic_tid=4531` | Seizure announcements move price immediately. |
| Congress.gov API | `https://api.congress.gov/v3/bill?format=json` | Legislation pipeline — 6-18 month leading indicator. |
| Federal Register API | `https://www.federalregister.gov/api/v1/documents.json` | Proposed rules → comment periods → enforcement. Timeline is tradeable. |
| Farside ETF Flows | `https://farside.co.uk/?p=997` | Spot ETF flows are the most direct institutional demand signal post-Jan 2024. |
| SEC EDGAR Full-Text | `https://efts.sec.gov/LATEST/search-index` | 19b-4 filings and STB orders are pre-announcement signals. |
| FinCEN RSS | `https://www.fincen.gov/news-room/rss.xml` | AML enforcement is the most common regulatory vector against exchanges. |

### P1 — HIGH VALUE (Implement Within 2 Weeks)

| Source | URL | Rationale |
|--------|-----|-----------|
| SEC Data API (CIK) | `https://data.sec.gov/submissions/CIK0001990422.json` | Entity-level tracking more precise than keyword search. |
| CFTC Press Releases | `https://www.cftc.gov/rss/PressRoom.xml` | Derivatives regulation directly affects futures markets and leveraged products. |
| BIS Speeches RSS | `https://www.bis.org/doclist/rss/cbspeeches.xml` | Central bank governors telegraph policy 3-6 months out. |
| EU EUR-Lex MiCA | `https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX%3A32023R1114` | MiCA enforcement dates (Dec 2024, Jun 2026) are hard calendar anchors. |
| ARK ARKB CSV | `https://ark-funds.com/wp-content/uploads/funds-etf-csv/ARKB.csv` | Machine-readable ETF flow without scraping. |
| OFAC SDN XML Bulk | `https://www.treasury.gov/ofac/downloads/sdn.xml` | Full entity list for batch cross-referencing. |

### P2 — SUPPLEMENTAL (Implement for Completeness)

| Source | URL | Rationale |
|--------|-----|-----------|
| IMF Data API | `https://www.imf.org/external/datamapper/api/v1` | Macro context for regulatory cycles but low frequency (quarterly). |
| World Bank API | `https://api.worldbank.org/v2/country/all/indicator/NY.GDP.MKTP.CD?format=json` | Country-level financial stress — too lagged for trading signals. |
| State NMLS Tracker | `https://www.nmlsconsumeraccess.org/` | State BitLicense tracking — useful for compliance mapping, not price signals. |
| iShares IBIT Holdings | `https://www.ishares.com/us/products/333011/ishares-bitcoin-trust` | Supplemental to Farside aggregation. |

---

## SECTION 5: Python Code — Primary Free Data Fetch (No API Key Required)

```python
"""
Bitcoin Regulatory Pressure Signal Aggregator
All P0 sources, no API keys required
Requires: pip install requests feedparser pandas beautifulsoup4 lxml
"""

import requests
import feedparser
import pandas as pd
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import json
import time
import re

# ============================================================
# CONFIG
# ============================================================
HEADERS = {
    "User-Agent": "BitcoinResearch research@domain.com",  # Required for SEC
    "Accept": "application/json"
}
KEYWORDS = [
    "bitcoin", "cryptocurrency", "digital asset", "virtual currency",
    "crypto", "blockchain", "btc", "stablecoin", "defi"
]
RESULTS = {}

# ============================================================
# SOURCE 1: FEDERAL REGISTER API (P0)
# ============================================================
def fetch_federal_register():
    """
    Fetches proposed rules, notices, executive orders mentioning crypto.
    Returns list of dicts with title, date, agency, abstract, url.
    """
    url = "https://www.federalregister.gov/api/v1/documents.json"
    params = {
        "conditions[term]": "cryptocurrency bitcoin",
        "fields[]": ["title", "publication_date", "agencies", "abstract",
                     "html_url", "document_number", "type"],
        "per_page": 20,
        "order": "newest"
    }
    
    try:
        r = requests.get(url, params=params, timeout=10)
        r.raise_for_status()
        data = r.json()
        
        results = []
        for doc in data.get("results", []):
            agencies = [a.get("name", "") for a in doc.get("agencies", [])]
            results.append({
                "source": "FederalRegister",
                "title": doc.get("title", ""),
                "date": doc.get("publication_date", ""),
                "agencies": agencies,
                "abstract": doc.get("abstract", "")[:500],
                "url": doc.get("html_url", ""),
                "doc_number": doc.get("document_number", ""),
                "type": doc.get("type", ""),
                "signal_strength": _score_regulatory_severity(
                    doc.get("title", "") + " " + doc.get("abstract", "")
                )
            })
        
        print(f"[FederalRegister] Fetched {len(results)} documents")
        return results
        
    except Exception as e:
        print(f"[FederalRegister] Error: {e}")
        return []


# ============================================================
# SOURCE 2: DOJ CYBERCRIME RSS (P0)
# ============================================================
def fetch_doj_cybercrime():
    """
    Parses DOJ press release feed filtered for crypto enforcement actions.
    Seizure announcements are immediate price-relevant events.
    """
    feed_url = "https://www.justice.gov/opa/rss.xml?field_pr_topic_tid=4531"
    
    try:
        feed = feedparser.parse(feed_url)
        
        results = []
        for entry in feed.entries[:20]:
            title = entry.get("title", "")
            summary = entry.get("summary", "")
            combined = (title + " " + summary).lower()
            
            # Filter for crypto-relevant entries
            if any(kw in combined for kw in KEYWORDS):
                results.append({
                    "source": "DOJ_Cybercrime",
                    "title": title,
                    "date": entry.get("published", ""),
                    "url": entry.get("link", ""),
                    "summary": summary[:400],
                    "enforcement_type": _classify_enforcement(combined),
                    "signal_strength": _score_regulatory_severity(combined)
                })
        
        print(f"[DOJ] Fet