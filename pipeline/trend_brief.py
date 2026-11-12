#!/usr/bin/env python3
"""pipeline/trend_brief.py — what is hot right now, as a RANKING input only (orchestrator Phase 2 addition '01:55';
law L-w 4, '02:30'). Trend is never a gate and never a fact source.

- TAXONOMY: a closed list of Bitcoin topic ids, each with our own fixed label and a keyword pattern. Every trend signal
  is forced into it; anything else is discarded.
- local_baseline(): the free signal from our own corpus. For each topic, the share of partner channels (last 24 h)
  with a Bitcoin sentence on that topic. Always available; no model, no network.
- grok_brief(): ONE live-search call per cycle (role "trend_brief" through pipeline/providers.py: xAI's Responses API
  with x_search + web_search). It asks for 8-12 Bitcoin-only topics with heat 0-1 and rising / fading / steady.
  - The reply is validated into the taxonomy (strict, never repaired). Raw post text never enters any prompt: only
    (topic id, heat, direction, source count) leave this module, and person names only as a list the packager may use
    to boost a moment whose verified SPEAKER is that person.
  - Cached per cycle (cycle id + timestamp + sha256 of the reply).
  - On any failure: no boost, and the cycle says so.
- SHADOW (law L-w 4): moments.TREND_WEIGHT is 0. The brief is logged and compared with the baseline, never used to
  rank, until it measurably helps. When enabled, the weight is capped at ~10-15 % of a moment's score. Titles never
  take trend phrasing: they use our taxonomy labels at most (law L-t: every word of a title must be supported by the
  clips).
"""
import hashlib
import json
import os
import re
import time

import eligibility as E

TAXONOMY = {   # id: (our own label, pattern over a sentence that names Bitcoin)
    "price_action": ("Bitcoin's price move", r"\b(price|all[- ]time high|support|resistance|pullback|sell[- ]?off|rally|"
                                             r"dump|pump|correction|drawdown|breakout|\$\d)"),
    "etf_flows": ("Bitcoin ETF flows", r"\b(etfs?|inflows?|outflows?|ibit|blackrock|fidelity|grayscale)\b"),
    "treasury_companies": ("Bitcoin treasury companies", r"\b(strategy|microstrategy|saylor|treasury compan|metaplanet|"
                                                         r"balance sheet|mnav|cost basis)"),
    "us_policy": ("US Bitcoin policy", r"\b(strategic (bitcoin )?reserve|congress|senate|house|bill|sec\b|regulat|"
                                       r"executive order|white house|legislation)"),
    "macro_fed": ("rates, the Fed and the dollar", r"\b(fed\b|federal reserve|rate cuts?|interest rates?|inflation|cpi|"
                                                   r"powell|dollar|yields?|liquidity|m2)\b"),
    "mining": ("Bitcoin mining", r"\b(miners?|mining|hash ?rate|difficulty|hashprice|halving)\b"),
    "onchain": ("on-chain signals", r"\b(on[- ]chain|whales?|long[- ]term holders?|short[- ]term holders?|"
                                     r"exchange reserves?|realized price)\b"),
    "derivatives_leverage": ("leverage and liquidations", r"\b(leverage|liquidat\w*|futures|options|open interest|"
                                                          r"funding rates?)\b"),
    "institutional_adoption": ("institutions and Bitcoin", r"\b(banks?|institution\w*|vanguard|jpmorgan|goldman|"
                                                           r"pensions?|wall street|custod\w*)\b"),
    "sovereign_adoption": ("countries and Bitcoin", r"\b(el salvador|bhutan|nation[- ]states?|countr(y|ies)|sovereign)\b"),
    "protocol_dev": ("Bitcoin development", r"\b(bitcoin core|knots|op_return|soft fork|covenants?|taproot|lightning|"
                                             r"nodes?)\b"),
    "security_custody": ("self-custody and security", r"\b(self[- ]custody|cold storage|seed phrase|hacks?|exploit|"
                                                       r"private keys?)\b"),
    "quantum": ("quantum computing and Bitcoin", r"\bquantum\b"),
    "elections_politics": ("elections and Bitcoin", r"\b(elections?|midterms?|democrats?|republicans?|votes?|campaign)\b"),
    "market_sentiment": ("market sentiment", r"\b(fear|greed|capitulat\w*|sentiment|bear market|bull market|cycle|"
                                             r"bottom|top)\b"),
    "stocks_correlation": ("Bitcoin and stocks", r"\b(nasdaq|s&p|stocks?|equities|tech stocks|nvidia|correlat\w*)"),
    "gold_comparison": ("Bitcoin and gold", r"\bgold\b"),
    "payments_adoption": ("Bitcoin as money", r"\b(payments?|merchants?|pay with|spend(ing)?|everyday use)\b"),
}
TOPICS = tuple(TAXONOMY)
_PAT = {t: re.compile(p, re.I) for t, (_, p) in TAXONOMY.items()}
DIRECTIONS = ("rising", "fading", "steady")
BRIEF_MAX_TOKENS = 5000            # < 6k out (token discipline, Phase 2 addition)


def label(topic):
    return TAXONOMY[topic][0]


def topics_of(text):
    """Taxonomy ids whose pattern a Bitcoin-naming text matches (the free local classifier)."""
    if not E.names_bitcoin(text):
        return []
    return [t for t in TOPICS if _PAT[t].search(text)]


