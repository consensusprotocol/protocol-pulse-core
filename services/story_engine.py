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
    # --- added 2026-08-27 (probed live from Ultron; primary sources first) ---
    ("macro",   "https://www.sec.gov/news/pressreleases.rss"),
    ("macro",   "https://www.ecb.europa.eu/rss/press.html"),
    ("macro",   "https://www.bankofengland.co.uk/rss/news"),
    ("macro",   "https://www.boj.or.jp/en/rss/whatsnew.xml"),
    ("macro",   "https://apps.bea.gov/rss/rss.xml"),
    ("macro",   "https://www.occ.gov/rss/occ_news.xml"),
    ("macro",   "https://www.federalreserve.gov/feeds/speeches.xml"),
    ("banking", "https://www.bis.org/doclist/cbspeeches.rss"),
    ("banking", "https://www.fsb.org/feed/"),
    ("markets", "https://feeds.bloomberg.com/markets/news.rss"),
    ("markets", "https://www.economist.com/finance-and-economics/rss.xml"),
    ("markets", "https://rss.nytimes.com/services/xml/rss/nyt/Business.xml"),
    ("markets", "https://www.cnbc.com/id/10000664/device/rss/rss.html"),
    ("crypto",  "https://bitcoinops.org/feed.xml"),
    ("crypto",  "https://blog.bitmex.com/feed/"),
    ("crypto",  "https://protos.com/feed/"),
    ("crypto",  "https://decrypt.co/feed"),
    ("onchain", "https://blog.blockstream.com/rss/"),
    ("energy",  "https://www.utilitydive.com/feeds/news/"),
    ("tech",    "https://www.theregister.com/headlines.atom"),
    ("tech",    "https://www.wired.com/feed/category/business/latest/rss"),
    ("tech",    "https://www.eff.org/rss/updates.xml"),
    ("tech",    "https://krebsonsecurity.com/feed/"),
    ("politics","https://feeds.bbci.co.uk/news/world/rss.xml"),
    ("politics","https://www.aljazeera.com/xml/rss/all.xml"),
]

XAI_SEARCH_THEMES = [
    "unusual Bitcoin on-chain movement today",
    "central bank policy surprise this week",
    "sovereign debt or currency stress today",
    "major institution Bitcoin or crypto move",
    "energy grid or mining news today",
    "financial censorship or account freeze news",
    # added 2026-08-27
    "BIP-110 Bitcoin consensus discussion this week",
    "stablecoin regulation or tokenized deposit news",
    "CBDC rollout or capital controls announcement",
    "AI datacenter power demand grid strain",
    "treasury auction or bond market stress",
    "corporate or sovereign bitcoin treasury purchase",
    "tariff sanction or trade escalation today",
]

