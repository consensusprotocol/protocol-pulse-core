"""
claim_verifier.py — EXTERNAL CLAIM VERIFICATION v1 (Layer 3.5)
================================================================
Scope is deliberately small (2026-08-27, GPT/PBX freeze): exactly four claim types.
  live_market_value        -> authoritative live API (DeFiLlama, mempool, Yahoo)
  quoted_statement         -> find ALL dated instances of the statement; original date = min
  official_document_claim  -> locate the primary document, fetch it, confirm the passage, date it
  reported_fact            -> fetch the cited article, confirm it actually supports the claim
Everything else (motive, causation, prediction, superlative-without-data) -> UNVERIFIABLE, blocked.

Per-claim output: {claim, type, candidate_value, observed_value, observed_at, source_url,
                   original_date, result}   result in VERIFIED | STALE | CONTRADICTED | UNVERIFIED | UNVERIFIABLE
Story-level: external_verification = {claims, overall, underlying_event_ts, fresh, cost_usd}

Principles:
  - Source domain is a prior, not the gate. A claim is VERIFIED only if we observed it.
  - Publication freshness != event freshness. underlying_event_ts is the OLDEST original date
    among the load-bearing claims. > FRESH_WINDOW_H -> story is STALE for posting purposes.
  - The auditor's "facts" list is REPLACED by what actually verified.
"""
import os, re, json, time, html
import urllib.request as u
import urllib.parse as up
from datetime import datetime, timezone, timedelta

OPENAI_KEY = os.environ.get("OPENAI_API_KEY", "")
XAI_KEY = os.environ.get("XAI_API_KEY", "")
UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/124 Safari/537.36"}
FRESH_WINDOW_H = int(os.environ.get("PP_FRESH_WINDOW_H", "72"))
VALUE_TOLERANCE = 0.06          # 6% for live values
MAX_CLAIMS = 8
_COST = {"usd": 0.0}

# ---------------------------------------------------------------- helpers
def _now(): return time.time()

def _gpt(prompt, temp=0.1, max_tokens=900):
    payload = json.dumps({"model": "gpt-4o", "temperature": temp, "max_tokens": max_tokens,
                          "messages": [{"role": "user", "content": prompt}]}).encode()
    req = u.Request("https://api.openai.com/v1/chat/completions", data=payload,
                    headers={"Authorization": "Bearer " + OPENAI_KEY, "Content-Type": "application/json"})
    d = json.loads(u.urlopen(req, timeout=60).read())
    return d["choices"][0]["message"]["content"]

def _json_in(txt):
    m = re.search(r"\{.*\}|\[.*\]", txt, re.S)
    if not m: return None
    try: return json.loads(m.group(0))
    except Exception:
        try: return json.loads(m.group(0).replace("**", ""))
        except Exception: return None

_XAI_LOG = []
def _xai_search(prompt, tools=None, from_date=None, retries=2):
    tools = tools or [{"type": "web_search"}]
    body = {"model": "grok-4.3", "input": prompt, "tools": tools}
    for attempt in range(retries + 1):
        req = u.Request("https://api.x.ai/v1/responses", data=json.dumps(body).encode(),
                        headers={"Authorization": "Bearer " + XAI_KEY, "Content-Type": "application/json"})
        try:
            d = json.loads(u.urlopen(req, timeout=80).read())
        except Exception as e:
            _XAI_LOG.append(f"error:{type(e).__name__}"); time.sleep(3); continue
        _COST["usd"] += d.get("usage", {}).get("cost_in_usd_ticks", 0) / 1e10
        txt = "".join(c.get("text", "") for o in d.get("output", []) for c in o.get("content", []) if isinstance(c, dict))
        if d.get("degraded") or not txt.strip():
            _XAI_LOG.append(f"degraded={d.get('degraded')} empty={not txt.strip()} attempt={attempt}"); time.sleep(3); continue
        return txt
    return ""

