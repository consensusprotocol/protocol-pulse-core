#!/usr/bin/env python3
"""RULING 85.1 (orchestrator 21:15 Nov 13): THE REPLAY. Every recorded Grok verdict since the first ledger build is
re-asked, with the SAME prompt, of Heimdall's model families: deepseek-v4.1-flash, z-ai/glm-5.3-flash, qwen3.8-27b.
No new Grok spend: Grok's answers are read from the recordings (tests/package/fixtures/replies). Each answer is
reduced to the pipeline's own DECISION with the pipeline's own parsers and bars, and compared with Grok's:
- step A (context_verdict, <excerpt>): per clip, context_integrity.a_failures ([] passes). REFERENT_OUTSIDE is
  counted on its own;
- step C (context_verdict, <pair>): per clip, entails == "yes". This is a PROXY: the full rule also reads the
  context window, which the prompt does not carry;
- clips-alone (coherence_verdict, joins): the through-line stated, every clip >= COHERENCE_MIN, flagged joins <=
  LY_MAX_BRIDGES; the flagged joins are compared too;
- coherence (coherence_verdict, vo_point): the through-line, every rating >= COHERENCE_MIN;
- hook rating (coherence_verdict, CANDIDATE): per hook, the lowest of scroll / alone >= HOOK_MIN (ruling 61);
- fidelity (fidelity_verdict): per line, every claim "supported": "yes", or commentary with no test "yes". This is a
  PROXY: the full check (verbatim supports) needs the package's inputs;
- exclusion (exclusion_verdict): keep (no risk, about Bitcoin "yes") or exclude;
- speaker (speaker_verdict): the speaker's name or "unknown". Naming no one where Grok named someone is "stricter".
- step B (viewer_takeaway) has no decision of its own (it feeds step C): its contract and its time are reported.
- The visual sheets (xai_vision) need their images. They are not in the recordings and come in a second pass.
Stricter: Heimdall fails what Grok passed. Looser: Heimdall passes what Grok failed. An answer out of contract is
"no verdict" (counted, never a pass). The anchors (the verdicts behind the delivered pins 0c68b589, 41f29b1f,
37c5b5f5) must still pass; the step-A REFERENT_OUTSIDE refusals must still be refused.

Spend: ruling 48's ledger (SPEND_LY.json, the order's $20 cap), roles "replay85_<model>", a reservation per call as
always. Replies are recorded under tests/package/proof/replay85/replies, so a re-run is free. A call is abandoned at
--deadline (300 s: production cuts at 120 s) and is then a timeout, with no decision; past-120 s answers are counted. RESULTS.jsonl is appended per (record, model); a re-run resumes.
Usage: python3 -B tests/package/replay85.py [--workers 2] [--models deepseek,glm,qwen] [--types ...] [--limit N]
                                            [--table-only]"""
import argparse
import glob
import json
import os
import re
import statistics
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(REPO, "pipeline"))
sys.path.insert(0, HERE)
import context_integrity as CI  # noqa: E402
import package as PK  # noqa: E402
import providers as P  # noqa: E402
import speakers as SP  # noqa: E402

WT = "/home/ultron/worktrees/pp-selectid"
REPLIES = os.path.join(WT, "tests", "package", "fixtures", "replies")
OUT = os.path.join(WT, "tests", "package", "proof", "replay85")
SPEND = os.path.join(WT, "tests", "package", "proof", "SPEND_LY.json")
ENV = "/home/ultron/protocol_pulse/" + "." + "env"
FIRST_LEDGER = "2026-11-13T07:37:38Z"          # ledger_20261113_073738: the first ledger build (UTC stamp)
LIMIT_USD, LIMIT_BASIS = 20.0, "reported"      # ruling 83 (b): the order's cap, on the same ledger
DEADLINE_S = 120.0                             # ruling 82's per-call deadline: answers past it are counted
MODELS = {"deepseek": "heimdall:deepseek/deepseek-v4.1-flash", "glm": "heimdall:z-ai/glm-5.3-flash",
          "qwen": "heimdall:qwen/qwen3.8-27b"}
ANCHOR_PINS = {                                # the delivered pins (ruling 85.1's anchors)
    "0c68b589": "tests/package/proof/ledger_20261113_183302/MOMENTS_PIN_ATTESTED.json",
    "41f29b1f": "tests/package/proof/fresh_20261112_050611/MOMENTS_PIN_LY.json",
    "37c5b5f5": "tests/package/proof/fresh_20261112_050611/MOMENTS_PIN.json",
}
TYPES = ("step_a", "step_c", "clips_alone", "coherence", "hook", "fidelity", "exclusion", "speaker", "step_b")
DECIDING = tuple(t for t in TYPES if t != "step_b")      # step B has no decision of its own: not asked by default


