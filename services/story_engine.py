#!/usr/bin/env python3
"""
story_engine.py — DISCOVERY-ONLY prototype (no posting, no writer integration)
Layers: Sensing -> Understanding -> Hybrid Scoring -> ranked candidate_stories.json
Hybrid score = deterministic signals (computed) + LLM soft judgment.
"""
import os, json, time, hashlib, re
from datetime import datetime, timezone
from pathlib import Path

BASE = Path("/home/ultron/protocol_pulse")
OUT = BASE / "data" / "intelligence" / "candidate_stories.json"
OUT.parent.mkdir(parents=True, exist_ok=True)

OPENAI_KEY = os.environ.get("OPENAI_API_KEY", "")
XAI_KEY = os.environ.get("XAI_API_KEY", "")

# ---- SOURCE CONFIG (phase 1: narrow enough to inspect manually) ----
RSS_FEEDS = [
    ("macro",   "https://www.federalreserve.gov/feeds/press_all.xml"),
    ("macro",   "https://home.treasury.gov/system/files/126/ofac.xml"),
    ("markets", "https://feeds.content.dowjones.io/public/rss/mw_topstories"),
    ("markets", "https://www.ft.com/rss/home"),
    ("crypto",  "https://www.coindesk.com/arc/outboundfeeds/rss/"),
    ("crypto",  "https://cointelegraph.com/rss"),
    ("crypto",  "https://bitcoinmagazine.com/feed"),
    ("crypto",  "https://www.theblock.co/rss.xml"),
    ("tech",    "https://techcrunch.com/feed/"),
    ("tech",    "https://arstechnica.com/feed/"),
    ("politics","https://www.politico.com/rss/politics08.xml"),
    ("energy",  "https://www.eia.gov/rss/todayinenergy.xml"),
    ("banking", "https://www.bis.org/rss/press.xml"),
    ("econ",    "https://feeds.bbci.co.uk/news/business/rss.xml"),
    ("onchain", "https://mempool.space/rss"),  # may 404; harvester tolerates
]

XAI_SEARCH_THEMES = [
    "unusual Bitcoin on-chain movement today",
    "central bank policy surprise this week",
    "sovereign debt or currency stress today",
    "major institution Bitcoin or crypto move",
    "energy grid or mining news today",
    "financial censorship or account freeze news",
]

# ---- SOURCE QUALITY WEIGHTS (deterministic) ----
SOURCE_QUALITY = {
    "federalreserve.gov": 0.98, "treasury.gov": 0.97, "bis.org": 0.96,
    "eia.gov": 0.95, "ft.com": 0.90, "theblock.co": 0.85,
    "coindesk.com": 0.80, "bitcoinmagazine.com": 0.78, "cointelegraph.com": 0.70,
    "techcrunch.com": 0.80, "arstechnica.com": 0.82, "politico.com": 0.82,
    "bbci.co.uk": 0.85, "marketwatch": 0.80, "mempool.space": 0.95,
    "x.com": 0.60,
}

def _domain(url):
    m = re.search(r"https?://([^/]+)", url or "")
    d = m.group(1).replace("www.", "") if m else "unknown"
    return d

def _source_quality(url):
    d = _domain(url)
    for k, v in SOURCE_QUALITY.items():
        if k in d:
            return v
    return 0.5

# ================= LAYER 1: SENSING (harvest) =================
def harvest_rss(max_per_feed=8):
    import feedparser
    items = []
    for domain_tag, feed_url in RSS_FEEDS:
        try:
            parsed = feedparser.parse(feed_url)
            for e in parsed.entries[:max_per_feed]:
                published = e.get("published_parsed") or e.get("updated_parsed")
                ts = time.mktime(published) if published else time.time()
                items.append({
                    "title": e.get("title", "").strip(),
                    "summary": re.sub("<[^>]+>", "", e.get("summary", ""))[:500],
                    "url": e.get("link", ""),
                    "domain_tag": domain_tag,
                    "source_domain": _domain(e.get("link", feed_url)),
                    "published_ts": ts,
                    "origin": "rss",
                })
        except Exception as ex:
            print(f"[rss] {feed_url} failed: {ex}")
    return items

