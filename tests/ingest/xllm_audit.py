#!/usr/bin/env python3
"""Two-cycle cross-LLM audit of the pp-ingest diff (CROSS_LLM_AUDIT_LAW; order: "run the repo's cross_llm_audit.py on
the ACTUAL diff (two cycles, cycle 2 cross-validates)").

The repo tool's run_audit() writes into /home/ultron/protocol_pulse/docs/audits (the main tree, which this session
must not touch) and reads key names the env file does not define (GEMINI_API_KEY / XAI_API_KEY). So this driver uses
the tool's OWN templates (utils/cross_llm_audit.DEFAULT_REVIEW_TASK and build_cycle2_prompt, imported read-only) on
the actual diff of this branch and writes only under docs/audits/parallel/pp-ingest_audit/. Reviewers (four vendors):
OpenAI (the tool's gpt-4o), xAI, Google, Heimdall (qwen3.8-27b; never the abliterated deepseek). Keys are read by
name inside code (pipeline.ingest.providers.Keyring) and never printed. The consensus is written by the session
(C1_CONSENSUS.md / C2_CONSENSUS.md): consensus = the same file, function and root cause from >= 2 reviewers, or one
reviewer's finding verified against the code; refutations are recorded with evidence.

  A=docs/audits/parallel/pp-ingest_audit/<change>
  python3 tests/ingest/xllm_audit.py --cycle 1 --base <rev> --context $A/CONTEXT.md --out $A/c1
  python3 tests/ingest/xllm_audit.py --cycle 2 --base <rev> --context $A/CONTEXT.md --c1 $A/c1 \
      --consensus $A/C1_CONSENSUS.md --out $A/c2

SPEND FREEZE (orchestrator 05:30 ET Nov 12): a reviewer whose vendor is in providers.json spend_freeze is never called
(skipped, and said so); the Heimdall-served reviewers of other model families stand in.

RULING 107 (2) (orchestrator 20:20 ET Nov 14; in force for batch 3 by ruling 108, 21:22): the package is the DIFF (git
diff --base of the watcher's code and its tests; a new file needs `git add -N`), the laws and the change's own context
(--context), never the whole files; the reviewers are two Heimdall families, qwen + glm (DEFAULT); a third family
(THIRD, by --only) only when the two disagree on a P0 / P1 or one of them is down (the paid frontier reviewers stay
out under pp-ingest's freeze). The audit is capped, vendor-reported, both cycles together: $0.30 for a change under 60
changed lines, else $1.00; a cycle that could pass the cap is refused before any call. Each review's cost goes to
COST.json in the audit folder and, one record per review, to the watcher's audit ledger (config.paths()
["audit_spend"]: ruling 108's batch line counts it); an abandoned review (a timeout, no cost reported) is booked at
the model's own rate (ruling 107: its reported dollars per prompt token in this audit history x the prompt; the list
price of the prompt until it has 3 reported reviews).
"""
import argparse
import json
import os
import subprocess
import sys
import threading
import time

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, REPO)
sys.path.insert(0, os.path.join(REPO, "utils"))

from pipeline.ingest import config, providers  # noqa: E402

ENV = "/home/ultron/protocol_pulse/.env"
HEIMDALL = {"kind": "openai_compat", "vendor": "heimdall", "base_url": "https://api-staging.heimdallm.com/api/v1",
            "key_env_prefix": "HEIMDALL_API_KEY", "timeout_s": 900, "cost_from_usage": True}