def kind(rec):
    """The verdict type of a recorded call, from its role and its prompt's own template markers."""
    role, pr = rec.get("role"), rec.get("prompt") or ""
    if role == "context_verdict":
        return "step_a" if '<excerpt label="' in pr else "step_c" if '<pair label="' in pr else None
    if role == "coherence_verdict":
        if 'CANDIDATE id="' in pr:
            return "hook"
        return "clips_alone" if '"followable"' in pr else "coherence" if '"vo_point"' in pr else None
    return {"fidelity_verdict": "fidelity", "exclusion_verdict": "exclusion", "speaker_verdict": "speaker",
            "viewer_takeaway": "step_b", "visual_check": "visual"}.get(role)


def _json(text):
    return json.loads(text.strip()) if isinstance(text, str) else None


def decide(k, text, prompt):
    """The DECISION a verdict's answer makes, by the pipeline's parsers and bars -> {unit: decision}; a decision is
    True (pass / keep), False (fail / exclude), or a string (a name, for the speaker). Raises ValueError / TypeError /
    KeyError for an answer out of contract (no verdict)."""
    if k == "step_a":
        labels = re.findall(r'<excerpt label="([^"]+)"', prompt)
        A = CI._strict(text, {"excerpts"}, {"excerpts": CI.A_KEYS})
        a_by = {e["label"]: e for e in A["excerpts"] if isinstance(e.get("label"), str)}
        if set(a_by) != set(labels) or len(A["excerpts"]) != len(labels):
            raise ValueError("step A must answer exactly the prompt's labels")
        return {lb: tuple(sorted(CI.a_failures(a_by[lb]))) for lb in labels}
    if k == "step_c":
        labels = re.findall(r'<pair label="([^"]+)"', prompt)
        C = CI._strict(text, {"pairs"}, {"pairs": ("label", "entails", "dropped_limit", "added_by", "same_polarity",
                                                   "stronger_certainty", "raising_words")})
        c_by = {c["label"]: c for c in C["pairs"] if isinstance(c.get("label"), str)}
        if set(c_by) != set(labels) or len(C["pairs"]) != len(labels):
            raise ValueError("step C must answer exactly the prompt's labels")
        return {lb: c_by[lb]["entails"] == "yes" for lb in labels}
    if k in ("clips_alone", "coherence"):
        # the prompt's own template names the clip keys; an older template ('"<label>": 1') rated every CLIP label,
        # the hook included, and an older contract also carried a top-level "hook" rating (both before ruling 61)
        named = re.findall(r'"(clip_\d+)": 1\b', prompt)
        labels = re.findall(r'CLIP label="([^"]+)"', prompt)
        allowed = [set(named)] if named else [set(labels), set(labels) - {"hook"}]
        v = _json(text)
        want = {"through_line", "clips", "joins"} if k == "clips_alone" else {"through_line", "clips", "vo_point"}
        if not isinstance(v, dict) or set(v) - {"hook"} != want or not isinstance(v["clips"], dict) or \
                set(v["clips"]) not in allowed or any(type(x) is not int or not 1 <= x <= 5 for x in v["clips"].values()):
            raise ValueError(f"{k} out of contract")
        extra = []
        if "hook" in v:
            hv = v["hook"]
            extra = [hv] if type(hv) is int else [x for x in hv.values() if type(x) is int] if isinstance(hv, dict) else []
            if not extra or any(not 1 <= x <= 5 for x in extra):
                raise ValueError(f"{k}: the hook's rating out of contract")
            extra = [min(extra)]
        if k == "coherence":
            if type(v["vo_point"]) is not int or not 1 <= v["vo_point"] <= 5:
                raise ValueError("coherence out of contract")
            return {"package": PK._line_ok(v["through_line"]) and
                    min(list(v["clips"].values()) + [v["vo_point"]] + extra) >= PK.COHERENCE_MIN}
        joins = re.findall(r'"([^"]+ -> [^"]+)": \{"followable"', prompt)
        if not isinstance(v["joins"], dict) or set(v["joins"]) != set(joins) or any(
                not isinstance(x, dict) or set(x) != {"followable", "why"} or type(x["followable"]) is not bool
                for x in v["joins"].values()):
            raise ValueError("clips-alone joins out of contract")
        flagged = tuple(sorted(j for j in joins if v["joins"][j]["followable"] is False))
        ok = PK._line_ok(v["through_line"]) and min(list(v["clips"].values()) + extra) >= PK.COHERENCE_MIN and \
            len(flagged) <= PK.LY_MAX_BRIDGES
        return {"lineup": ok, "flagged": flagged}
    if k == "hook":
        ids = re.findall(r'CANDIDATE id="([^"]+)"', prompt)
        v = _json(text)
        h = v["hooks"] if isinstance(v, dict) and set(v) == {"hooks"} else None
        if not isinstance(h, dict) or set(h) != set(ids) or any(
                not isinstance(x, dict) or any(type(x.get(p)) is not int or not 1 <= x[p] <= 5 for p in PK.HOOK_PARTS)
                for x in h.values()):
            raise ValueError("hook ratings out of contract")
        return {i: min(h[i][p] for p in PK.HOOK_OWN) >= PK.HOOK_MIN for i in ids}
    if k == "exclusion":
        o = _json(text)
        if not isinstance(o, dict) or set(o) != {"risks", "about_bitcoin", "why"} or not isinstance(o["risks"], list) \
                or o["about_bitcoin"] not in ("yes", "no", "uncertain"):
            raise ValueError("exclusion out of contract")
        return {"moment": not o["risks"] and o["about_bitcoin"] == "yes"}
    if k == "fidelity":
        o = _json(text)
        if not isinstance(o, dict) or set(o) != {"claims"} or not isinstance(o["claims"], list):
            raise ValueError("fidelity out of contract")
        by = {}
        for c in o["claims"]:
            if not isinstance(c, dict) or not isinstance(c.get("line"), str) or \
                    c.get("supported") not in ("yes", "no", "uncertain", "n/a") or not isinstance(c.get("tests"), dict):
                raise ValueError("fidelity claim out of contract")
            ok = c["supported"] == "yes" or (c.get("class") == "commentary" and
                                             not any(t == "yes" for t in c["tests"].values()))
            by[c["line"]] = by.get(c["line"], True) and ok
        return by
    if k == "speaker":
        v = SP._json(text)
        if not isinstance(v, dict) or not isinstance(v.get("people"), list) or not isinstance(v.get("speaker"), dict):
            raise ValueError("speaker out of contract")
        n = SP._norm(v["speaker"].get("name") or "")
        return {"speaker": n if n and n != SP.UNKNOWN else SP.UNKNOWN}
    if k == "step_b":
        labels = re.findall(r'"label": "([^"]+)"', prompt) or []
        CI._strict(text, {"takeaways", "relations"}, {"takeaways": ("label", "asserts", "certainty", "polarity"),
                                                      "relations": ("labels", "relation")})
        return {"contract": True}
    raise ValueError(f"no decision rule for {k}")