def harvest_xai(max_per_theme=5):
    """Correct xAI Agent Tools format: POST /v1/responses, model grok-4.3, tools=[{type:x_search}]."""
    if not XAI_KEY:
        return []
    import urllib.request as u
    from datetime import timedelta
    items = []
    from_date = (datetime.now(timezone.utc) - timedelta(days=2)).strftime("%Y-%m-%d")
    for theme in XAI_SEARCH_THEMES:
        try:
            payload = json.dumps({
                "model": "grok-4.3",
                "input": "Find the most significant, recent, specific news about: " + theme + ". Return a JSON array of 3-5 items, each with keys headline, summary, source_url, why_significant. Only real verifiable items from the last 48h with citations.",
                "tools": [{"type": "x_search", "from_date": from_date}],
            }).encode()
            req = u.Request("https://api.x.ai/v1/responses", data=payload,
                headers={"Authorization": "Bearer " + XAI_KEY, "Content-Type": "application/json"})
            resp = json.loads(u.urlopen(req, timeout=45).read().decode())
            text = ""
            for out in resp.get("output", []):
                for block in out.get("content", []):
                    if block.get("type") in ("output_text", "text"):
                        text += block.get("text", "")
            if not text and "output_text" in resp:
                text = resp["output_text"]
            found = re.search(r"\[.*\]", text, re.DOTALL)
            if found:
                for it in json.loads(found.group(0)):
                    items.append({
                        "title": it.get("headline", "")[:200],
                        "summary": it.get("summary", "")[:500],
                        "url": it.get("source_url", ""),
                        "domain_tag": "xai_discovery",
                        "source_domain": _domain(it.get("source_url", "")),
                        "published_ts": time.time(),
                        "origin": "xai",
                        "why_significant": it.get("why_significant", ""),
                    })
        except Exception as ex:
            print("[xai] theme " + theme[:30] + " failed: " + str(ex))
        time.sleep(1)
    return items

# ================= DETERMINISTIC SIGNALS =================
def recency_score(ts):
    age_min = (time.time() - ts) / 60
    # Guard against unparseable/garbage timestamps (future or >7d) -> hard floor
    if age_min < 0 or age_min > 10080:
        return 0.05
    if age_min < 60: return 1.0
    if age_min < 360: return 0.8
    if age_min < 1440: return 0.5
    if age_min < 2880: return 0.3
    return 0.1

def saturation_and_corroboration(item, all_items):
    # Returns (saturation, corroboration). Saturation = same-source echo (bad).
    # Corroboration = DISTINCT independent domains covering it (good).
    toks = set(re.findall(r"[a-z]{4,}", item["title"].lower()))
    if not toks: return 0.0, 0
    covering_domains = set()
    dupes = 0
    for other in all_items:
        if other is item: continue
        otoks = set(re.findall(r"[a-z]{4,}", other["title"].lower()))
        if otoks and len(toks & otoks) / len(toks) > 0.4:
            dupes += 1
            covering_domains.add(other.get("source_domain",""))
    saturation = min(dupes / 6.0, 1.0)
    corroboration = len(covering_domains)  # # of independent domains
    return saturation, corroboration

def magnitude_score(item):
    # look for big numbers / % changes in title+summary
    text = (item["title"] + " " + item["summary"])
    nums = re.findall(r"(\d+(?:\.\d+)?)\s*(%|percent|billion|trillion|million|bps|basis points)", text, re.I)
    if not nums: return 0.2
    score = 0.2
    for val, unit in nums:
        v = float(val)
        if "trillion" in unit.lower(): score = max(score, 1.0)
        elif "billion" in unit.lower(): score = max(score, 0.8)
        elif "%" in unit or "percent" in unit.lower():
            score = max(score, min(v / 20.0, 1.0))
    return score

def dedup_items(items):
    seen, out = set(), []
    for it in items:
        h = hashlib.md5(it["title"].lower().encode()).hexdigest()[:12]
        if h in seen or len(it["title"]) < 15: continue
        seen.add(h); out.append(it)
    return out

# ================= LAYER 2+3: LLM SOFT SCORING =================
def llm_score_batch(items):
    if not OPENAI_KEY: return items
    import urllib.request as u
    for it in items:
        try:
            prompt = f"""Score this news item for a sophisticated financial/Bitcoin intelligence account. Return ONLY JSON.

TITLE: {it['title']}
SUMMARY: {it['summary']}
SOURCE: {it['source_domain']}

Score each 1-5 (integers):
- unexpectedness: does this defy the expected narrative?
- tension: is there contradiction, hypocrisy, or conflict?
- specificity: concrete facts/numbers vs vague?
- stakes: does it matter to money/power/sovereignty?
- connection: does it link to a bigger pattern a smart reader would appreciate?

Also: would_teach (true/false): would a sophisticated reader learn something NEW?
And: suggested_editorial_type (one of: anomaly, divergence, receipt, connection, deadpan, investigation, chart)
And: why_interesting (one sentence, plain, no hype)

JSON: {{"unexpectedness":N,"tension":N,"specificity":N,"stakes":N,"connection":N,"would_teach":bool,"suggested_editorial_type":"...","why_interesting":"..."}}"""
            payload = json.dumps({
                "model": "gpt-4o",
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 250,
                "temperature": 0.3,
            }).encode()
            req = u.Request("https://api.openai.com/v1/chat/completions", data=payload,
                headers={"Authorization": f"Bearer {OPENAI_KEY}", "Content-Type": "application/json"})
            resp = json.loads(u.urlopen(req, timeout=30).read().decode())
            content = resp["choices"][0]["message"]["content"]
            j = re.search(r"\{.*\}", content, re.DOTALL)
            if j:
                scores = json.loads(j.group(0))
                it.update(scores)
        except Exception as ex:
            print(f"[llm] score failed: {ex}")
            it.update({"unexpectedness":2,"tension":2,"specificity":2,"stakes":2,"connection":2,
                       "would_teach":False,"suggested_editorial_type":"unknown","why_interesting":""})
    return items