def _fetch_text(url, limit=14000):
    try:
        req = u.Request(url, headers=UA)
        raw = u.urlopen(req, timeout=25).read(600000).decode("utf-8", "ignore")
    except Exception as e:
        return None, f"fetch_error:{type(e).__name__}"
    raw = re.sub(r"(?is)<(script|style|noscript|svg).*?</\1>", " ", raw)
    txt = html.unescape(re.sub(r"(?s)<[^>]+>", " ", raw))
    txt = re.sub(r"\s+", " ", txt).strip()
    return txt[:limit], None

def _iso_to_ts(s):
    if not s or not isinstance(s, str): return None
    s = s.strip()
    for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%d %H:%M:%S"):
        try: return datetime.strptime(s[:19], fmt).replace(tzinfo=timezone.utc).timestamp()
        except Exception: pass
    try: return datetime.fromisoformat(s.replace("Z", "+00:00")).timestamp()
    except Exception: return None

def _num(v):
    if v is None: return None
    if isinstance(v, (int, float)): return float(v)
    s = str(v).lower().replace(",", "").replace("$", "").strip()
    m = re.match(r"([\d\.]+)\s*(t|tn|trillion|b|bn|billion|m|mn|million|k)?", s)
    if not m: return None
    x = float(m.group(1)); unit = m.group(2) or ""
    mult = {"t":1e12,"tn":1e12,"trillion":1e12,"b":1e9,"bn":1e9,"billion":1e9,"m":1e6,"mn":1e6,"million":1e6,"k":1e3}.get(unit, 1)
    return x * mult

# ---------------------------------------------------------------- 1) classify
CLASSIFY_PROMPT = """You are a claim classifier for a fact-checking pipeline. Break the text into ATOMIC, checkable claims.
Assign each claim exactly ONE type:
- live_market_value: a current numeric market value (stablecoin supply/market cap, BTC price, block height, gold price, dollar index, yield). Fill metric (one of: stablecoin_supply, btc_price, block_height, gold_price, dxy, other), entity (e.g. USD1), value (number with unit as written), date_claimed (date the value is claimed for, ISO or null).
- quoted_statement: a named person/org said something. Fill actor, gist (one sentence paraphrase of what they said), date_claimed.
- official_document_claim: an official act or document exists (law passed, charter approved, order signed, database deleted, report published by Fed/Treasury/OCC/SEC/Brookings etc). Fill issuer, gist, value (if a number is in the claim), date_claimed.
- reported_fact: a factual event/number that the cited source reports (deal happened, X amount routed, etc). Fill gist, value, date_claimed.
- unverifiable: motive attribution, intent, causation ("because", "so that", "forces"), prediction, hypothetical, "every step has happened", opinion. Fill gist.
Routing rules (strict):
- ANY "$X in circulation / market cap / supply" of a stablecoin or token is live_market_value with metric stablecoin_supply, EVEN IF the text describes the entity obliquely. Resolve oblique descriptions to the well-known entity when unambiguous (e.g. "the president's family's private digital dollar" -> entity USD1, "the Trump-linked stablecoin" -> USD1) and record the resolution in entity.
- ANY number or finding attributed to a named institution's report or study (Brookings, Fed, BIS, IMF, Treasury, GAO, CBO, a bank research note) is official_document_claim with issuer = that institution.
- A law, executive order, charter, rule, or database action is official_document_claim.
Rules: max {maxc} claims, choose the LOAD-BEARING ones. Never merge two claims. Return ONLY a JSON array of objects with keys:
claim, type, metric, entity, actor, issuer, gist, value, date_claimed, threshold_event (true if the claim is that a value CROSSED/SURPASSED/HIT/TOPPED/REACHED a level on a date, false if it is a current level).

TEXT:
{text}
"""