def compare(k, g, h):
    """Grok's decision g against Heimdall's h for one unit -> "agree" | "stricter" | "looser" | "different"."""
    if g == h:
        return "agree"
    if k == "speaker":
        if h == SP.UNKNOWN:
            return "stricter"
        return "looser" if g == SP.UNKNOWN else "different"
    if k == "step_a":                                  # a tuple of failures: [] passes
        if bool(g) == bool(h):
            return "agree"                             # both fail (for possibly different rules): the decision agrees
        return "stricter" if h else "looser"
    if isinstance(g, tuple):                           # the flagged joins: compared as a set
        return "different"
    return "stricter" if g is True and h is False else "looser" if g is False and h is True else "different"


def records(since=FIRST_LEDGER, anchors=()):
    """Every recorded Grok verdict (xAI text back-end) since `since`, plus older ones whose prompt carries an anchor
    pin's clip text. -> [(path, rec, kind, anchor names)]."""
    out = []
    for p in sorted(glob.glob(os.path.join(REPLIES, "*", "*.json"))):
        try:
            with open(p) as f:
                r = json.load(f)
        except (OSError, ValueError):
            continue
        if not str(r.get("backend", "")).startswith("xai:"):
            continue
        k = kind(r)
        if k is None:
            continue
        pr = _norm(r.get("prompt") or "")
        hit = sorted({name for name, texts in anchors for t in texts if t and t in pr})
        if str(r.get("recorded_at", "")) >= since:
            out.append((p, r, k, hit))
        elif hit:                                      # an older anchor record: only where Grok's answer still reads
            try:
                decide(k, r["text"], r.get("prompt") or "")
                out.append((p, r, k, hit))
            except (ValueError, TypeError, KeyError):
                pass
    seen, uniq = {}, []                                # the same prompt asked again (another seed): asked once here
    for x in out:
        key = (x[1].get("role"), x[1].get("prompt"), x[1].get("system"), x[1].get("max_tokens"))
        if key in seen:
            seen[key][3].extend(a for a in x[3] if a not in seen[key][3])
            continue
        seen[key] = x
        uniq.append(x)
    return uniq


def _norm(t):
    """Lower case letters and digits, single spaces: a prompt quotes a clip through quote_data (escaping)."""
    return " ".join(re.sub(r"[^a-z0-9]+", " ", str(t).lower()).split())


