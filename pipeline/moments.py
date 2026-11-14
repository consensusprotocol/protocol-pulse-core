#!/usr/bin/env python3
"""pipeline/moments.py — STEP 1 MINE (law L-q, orchestrator 2026-11-12 '01:55'): the cycle's best MOMENTS, by sentence id,
never rewritten. A moment is 1-3 consecutive whole sentences of ONE source record that makes sense heard on its own.

1 LOCAL PRE-FILTER (free, deterministic, no model): sources of the window (published since the last cycle, plus the
  recent window RECENT_H, inside the 72 h universe; opted-out channels never: pipeline/optout.json), eligible as
  sources (partner, identity, upload, current); rows = punctuated, injection-free sentences within one sentence of a
  sentence that names Bitcoin; an ad read (sponsor markers) is never offered; rows are taken round-robin across videos,
  word-timed and on-screen-capable videos first, inside the model's context budget (one call per chunk).
2 ONE BATCHED MINING PASS (role "mine" through pipeline/providers.py, law L-x: local gemma first): the model sees
  numbered rows and answers ids only: {"moments": [{"range": [a, b], "scores": {7 axes, ints 0-5}, "names_person",
  "risk": [enum], "topics": [taxonomy ids], "reason"}]}. The REPLY contract is strict and never repaired (law L-l):
  exact keys, integer scores, closed enums, ranges of existing consecutive ids of one video, no overlap; anything else
  is rejected and asked again with the reason. Each accepted moment is then judged on its own by eligibility (a
  moment is its own statement): failures are recorded on the moment (excluded from packaging), never edited.
3 DETERMINISTIC RANKING (law L-u): hook_first_2s + quotable + surprising_fact + stance + stakes + stands_alone
  - 2 x contempt_outrage - soft-risk penalties + trend weight x trend match (SHADOW: weight 0, law L-w 4); "named
  figure" is a fact, never a positive axis; hard-exclusion risks never rank. Ties by moment_id.

Durations come from locked word timing (timing "word"); a caption / segment duration is only a FLAGGED estimate
(duration_estimate_s) and never feeds a runtime. The model's `reason` is forensic only: it never enters a prompt or
anything audience-facing. Output records follow the contract published in docs/audits/parallel/pp-selectid_STATE.md
(pp.moment/1).
"""
import hashlib
import json
import os
import re
import time
from dataclasses import replace

import eligibility as E
import select_by_id as SB
import sentence_law

HERE = os.path.dirname(os.path.abspath(__file__))
RECENT_H = 24.0                    # "plus a recent window": the last 24 h, beside what is new since the last cycle
MAX_MOMENTS_PER_CALL = 12
MINE_MAX_TOKENS = 3000
ATTEMPTS = 3
AXES = ("hook_first_2s", "quotable", "surprising_fact", "stance", "stakes", "stands_alone", "contempt_outrage")
POSITIVE = AXES[:6]
HARD_RISKS = ("accusation", "partner_attack", "imperative", "guaranteed_return", "single_source_breaking", "ad_read",
              "third_party_media")                                  # law L-u: never auto-selected
SOFT_RISKS = {"price_prediction": 2, "doom": 2, "politics_non_btc": 3, "time_sensitive": 0}   # down-weights (L-u)
RISKS = HARD_RISKS + tuple(SOFT_RISKS)
CONTEMPT_WEIGHT = 2                # contempt / outrage is a PENALTY (law L-u)
TREND_WEIGHT = 0.0                 # SHADOW (law L-w 4): logged, zero weight; when enabled, capped at ~10-15 % of score
REASON_MAX = 200
AD_MARKERS = re.compile(r"\b(sponsor(ed)?|brought to you by|use (my |our )?code|promo code|link in the description|"
                        r"affiliate link|today's sponsor|check out .{0,30}(dot com|\.com))\b", re.I)
OPTOUT = os.path.join(HERE, "optout.json")


class Rejected(SB.Rejected):
    pass


def optout_ids(path=OPTOUT):
    """The opt-out registry (PBX 02:35: no outreach; a simple file the selector honours): channel ids never mined or
    packaged. A missing file = nobody opted out; an unreadable one fails closed (raises)."""
    if not os.path.exists(path):
        return frozenset()
    with open(path) as f:
        d = json.load(f)
    ids = d.get("channel_ids") if isinstance(d, dict) else None
    if not isinstance(ids, list) or not all(isinstance(x, str) for x in ids):
        raise ValueError(f"{path}: expected {{'channel_ids': [str, ...]}}")
    return frozenset(ids)