def classify_claims(text):
    out = _gpt(CLASSIFY_PROMPT.format(text=text[:6000], maxc=MAX_CLAIMS), max_tokens=1400)
    arr = _json_in(out) or []
    if not isinstance(arr, list): return []
    ok = []
    for c in arr[:MAX_CLAIMS]:
        if not isinstance(c, dict) or not c.get("claim"): continue
        c["type"] = c.get("type") if c.get("type") in ("live_market_value","quoted_statement","official_document_claim","reported_fact","unverifiable") else "unverifiable"
        cl = c["claim"].lower()
        # deterministic post-pass: the LLM under-routes document claims to "unverifiable"
        if c["type"] == "unverifiable":
            if re.search(r"\b(executive order|signed|passed a law|the act|charter|database|deleted|rule|regulation|report|study|projects?|estimates?)\b", cl):
                c["type"] = "official_document_claim"
            elif re.search(r"\$\s?\d|\d+\s?(billion|million|trillion|%)", cl) and not re.search(r"\b(because|so that|forces?|in order to|wanted|would|toll booth)\b", cl):
                c["type"] = "reported_fact"
        if re.search(r"\b(crossed|surpassed|topped|hit|reached|exceeded)\b", cl): c["threshold_event"] = True
        ok.append(c)
    return ok

# ---------------------------------------------------------------- 2) verifiers
def _defillama_asset(entity):
    d = json.loads(u.urlopen(u.Request("https://stablecoins.llama.fi/stablecoins?includePrices=false", headers=UA), timeout=30).read())
    e = (entity or "").lower().replace(" ", "")
    for a in d.get("peggedAssets", []):
        if e in (a.get("symbol","").lower(), a.get("name","").lower().replace(" ","")):
            return a
    return None

def _defillama_supply(entity):
    a = _defillama_asset(entity)
    if not a: return None, None
    return float(a.get("circulating", {}).get("peggedUSD")), "https://defillama.com/stablecoin/" + a.get("name","").replace(" ","-").lower()

def _defillama_history(entity):
    """[(ts, circulating_usd)] daily, oldest first."""
    a = _defillama_asset(entity)
    if not a: return []
    d = json.loads(u.urlopen(u.Request(f"https://stablecoins.llama.fi/stablecoin/{a['id']}", headers=UA), timeout=30).read())
    pts = []
    for t in d.get("tokens", []):
        v = (t.get("circulating") or {}).get("peggedUSD")
        if v is not None and t.get("date"): pts.append((int(t["date"]), float(v)))
    return sorted(pts)

def _stooq(sym):
    url = f"https://stooq.com/q/l/?s={sym}&f=sd2t2ohlcv&h&e=csv"
    rows = u.urlopen(u.Request(url, headers=UA), timeout=20).read().decode().strip().splitlines()
    return float(rows[1].split(",")[6]), url

def _yahoo(sym):
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{up.quote(sym)}?range=1d&interval=1d"
    d = json.loads(u.urlopen(u.Request(url, headers=UA), timeout=25).read())
    return float(d["chart"]["result"][0]["meta"]["regularMarketPrice"]), url