def anchor_texts():
    """[(pin name, [its segments' approved texts, normalised, 60 characters from the 10th])]: a prompt that carries
    one of them judged that clip."""
    out = []
    for name, rel in ANCHOR_PINS.items():
        try:
            with open(os.path.join(WT, rel)) as f:
                pin = json.load(f)
        except (OSError, ValueError):
            out.append((name, []))
            continue
        segs = pin.get("segments") or (pin.get("package") or {}).get("segments") or []
        out.append((name, [_norm(s.get("approved_text") or s.get("text") or "")[10:70] for s in segs
                           if isinstance(s, dict)]))
    return out


def run(args):
    os.makedirs(os.path.join(OUT, "replies"), exist_ok=True)
    res_path = os.path.join(OUT, "RESULTS.jsonl")
    done = set()
    if os.path.exists(res_path):
        with open(res_path) as f:
            for line in f:
                try:
                    x = json.loads(line)
                    done.add((x["record"], x["model"]))
                except (ValueError, KeyError):
                    pass
    anchors = anchor_texts()
    recs = [x for x in records(anchors=anchors) if x[2] in args.types]
    if args.limit:
        recs = recs[:args.limit]
    models = [m for m in args.models if m in MODELS]
    chains = {f"replay85_{m}": [MODELS[m]] for m in models}
    router = P.Router(env_path=ENV, record_dir=os.path.join(OUT, "replies"), spend_path=SPEND, limit_usd=LIMIT_USD,
                      limit_basis=LIMIT_BASIS, chains=chains)
    lock = threading.Lock()
    # round-robin by verdict type, the records since the first ledger build first, so an early table covers them all
    order, by_type = [], {}
    for x in sorted(recs, key=lambda x: str(x[1].get("recorded_at", "")) < FIRST_LEDGER):
        by_type.setdefault(x[2], []).append(x)
    while any(by_type.values()):
        for k in list(by_type):
            if by_type[k]:
                order.append(by_type[k].pop(0))
    jobs = [(p, r, k, hit, m) for (p, r, k, hit) in order for m in models
            if (os.path.relpath(p, WT), m) not in done]
    print(f"replay85: {len(recs)} Grok records, {len(models)} models, {len(jobs)} calls to make "
          f"({len(done)} already in RESULTS)", flush=True)

    def one(job):
        p, r, k, hit, m = job
        row = {"record": os.path.relpath(p, WT), "type": k, "model": m, "anchors": hit,
               "grok_recorded_at": r.get("recorded_at"), "grok_seconds": r.get("seconds"),
               "grok_usd_reported": (r.get("usage") or {}).get("usd_reported")}
        try:
            row["grok"] = {u: (list(d) if isinstance(d, tuple) else d) for u, d in decide(k, r["text"], r["prompt"]).items()}
        except (ValueError, TypeError, KeyError) as e:
            row["grok"], row["grok_error"] = None, f"{type(e).__name__}: {str(e)[:160]}"
        t0 = time.time()
        router.down.pop(MODELS[m], None)               # a rate limit is never a verdict: each call is tried afresh
        try:
            rep = router.call(f"replay85_{m}", r["prompt"], int(r.get("max_tokens") or 2000), int(r.get("seed") or 7),
                              system=r.get("system"), deadline_s=args.deadline or None)
            row.update(seconds=round(rep.seconds or (time.time() - t0), 2), cached=bool(rep.cached),
                       usd_reported=(rep.usage or {}).get("usd_reported"), usd_estimate=rep.usd)
            try:
                h = decide(k, rep.text, r["prompt"])
                row["heimdall"] = {u: (list(d) if isinstance(d, tuple) else d) for u, d in h.items()}
            except (ValueError, TypeError, KeyError) as e:
                row["heimdall"], row["heimdall_error"] = None, f"out of contract: {type(e).__name__}: {str(e)[:160]}"
                router.reject(rep)
        except (P.ProviderError, P.SpendLimit) as e:
            if "HTTP 429" in str(e):                   # rate limited (after the router's own backoff): no row, so a
                time.sleep(30)                         # resume asks it again; never counted as the model's answer
                return None
            row.update(seconds=round(time.time() - t0, 2), heimdall=None,
                       heimdall_error=f"{type(e).__name__}: {str(e)[:200]}")
        if row.get("grok") is not None and row.get("heimdall") is not None:
            row["compare"] = {u: compare(k, tuple(g) if isinstance(g, list) else g,
                                         tuple(row["heimdall"].get(u)) if isinstance(row["heimdall"].get(u), list)
                                         else row["heimdall"].get(u))
                              for u, g in row["grok"].items()}
        with lock:
            with open(res_path, "a") as f:
                f.write(json.dumps(row) + "\n")
        return row

    n_done = [0]

    def per_model(m):                                  # one pool per model: a slow model never starves the others
        mine = [j for j in jobs if j[4] == m]
        with ThreadPoolExecutor(max_workers=args.per_model.get(m, args.workers)) as ex:
            for _ in ex.map(one, mine):
                with lock:
                    n_done[0] += 1
                    if n_done[0] % 10 == 0 or n_done[0] == len(jobs):
                        print(f"  {n_done[0]}/{len(jobs)} at {time.strftime('%H:%M:%S')}", flush=True)
    ts = [threading.Thread(target=per_model, args=(m,)) for m in models]
    for t in ts:
        t.start()
    for t in ts:
        t.join()
    table()