def moment_id(src, w0, w1):
    return hashlib.sha256(f"{src.video_id}|{src.transcript_sha256}|{w0}|{w1}".encode()).hexdigest()[:20]


# ── 1 local pre-filter ──

def window_sources(sources, ctx, since=None, recent_h=RECENT_H, optout=frozenset()):
    """The cycle's sources: published since `since` (an aware datetime: new since the last cycle) or inside the recent
    window, eligible as sources, not opted out; on-screen-capable (word-timed, sentence-ready, layout-eligible) first,
    then newest first. Returns (sources, {video_id: why not})."""
    keep, skipped = [], {}
    for src in sources:
        if src.channel_id in optout:
            skipped[src.video_id] = "opted out (pipeline/optout.json)"
            continue
        r = E.eligible(src, replace(ctx, role="evidence"))
        if not r.ok:
            skipped[src.video_id] = r.why()
            continue
        age = r.facts.get("age_h")
        new = since is not None and E._parse_time(src.published_at) is not None and E._parse_time(src.published_at) >= since
        if not (new or (age is not None and age <= recent_h)):
            skipped[src.video_id] = (f"outside the window ({'?' if age is None else f'{age:.1f}'} h old, not new since "
                                     f"the last cycle)")
            continue
        keep.append(src)
    on = lambda s: (s.timing == "word" and E.sentence_ready(s) and E.layout_ok(ctx.channel(s.channel_id)))
    keep.sort(key=lambda s: (not on(s), E.age_hours(s.published_at, ctx.now) or 1e9, s.video_id))
    return keep, skipped


def candidate_rows(src):
    """Sentence indices of one source worth offering: punctuated, injection-free, not an ad read, within one sentence
    of a sentence that names Bitcoin (a range of 1-3 sentences can then name it)."""
    import story_semantics as sm
    S, T = src.sentences, src.tokens
    text = [E.spoken(T[a:b + 1]) for a, b in S]
    btc = [E.names_bitcoin(t) for t in text]
    rows = []
    for k, (a, b) in enumerate(S):
        if not any(btc[max(0, k - 1):k + 2]):
            continue
        if AD_MARKERS.search(text[k]) or sm.injection_markers(text[k]):
            continue
        if not (E.ends_statement(T[b].get("word")) or (T[b].get("word") or "").rstrip().endswith("?")):
            continue
        if not all(sentence_law.is_punctuated(T, i) for i in ([a - 1] if a > 0 else []) + [b]):
            continue
        rows.append(k)
    return rows


def tables(sources, ctx, budget_chars):
    """Round-robin over the sources (no video crowds out the others) into Tables of at most budget_chars of row text."""
    per = [(s, candidate_rows(s)) for s in sources]
    order, i = [], 0
    while any(i < len(ks) for _, ks in per):
        for s, ks in per:
            if i < len(ks):
                order.append((s, ks[i]))
        i += 1
    chunks, cur, used = [], [], 0
    for s, k in order:
        cost = len(SB._q(E.Span(s, k, k).text, 600)) + 40
        if cur and used + cost > budget_chars:
            chunks.append(cur)
            cur, used = [], 0
        cur.append((s, k))
        used += cost
    if cur:
        chunks.append(cur)
    out = []
    for ch in chunks:                                  # each table: its sources' rows in sentence order
        srcs = list(dict.fromkeys(s for s, _ in ch))
        items = [(s, k, False) for s in srcs for k in sorted(k for t, k in ch if t is s)]
        out.append(SB.Table(items))
    return out


# ── 2 the mining call ──

MINE_PROMPT = """You pick MOMENTS for 60-second Bitcoin videos built from other channels' own words: the lines a viewer
would stop scrolling for. Below are numbered sentences, transcribed word for word, from recent videos (one block per
video). Today is {today}.

{note}
<sentences>
{rows}
</sentences>

A moment is a range [first id, last id] of 1 to 3 consecutive sentences of ONE video that makes sense heard with
nothing before it, states something (not a question) and names Bitcoin.
For each moment give:
- "scores", integers 0-5: "hook_first_2s" (do its first words grab attention), "quotable", "surprising_fact" (a
  surprising number or fact), "stance" (a clear opinion), "stakes" (why it matters, emotion), "stands_alone" (clear
  without any context), "contempt_outrage" (contempt or outrage: counted AGAINST the moment)
- "names_person": true if it names a person
- "risk": every one that applies, from: {risks}
  (accusation = crime, fraud, insolvency or dishonesty alleged against a named person or company; partner_attack = one
  channel attacking another; imperative = telling the viewer to buy, sell or use leverage; ad_read = a sponsor or ad;
  third_party_media = someone else's clip being played; time_sensitive = 'today', 'just', or a price level that dates)
- "topics": one to three, from: {topics}
- "reason": why it works, at most 20 words (internal note; never shown to anyone)
Return at most {n} moments, best first, never two that overlap. Use ids only; never rewrite a sentence.
If nothing qualifies, answer {{"moments": []}}.
Return ONLY this JSON object: {{"moments": [{{"range": [first, last], "scores": {{...}}, "names_person": false,
"risk": [], "topics": [], "reason": "..."}}]}}"""