def verify_live_market_value(c):
    metric = (c.get("metric") or "other").lower(); cand = _num(c.get("value"))
    obs, src = None, None
    try:
        if metric == "stablecoin_supply": obs, src = _defillama_supply(c.get("entity"))
        elif metric == "btc_price":
            d = json.loads(u.urlopen(u.Request("https://mempool.space/api/v1/prices", headers=UA), timeout=20).read()); obs, src = float(d["USD"]), "https://mempool.space/api/v1/prices"
        elif metric == "block_height":
            obs, src = float(u.urlopen(u.Request("https://mempool.space/api/blocks/tip/height", headers=UA), timeout=20).read()), "https://mempool.space/api/blocks/tip/height"
        elif metric == "gold_price":
            try: obs, src = _yahoo("GC=F")
            except Exception: obs, src = None, None
        elif metric == "dxy":
            try: obs, src = _yahoo("DX-Y.NYB")
            except Exception: obs, src = None, None
    except Exception as e:
        return dict(result="UNVERIFIED", note=f"api_error:{type(e).__name__}")
    if obs is None: return dict(result="UNVERIFIED", note="no_authoritative_source_for_metric")
    r = dict(observed_value=obs, observed_at=_now(), source_url=src, candidate_value=cand)
    if c.get("threshold_event") and metric == "stablecoin_supply" and cand:
        hist = _defillama_history(c.get("entity"))
        if hist:
            first_above = next((ts for ts, v in hist if v >= cand), None)
            peak_ts, peak = max(hist, key=lambda x: x[1])
            r["history_first_above"] = datetime.utcfromtimestamp(first_above).strftime("%Y-%m-%d") if first_above else None
            r["history_peak"] = round(peak); r["history_peak_date"] = datetime.utcfromtimestamp(peak_ts).strftime("%Y-%m-%d")
            claimed_ts = _iso_to_ts(c.get("date_claimed"))
            if first_above is None:
                r["result"] = "CONTRADICTED"; r["note"] = f"never reached {cand:,.0f} per DeFiLlama history"; return r
            if claimed_ts and first_above < claimed_ts - 7 * 86400:
                r["result"] = "CONTRADICTED"
                r["note"] = f"not a crossing: first above {cand:,.0f} on {r['history_first_above']}; peak {peak:,.0f} on {r['history_peak_date']}; now {obs:,.0f}"
                return r
            if not claimed_ts and _now() - first_above > FRESH_WINDOW_H * 3600:
                r["result"] = "STALE"; r["note"] = f"crossed {cand:,.0f} on {r['history_first_above']}, not recent"; return r
    if cand is None: r["result"] = "UNVERIFIED"; r["note"] = "no_numeric_candidate"; return r
    dev = abs(obs - cand) / max(obs, 1e-9)
    r["deviation"] = round(dev, 4)
    if dev <= VALUE_TOLERANCE: r["result"] = "VERIFIED"
    else:
        # A number that WAS true at some point but isn't now is STALE, not a lie; we can't
        # prove history here, so anything off by >tolerance is STALE_OR_CONTRADICTED and blocked.
        r["result"] = "CONTRADICTED"; r["note"] = f"live value {obs:,.0f} vs claimed {cand:,.0f} ({dev:.1%} off)"
    return r

QUOTE_PROMPT = """Find EVERY dated public instance of {actor} saying, in substance: "{gist}".
Include interviews, X posts, op-eds, hearings, press releases. Search back several years, not just recent news.
Return ONLY a JSON array, one object per instance, oldest first: {{"date":"YYYY-MM-DD","url":"...","venue":"...","quote":"<=30 words"}}.
If you cannot find any, return []."""

def _snowflake_date(url):
    """X/Twitter status IDs encode creation time: (id >> 22) + 1288834974657 ms. Deterministic, beats any LLM date label."""
    m = re.search(r"(?:x|twitter)\.com/[^/]+/status/(\d{15,20})", url or "")
    if not m: return None
    try:
        ms = (int(m.group(1)) >> 22) + 1288834974657
        return datetime.utcfromtimestamp(ms / 1000).strftime("%Y-%m-%d")
    except Exception: return None