def grok_self():
    """The baseline: Grok against GROK on the same prompt asked again (another seed, another build), from every
    recorded Grok answer. -> {type: {"pairs": n, "agree": n}} by the same decide / compare."""
    by = {}
    for p in sorted(glob.glob(os.path.join(REPLIES, "*", "*.json"))):
        try:
            with open(p) as f:
                r = json.load(f)
        except (OSError, ValueError):
            continue
        if not str(r.get("backend", "")).startswith("xai:"):
            continue
        k = kind(r)
        if k not in DECIDING:
            continue
        try:
            d = decide(k, r["text"], r.get("prompt") or "")
        except (ValueError, TypeError, KeyError):
            continue
        by.setdefault((k, r.get("role"), r.get("prompt"), r.get("max_tokens")), []).append(d)
        if k == "step_a":                              # the same excerpt inside OTHER batches too (its own block)
            for lb, blk in re.findall(r'<excerpt label="([^"]+)"(.*?)</excerpt>', r.get("prompt") or "", re.S):
                if lb in d:
                    by.setdefault(("step_a_excerpt", lb, blk), []).append({lb: d[lb]})
    out = {}
    for (k, *_), ds in by.items():
        for i in range(len(ds)):
            for j in range(i + 1, len(ds)):
                for u, g in ds[i].items():
                    if u not in ds[j]:
                        continue
                    o = out.setdefault(k, {"pairs": 0, "agree": 0})
                    o["pairs"] += 1
                    o["agree"] += compare("step_a" if k == "step_a_excerpt" else k, g, ds[j][u]) == "agree"
    if (out.get("step_a_excerpt") or {}).get("pairs", 0) > (out.get("step_a") or {}).get("pairs", 0):
        out["step_a_identical_prompt"] = out.get("step_a")
        out["step_a"] = out["step_a_excerpt"]            # the bar for step A: the same excerpt, any batch
    return out


_PROMPTS = {}


def anchor_units(row, anchors):
    """The units of a row that are an anchor's OWN decision (a delivered pin's clip let through):
    - step A, step C, hook: the unit whose own block (<excerpt>, <pair>, CANDIDATE line) quotes an anchor clip;
    - clips-alone, coherence, fidelity: every unit, only when the prompt quotes ALL clips of one anchor pin (its own
      line-up);
    - exclusion, speaker: the one unit when the prompt quotes an anchor clip.
    -> {unit: [pin names]}."""
    if not row.get("anchors"):
        return {}
    pr = _PROMPTS.get(row["record"])
    if pr is None:
        try:
            with open(os.path.join(WT, row["record"])) as f:
                pr = _PROMPTS[row["record"]] = json.load(f).get("prompt") or ""
        except (OSError, ValueError):
            return {}
    k, out = row["type"], {}
    if k in ("step_a", "step_c", "hook"):
        pat = {"step_a": r'<excerpt label="([^"]+)"(.*?)</excerpt>', "step_c": r'<pair label="([^"]+)"(.*?)</pair>',
               "hook": r'CANDIDATE id="([^"]+)"([^\n]*)'}[k]
        for u, blk in re.findall(pat, pr, re.S):
            hit = [n for n, ts in anchors for t in ts if t and t in _norm(blk)]
            if hit:
                out[u] = sorted(set(hit))
        return out
    npr = _norm(pr)
    if k in ("clips_alone", "coherence", "fidelity"):
        whole = [n for n, ts in anchors if ts and all(t in npr for t in ts if t)]
        return {u: whole for u in (row.get("grok") or {})} if whole else {}
    hit = [n for n, ts in anchors for t in ts if t and t in npr]
    return {u: sorted(set(hit)) for u in (row.get("grok") or {})} if hit else {}