def local_baseline(sources, ctx, hours=24.0):
    """{topic: heat 0-1}: the share of the window's partner channels with a Bitcoin sentence on that topic; plus the
    channel counts. Free, deterministic, always available (law L-w 4's baseline)."""
    by_topic, channels = {t: set() for t in TOPICS}, set()
    for src in sources:
        age = E.age_hours(src.published_at, ctx.now)
        if age is None or age > hours or age < 0:
            continue
        channels.add(src.channel_id)
        for a, b in src.sentences:
            for t in topics_of(E.spoken(src.tokens[a:b + 1])):
                by_topic[t].add(src.channel_id)
    n = max(1, len(channels))
    return {"topics": {t: round(len(c) / n, 3) for t, c in by_topic.items() if c},
            "channels": {t: len(c) for t, c in by_topic.items() if c}, "window_channels": len(channels),
            "hours": hours}


BRIEF_PROMPT = """Search X and the web now ({now} UTC) for what Bitcoin-focused accounts and outlets are talking about
in the last 24 hours. Bitcoin only: ignore altcoins, memecoins and general politics unless it is about Bitcoin policy.
Classify what you find into these topic ids ONLY (anything else is discarded): {topics}.
Return 8 to 12 topics. For each: "topic" (an id from the list), "heat" (0 to 1: how much attention it has now),
"direction" ("rising", "fading" or "steady"), "sources" (how many distinct posts or articles you saw on it, an integer).
Also "persons": at most 5 names of people at the centre of today's Bitcoin conversation (names only).
Do not include quotes, post text, links or opinions.
Return ONLY this JSON object: {{"topics": [{{"topic": "...", "heat": 0.0, "direction": "...", "sources": 0}}],
"persons": []}}"""


def check_brief(obj):
    """Strict validation into the closed taxonomy (never repaired): -> {topic: {heat, direction, sources}}, persons."""
    if not isinstance(obj, dict) or set(obj) != {"topics", "persons"}:
        raise ValueError("keys must be exactly ['topics', 'persons']")
    ts = obj["topics"]
    if not isinstance(ts, list) or not 1 <= len(ts) <= 12:
        raise ValueError("'topics' must hold 1-12 items")
    out = {}
    for t in ts:
        if not isinstance(t, dict) or set(t) != {"topic", "heat", "direction", "sources"}:
            raise ValueError("each topic needs exactly topic, heat, direction, sources")
        if t["topic"] not in TAXONOMY or t["topic"] in out:
            raise ValueError(f"topic {t['topic']!r} not in the taxonomy or repeated")
        if type(t["heat"]) not in (int, float) or not 0 <= t["heat"] <= 1 or t["direction"] not in DIRECTIONS or \
                type(t["sources"]) is not int or t["sources"] < 0:
            raise ValueError(f"topic {t['topic']}: heat 0-1, direction {DIRECTIONS}, sources an integer")
        out[t["topic"]] = {"heat": float(t["heat"]), "direction": t["direction"], "sources": t["sources"]}
    ps = obj["persons"]
    if not isinstance(ps, list) or len(ps) > 5 or any(not isinstance(p, str) or not 2 <= len(p) <= 60 or
                                                      not re.fullmatch(r"[A-Za-z][A-Za-z .'\-]+", p) for p in ps):
        raise ValueError("'persons' must be at most 5 plain names")
    return out, list(ps)


def cycle_id(now, hours=4):
    """A cycle is a 4 h slot of the UTC day (one call per cycle; law L-p cadence 3-5 h)."""
    return f"{now.strftime('%Y%m%d')}T{now.hour // hours * hours:02d}"


def grok_brief(router, now, cache_dir, log=print):
    """ONE live-search call per cycle, cached when it succeeded; -> {"status", "topics", "persons", "cycle", "backend",
    "sha256", ...}. Failure (no back-end, invalid reply) -> status "failed" and NO boost (trend is never a gate); a
    failure is not cached, so the next run of the cycle asks again."""
    import providers as P
    cyc = cycle_id(now)
    path = os.path.join(cache_dir, f"brief_{cyc}.json")
    if os.path.exists(path):
        with open(path) as f:
            return dict(json.load(f), cached=True)
    prompt = BRIEF_PROMPT.format(now=now.strftime("%Y-%m-%d %H:%M"), topics=", ".join(TOPICS))
    rec = {"cycle": cyc, "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "mode": "shadow (weight 0)"}
    try:
        r = router.call("trend_brief", prompt, BRIEF_MAX_TOKENS, seed=7)
        raw = r.text.strip()
        rec.update(backend=r.backend, usd=r.usd, usage=r.usage, sha256=hashlib.sha256(raw.encode()).hexdigest())
        topics, persons = check_brief(json.loads(raw))        # exactly one JSON object: prose is never repaired
        rec.update(status="ok", topics=topics, persons=persons)
    except (P.ProviderError, P.SpendLimit, ValueError, KeyError) as e:
        rec.update(status="failed", why=f"{type(e).__name__}: {str(e)[:200]}", topics={}, persons=[])
        log(f"  trend brief: no boost this cycle ({rec['why']})")
    if rec.get("status") == "ok":                             # a failed brief is never cached (audit p2 U13)
        os.makedirs(cache_dir, exist_ok=True)
        with open(path, "w") as f:
            json.dump(rec, f, indent=1)
    return rec


def trend_match(moment, brief, baseline=None):
    """The local trend-match axis (no model call): the hottest brief topic among the moment's topics (0 when the brief
    failed); person-trends only for a moment whose VERIFIED speaker is that person (law L-w 4)."""
    heat = max([((brief or {}).get("topics") or {}).get(t, {}).get("heat", 0.0) for t in moment.get("topics") or []]
               or [0.0])
    sp = (moment.get("speaker") or {}).get("named")
    if sp and sp in ((brief or {}).get("persons") or []) and (moment.get("speaker") or {}).get("named_source"):
        heat = max(heat, 0.5)
    base = max([((baseline or {}).get("topics") or {}).get(t, 0.0) for t in moment.get("topics") or []] or [0.0])
    return {"brief": round(heat, 3), "baseline": round(base, 3)}