# ---- SOURCE QUALITY WEIGHTS (deterministic) ----
SOURCE_QUALITY = {
    "federalreserve.gov": 0.98, "treasury.gov": 0.97, "bis.org": 0.96,
    "eia.gov": 0.95, "ft.com": 0.90, "theblock.co": 0.85,
    "coindesk.com": 0.80, "bitcoinmagazine.com": 0.78, "cointelegraph.com": 0.70,
    "techcrunch.com": 0.80, "arstechnica.com": 0.82, "politico.com": 0.82,
    "bbci.co.uk": 0.85, "marketwatch": 0.80, "mempool.space": 0.95,
    "x.com": 0.60,
    # added 2026-08-27
    "sec.gov": 0.97, "ecb.europa.eu": 0.96, "bankofengland.co.uk": 0.96,
    "boj.or.jp": 0.95, "bea.gov": 0.95, "occ.gov": 0.95, "fsb.org": 0.95,
    "bloomberg.com": 0.92, "economist.com": 0.88, "nytimes.com": 0.85,
    "cnbc.com": 0.78, "bitcoinops.org": 0.92, "blog.bitmex.com": 0.80,
    "protos.com": 0.75, "decrypt.co": 0.70, "blockstream.com": 0.85,
    "utilitydive.com": 0.80, "theregister.com": 0.78, "wired.com": 0.78,
    "eff.org": 0.85, "krebsonsecurity.com": 0.85, "aljazeera.com": 0.75,
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
    import feedparser, calendar
    items = []
    for domain_tag, feed_url in RSS_FEEDS:
        try:
            parsed = feedparser.parse(feed_url)
            for e in parsed.entries[:max_per_feed]:
                published = e.get("published_parsed") or e.get("updated_parsed")
                ts = calendar.timegm(published) if published else time.time()  # feedparser structs are UTC; mktime assumed local (ET) and pushed fresh items 4h into the future
                items.append({
                    "title": e.get("title", "").strip(),
                    "summary": re.sub("<[^>]+>", "", e.get("summary", ""))[:500],
                    "url": e.get("link", ""),
                    "domain_tag": domain_tag,
                    "source_domain": _domain(e.get("link", feed_url)),
                    "published_ts": ts,
                    "discovered_ts": time.time(),
                    "timestamp_provenance": "source" if published else "unknown_defaulted_now",
                    "origin": "rss",
                })
        except Exception as ex:
            print(f"[rss] {feed_url} failed: {ex}")
    return items

def _parse_iso_utc(v):
    """ISO 8601 -> epoch (UTC). Returns None if missing/garbage/future(>15m)/older than 30d."""
    if not v or not isinstance(v, str):
        return None
    try:
        v2 = v.strip().replace("Z", "+00:00")
        dt = datetime.fromisoformat(v2)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        ts = dt.timestamp()
        now = time.time()
        if ts > now + 900 or ts < now - 30 * 86400:
            return None
        return ts
    except Exception:
        return None

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
                "input": "Find the most significant, recent, specific news about: " + theme + ". Return a JSON array of 3-5 items, each with keys headline, summary, source_url, published_at, why_significant. published_at MUST be the ISO 8601 UTC datetime the SOURCE published it (e.g. 2026-08-26T14:30:00Z), not the time you found it; use null if unknown. Only real verifiable items from the last 48h with citations.",
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
                    # TIMESTAMP PROVENANCE: never stamp discovery time as publish time.
                    # Unknown publish time -> neutral 12h-old (recency 0.5), not "now" (1.0).
                    src_ts = _parse_iso_utc(it.get("published_at"))
                    items.append({
                        "title": it.get("headline", "")[:200],
                        "summary": it.get("summary", "")[:500],
                        "url": it.get("source_url", ""),
                        "domain_tag": "xai_discovery",
                        "source_domain": _domain(it.get("source_url", "")),
                        "published_ts": src_ts if src_ts else time.time() - 12 * 3600,
                        "discovered_ts": time.time(),
                        "timestamp_provenance": "source" if src_ts else "unknown_defaulted_12h",
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


# ================= LAYER 1.75: SEMANTIC EVENT CLUSTERING =================
# One wire story reported by three outlets is ONE event with three reports, not three events.
# Fingerprint = primary_entity + event + object + event_date, normalized by gpt-4o in one batch call.
# origin_outlet captures syndication ("per Reuters", "Bloomberg reported") so independent_corroboration
# counts distinct ORIGINS, not distinct domains.
CLUSTER_PROMPT = """You normalize news items into event fingerprints for de-duplication. TODAY is {today}; all items were published in the last 48 hours, so event dates are {today} or a few days before — never earlier years unless the text explicitly says so.
For EACH item return one object: {{"i": <index>, "event_key": "<entity>_<event>_<object>_<YYYY-MM-DD or unknown>" as a lowercase snake slug,
"entity": "...", "event": "<verb phrase, 1-3 words>", "object": "...", "event_date": "YYYY-MM-DD or null (date the underlying event happened, NOT the article date)",
"origin_outlet": "<the UPSTREAM outlet this item is relaying, e.g. Reuters, Bloomberg, WSJ, AP, FT, CNBC, court filing, company release. NEVER the item's own [domain] shown in brackets. null if the item is itself the original report or you cannot tell>"}}
Two items describing the SAME real-world event MUST get the IDENTICAL event_key even if headlines differ. Different events about the same entity get different keys.
Return ONLY a JSON array.

ITEMS:
{items}
"""

def _origin_label(x):
    """'Bloomberg' / 'bloomberg.com' / 'www.bloomberg.co.uk' / 'Reuters' -> 'bloomberg' / 'reuters'."""
    x = (x or "").lower().strip()
    x = re.sub(r"^https?://", "", x).split("/")[0]
    parts = [p for p in x.split(".") if p not in ("www", "en", "m")]
    if len(parts) >= 2 and parts[-1] in ("com","org","net","io","co","gov","uk","de","jp","info") :
        parts = parts[:-1]
        if parts and parts[-1] in ("co","com"): parts = parts[:-1]
    return re.sub(r"[^a-z0-9]", "", parts[-1] if parts else x)

def cluster_events(items):
    if not OPENAI_KEY or len(items) < 2:
        for it in items: it.update(report_count=1, independent_corroboration=1, sources_all=[it["url"]])
        return items
    import urllib.request as u
    fps = {}
    for start in range(0, len(items), 30):
        batch = items[start:start+30]
        listing = "\n".join(f'{start+i}. [{it.get("source_domain","")}] {it["title"][:140]} :: {it["summary"][:220]}' for i, it in enumerate(batch))
        try:
            today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            payload = json.dumps({"model": "gpt-4o", "temperature": 0, "max_tokens": 3500,
                                  "messages": [{"role": "user", "content": CLUSTER_PROMPT.format(items=listing, today=today)}]}).encode()
            req = u.Request("https://api.openai.com/v1/chat/completions", data=payload,
                            headers={"Authorization": "Bearer " + OPENAI_KEY, "Content-Type": "application/json"})
            txt = json.loads(u.urlopen(req, timeout=90).read())["choices"][0]["message"]["content"]
            m = re.search(r"\[.*\]", txt, re.S)
            for fp in json.loads(m.group(0)) if m else []:
                if isinstance(fp, dict) and isinstance(fp.get("i"), int): fps[fp["i"]] = fp
        except Exception as e:
            print(f"  [cluster] batch {start} failed: {type(e).__name__}")
    groups = {}
    for i, it in enumerate(items):
        fp = fps.get(i) or {}
        key = (fp.get("event_key") or hashlib.md5(it["title"].lower().encode()).hexdigest()[:12]).lower().strip()
        it["event_fingerprint"] = fp
        groups.setdefault(key, []).append(it)
    merged = []
    for key, grp in groups.items():
        grp.sort(key=lambda x: (-_source_quality(x["url"]), x["published_ts"]))
        canon = grp[0]
        origins = set()
        for g in grp:
            fp = g.get("event_fingerprint") or {}
            oo = fp.get("origin_outlet")
            own = (g.get("source_domain") or "").lower()
            if oo and (oo.lower() in own or own.split(".")[0] in oo.lower()):
                oo = None; fp["origin_outlet"] = None
            origins.add(_origin_label(oo or own))
        canon["event_key"] = key
        canon["report_count"] = len(grp)
        canon["independent_corroboration"] = max(1, len(origins))
        canon["sources_all"] = [g["url"] for g in grp]
        canon["source_domains_all"] = sorted({g.get("source_domain","") for g in grp})
        canon["syndicated_from"] = sorted({(g.get("event_fingerprint") or {}).get("origin_outlet") for g in grp} - {None})
        canon["earliest_published_ts"] = min(g["published_ts"] for g in grp)
        ed = (canon.get("event_fingerprint") or {}).get("event_date")
        if ed: canon["event_date_hint"] = ed
        merged.append(canon)
    return merged

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
        if otoks and len(toks & otoks) / len(toks) > 0.3:
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
    if item.get("report_count"):
        sat = min((item["report_count"] - 1) / 6.0, 1.0)          # echo of the same event = less unique
        corrob = item.get("independent_corroboration", 1)          # distinct ORIGINS, syndication collapsed
    else:
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



# ================= LAYER 3.5: ADVERSARIAL VERIFICATION =================
# GPT spec: the verifier is HOSTILE to the candidate. Its job is to BREAK the story.
# Core rule: a story can survive with inference, but a claim cannot masquerade as fact.
# Outputs: per-claim status, story status, a do-not-say list (writer guardrail),
# and logs rejected claims to a growing dataset.

REJECTED_CLAIMS_LOG = BASE / "data" / "intelligence" / "rejected_claims.jsonl"

def _live_block_height():
    import urllib.request as u
    try:
        return int(u.urlopen("https://mempool.space/api/blocks/tip/height", timeout=8).read().decode())
    except Exception:
        return None

def _live_btc_price():
    import urllib.request as u
    try:
        r = u.urlopen("https://query1.finance.yahoo.com/v8/finance/chart/BTC-USD?interval=1d&range=1d", timeout=8)
        d = json.loads(r.read().decode())
        return float(d["chart"]["result"][0]["meta"]["regularMarketPrice"])
    except Exception:
        return None

def extract_claims(item):
    """Pull atomic, checkable claims. Tag superlatives and causal/inference language."""
    text = (item.get("title","") + " . " + item.get("summary",""))
    claims = []
    for m in re.finditer(r"(\$?\d[\d,\.]*)\s*(%|percent|billion|trillion|million|bps|EH/s|sat|BTC|k)?", text):
        val = m.group(1)
        if len(val.replace(",","").replace(".","").replace("$","")) >= 2:
            claims.append({"raw": m.group(0).strip(), "value": val, "unit": m.group(2) or "", "kind": "numeric"})
    # superlative / "first/record/largest/unprecedented" claims
    for m in re.finditer(r"\b(first|largest|biggest|record|unprecedented|highest|lowest|never before|all-time)\b", text, re.I):
        claims.append({"raw": m.group(0), "kind": "superlative"})
    return claims[:10]

def adversarial_verify(item):
    """
    CLAIM AUDITOR (not an external verifier). Hostile internal-consistency pass.
    Only BTC price + block height are live hard-checked; every other claim is judged
    by an LLM against the packet text. See docs/SOCIAL_ENGINE_HANDOFF.md Layer 3. Tries to break each claim. Produces:
      - per-claim status: VERIFIED_PRIMARY | VERIFIED_SECONDARY | INFERENCE_SUPPORTED | UNVERIFIED | CONTRADICTED | STALE
      - story-level verification_status (worst-case aware)
      - do_not_say[]  (active writer guardrail)
      - writer_eligible / requires_hedge
    Uses GPT-4o as an adversarial checker for claims we can't hard-verify.
    """
    claims = extract_claims(item)
    item["primary_claims"] = [c["raw"] for c in claims]
    do_not_say = []
    claim_results = []

    src_q = _source_quality(item.get("url",""))
    has_primary = bool(item.get("url")) and src_q >= 0.9   # gov/primary-grade
    domain = item.get("source_domain","")

    # 1) HARD live checks (block height / btc price if the story states one)
    text_low = (item.get("title","") + " " + item.get("summary","")).lower()
    hard = []
    bh = re.search(r"\bblock\s*(9\d{5})\b", text_low) or (re.search(r"\b(9\d{5})\b", text_low) if "block" in text_low else None)
    if bh:
        live = _live_block_height()
        if live:
            diff = abs(int(bh.group(1)) - live)
            ok = diff <= 20
            hard.append({"field":"block_height","status":"VERIFIED_PRIMARY" if ok else "CONTRADICTED","detail":f"claimed {bh.group(1)} vs live {live}"})
            if not ok: do_not_say.append(f"Do not cite block height {bh.group(1)} (live chain is {live})")

    # 2) Superlative claims: require primary proof, else forbid the word
    for c in claims:
        if c["kind"] == "superlative":
            if has_primary:
                claim_results.append({"claim": c["raw"], "status": "VERIFIED_SECONDARY"})
            else:
                claim_results.append({"claim": c["raw"], "status": "UNVERIFIED"})
                do_not_say.append(f'Do not use "{c["raw"]}" unless a primary source proves it')

    # 3) LLM adversarial pass on the story's factual spine (fact vs inference separation)
    if OPENAI_KEY:
        try:
            import urllib.request as u
            prompt = "You are a HOSTILE fact-checker. Your job is to BREAK this story, not confirm it.\n\n"
            prompt += "TITLE: " + item.get("title","") + "\nSUMMARY: " + item.get("summary","") + "\nSOURCE: " + domain + "\n\n"
            prompt += ("For the main factual claims, separate FACT (directly stated by a primary/named source) "
                       "from INFERENCE (analyst interpretation, projection, implied causation). "
                       "Flag any: motive attribution, unproven causation between two events, "
                       "superlatives without proof, stale numbers, or a single original report dressed up as multiple sources. "
                       'Return ONLY JSON: {"facts":[".."],"inferences":[".."],"red_flags":[".."],'
                       '"do_not_say":[".."],"overall":"VERIFIED_PRIMARY|VERIFIED_SECONDARY|INFERENCE_SUPPORTED|UNVERIFIED|CONTRADICTED"}')
            payload = json.dumps({"model":"gpt-4o","messages":[{"role":"user","content":prompt}],
                                  "max_tokens":400,"temperature":0.1}).encode()
            req = u.Request("https://api.openai.com/v1/chat/completions", data=payload,
                headers={"Authorization":"Bearer "+OPENAI_KEY,"Content-Type":"application/json"})
            resp = json.loads(u.urlopen(req, timeout=30).read().decode())
            content = resp["choices"][0]["message"]["content"]
            j = re.search(r"\{.*\}", content, re.DOTALL)
            if j:
                adv = json.loads(j.group(0))
                item["facts"] = adv.get("facts", [])
                item["inferences"] = adv.get("inferences", [])
                item["red_flags"] = adv.get("red_flags", [])
                do_not_say.extend(adv.get("do_not_say", []))
                llm_status = adv.get("overall", "UNVERIFIED")
            else:
                llm_status = "UNVERIFIED"
        except Exception as ex:
            print("[verify] LLM adversarial failed: " + str(ex))
            llm_status = "UNVERIFIED"
    else:
        llm_status = "SOURCE_BACKED" if src_q >= 0.7 else "UNVERIFIED"

    # 4) Resolve story status — GPT tier ladder separating TRUTH-CONFIDENCE from AUTHORITY-LEVEL.
    #    The question is never "true in the abstract" but "can we say it responsibly, at the
    #    correct attribution level." Reputable outlets on-record => REPORTED_ATTRIBUTED (eligible).
    statuses = [h["status"] for h in hard] + [c["status"] for c in claim_results] + [llm_status]
    src_q = _source_quality(item.get("url",""))
    is_reputable = src_q >= 0.70          # FT, Block, MarketWatch, Ars, CoinDesk, gov, etc.
    is_primary_grade = src_q >= 0.90      # Fed, Treasury, BIS, EIA, mempool (direct)

    if "CONTRADICTED" in statuses:
        story_status = "CONTRADICTED"
    elif is_primary_grade and llm_status in ("VERIFIED_PRIMARY","VERIFIED_SECONDARY"):
        story_status = "VERIFIED_PRIMARY"          # direct from primary source, checkable
    elif is_reputable and llm_status in ("VERIFIED_PRIMARY","VERIFIED_SECONDARY"):
        story_status = "VERIFIED_SECONDARY"        # solid, corroborated reporting
    elif is_reputable:
        story_status = "REPORTED_ATTRIBUTED"       # credible outlet reports it; we attribute
    elif llm_status == "INFERENCE_SUPPORTED":
        story_status = "INFERENCE_SUPPORTED"       # interpretation the source's logic supports
    else:
        story_status = "UNVERIFIED"

    item["verification_status"] = story_status
    item["hard_checks"] = hard
    item["claim_results"] = claim_results
    item["do_not_say"] = list(dict.fromkeys(do_not_say))
    # Writer-eligible tiers (each carries its own required attribution level, enforced by the ladder):
    #   VERIFIED_PRIMARY   -> may state directly
    #   VERIFIED_SECONDARY -> state with normal attribution where useful
    #   REPORTED_ATTRIBUTED-> MUST attribute to the outlet ("The FT reports...")
    #   INFERENCE_SUPPORTED-> MUST hedge ("suggests", "would imply")
    #   UNVERIFIED/CONTRADICTED/STALE -> blocked
    # HARD INVARIANT (2026-08-27): no evidence -> no eligibility. A story whose audit
    # returned zero usable facts/inferences gives the writer only a headline to rewrite.
    usable_claims = len(item.get("facts") or []) + len(item.get("inferences") or [])
    item["usable_claim_count"] = usable_claims
    item["writer_eligible"] = story_status in (
        "VERIFIED_PRIMARY","VERIFIED_SECONDARY","REPORTED_ATTRIBUTED","INFERENCE_SUPPORTED") \
        and usable_claims > 0
    if usable_claims == 0 and story_status not in ("UNVERIFIED","CONTRADICTED","STALE"):
        item.setdefault("red_flags", []).append("EMPTY_EVIDENCE: audit returned no facts/inferences; eligibility forced False")
    item["requires_hedge"] = story_status in ("INFERENCE_SUPPORTED",)
    item["requires_attribution"] = story_status in ("REPORTED_ATTRIBUTED","VERIFIED_SECONDARY")

    # 5) Log rejected claims as a growing hallucination dataset
    if story_status in ("UNVERIFIED","CONTRADICTED","STALE"):
        try:
            with open(REJECTED_CLAIMS_LOG, "a") as f:
                f.write(json.dumps({
                    "ts": datetime.now(timezone.utc).isoformat(),
                    "headline": item.get("title",""),
                    "source": domain,
                    "status": story_status,
                    "claims": item.get("primary_claims", []),
                    "red_flags": item.get("red_flags", []),
                }) + "\n")
        except Exception:
            pass
    return item


# ================= DOMAIN-FIT GATE (runs before expensive scoring) =================
# GPT spec: kill off-topic stories before costly verification/writing.
# PP covers: money, markets, bitcoin/crypto, macro, monetary policy, tech-power,
# energy, financial censorship/sovereignty. NOT: personal finance advice columns,
# lifestyle, sports, celebrity, generic consumer news.

DOMAIN_FIT_KILL = [
    r"\bam i too old\b", r"\broth conversion\b", r"\bshould i (buy|sell|retire)\b",
    r"\bmy (wife|husband|spouse|kids?|401k|ira)\b", r"\bdear (moneyist|abby)\b",
    r"\brecipe\b", r"\bhoroscope\b", r"\bcelebrity\b", r"\bhow to save money on\b",
    r"\bbest (deals?|gifts?)\b", r"\btravel tips\b",
]
DOMAIN_FIT_CORE = [
    "bitcoin","btc","crypto","fed","treasury","inflation","debt","dollar","currency",
    "mining","hashrate","etf","blackrock","monetary","central bank","sovereign","sanction",
    "stablecoin","energy","grid","ai","chip","semiconductor","regulation","sec","tariff",
    "yield","bond","liquidity","banking","default","gold","reserve",
]

def domain_fit_score(item):
    text = (item.get("title","") + " " + item.get("summary","")).lower()
    for pat in DOMAIN_FIT_KILL:
        if re.search(pat, text):
            return 0.0  # hard kill
    hits = sum(1 for kw in DOMAIN_FIT_CORE if kw in text)
    return min(hits / 3.0, 1.0)  # 0 = off-topic, 1 = squarely in domain


def run(top_n=20, extra_items=None):
    print("=== SENSING ===")
    rss = harvest_rss()
    print(f"  RSS harvested: {len(rss)}")
    xai = harvest_xai()
    print(f"  xAI harvested: {len(xai)}")
    extra = extra_items or []   # shadow-mode RSS pool (plumbing only; same item schema)
    all_items = dedup_items(rss + xai + extra)
    # Hard freshness gate: drop anything older than 48h (news must be current)
    now = time.time()
    fresh = [it for it in all_items if 0 <= (now - it["published_ts"]) <= 172800]
    dropped = len(all_items) - len(fresh)
    all_items = fresh
    print(f"  After dedup + 48h freshness gate: {len(all_items)} (dropped {dropped} stale)")

    print("=== DOMAIN-FIT GATE ===")
    before = len(all_items)
    all_items = [it for it in all_items if domain_fit_score(it) > 0.0]
    # Sort by domain-fit so the LLM scores the most on-brand first; keep top 40 to bound cost
    all_items.sort(key=lambda x: domain_fit_score(x), reverse=True)
    all_items = all_items[:60]
    print(f"  Domain-fit: {before} -> {len(all_items)} (killed off-topic + capped at 60)")

    print("=== EVENT CLUSTERING ===")
    before = len(all_items)
    all_items = cluster_events(all_items)
    multi = [it for it in all_items if it.get("report_count", 1) > 1]
    print(f"  {before} items -> {len(all_items)} events ({len(multi)} multi-report; "
          f"syndication collapsed on {sum(1 for it in multi if it['independent_corroboration'] < it['report_count'])})")
    for it in sorted(multi, key=lambda x: -x["report_count"])[:6]:
        print(f"    x{it['report_count']} reports / {it['independent_corroboration']} independent :: {it['title'][:70]}")

    print("=== DETERMINISTIC + LLM SCORING ===")
    all_items = llm_score_batch(all_items)
    for it in all_items:
        compute_overall(it, all_items)

    ranked = sorted(all_items, key=lambda x: x.get("overall_score", 0), reverse=True)[:top_n]

    # Audit each ranked story (claim auditor: internal consistency, fact/inference split)
    for it in ranked:
        adversarial_verify(it)

    # LAYER 3.5: external claim verification on auditor-eligible candidates only (cost ~$0.25/story).
    # External evidence OVERRIDES the auditor. Cap bounds cost; env PP_EXTERNAL_VERIFY=0 disables.
    if os.environ.get("PP_EXTERNAL_VERIFY", "1") == "1":
        from services import claim_verifier
        cap = int(os.environ.get("PP_EXTERNAL_VERIFY_CAP", "10"))
        elig = [it for it in ranked if it.get("writer_eligible")]
        todo, pending = elig[:cap], elig[cap:]
        for it in pending:   # no unverified claim reaches the writer: beyond the cap = not yet eligible
            it["writer_eligible"] = False
            it.setdefault("red_flags", []).append("PENDING_EXTERNAL_VERIFICATION: outside top-%d cap" % cap)
        print(f"=== EXTERNAL VERIFICATION (Layer 3.5) on {len(todo)} eligible ({len(pending)} pending, beyond cap) ===")
        spent = 0.0
        for it in todo:
            try:
                claim_verifier.apply(it)
                ev = it["external_verification"]
                per = ev["cost_usd"] - spent; spent = ev["cost_usd"]; ev["cost_usd_story"] = round(per, 4)
                print(f"  [{ev['overall']:12s}] v/s/c/u {ev['n_verified']}/{ev['n_stale']}/{ev['n_contradicted']}/{ev['n_unverifiable']} ${per:.2f} :: {it['title'][:70]}")
            except Exception as e:
                it["writer_eligible"] = False
                it["verification_status"] = "UNVERIFIED"
                it.setdefault("red_flags", []).append(f"external_verifier_error:{type(e).__name__}")
                print(f"  [VERIFIER ERR ] {type(e).__name__}: {it['title'][:70]}")

    stories = []
    for i, it in enumerate(ranked):
        stories.append({
            "story_id": hashlib.md5(it["title"].encode()).hexdigest()[:10],
            "rank": i + 1,
            "headline": it["title"],
            "domain": it["domain_tag"],
            "summary": it["summary"][:300],
            "why_interesting": it.get("why_interesting", ""),
            "sources": it.get("sources_all") or [it["url"]],
            "report_count": it.get("report_count", 1),
            "independent_corroboration": it.get("independent_corroboration", 1),
            "syndicated_from": it.get("syndicated_from", []),
            "event_key": it.get("event_key"),
            "event_date_hint": it.get("event_date_hint"),
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
            "verification_status": it.get("verification_status", "unverified"),
            "writer_eligible": it.get("writer_eligible", False),
            "external_verification": it.get("external_verification"),
            "underlying_event_ts": it.get("underlying_event_ts"),
            "event_age_hours": it.get("event_age_hours"),
            "usable_claim_count": it.get("usable_claim_count"),
            "requires_hedge": it.get("requires_hedge", True),
            "primary_claims": it.get("primary_claims", []),
            "hard_checks": it.get("hard_checks", []),
            "facts": it.get("facts", []),
            "inferences": it.get("inferences", []),
            "red_flags": it.get("red_flags", []),
            "do_not_say": it.get("do_not_say", []),
        })

    with open(OUT, "w") as f:
        json.dump({"generated_at": datetime.now(timezone.utc).isoformat(),
                   "total_harvested": len(all_items), "stories": stories}, f, indent=2)
    print(f"=== DONE: {len(stories)} ranked stories -> {OUT} ===")
    return stories
    return stories

if __name__ == "__main__":
    run()