def table():
    """TABLE.md from RESULTS.jsonl: per verdict type and model, with Grok's agreement with itself as the baseline."""
    rows = []
    with open(os.path.join(OUT, "RESULTS.jsonl")) as f:
        for line in f:
            try:
                rows.append(json.loads(line))
            except ValueError:
                pass
    out = ["# Ruling 85.1: the replay of Grok's recorded verdicts on Heimdall's families", "",
           f"Built {time.strftime('%Y-%m-%d %H:%M %Z')} from {len(rows)} (record, model) rows. A unit is one decision "
           "(a clip, a line-up, a hook, a line, a moment). Stricter: Heimdall fails what Grok passed. Looser: Heimdall "
           "passes what Grok failed. Different: another name, or other flagged joins with the same decision.", "",
           "| type | model | records | answered | no verdict | units | agree | stricter | looser | different | "
           "agree % | median s | > 120 s | timeouts | errors | usd reported |", "|" + "---|" * 16]
    for k in TYPES:
        for m in MODELS:
            rs = [r for r in rows if r["type"] == k and r["model"] == m]
            if not rs:
                continue
            ans = [r for r in rs if r.get("heimdall") is not None]
            nov = [r for r in rs if r.get("heimdall") is None and "out of contract" in str(r.get("heimdall_error"))]
            tmo = [r for r in rs if r.get("heimdall") is None and "abandoned at the deadline" in
                   str(r.get("heimdall_error"))]
            err = [r for r in rs if r.get("heimdall") is None and r not in nov and r not in tmo]
            cmp_ = [c for r in rs for c in (r.get("compare") or {}).values()]
            n = {x: cmp_.count(x) for x in ("agree", "stricter", "looser", "different")}
            secs = [r["seconds"] for r in rs if isinstance(r.get("seconds"), (int, float)) and not r.get("cached")]
            usd = sum(float(r["usd_reported"]) for r in rs if P._num(r.get("usd_reported")) and not r.get("cached"))
            out.append(f"| {k} | {m} | {len(rs)} | {len(ans)} | {len(nov)} | {len(cmp_)} | {n['agree']} | "
                       f"{n['stricter']} | {n['looser']} | {n['different']} | "
                       f"{(100 * n['agree'] / len(cmp_)) if cmp_ else 0:.0f} | "
                       f"{statistics.median(secs) if secs else 0:.0f} | {sum(1 for s in secs if s > DEADLINE_S)} | "
                       f"{len(tmo)} | {len(err)} | {usd:.4f} |")
    base = grok_self()
    out += ["", "## The baseline: Grok against Grok (the same prompt asked again: another seed or build)", "",
            "| type | unit pairs | agree | agree % |", "|---|---|---|---|"]
    for k in DECIDING + ("step_a_excerpt",):
        b = base.get(k)
        if b:
            out.append(f"| {k} | {b['pairs']} | {b['agree']} | {100 * b['agree'] / b['pairs']:.0f} |")
    anchors = anchor_texts()
    out += ["", "## Anchors: the delivered pins' own decisions that Grok passed must still pass", ""]
    for m in MODELS:
        units = bad = nov = 0
        ex = []
        for r in rows:
            if r["model"] != m:
                continue
            au = anchor_units(r, anchors)
            for u in au:
                g = (r.get("grok") or {}).get(u)
                if g is None or (r["type"] == "step_a" and g) or g is False:
                    continue                           # Grok did not pass it: not a decision that let a clip through
                units += 1
                if r.get("heimdall") is None:
                    nov += 1
                    ex.append(f"{r['type']} {u} {au[u]}: no Heimdall verdict")
                elif (r.get("compare") or {}).get(u) == "stricter":
                    bad += 1
                    ex.append(f"{r['type']} {u} {au[u]}: FAILED ({r['record'][-24:]})")
        out.append(f"- {m}: {units} anchor decisions Grok passed; {bad} failed by {m}; {nov} without a verdict" +
                   (": " + "; ".join(ex[:10]) if ex else ""))
    out += ["", "## Step A's REFERENT_OUTSIDE refusals (Grok's) must still be refused", ""]
    for m in MODELS:
        tot = kept = ro = 0
        for r in rows:
            if r["model"] != m or r["type"] != "step_a" or not r.get("grok") or r.get("heimdall") is None:
                continue                               # only the answered rows: no answer is no verdict either way
            for u, g in r["grok"].items():
                if "REFERENT_OUTSIDE" in (g or []):
                    tot += 1
                    h = (r.get("heimdall") or {}).get(u)
                    kept += bool(h)
                    ro += "REFERENT_OUTSIDE" in (h or [])
        out.append(f"- {m}: Grok refused {tot} clips for REFERENT_OUTSIDE; Heimdall refuses {kept} of them "
                   f"({ro} for REFERENT_OUTSIDE itself)")
    vp = os.path.join(OUT, "VISUAL.jsonl")
    if os.path.exists(vp):                             # the visual sheets (run_visual): the set of flags per sheet
        with open(vp) as f:
            vis = [json.loads(x) for x in f if x.strip()]
        out += ["", "## The visual sheets (nemotron and qwen against Grok's flags)", "",
                "| model | sheets | answered | agree | stricter | looser | different | median s | usd reported |",
                "|---|---|---|---|---|---|---|---|---|"]
        for m in VISION:
            vs = [v for v in vis if v.get("model") == m]
            if not vs:
                continue
            c = [v.get("compare") for v in vs if v.get("compare")]
            secs = [v["seconds"] for v in vs if isinstance(v.get("seconds"), (int, float))]
            out.append(f"| {m} | {len(vs)} | {len(c)} | {c.count('agree')} | {c.count('stricter')} | "
                       f"{c.count('looser')} | {c.count('different')} | "
                       f"{statistics.median(secs) if secs else 0:.0f} | "
                       f"{sum(float(v.get('usd_reported') or 0) for v in vs):.4f} |")
        skipped = [v for v in vis if v.get("skipped")]
        if skipped:
            out.append(f"- {len(skipped)} sheet(s) skipped: " + "; ".join(v["skipped"] for v in skipped)[:300])
        sheets = {v["sheet"] for v in vis if v.get("sheet") and not v.get("skipped")}
        flagged = {v["sheet"] for v in vis if v.get("grok")}
        out.append(f"- Grok flagged {len(flagged)} of the {len(sheets)} sheets compared; agreement on unflagged sheets "
                   f"says little about a model's eye for a flag.")
    out += propose(rows, base)
    with open(os.path.join(OUT, "TABLE.md"), "w") as f:
        f.write("\n".join(out) + "\n")
    print("\n".join(out), flush=True)