def verify_quoted_statement(c):
    actor, gist = c.get("actor") or "", c.get("gist") or c.get("claim")
    txt = _xai_search(QUOTE_PROMPT.format(actor=actor, gist=gist), tools=[{"type": "web_search"}, {"type": "x_search"}])
    arr = _json_in(txt) or []
    inst = [x for x in arr if isinstance(x, dict) and _iso_to_ts(x.get("date"))] if isinstance(arr, list) else []
    # Second pass anchored in the past: recent coverage dominates search rank, so ask
    # explicitly for the EARLIEST instances and exclude the last 30 days.
    cutoff = (datetime.now(timezone.utc) - timedelta(days=30)).strftime("%Y-%m-%d")
    p2 = (f'List every dated instance before {cutoff} where {actor} said this or its substance: "{gist}" (interviews, hearings, X posts, press releases, one-pagers). '
          'Match the SUBSTANCE, not the exact wording: drop adjectives and framing. For example if the gist says "structural demand for Treasuries", '
          'an earlier instance saying "increase demand for Treasuries" or "extend demand for U.S. Treasuries" COUNTS. '
          'Return ONLY a JSON array [{"date":"YYYY-MM-DD","url":"...","venue":"...","quote":"<=25 words"}].')
    txt2, arr2 = "", []
    for attempt in range(3):   # an empty array from the history pass is usually a quiet tool failure, not proof of absence
        txt2 = _xai_search(p2, tools=[{"type": "x_search", "to_date": cutoff, "from_date": "2023-01-01"}, {"type": "web_search"}])
        arr2 = _json_in(txt2) or []
        if isinstance(arr2, list) and arr2: break
        time.sleep(4)
    inst2 = [x for x in arr2 if isinstance(x, dict) and _iso_to_ts(x.get("date"))] if isinstance(arr2, list) else []
    inst += inst2
    _dbg = {"pass1_n": len(inst) - len(inst2), "pass2_n": len(inst2), "pass2_head": txt2[:160], "p2": p2, "cutoff": cutoff}
    if not inst: return dict(result="UNVERIFIED", note="no_dated_instance_found", search_debug=_dbg)
    for x in inst:
        sf = _snowflake_date(x.get("url"))
        if sf and sf != x.get("date"): x["date_llm"] = x["date"]; x["date"] = sf; x["date_source"] = "snowflake"
    inst.sort(key=lambda x: _iso_to_ts(x["date"]))
    orig, latest = inst[0], inst[-1]
    r = dict(result="VERIFIED", original_date=orig["date"], original_url=orig.get("url"), search_debug=_dbg,
             latest_date=latest["date"], latest_url=latest.get("url"), instances=len(inst),
             observed_value=orig.get("quote"), observed_at=_now(), source_url=orig.get("url"))
    if _now() - _iso_to_ts(orig["date"]) > FRESH_WINDOW_H * 3600:
        r["result"] = "STALE"; r["note"] = f"original statement {orig['date']}; recent instance {latest['date']} is a restatement"
    return r

DOC_PROMPT = """Locate the PRIMARY official document or announcement for this claim: "{claim}" (issuer: {issuer}).
Prefer .gov, the issuer's own site, congress.gov, federalregister.gov, or the publishing institution (e.g. brookings.edu).
Return ONLY JSON: {{"url":"...","published_date":"YYYY-MM-DD","title":"...","supporting_passage":"<=60 words verbatim","supports":true|false,"nuance":"<=30 words on any caveat/range/condition the document adds"}}"""