REVIEWERS = {
    "gpt4o": {"kind": "openai_compat", "vendor": "openai", "base_url": "https://api.openai.com/v1", "model": "gpt-4o",
              "key_env": "OPENAI_API_KEY", "timeout_s": 600, "json_schema": False},
    "grok": {"kind": "openai_compat", "vendor": "xai", "base_url": "https://api.x.ai/v1",
             "model": "grok-4.20-0309-reasoning", "key_env": "XAI_API_KEY_MEDLEY", "timeout_s": 900,
             "json_schema": False},
    "gemini": {"kind": "gemini", "vendor": "google", "model": "gemini-pro-latest", "key_env": "GEMINI_API_KEY_MEDLEY",
               "timeout_s": 900, "max_tokens_floor": 48000},   # c1: its thinking used ~16k of 16k: cut off
    "heimdall_qwen": dict(HEIMDALL, model="qwen/qwen3.8-27b", extra_body={"reasoning": {"effort": "none"}}),
    # other model families served by Heimdall (not frozen; billed against the Heimdall cap), added under the freeze:
    # freeze c1 (111k-token package): glm and minimax at their default reasoning spent all 16k output tokens thinking
    # (empty, finish_reason length, like INGEST-FAIL-04); muse timed out at 900 s. Re-run at effort none / 1800 s.
    "heimdall_glm": dict(HEIMDALL, model="z-ai/glm-5.3-flash", extra_body={"reasoning": {"effort": "none"}},
                         max_tokens_floor=24000),     # freeze c1: its review was cut at 16,000 tokens
    "heimdall_muse": dict(HEIMDALL, model="meta-models/muse-spark-open-816b-a42b", timeout_s=1800,
                          extra_body={"reasoning": {"effort": "none"}}),
    "heimdall_minimax": dict(HEIMDALL, model="minimax/minimax-m3.1-flash", extra_body={"reasoning": {"effort": "none"}}),
}  # Heimdall qwen at effort none. deepseek-v4.1-flash dropped after c1: empty content twice (effort low, then none; its
   # hidden reasoning took the whole budget on the 64k-token package); the abliterated deepseek and ling-3.0-flash are
   # excluded by the order (incoherent on long prompts / always 429)


DEFAULT = ("heimdall_qwen", "heimdall_glm")       # ruling 107 (2): two Heimdall families
THIRD = "heimdall_muse"                           # the third family: a P0 / P1 disagreement, or one of the two down
DIFF_PATHS = ["pipeline/ingest", "tools/ingest_watch.py", "tests/ingest"]
SMALL_LINES, SMALL_CAP, BIG_CAP = 60, 0.30, 1.00  # ruling 107 (2): per audit, both cycles, vendor-reported
MIN_REPORTED = 3                                  # ruling 107: list price until a model has 3 reported reviews
CUT_S = 30.0                                      # a review cut off after this long in flight may have been billed
AUDIT_ROOT = os.path.join(REPO, "docs/audits/parallel/pp-ingest_audit")


def frozen():
    return providers.frozen_vendors(providers.load_config())

LAWS = """Standing order (PBX 02:30 / orchestrator 02:45 ET 2026-11-12) and laws this code must obey:
- BUILD: continuous ingest of every registered partner channel (RSS first, yt-dlp metadata fallback, ~10 min, ETag /
  backoff, last-seen ledger, re-upload / duplicate detection, Shorts and live-in-progress handled explicitly, durable
  queue); captions into the SAME transcript store format via the store's writer, in a staging copy, never the main
  tree; first-pass mining by sentence ids on Heimdall (bounded concurrency, queue-aware backoff on 429/503, <= ~20 in
  flight, spend tracked vs the $460 cap with a 90 % tripwire that NOTIFIES and falls back, never halts); an
  append-only moment ledger matching pp-selectid's pp.moment/1 contract and an adapter "best unused moments since T";
  a daily coverage check; a blind A/B of back-ends (generator and judge different models).
- L-x NO SINGLE MODEL, ULTRON FIRST: every model role behind ONE provider interface with >= 2 interchangeable
  back-ends; the run continues when any one vendor is down or out of credit; no vendor / model name outside the
  provider config; the local model on Ultron is the default where it meets the bar (it runs only under the GPU0
  lease, which this builder never holds: no GPU use at all here).
- L-l a model reply counts only whole: strict schema, ids validated, NOTHING REPAIRED; a failed call is never a
  default, a pass or an agreement. L-j / L-m: fail closed; nothing measured is never a pass.
- L-h / L-k: transcript text is read as spoken (entities decoded, split tokens joined) through the repo's canonical
  form; stored records are never rewritten. L-e: word timing for anything heard (the packager's job at cut time).
- L-u hard exclusions (accusation, partner attack, buy/sell imperative, guaranteed return, single-source breaking, ad
  read, third-party media) are flagged and excluded before ranking; L-v: a moment never spans a speaker change;
  re-uploads excluded; time-sensitive language needs the original publish time.
- Secrets: keys read by name from the env file inside code; never printed, logged or written.
- SPEND FREEZE (orchestrator 05:30 ET Nov 12, until told otherwise): paid frontier vendors (OpenAI, Anthropic, xAI;
  Google by the builder's assumption) are never called by any role; the watcher's mine chain is Heimdall then the
  local interface ONLY; if both are down the videos queue and are mined later, never on a paid frontier model; Heimdall
  mining continues; the 90 % tripwire is a NOTIFY ("HEIMDALL SPEND AT 90%" at the top of STATE), never a halt.
Only report issues you can verify from the code provided. Do not speculate. Cite file:line."""