ROLES = {"context_verdict": ("step_a", "step_c"), "coherence_verdict": ("clips_alone", "coherence", "hook"),
         "fidelity_verdict": ("fidelity",), "exclusion_verdict": ("exclusion",), "speaker_verdict": ("speaker",)}
MIN_UNITS = 10


def passes(rows, base, k, m):
    """The PROPOSED rule (the orchestrator rules it): -> (pass, [reasons it fails])."""
    rs = [r for r in rows if r["type"] == k and r["model"] == m]
    cmp_ = [c for r in rs for c in (r.get("compare") or {}).values()]
    why = []
    if len(cmp_) < MIN_UNITS:
        why.append(f"only {len(cmp_)} decisions (< {MIN_UNITS})")
    anchors = anchor_texts()
    if any((r.get("compare") or {}).get(u) == "stricter" for r in rs for u in anchor_units(r, anchors)):
        why.append("an anchor decision Grok passed is failed")
    if k == "step_a":
        miss = sum(1 for r in rs if r.get("grok") and r.get("heimdall") is not None for u, g in r["grok"].items()
                   if "REFERENT_OUTSIDE" in (g or []) and not r["heimdall"].get(u))
        if miss:
            why.append(f"{miss} REFERENT_OUTSIDE refusal(s) let through")
    agree = 100 * cmp_.count("agree") / len(cmp_) if cmp_ else 0
    b = base.get(k) or {}
    bar = 100 * b["agree"] / b["pairs"] if b.get("pairs", 0) >= 5 else 75.0
    if agree < bar:
        why.append(f"agreement {agree:.0f}% < the bar {bar:.0f}%")
    ans = [r for r in rs if r.get("heimdall") is not None]
    nov = [r for r in rs if r.get("heimdall") is None and "out of contract" in str(r.get("heimdall_error"))]
    if ans and len(ans) / max(1, len(ans) + len(nov)) < 0.9:
        why.append(f"{len(nov)} of {len(ans) + len(nov)} answers out of contract")
    secs = [r["seconds"] for r in rs if isinstance(r.get("seconds"), (int, float)) and not r.get("cached")]
    if secs and statistics.median(secs) > DEADLINE_S:
        why.append(f"median {statistics.median(secs):.0f} s > {DEADLINE_S:.0f} s")
    return not why, why, agree, (statistics.median(secs) if secs else None)


def propose(rows, base):
    """The proposed Heimdall-first list per role: the families that pass EVERY type of the role, best agreement
    first; Grok last; a role with fewer than two passing families keeps Grok as its second family."""
    out = ["", "## The proposed routing (the rule is the orchestrator's to rule)", ""]
    for role, types in ROLES.items():
        ok, notes = [], []
        for m in MODELS:
            res = [(k, passes(rows, base, k, m)) for k in types]
            if all(x[1][0] for x in res):
                ok.append((m, min(x[1][2] for x in res)))
            notes.append(f"{m}: " + ("PASSES" if all(x[1][0] for x in res) else
                                     "; ".join(f"{k}: {', '.join(x[1])}" for k, x in res if not x[0])))
        order = [m for m, _ in sorted(ok, key=lambda x: -x[1])]
        tail = "Grok last" if len(order) >= 2 else "Grok as the second family (fewer than two Heimdall families pass)"
        out.append(f"- {role} ({', '.join(types)}): {' -> '.join(order) or 'none'}; {tail}")
        out += [f"  - {n}" for n in notes]
    return out