def verify_official_document_claim(c):
    txt = _xai_search(DOC_PROMPT.format(claim=c.get("claim"), issuer=c.get("issuer") or "unknown"))
    d = _json_in(txt)
    if not isinstance(d, dict) or not str(d.get("url","")).startswith("http"): return dict(result="UNVERIFIED", note="no_primary_document_found")
    r = dict(source_url=d["url"], original_date=d.get("published_date"), observed_value=d.get("supporting_passage"),
             nuance=d.get("nuance"), observed_at=_now(), title=d.get("title"))
    # independent confirmation: fetch and let gpt-4o judge the actual page, not Grok's summary
    page, err = _fetch_text(d["url"])
    if page:
        j = _json_in(_gpt(f'Evaluate the claim "{c.get("claim")}" against this document. verdict must be one of: "supports" (document states it), "contradicts" (document states something incompatible, e.g. a different number or the opposite), "absent" (document does not address it, or the relevant content is missing from this text). Answer ONLY JSON {{"verdict":"supports|contradicts|absent","date_in_doc":"YYYY-MM-DD or null","passage":"<=40 words verbatim or null","nuance":"<=30 words on caveats/ranges the document adds, or null"}}.\n\nDOCUMENT:\n{page[:9000]}', max_tokens=300)) or {}
        r["fetched"] = True
        if j.get("date_in_doc"): r["original_date"] = j["date_in_doc"]
        if j.get("passage"): r["observed_value"] = j["passage"]
        if j.get("nuance"): r["nuance"] = j["nuance"]
        verdict = j.get("verdict", "absent")
    else:
        r["fetched"] = False; r["fetch_note"] = err; verdict = "supports" if d.get("supports") else "absent"
    if verdict == "contradicts": r["result"] = "CONTRADICTED"; r["note"] = "primary document contradicts claim as stated"; return r
    if verdict != "supports": r["result"] = "UNVERIFIED"; r["note"] = "document found but does not contain the claim (or page text unavailable)"; return r
    r["result"] = "VERIFIED"
    ts = _iso_to_ts(r.get("original_date"))
    if ts and _now() - ts > FRESH_WINDOW_H * 3600: r["result"] = "STALE"; r["note"] = f"event dated {r['original_date']}"
    return r

REPORT_PROMPT = """Find a reputable news report or primary source that directly states this: "{claim}".
Prefer wire services, major outlets, or the primary institution. Return ONLY JSON:
{{"url":"...","published_date":"YYYY-MM-DD","event_date":"YYYY-MM-DD or null","outlet":"..."}} or {{}} if none."""

def verify_reported_fact(c, story_url):
    social = (not story_url) or ("x.com" in story_url) or ("twitter.com" in story_url)
    page, err, found = None, None, None
    if not social:
        page, err = _fetch_text(story_url)
    if not page:
        d = _json_in(_xai_search(REPORT_PROMPT.format(claim=c.get("claim")))) or {}
        if isinstance(d, dict) and d.get("url"):
            found = d; story_url = d["url"]; page, err = _fetch_text(story_url)
        if not page: return dict(result="UNVERIFIED", note=("no report found" if not found else err), source_url=story_url)
    j = _json_in(_gpt(f'Evaluate the claim "{c.get("claim")}" against this article. verdict: "supports" (article states it), "contradicts" (article states something incompatible), "absent" (not addressed / text missing). Do not infer. Answer ONLY JSON {{"verdict":"supports|contradicts|absent","passage":"<=40 words verbatim or null","article_date":"YYYY-MM-DD or null","event_date":"YYYY-MM-DD or null (date of the underlying event if given)"}}.\n\nARTICLE:\n{page[:9000]}', max_tokens=300)) or {}
    r = dict(source_url=story_url, observed_value=j.get("passage"), observed_at=_now(),
             original_date=j.get("event_date") or j.get("article_date") or (found or {}).get("event_date") or (found or {}).get("published_date"),
             article_date=j.get("article_date") or (found or {}).get("published_date"))
    if j.get("verdict") == "contradicts": r["result"] = "CONTRADICTED"; r["note"] = "cited article contradicts the claim"; return r
    if j.get("verdict") != "supports": r["result"] = "UNVERIFIED"; r["note"] = "article does not contain the claim (or text unavailable)"; return r
    r["result"] = "VERIFIED"
    ts = _iso_to_ts(r.get("original_date"))
    if ts and _now() - ts > FRESH_WINDOW_H * 3600: r["result"] = "STALE"; r["note"] = f"underlying event {r['original_date']}"
    return r