def changed_lines(base):
    """Added + deleted lines of the change (git diff --numstat; a binary file counts 0)."""
    out = subprocess.check_output(["git", "diff", "--numstat", base, "--"] + DIFF_PATHS, cwd=REPO, text=True)
    return sum(int(a) + int(d) for a, d, _ in (l.split("\t", 2) for l in out.splitlines() if l.strip())
               if a.isdigit() and d.isdigit())


def package(base, context=None):
    """Ruling 107 (2): the laws, the change's own context and its diff (never the whole files)."""
    import cross_llm_audit as tool
    head = subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=REPO, text=True).strip()
    diff = subprocess.check_output(["git", "diff", base, "--"] + DIFF_PATHS, cwd=REPO, text=True)
    if not diff.strip():
        raise SystemExit(f"nothing to review: git diff {base} is empty (a new file needs git add -N)")
    ctx = open(context).read() if context else ""
    return f"""# PROTOCOL PULSE: CODE AUDIT PACKAGE (pp-ingest; the DIFF only, ruling 107 (2))
# Feature: pp-ingest (continuous ingest + first-pass moment mining); branch pp-ingest, working tree at {head}
# The change under review: git diff {base} (working tree) of {", ".join(DIFF_PATHS)}

## GOVERNING LAWS (this code MUST comply with every law below: flag any violation)
{LAWS}

## THE CHANGE UNDER REVIEW: its orders and design
{ctx}

```diff
{diff}
```

You see the diff, not the whole files: when a finding needs code outside it, say which function you need instead of
guessing.

---

{tool.DEFAULT_REVIEW_TASK}
"""


def _rates(root=AUDIT_ROOT):
    """Each reviewer's own rate (ruling 107): its reported dollars per prompt token over every review in the audit
    history -> {reviewer: (dollars per token, reviews)}."""
    import glob
    agg = {}
    for path in glob.glob(os.path.join(root, "**", "results.json"), recursive=True):
        try:
            with open(path) as f:
                res = json.load(f).get("results") or {}
        except (OSError, ValueError):
            continue
        for rid, r in res.items():
            pt = (r.get("usage") or {}).get("prompt_tokens")
            if isinstance(r.get("cost_usd"), (int, float)) and r["cost_usd"] > 0 and isinstance(pt, int) and pt > 0:
                c, p, n = agg.get(rid, (0.0, 0, 0))
                agg[rid] = (c + r["cost_usd"], p + pt, n + 1)
    return {rid: (c / p, n) for rid, (c, p, n) in agg.items()}


def _rate(rid, rates):
    """(dollars per prompt token, basis): the reviewer's own once it has MIN_REPORTED reviews, else the list price of
    the prompt (providers.json, the same model), else None (unpriced)."""
    own = rates.get(rid)
    if own and own[1] >= MIN_REPORTED:
        return own[0], f"the model's own rate ({own[1]} reported reviews)"
    model = REVIEWERS[rid].get("model")
    for b in providers.load_config()["backends"].values():
        if b.get("model") == model and (b.get("price") or {}).get("in_per_mtok") is not None:
            return float(b["price"]["in_per_mtok"]) / 1e6, "the list price of the prompt (fewer than 3 reported reviews)"
    return None, "UNPRICED (no rate known)"