def mine_prompt(table, ctx, topics, n=MAX_MOMENTS_PER_CALL):
    return MINE_PROMPT.format(today=ctx.now.strftime("%Y-%m-%d"), note=SB.UNTRUSTED, rows=_rows(table, ctx),
                              risks=", ".join(RISKS), topics=", ".join(topics), n=n)


def _rows(table, ctx):
    out, cur, prev = [], None, None
    for r in table.rows:
        if prev is not None and r.source is prev.source and r.k != prev.k + 1:
            out.append("   ... (sentences not shown here: a range never crosses this line)")
        prev = r
        if r.source is not cur:
            cur = r.source
            reg = ctx.channel(cur.channel_id) or {}
            age = E.age_hours(cur.published_at, ctx.now)
            out.append(f"== {reg.get('display_name') or cur.channel_name} | published "
                       f"{'?' if age is None else f'{age:.0f} h'} ago | \"{SB._q(cur.title or '', 120)}\"")
        sp = r.span
        dur = f"{sp.end - sp.start:4.1f} s" if cur.timing == "word" else "  ?  s"
        out.append(f"{r.n} | {SB._mmss(sp.start)} | {dur} | {SB._q(sp.text, 600)}")
    return "\n".join(out)


def check_moments(obj, table, topics, n=MAX_MOMENTS_PER_CALL):
    """The reply contract (rejected, never repaired) -> [(span, fields)]. {"moments": []} is a valid empty answer."""
    SB._keys(obj, ("moments",))
    ms = obj["moments"]
    if not isinstance(ms, list) or len(ms) > n:
        raise Rejected(f"'moments' must be a list of at most {n}")
    out, used = [], {}
    for i, m in enumerate(ms):
        what = f"moment {i + 1}"
        if not isinstance(m, dict):
            raise Rejected(f"{what} is not an object")
        SB._keys(m, ("range", "scores", "names_person", "risk", "topics", "reason"))
        sp = SB._range(m["range"], table, what)
        for k in range(sp.k0, sp.k1 + 1):
            if (sp.source.video_id, k) in used:
                raise Rejected(f"{what} overlaps {used[(sp.source.video_id, k)]}")
            used[(sp.source.video_id, k)] = what
        sc = m["scores"]
        if not isinstance(sc, dict) or set(sc) != set(AXES):
            raise Rejected(f"{what}: 'scores' must have exactly {list(AXES)}")
        for a in AXES:
            if type(sc[a]) is not int or not 0 <= sc[a] <= 5:
                raise Rejected(f"{what}: score {a} must be an integer 0-5")
        if type(m["names_person"]) is not bool:
            raise Rejected(f"{what}: 'names_person' must be true or false")
        for key, allowed, lo, hi in (("risk", RISKS, 0, len(RISKS)), ("topics", topics, 1, 3)):
            v = m[key]
            if not isinstance(v, list) or not lo <= len(v) <= hi or len(set(v)) != len(v) or \
                    any(not isinstance(x, str) or x not in allowed for x in v):
                raise Rejected(f"{what}: '{key}' must be {lo}-{hi} distinct values from the given list")
        if not isinstance(m["reason"], str) or not m["reason"].strip() or len(m["reason"]) > REASON_MAX:
            raise Rejected(f"{what}: 'reason' must be a short non-empty string")
        out.append((sp, m))
    return out


# ── 3 judging and ranking ──

def judge(sp, ctx):
    """The moment on its own (it is its own statement: T13 is met by its own sentences; L-s context integrity judges
    what it leaves out). Word-timed: as hook and as clip; otherwise as evidence only (on screen after the word pass)."""
    own = tuple(E.statement_entry(E.Span(sp.source, k, k)) for k in range(sp.k0, sp.k1 + 1))
    if sp.source.timing == "word":
        res = {role: E.eligible(sp, replace(ctx, role=role, story=own)) for role in ("hook", "clip")}
    else:
        res = {"evidence": E.eligible(sp, replace(ctx, role="evidence"))}
    return res