# ---------------------------------------------------------------- 3) orchestrate
def verify_story(story, text=None):
    text = text or (story.get("title", "") + ". " + story.get("summary", ""))
    claims = classify_claims(text)
    results = []
    for c in claims:
        t = c["type"]
        try:
            if t == "live_market_value": r = verify_live_market_value(c)
            elif t == "quoted_statement": r = verify_quoted_statement(c)
            elif t == "official_document_claim": r = verify_official_document_claim(c)
            elif t == "reported_fact": r = verify_reported_fact(c, story.get("url"))
            else: r = dict(result="UNVERIFIABLE", note="motive/causation/prediction/opinion")
        except Exception as e:
            r = dict(result="UNVERIFIED", note=f"verifier_error:{type(e).__name__}:{str(e)[:80]}")
        r.update(claim=c.get("claim"), type=t)
        if "candidate_value" not in r: r["candidate_value"] = c.get("value")
        results.append(r)

    verified = [r for r in results if r["result"] == "VERIFIED"]
    stale = [r for r in results if r["result"] == "STALE"]
    contradicted = [r for r in results if r["result"] == "CONTRADICTED"]
    checkable = [r for r in results if r["type"] != "unverifiable"]
    dates = [_iso_to_ts(r.get("original_date")) for r in verified + stale if r.get("original_date")]
    underlying = min([d for d in dates if d], default=None)
    fresh_claims = [r for r in verified if not r.get("original_date") or _now() - (_iso_to_ts(r["original_date"]) or _now()) <= FRESH_WINDOW_H * 3600]

    if contradicted: overall = "CONTRADICTED"
    elif not checkable: overall = "UNVERIFIABLE"
    elif verified and fresh_claims: overall = "VERIFIED"
    elif verified or stale: overall = "STALE"
    else: overall = "UNVERIFIED"

    return dict(claims=results, overall=overall, underlying_event_ts=underlying,
                fresh=bool(fresh_claims), n_verified=len(verified), n_stale=len(stale),
                n_contradicted=len(contradicted), n_unverifiable=len(results) - len(checkable),
                cost_usd=round(_COST["usd"], 4), verified_at=_now(), xai_log=list(_XAI_LOG))

def apply(item, text=None):
    """Mutates a story_engine item after the claim auditor. External evidence overrides the auditor."""
    ev = verify_story(item, text)
    item["external_verification"] = ev
    ov = ev["overall"]
    # facts become ONLY what we observed; stale facts move to do-not-say-as-fresh
    item["auditor_facts"] = item.get("facts", [])
    item["facts"] = [f"{r['claim']} [observed: {str(r.get('observed_value'))[:80]} | {r.get('source_url','')}]"
                     for r in ev["claims"] if r["result"] == "VERIFIED"]
    dns = item.get("do_not_say", []) or []
    for r in ev["claims"]:
        if r["result"] == "CONTRADICTED": dns.append(f"{r['claim']} ({r.get('note','contradicted')})")
        elif r["result"] == "STALE": dns.append(f"Do not present as new: {r['claim']} ({r.get('note','')})")
        elif r["result"] == "UNVERIFIABLE": dns.append(f"Unverifiable: {r['claim']}")
    item["do_not_say"] = list(dict.fromkeys(dns))
    if ov == "CONTRADICTED":
        item["verification_status"] = "CONTRADICTED"; item["writer_eligible"] = False
    elif ov == "STALE":
        item["verification_status"] = "STALE"; item["writer_eligible"] = False
    elif ov in ("UNVERIFIED", "UNVERIFIABLE"):
        item["verification_status"] = "UNVERIFIED"; item["writer_eligible"] = False
    else:  # VERIFIED
        item["verification_status"] = "VERIFIED_PRIMARY" if ev["n_verified"] >= 2 else "VERIFIED_SECONDARY"
        item["writer_eligible"] = len(item["facts"]) > 0
    item["usable_claim_count"] = len(item["facts"]) + len(item.get("inferences", []) or [])
    if ev["underlying_event_ts"]:
        item["underlying_event_ts"] = ev["underlying_event_ts"]
        item["event_age_hours"] = round((_now() - ev["underlying_event_ts"]) / 3600, 1)
    return item