def book(results, errors, error_costs, prompts, rates):
    """Every review's cost: reported (the reply's or the failed call's own figure), or, for an abandoned review (a
    timeout, or a review cut off after CUT_S in flight with no answer: a dropped connection; the stricter reading,
    ruling 106 (b)), at the model's own rate x its prompt (the answered reviews' prompt tokens, else 3 characters a
    token); a quick failure or an error the vendor answered with no cost is not booked, and says so ->
    {reviewer: {usd, basis}}. (b108 c1: glm's connection dropped after 420 s was first written 'failed before any
    cost'.)"""
    tok = [((r.get("usage") or {}).get("prompt_tokens") or 0, len(prompts.get(rid) or "")) for rid, r in results.items()]
    tok = [(t, n) for t, n in tok if t > 0 and n > 0]
    per_char = sum(t for t, _ in tok) / sum(n for _, n in tok) if tok else None   # measured on this cycle's prompts
    out = {}
    for rid, r in results.items():
        out[rid] = {"usd": float(r.get("cost_usd") or 0.0), "basis": "reported"}
    for rid in errors:
        ec = error_costs.get(rid) or {}
        if isinstance(ec.get("cost_usd"), (int, float)):
            out[rid] = {"usd": float(ec["cost_usd"]), "basis": f"reported (failed: {ec.get('kind')})"}
        elif ec.get("kind") == "timeout" or (ec.get("http_status") is None and
                                             float(ec.get("seconds") or 0.0) >= CUT_S):
            rate, basis = _rate(rid, rates)
            own = len(prompts.get(rid) or "")      # its own prompt (cycle 2 prompts differ: audit b108 c2), at the
            tokens = own * per_char if per_char and own else (own / 3.0 if own else  # answered reviews' tokens per
                     sum(t for t, _ in tok) / len(tok) if tok else 0.0)               # character, else 3 a token
            what = ("abandoned" if ec.get("kind") == "timeout" else
                    f"cut off after {ec.get('seconds')} s in flight ({ec.get('kind')})")
            out[rid] = ({"usd": rate * tokens, "basis": f"{what}: {basis} x {int(tokens)} prompt tokens"}
                        if rate is not None else {"usd": 0.0, "basis": f"{what}: {basis}"})
        else:
            out[rid] = {"usd": 0.0, "basis": f"failed in {ec.get('seconds')} s with no cost reported "
                                             f"({ec.get('kind') or 'no reply'}, status {ec.get('http_status')}): "
                                             "not booked"}
    return out


def cost_path(out):
    return os.path.join(os.path.dirname(os.path.abspath(out)), "COST.json")


def cap_check(out, cap, estimate):
    """The audit's spend so far (COST.json beside the cycle folders); raises SystemExit when the next cycle's estimate
    could pass the cap (ruling 107 (2)): nothing is sent."""
    spent = 0.0
    if os.path.exists(cost_path(out)):
        with open(cost_path(out)) as f:
            spent = float(json.load(f).get("total_usd") or 0.0)
    if spent + estimate > cap:
        raise SystemExit(f"REFUSED: this audit has spent ${spent:.4f} of its ${cap:.2f} cap (ruling 107 (2)) and the "
                         f"next cycle may cost ${estimate:.4f}: nothing sent")
    return spent


