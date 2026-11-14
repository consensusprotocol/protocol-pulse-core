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

  python3 tests/ingest/xllm_audit.py --cycle 1 --out docs/audits/parallel/pp-ingest_audit/c1
  python3 tests/ingest/xllm_audit.py --cycle 2 --c1 docs/audits/parallel/pp-ingest_audit/c1 \
      --consensus docs/audits/parallel/pp-ingest_audit/C1_CONSENSUS.md --out docs/audits/parallel/pp-ingest_audit/c2

SPEND FREEZE (orchestrator 05:30 ET Nov 12): a reviewer whose vendor is in providers.json spend_freeze is never called
(skipped, and said so); the Heimdall-served reviewers of other model families stand in. --base / --context add the
diff of a later change and its orders to the package (the change is reviewed in full files plus its diff).
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

from pipeline.ingest import providers  # noqa: E402

ENV = "/home/ultron/protocol_pulse/.env"
BASE_REV = "c1451047"
FILES = ["pipeline/ingest/__init__.py", "pipeline/ingest/config.py", "pipeline/ingest/contract.py",
         "pipeline/ingest/providers.py", "pipeline/ingest/providers.json", "pipeline/ingest/spend.py",
         "pipeline/ingest/queue.py", "pipeline/ingest/watch.py", "pipeline/ingest/fetch.py", "pipeline/ingest/mine.py",
         "pipeline/ingest/ledger.py", "pipeline/ingest/coverage.py", "pipeline/ingest/stats.py",
         "pipeline/ingest/service.py", "pipeline/ingest/ab.py", "pipeline/ingest/flagcheck.py",
         "pipeline/ingest/purge.py", "pipeline/ingest/purge.json", "pipeline/ingest/downsignal.py",
         "tools/ingest_watch.py"]
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
- The integrator's merge audit (cycle 1) BLOCKING findings B1-B4 and its non-blocking list are in the change context
  below; the change must answer each without weakening any check.
Only report issues you can verify from the code provided. Do not speculate. Cite file:line."""


def package(files, extra="", base=None, context=None):
    import cross_llm_audit as tool
    head = subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=REPO, text=True).strip()
    parts = []
    for f in files:
        txt = open(os.path.join(REPO, f)).read()
        lines = txt.split("\n")
        parts.append(f"\n### File: {f} ({len(lines)} lines)\n```\n" +
                     "\n".join(f"{i + 1:4d} | {l}" for i, l in enumerate(lines)) + "\n```")
    tests = subprocess.run([sys.executable, "-m", "pytest", "tests/ingest", "--collect-only", "-q"], cwd=REPO,
                           capture_output=True, text=True).stdout
    design = open(os.path.join(REPO, "docs/audits/INGEST_DESIGN.md")).read()
    if base:
        diff = subprocess.check_output(["git", "diff", base, "--", "pipeline/ingest", "tools/ingest_watch.py"],
                                       cwd=REPO, text=True)
        extra = (extra + f"\n\n## THE CHANGE UNDER REVIEW: git diff {base} (working tree)\n"
                 + (open(context).read() if context else "") + f"\n```diff\n{diff}\n```\n")
    return f"""# PROTOCOL PULSE — CODE AUDIT PACKAGE
# Feature: pp-ingest (continuous ingest + first-pass moment mining)
# Branch: pp-ingest (base {BASE_REV}, working tree at {head} + the uncommitted files below = the ACTUAL diff: all new)
# Purpose: Pre-merge quality gate. Several independent AI models review this same code.

## WHAT THIS FEATURE DOES
{design}

## GOVERNING LAWS (this code MUST comply with every law below — flag any violation)
{LAWS}

## TECHNOLOGY STACK
- Python 3.10, stdlib sqlite3 / urllib / threads; yt-dlp subprocesses; the Anthropic SDK and google-genai for two
  back-ends; no GPU. Runs as one long-lived process (tmux), not cron.

## THE CODE (every new file of the diff; tests are listed by name after the code)
{''.join(parts)}

### Test inventory (tests/ingest, {tests.strip().splitlines()[-1] if tests.strip() else 'not collected'})
```
{tests.strip()}
```
{extra}

---

{tool.DEFAULT_REVIEW_TASK}
"""


def call(rid, cfg, prompt, results, errors, kr, error_costs=None):
    b = providers.make_backend(rid, dict(cfg, enabled=True), kr)
    t0 = time.time()
    try:
        r = b.complete(prompt, None, max(16000, int(cfg.get("max_tokens_floor", 0))))
        results[rid] = {"model": r.model, "content": r.content, "usage": r.usage, "cost_usd": r.cost_usd,
                        "seconds": round(time.time() - t0, 1), "finish_reason": r.finish_reason}
        print(f"  [{rid}] done {time.time() - t0:.0f} s, {len(r.content)} chars, ${r.cost_usd:.3f}", flush=True)
    except Exception as e:
        errors[rid] = f"{type(e).__name__}: {e}"[:500]
        if error_costs is not None and isinstance(e, providers.BackendError):     # a failed call is spend too
            error_costs[rid] = {"usage": e.usage, "cost_usd": e.cost_usd, "kind": e.kind,
                                "seconds": round(time.time() - t0, 1)}
        print(f"  [{rid}] ERROR {errors[rid][:200]}", flush=True)


def fire(prompt_for, out, only=None):
    kr = providers.Keyring(ENV)
    results, errors = {}, {}
    fz = frozen()
    skipped = {rid: f"spend freeze: vendor {cfg['vendor']!r}" for rid, cfg in REVIEWERS.items()
               if cfg["vendor"] in fz and (not only or rid in only)}
    for rid, why in skipped.items():
        print(f"  [{rid}] SKIPPED ({why})", flush=True)
    error_costs = {}
    th = [threading.Thread(target=call, args=(rid, cfg, prompt_for(rid), results, errors, kr, error_costs))
          for rid, cfg in REVIEWERS.items() if (not only or rid in only) and rid not in skipped]
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
    return results, errors


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cycle", type=int, required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--c1")
    ap.add_argument("--consensus")
    ap.add_argument("--only", help="comma-separated reviewer ids (re-run failed legs)")
    ap.add_argument("--base", help="review the change since this revision: its diff is added to the package")
    ap.add_argument("--context", help="a text file with the orders / findings the change answers")
    a = ap.parse_args()
    only = set(a.only.split(",")) if a.only else None
    if a.cycle == 1:
        pkg = package(FILES, base=a.base, context=a.context)
        os.makedirs(a.out, exist_ok=True)
        open(os.path.join(a.out, "PACKAGE.md"), "w").write(pkg)
        print(f"package {len(pkg)} chars")
        fire(lambda rid: pkg, a.out, only)
    else:
        import cross_llm_audit as tool
        c1 = {}
        for f in sorted(os.listdir(a.c1)):
            if f.endswith(".md") and f != "PACKAGE.md":
                c1[f[:-3]] = open(os.path.join(a.c1, f)).read()
        consensus = open(a.consensus).read()
        pkg = package(FILES, base=a.base, context=a.context)
        os.makedirs(a.out, exist_ok=True)
        open(os.path.join(a.out, "PACKAGE.md"), "w").write(pkg)

        def prompt_for(rid):
            p = tool.build_cycle2_prompt("pp-ingest", pkg, c1, consensus)
            mine = c1.get(rid)
            return p.replace("[See below — you wrote this]", (mine or "(you did not answer in cycle 1)")[:6000])
        fire(prompt_for, a.out, only)


if __name__ == "__main__":
    main()