VISION = {"nemotron": "heimdall:nvidia/nemotron-3.5-super-vl", "qwen": "heimdall:qwen/qwen3.8-27b"}


def run_visual(args):
    """The visual sheets (ruling 85.1: "and nemotron for the visual sheets"). Every sheet Grok judged is in
    tests/package/proof/VISUAL_CACHE.json, with its path, sha256 and frame times. The prompt is rebuilt exactly as
    visual_pin.visual_for builds it (PROMPT.format(n, text) and the sheet image), and asked of nemotron and qwen. The
    decision is visual_pin.flags of the verdict (the set of flags), compared with Grok's. A sheet whose bytes changed,
    or whose moment text cannot be found, is skipped and said so."""
    import base64
    import hashlib
    import visual_pin as VP
    with open(os.path.join(WT, "tests", "package", "proof", "VISUAL_CACHE.json")) as f:
        cache = json.load(f)
    texts = {}
    for p in sorted(glob.glob(os.path.join(WT, "tests", "package", "proof", "ledger_*", "inputs.json"))):
        try:
            with open(p) as f:
                for m in json.load(f).get("moments") or []:
                    texts.setdefault(m.get("moment_id"), m.get("text"))
        except (OSError, ValueError):
            continue
    router = P.Router(env_path=ENV, record_dir=os.path.join(OUT, "replies"), spend_path=SPEND, limit_usd=LIMIT_USD,
                      limit_basis=LIMIT_BASIS, chains={f"replay85v_{m}": [n] for m, n in VISION.items()})
    rows = []
    for k, g in cache.items():
        sh, mid = g.get("sheet") or {}, k.split(":")[0]
        path = sh.get("path") or ""
        try:
            with open(path, "rb") as f:
                raw = f.read()
        except OSError:
            rows.append({"sheet": k, "skipped": f"the sheet is not on disk: {path}"})
            continue
        if hashlib.sha256(raw).hexdigest() != sh.get("sha256") or texts.get(mid) is None:
            rows.append({"sheet": k, "skipped": "the sheet's bytes changed, or its moment's text is not found"})
            continue
        prompt = {"text": VP.PROMPT.format(n=len(sh.get("times") or []), text=str(texts[mid]).replace('"', "'")),
                  "images": [base64.b64encode(raw).decode()]}
        grok = sorted(g.get("flags") or [])
        for m in VISION:
            t0 = time.time()
            row = {"sheet": k, "model": m, "grok": grok}
            try:
                r = router.call(f"replay85v_{m}", prompt, 1500, 7)
                row.update(seconds=round(r.seconds or (time.time() - t0), 2),
                           usd_reported=(r.usage or {}).get("usd_reported"))
                try:
                    row["heimdall"] = sorted(VP.flags(VP.check(VP._json(r.text))))
                    h, gg = set(row["heimdall"]), set(grok)
                    row["compare"] = "agree" if h == gg else "stricter" if h > gg else "looser" if h < gg \
                        else "different"
                except (ValueError, TypeError, KeyError) as e:
                    row["heimdall"], row["error"] = None, f"out of contract: {type(e).__name__}: {str(e)[:120]}"
                    router.reject(r)
            except (P.ProviderError, P.SpendLimit) as e:
                row.update(heimdall=None, error=f"{type(e).__name__}: {str(e)[:160]}",
                           seconds=round(time.time() - t0, 2))
            rows.append(row)
            print(json.dumps(row)[:300], flush=True)
    with open(os.path.join(OUT, "VISUAL.jsonl"), "w") as f:
        f.write("".join(json.dumps(r) + "\n" for r in rows))
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=2, help="calls in flight per model")
    ap.add_argument("--models", default="deepseek,glm,qwen")
    ap.add_argument("--per-model", default="", help="calls in flight per model, e.g. deepseek=12,glm=8")
    ap.add_argument("--deadline", type=float, default=300.0,
                    help="seconds a call may take (abandoned past it: a timeout; production cuts at 120 s)")
    ap.add_argument("--types", default=",".join(DECIDING))
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--table-only", action="store_true")
    ap.add_argument("--visual", action="store_true", help="the visual sheets only (nemotron and qwen)")
    a = ap.parse_args()
    a.models, a.types = a.models.split(","), a.types.split(",")
    a.per_model = {k: int(v) for k, v in (x.split("=") for x in a.per_model.split(",") if x)}
    if a.table_only:
        table()
        return 0
    if a.visual:
        run_visual(a)
        return 0
    run(a)
    return 0


if __name__ == "__main__":
    sys.exit(main())