def rank_score(rec, trend=None, trend_weight=TREND_WEIGHT):
    s = rec["scores"]
    score = sum(s[a] for a in POSITIVE) - CONTEMPT_WEIGHT * s["contempt_outrage"]
    score -= sum(SOFT_RISKS.get(r, 0) for r in rec["risk"])
    if trend and trend_weight:
        score += trend_weight * max([trend.get(t, 0.0) for t in rec["topics"]] or [0.0])
    return score


def record(sp, m, ctx, res, mined):
    src = sp.source
    dur = round(sp.end - sp.start, 2) if src.timing == "word" else None
    elig = {role: {"ok": r.ok, "reasons": r.names(), "targets_missed": r.facts.get("targets_missed", [])}
            for role, r in res.items()}
    reg = ctx.channel(src.channel_id) or {}
    return {"schema": "pp.moment/1", "moment_id": moment_id(src, sp.w0, sp.w1), "video_id": src.video_id,
            "channel_id": src.channel_id, "channel_name": reg.get("display_name") or src.channel_name,
            "published_at": src.published_at, "title": src.title, "transcript_sha256": src.transcript_sha256,
            "transcript_method": src.transcript_method, "timing": src.timing, "words": [sp.w0, sp.w1],
            "sentences": [sp.k0, sp.k1], "text": sp.text, "start": sp.start, "end": sp.end, "duration_s": dur,
            "duration_estimate_s": None if dur is not None else round(sp.end - sp.start, 2),
            "speaker": {"turn_change_inside": None, "label": None, "confidence": None, "named": None,
                        "named_source": None},
            "scores": dict(m["scores"]), "names_person": m["names_person"], "risk": list(m["risk"]),
            "topics": list(m["topics"]), "reason": m["reason"], "eligibility": elig,
            "on_screen_ok": any(r.ok for role, r in res.items() if role in E.ON_SCREEN), "excluded": sorted(set(m["risk"]) & set(HARD_RISKS)),
            "mined": mined}