def record(out, cycle, booked, cap, lines, ledger=None, now=None):
    """COST.json (the audit folder's cycles, each review's cost and basis, the total) and one ledger record per review
    (ruling 108's batch line reads the ledger)."""
    now = time.time() if now is None else now
    path = cost_path(out)
    rec = {"cap_usd": cap, "changed_lines": lines, "cycles": {}}
    if os.path.exists(path):
        with open(path) as f:
            rec = json.load(f)
    cyc = rec["cycles"].setdefault(f"c{cycle}", {"reviews": {}})
    for rid, b in booked.items():
        key, k = rid, 1
        while key in cyc["reviews"]:                  # a leg run again costs again: kept beside the first
            k += 1
            key = f"{rid} (run {k})"
        cyc["reviews"][key] = b
    cyc["usd"] = round(sum(b["usd"] for b in cyc["reviews"].values()), 6)
    rec["total_usd"] = round(sum(c["usd"] for c in rec["cycles"].values()), 6)
    rec["updated_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now))
    tmp = f"{path}.{os.getpid()}.tmp"              # whole or not at all (audit b108 c1, qwen): a torn COST.json would
    with open(tmp, "w") as f:                      # stop every later cycle of the audit (cap_check cannot read it)
        json.dump(rec, f, indent=1)
    os.replace(tmp, path)
    ledger = ledger or config.paths()["audit_spend"]
    os.makedirs(os.path.dirname(ledger), exist_ok=True)
    audit = os.path.relpath(os.path.dirname(os.path.abspath(out)), REPO)
    block = "".join(json.dumps({"ts": now, "at": rec["updated_utc"], "audit": audit, "cycle": cycle, "reviewer": rid,
                                "usd": round(b["usd"], 6), "basis": b["basis"],
                                "reported": b["basis"].startswith("reported")}) + "\n" for rid, b in booked.items())
    with open(ledger, "a") as f:                   # one write for the cycle's records (audit b108 c2); a torn line is
        f.write(block)                             # said on line 1 as unreadable, never counted silently
    return rec


def call(rid, cfg, prompt, results, errors, kr, error_costs=None):
    b = providers.make_backend(rid, dict(cfg, enabled=True), kr)
    t0 = time.time()
    try:
        r = b.complete(prompt, None, max_out(cfg))
        results[rid] = {"model": r.model, "content": r.content, "usage": r.usage, "cost_usd": r.cost_usd,
                        "seconds": round(time.time() - t0, 1), "finish_reason": r.finish_reason}
        print(f"  [{rid}] done {time.time() - t0:.0f} s, {len(r.content)} chars, ${r.cost_usd:.3f}", flush=True)
    except Exception as e:
        errors[rid] = f"{type(e).__name__}: {e}"[:500]
        if error_costs is not None and isinstance(e, providers.BackendError):     # a failed call is spend too
            error_costs[rid] = {"usage": e.usage, "cost_usd": e.cost_usd, "kind": e.kind,
                                "http_status": e.http_status, "seconds": round(time.time() - t0, 1)}
        print(f"  [{rid}] ERROR {errors[rid][:200]}", flush=True)


def chosen(only=None):
    """The reviewers of this cycle: --only, else ruling 107 (2)'s two families; a frozen vendor's are skipped."""
    want = set(only) if only else set(DEFAULT)
    fz = frozen()
    skipped = {rid: f"spend freeze: vendor {REVIEWERS[rid]['vendor']!r}" for rid in want
               if rid in REVIEWERS and REVIEWERS[rid]["vendor"] in fz}
    unknown = sorted(want - set(REVIEWERS))
    if unknown:
        raise SystemExit(f"unknown reviewer(s) {unknown}")
    return [rid for rid in REVIEWERS if rid in want and rid not in skipped], skipped


def fire(prompt_for, out, only=None):
    kr = providers.Keyring(ENV)
    results, errors = {}, {}
    run, skipped = chosen(only)
    for rid, why in skipped.items():
        print(f"  [{rid}] SKIPPED ({why})", flush=True)
    error_costs = {}
    prompts = {rid: prompt_for(rid) for rid in run}
    th = [threading.Thread(target=call, args=(rid, REVIEWERS[rid], prompts[rid], results, errors, kr, error_costs))
          for rid in run]
    for t in th:
        t.start()
    for t in th:
        t.join()
    os.makedirs(out, exist_ok=True)
    for rid, r in results.items():
        with open(os.path.join(out, f"{rid}.md"), "w") as f:
            f.write(f"# {rid} ({r['model']}, {r['seconds']} s, ${r['cost_usd']:.3f}, finish {r['finish_reason']})\n\n"
                    + r["content"])
    path = os.path.join(out, "results.json")
    prev = {}
    if only and os.path.exists(path):              # a re-run of some legs keeps the others' records
        with open(path) as f:
            prev = json.load(f)
    rec = {"results": dict(prev.get("results") or {}), "errors": dict(prev.get("errors") or {}),
           "error_costs": dict(prev.get("error_costs") or {}), "skipped": dict(prev.get("skipped") or {}),
           "earlier_attempts": list(prev.get("earlier_attempts") or [])}
    for rid in set(results) | set(errors):
        if rid in rec["errors"] or rid in rec["results"]:
            rec["earlier_attempts"].append({"reviewer": rid, "error": rec["errors"].pop(rid, None),
                                            "error_cost": rec["error_costs"].pop(rid, None),
                                            "result": rec["results"].pop(rid, None)})
    rec["results"].update({k: {kk: vv for kk, vv in v.items() if kk != "content"} for k, v in results.items()})
    rec["errors"].update(errors)
    rec["error_costs"].update(error_costs)
    rec["skipped"].update(skipped)
    with open(path, "w") as f:
        json.dump(rec, f, indent=1)
    return results, errors, error_costs, prompts


def max_out(cfg):
    """A review's reply budget in tokens."""
    return max(16000, int(cfg.get("max_tokens_floor", 0)))


def _price(rid):
    """The list price of the reviewer's model (providers.json, the same model): {in_per_mtok, out_per_mtok} or None."""
    model = REVIEWERS[rid].get("model")
    for b in providers.load_config()["backends"].values():
        p = b.get("price") or {}
        if b.get("model") == model and p.get("in_per_mtok") is not None and p.get("out_per_mtok") is not None:
            return p
    return None


def estimate(prompt_for, only, rates):
    """The most the next cycle can cost, for the cap's check before any call: each reviewer's prompt (3 characters a
    token, over-counting code) and its whole reply budget at its model's list price, with half again for the
    tokenizer; a reviewer without a list price at 4 x its own rate (else the highest rate known) on the prompt and the
    reply budget. (Cycle 1 of b108: qwen's reported $0.009 passed the doubled own-rate guess of $0.006: a long reply.)"""
    run, _ = chosen(only)
    top = max([r for r, _ in rates.values()] or [0.0])
    total = 0.0
    for rid in run:
        tokens, out = len(prompt_for(rid)) / 3.0, max_out(REVIEWERS[rid])
        p = _price(rid)
        if p is not None:
            total += 1.5 * (tokens * float(p["in_per_mtok"]) + out * float(p["out_per_mtok"])) / 1e6
        else:
            rate, _ = _rate(rid, rates)
            total += 4.0 * (rate if rate is not None else top) * (tokens + out)
    return total


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cycle", type=int, required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--c1")
    ap.add_argument("--consensus")
    ap.add_argument("--only", help="comma-separated reviewer ids (a failed leg again, or the third family)")
    ap.add_argument("--base", required=True, help="the change since this revision: its diff is the package")
    ap.add_argument("--context", help="a text file with the orders / design the change answers")
    a = ap.parse_args()
    only = set(a.only.split(",")) if a.only else None
    lines = changed_lines(a.base)
    cap = SMALL_CAP if lines < SMALL_LINES else BIG_CAP
    pkg = package(a.base, a.context)
    os.makedirs(a.out, exist_ok=True)
    open(os.path.join(a.out, "PACKAGE.md"), "w").write(pkg)
    if a.cycle == 1:
        def prompt_for(rid):
            return pkg
    else:
        import cross_llm_audit as tool
        c1 = {}
        for f in sorted(os.listdir(a.c1)):
            if f.endswith(".md") and f != "PACKAGE.md":
                c1[f[:-3]] = open(os.path.join(a.c1, f)).read()
        consensus = open(a.consensus).read()

        def prompt_for(rid):
            p = tool.build_cycle2_prompt("pp-ingest", pkg, c1, consensus)
            mine = c1.get(rid)
            return p.replace("[See below — you wrote this]", (mine or "(you did not answer in cycle 1)")[:6000])
    rates = _rates()
    est = estimate(prompt_for, only, rates)
    spent = cap_check(a.out, cap, est)
    print(f"package {len(pkg)} chars; {lines} changed lines: cap ${cap:.2f}; spent ${spent:.4f}; this cycle at most "
          f"${est:.4f} (list price, the whole reply budget)", flush=True)
    results, errors, error_costs, prompts = fire(prompt_for, a.out, only)
    rec = record(a.out, a.cycle, book(results, errors, error_costs, prompts, rates), cap, lines)
    print(f"cycle {a.cycle}: ${rec['cycles'][f'c{a.cycle}']['usd']:.4f}; the audit ${rec['total_usd']:.4f} of its "
          f"${cap:.2f} cap ({cost_path(a.out)})", flush=True)


if __name__ == "__main__":
    main()