# ================= HYBRID FINAL SCORE =================
def compute_overall(item, all_items):
    rec = recency_score(item["published_ts"])
    sq = _source_quality(item["url"])
    sat, corrob = saturation_and_corroboration(item, all_items)
    mag = magnitude_score(item)
    # independent corroboration credit (2+ distinct domains = more trustworthy story)
    corrob_bonus = min(corrob, 3) / 3.0 * 0.08
    # soft (LLM) 1-5 -> normalize. Weight tension + unexpectedness higher per GPT.
    sv = {k: item.get(k, 2) for k in ["unexpectedness","tension","specificity","stakes","connection"]}
    soft = (sv["unexpectedness"]*1.3 + sv["tension"]*1.3 + sv["specificity"]*1.0 +
            sv["stakes"]*1.1 + sv["connection"]*1.0) / (5.7 * 5)
    teach_bonus = 0.1 if item.get("would_teach") else 0.0
    overall = (
        0.15 * rec + 0.12 * sq + 0.08 * (1 - sat) + 0.15 * mag +
        0.35 * soft + teach_bonus + corrob_bonus
    )
    item["_signals"] = {"recency":round(rec,2),"source_quality":round(sq,2),
                        "saturation":round(sat,2),"corroboration":corrob,
                        "magnitude":round(mag,2),"soft":round(soft,2)}
    item["overall_score"] = round(overall * 100)
    return item

def run(top_n=10):
    print("=== SENSING ===")
    rss = harvest_rss()
    print(f"  RSS harvested: {len(rss)}")
    xai = harvest_xai()
    print(f"  xAI harvested: {len(xai)}")
    all_items = dedup_items(rss + xai)
    # Hard freshness gate: drop anything older than 48h (news must be current)
    now = time.time()
    fresh = [it for it in all_items if 0 <= (now - it["published_ts"]) <= 172800]
    dropped = len(all_items) - len(fresh)
    all_items = fresh
    print(f"  After dedup + 48h freshness gate: {len(all_items)} (dropped {dropped} stale)")

    print("=== DETERMINISTIC + LLM SCORING ===")
    all_items = llm_score_batch(all_items)
    for it in all_items:
        compute_overall(it, all_items)

    ranked = sorted(all_items, key=lambda x: x.get("overall_score", 0), reverse=True)[:top_n]

    stories = []
    for i, it in enumerate(ranked):
        stories.append({
            "story_id": hashlib.md5(it["title"].encode()).hexdigest()[:10],
            "rank": i + 1,
            "headline": it["title"],
            "domain": it["domain_tag"],
            "summary": it["summary"][:300],
            "why_interesting": it.get("why_interesting", ""),
            "sources": [it["url"]],
            "source_domain": it["source_domain"],
            "primary_source_found": bool(it["url"]),
            "freshness_minutes": round((time.time() - it["published_ts"]) / 60),
            "signals": it.get("_signals", {}),
            "unexpectedness": it.get("unexpectedness"),
            "tension": it.get("tension"),
            "specificity": it.get("specificity"),
            "stakes": it.get("stakes"),
            "connection": it.get("connection"),
            "would_teach": it.get("would_teach"),
            "suggested_editorial_type": it.get("suggested_editorial_type", "unknown"),
            "overall_score": it["overall_score"],
            "verification_status": "unverified",
        })

    with open(OUT, "w") as f:
        json.dump({"generated_at": datetime.now(timezone.utc).isoformat(),
                   "total_harvested": len(all_items), "stories": stories}, f, indent=2)
    print(f"=== DONE: {len(stories)} ranked stories -> {OUT} ===")
    return stories

if __name__ == "__main__":
    run()