def mine(router, sources, ctx, topics, since=None, optout=frozenset(), log=print, n=MAX_MOMENTS_PER_CALL,
         budget_chars=None, attempts=ATTEMPTS, cycle="", recent_h=RECENT_H):
    """The cycle's mining pass -> {"moments": [records, ranked], "calls": [...], "rows": n, "skipped": {...}}."""
    srcs, skipped = window_sources(sources, ctx, since=since, recent_h=recent_h, optout=optout)
    budget = budget_chars or SB.row_budget(MINE_MAX_TOKENS)
    out = {"moments": [], "calls": [], "skipped": skipped, "sources": len(srcs), "rows": 0}
    model = _MineModel(router)
    for ti, table in enumerate(tables(srcs, ctx, budget)):
        out["rows"] += len(table)
        log_ = []
        base = mine_prompt(table, ctx, topics, n)
        status, got = SB._ask(model, base, MINE_MAX_TOKENS, lambda obj: check_moments(obj, table, topics, n),
                              attempts, log_)
        call = {"table": ti, "rows": len(table), "status": status, "attempts": log_}
        out["calls"].append(call)
        if status != "accepted":
            continue
        last = log_[-1]
        mined = {"by": (last.get("meta") or {}).get("backend"), "prompt_sha256": last.get("prompt_sha256"),
                 "reply_sha256": hashlib.sha256((last.get("raw") or "").encode()).hexdigest(),
                 "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "cycle": cycle}
        for sp, m in got:
            out["moments"].append(record(sp, m, ctx, judge(sp, ctx), mined))
    seen = {}
    for rec in out["moments"]:                          # one record per moment id (a re-mined moment: the last wins)
        seen[rec["moment_id"]] = rec
    ranked = sorted(seen.values(), key=lambda r: (-rank_score(r), r["moment_id"]))
    for i, rec in enumerate(ranked):
        rec["rank"], rec["rank_score"] = i + 1, rank_score(rec)
    out["moments"] = ranked
    return out


class _MineModel(SB.Model):
    """select_by_id's call loop over the router's "mine" role (law L-x)."""

    def __init__(self, router):
        self.router, self.name = router, "role:mine"

    def complete(self, prompt, max_tokens, seed):
        import providers as P
        try:
            r = self.router.call("mine", prompt, max_tokens, seed)
        except P.ProviderError as e:
            raise SB.ModelError(str(e)[:300]) from None
        except P.ReplayMiss as e:
            raise SB.ReplayMiss(str(e)[:300]) from None
        except P.SpendLimit as e:
            raise SB.SpendLimit(str(e)) from None
        return r.text, {"backend": r.backend, "vendor": r.vendor, "usd": r.usd, "usage": r.usage,
                        "replayed": r.replayed, "tried": r.tried}


# ── the exclusion verdict on one moment in its context (law L-u; also the pp-tests harness's exclusion gate) ──

EXCLUSION_PROMPT = """You screen ONE moment (the sentences inside <moment>) from a Bitcoin video before it can be clipped
into a short video. The text around it is context only.

<before>{before}</before>
<moment>{moment}</moment>
<after>{after}</after>

Answer:
- "risks": every one that applies to the MOMENT: "accusation" (crime, fraud, insolvency or dishonesty alleged against a
  named person or company), "partner_attack" (one Bitcoin channel or host attacking another), "imperative" (telling
  the viewer to buy, sell or use leverage), "guaranteed_return", "single_source_breaking" (a breaking factual claim
  resting on one unnamed source or rumour), "ad_read" (a sponsor, ad or affiliate pitch), "third_party_media" (someone
  else's clip, song or broadcast being played); an empty list if none
- "about_bitcoin": "yes" if the moment is about Bitcoin, "no" if it is about another coin or no crypto at all,
  "uncertain"
- "why": one short line
Criticising a policy is not an accusation; a prediction framed as the speaker's own view is not an imperative;
naming a company neutrally is not an accusation.
Return ONLY this JSON object: {{"risks": [], "about_bitcoin": "yes", "why": "..."}}"""


def ad_read_marker(moment_text, before_text=""):
    """The exclusion screen's DETERMINISTIC part: an ad-read marker in the moment, or in the sentence right before it
    (an ad read runs on) -> the reason, else None. exclusion_verdict() and package.build() (before step A) share it."""
    last_before = re.split(r"(?<=[.!?])\s+", (before_text or "").strip())[-1] if (before_text or "").strip() else ""
    for where, txt in (("the moment", moment_text or ""), ("the sentence before it", last_before)):
        hit = AD_MARKERS.search(txt)
        if hit:
            return f"ad-read marker '{hit.group(0)}' in {where}"
    return None


def exclusion_verdict(router, moment_text, before_text="", after_text="", seed=7, avoid_model=None):
    """-> {"verdict": "keep" | "exclude", "why", "risks", "backend", "measured", "replayed"}: a deterministic ad-read
    screen (a marker in the moment, or in the sentence right before it: an ad read runs on), then the blind model
    verdict (role "exclusion_verdict", never on the moment's own miner: avoid_model; audit p2 C3); any hard risk, a
    moment not about Bitcoin, an unreadable or uncertain verdict excludes (law L-m). An unreadable or unavailable verdict
    is also NOT measured (the exam adapter reports it as such)."""
    import providers as P
    from story_semantics import quote_data
    why = ad_read_marker(moment_text, before_text)
    if why:
        return {"verdict": "exclude", "why": why, "risks": ["ad_read"], "backend": "deterministic", "measured": True,
                "replayed": False}
    def parse(text):
        obj = json.loads(text.strip())
        if not isinstance(obj, dict) or set(obj) != {"risks", "about_bitcoin", "why"} or \
                not isinstance(obj["risks"], list) or any(not isinstance(x, str) or x not in HARD_RISKS
                                                          for x in obj["risks"]) or \
                obj["about_bitcoin"] not in ("yes", "no", "uncertain"):
            raise ValueError("the verdict does not match its contract")
        return obj
    try:                                      # the 20:33 order: an answer out of contract moves on (P.call_parsed)
        r, obj = P.call_parsed(router, "exclusion_verdict", EXCLUSION_PROMPT.format(
            before=quote_data(before_text, 3000), moment=quote_data(moment_text, 1500),
            after=quote_data(after_text, 3000)), parse, 800, seed, avoid_model=avoid_model)
    except (P.ProviderError, P.SpendLimit, ValueError, TypeError) as e:
        return {"verdict": "exclude", "why": f"no readable verdict ({type(e).__name__}: {str(e)[:160]})",
                "risks": [], "backend": None, "measured": False, "replayed": False}
    meas = {"measured": True, "replayed": bool(getattr(r, "replayed", False))}
    if obj["risks"]:
        return dict(meas, verdict="exclude", why=f"{obj['risks']}: {str(obj['why'])[:200]}", risks=obj["risks"],
                    backend=r.backend)
    if obj["about_bitcoin"] != "yes":
        return dict(meas, verdict="exclude", why=f"about Bitcoin: {obj['about_bitcoin']}: {str(obj['why'])[:200]}",
                    risks=[], backend=r.backend)
    return dict(meas, verdict="keep", why=str(obj["why"])[:200], risks=[], backend=r.backend)
