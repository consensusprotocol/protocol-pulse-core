#!/usr/bin/env python3
"""
PROTOCOL PULSE — CROSS-LLM CODE AUDIT ENGINE
Full two-cycle audit: build code → Cycle 1 (3 LLMs) → consensus → Cycle 2 (3 LLMs review each other)
→ final winner determination → second Claude Code pass prompt generated

Usage:
    python3 cross_llm_audit.py --feature f1-avatar-oracle
    python3 cross_llm_audit.py --feature all
    python3 cross_llm_audit.py --feature f1-avatar-oracle --cycle 2 --cycle1-results /path/to/c1.json

Requirements in .env:
    GEMINI_API_KEY=...
    OPENAI_API_KEY=...
    XAI_API_KEY=...
    ANTHROPIC_API_KEY=...

Created: 2026-03-09
"""

import os, sys, json, time, threading, argparse, subprocess
from pathlib import Path
from datetime import datetime

# ─── CONFIG ──────────────────────────────────────────────────────────────────

BASE = Path.home() / "protocol_pulse"
GOSPELS = BASE / "docs/gospels"
AUDITS  = BASE / "docs/audits"
AUDITS.mkdir(parents=True, exist_ok=True)

FEATURE_MAP = {
    "f1-avatar-oracle":  ("F1_AVATAR_ORACLE_GOSPEL.md",  "feature/f1-avatar-oracle"),
    "f2-briefing-room":  ("F2_BRIEFING_ROOM_GOSPEL.md",  "feature/f2-briefing-room"),
    "f3-schiff-bot":     ("F3_SCHIFF_BOT_GOSPEL.md",     "feature/f3-schiff-bot"),
    "f4-nostr":          ("F4_NOSTR_GOSPEL.md",          "feature/f4-nostr"),
    "f5-node-watch":     ("F5_NODE_WATCH_GOSPEL.md",     "feature/f5-node-watch"),
    "f6-marketing-os":   ("F6_MARKETING_OS_GOSPEL.md",   "feature/f6-marketing-os"),
    "v30-terminal-api":  ("V30_TERMINAL_API_GOSPEL.md",  "feature/v30-terminal-api"),
    "b1-newsletter":     ("B1_NEWSLETTER_GOSPEL.md",     "feature/b1-newsletter"),
    "v22-multi-format":  ("V22_MULTI_FORMAT_GOSPEL.md",  "feature/v22-multi-format"),
    "video-audio-fix":   ("VIDEO_AUDIO_FIX_GOSPEL.md",   "feature/video-audio-fix"),
    "f6-price-alerts":  ("F6_PRICE_ALERTS_GOSPEL.md",   "feature/f6-price-alerts"),
    "f8-sponsor-agent": ("P3_SPONSOR_AGENT_GOSPEL.md",  "feature/f8-sponsor-agent"),
    "f4-cron-heygen":   ("F4_CRON_HEYGEN_GOSPEL.md",   "feature/f4-cron-heygen"),
    "stripe_commander": ("F1_STRIPE_COMMANDER_GOSPEL.md", "feature/f1-stripe-commander"),
    "article_page_laws": ("ARTICLE_PAGE_LAWS.md", "feature/f2-article-laws"),
    "tts-pipeline": ("TTS_PIPELINE_AUDIT_GOSPEL.md", "feature/tts-pipeline"),
}

# High-stakes features get full 2-cycle audit. Others can use 1-cycle if score > 85.
HIGH_STAKES = {"f1-avatar-oracle", "v30-terminal-api", "v22-multi-format", "f2-briefing-room"}

# ─── AUDIT PACKAGE BUILDER ───────────────────────────────────────────────────

def build_audit_package(feature_name: str) -> str:
    """Pull all new/modified files from feature branch and assemble audit package."""
    gospel_file, branch = FEATURE_MAP[feature_name]
    gospel_text = (GOSPELS / gospel_file).read_text()

    # Extract just the LAWS section from gospel
    laws_section = ""
    in_laws = False
    for line in gospel_text.split("\n"):
        if "## THE LAWS" in line:
            in_laws = True
        elif line.startswith("## ") and in_laws and "LAW" not in line:
            in_laws = False
        if in_laws:
            laws_section += line + "\n"

    # Get diff vs main
    print(f"  [PACKAGE] Pulling code diff for {branch}...")
    try:
        diff_files = subprocess.check_output(
            ["git", "diff", "main.." + branch, "--name-only"],
            cwd=BASE, text=True
        ).strip().split("\n")
        diff_files = [f for f in diff_files if f]
    except Exception as e:
        print(f"  [PACKAGE] Git diff failed: {e}. Using worktree scan.")
        worktree = Path.home() / f"worktrees/{feature_name}"
        if worktree.exists():
            diff_files = [
                str(p.relative_to(worktree))
                for p in worktree.rglob("*.py")
                if "pycache" not in str(p)
            ] + [
                str(p.relative_to(worktree))
                for p in worktree.rglob("*.html")
                if "pycache" not in str(p)
            ]
        else:
            diff_files = []

    # Build code section
    code_sections = []
    worktree = Path.home() / f"worktrees/{feature_name}"
    for fpath in diff_files[:20]:  # cap at 20 files to stay within context
        full_path = worktree / fpath if worktree.exists() else BASE / fpath
        if full_path.exists() and full_path.stat().st_size < 100_000:
            try:
                code = full_path.read_text()
                lines = code.split("\n")
                numbered = "\n".join(f"{i+1:4d} | {l}" for i, l in enumerate(lines))
                code_sections.append(f"\n### File: {fpath} ({len(lines)} lines)\n```\n{numbered}\n```")
            except Exception:
                pass

    code_block = "\n".join(code_sections) if code_sections else "(No code files found — run after Claude Code session completes)"

    # Assemble the full audit package
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M UTC")
    package = f"""# PROTOCOL PULSE — CODE AUDIT PACKAGE
# Feature: {feature_name}
# Branch: {branch}
# Generated: {timestamp}
# Purpose: Pre-merge quality gate. 3 independent AI models will review this.
# You are one of: Gemini 2.5 Pro / GPT-4o / Grok-3
# Other top AI models will also review this same code. Put your best work forward.

---

## WHAT THIS FEATURE DOES
{gospel_text.split("## WHAT THIS FEATURE IS")[1].split("##")[0].strip() if "## WHAT THIS FEATURE IS" in gospel_text else "(see gospel)"}

---

## GOVERNING LAWS (this code MUST comply with every law below — flag any violation)
{laws_section}

---

## TECHNOLOGY STACK
- Python 3.12, Flask 3.x, SQLite via SQLAlchemy ORM
- Ubuntu 24.04 on Ultron server (2x RTX 4090, 93GB RAM)
- All UI animations: CSS/SVG only — NO Three.js, no WebGL, no Canvas
- External services: ElevenLabs TTS, HeyGen avatars, Wav2Lip GPU lip-sync
- ~1000 concurrent users at peak — every route must handle load
- Every DB query on a sort/filter column MUST have an index

---

## THE CODE (every new and modified file)
{code_block}

---

## YOUR REVIEW TASK

Perform a forensic code review. Be brutally honest. Cite line numbers.
There is no developer present. No ego to protect. Only quality matters.

### SECTION 1: CORRECTNESS
Walk through the main user flow step by step. Does the code do what it claims?
- Logic errors, wrong variable names, silent failures
- Race conditions (concurrent requests hitting same state)
- N+1 query problems (DB queries inside loops)
- Edge cases that will break in production (empty DB, API timeout, bad input)

### SECTION 2: LAW COMPLIANCE
For each LAW in the governing spec above, state: COMPLIANT / VIOLATION / PARTIAL
Cite specific line numbers for any violation or partial compliance.

### SECTION 3: SECURITY
- SQL injection (check raw queries and ORM filter() with user input)
- Authentication bypasses (routes that should require login but don't)
- Rate limiting gaps (can one user exhaust paid API limits?)
- Secrets in code (API keys, tokens, passwords hardcoded anywhere?)
- Unvalidated user input reaching DB, filesystem, or shell

### SECTION 4: FRONTEND QUALITY
- Does the UI match the spec layout exactly?
- Hardcoded values that should be dynamic (prices, counts, dates)
- Mobile viewport breakage
- JS errors that prevent page functioning
- Loading / error / empty state for every async operation — are all 3 handled?
- Does it look world-class? Or does it look like a rushed prototype?

### SECTION 5: BACKEND QUALITY
- DB operations: try/except with rollback on every write?
- External API calls: timeout + retry + graceful degradation on every call?
- Cron job: does it handle failure without crashing the service?
- Memory leaks: large objects created per-request without cleanup?
- Logging: are errors logged with enough context to debug production issues?

### SECTION 6: WORLD-CLASS GAP ANALYSIS
This is Protocol Pulse — a premium Bitcoin intelligence product.
What would Bloomberg Terminal, Coinbase Advanced, or Blockworks do differently?
What is genuinely missing that would make this impressive to a professional?
DO NOT pad this section. Only include changes with material impact.
If an area is already excellent, explicitly say so — that's equally important.

### SECTION 7: SCORES (0-100 each)
- Backend logic:    X/100
- Frontend/UI:      X/100
- Error handling:   X/100
- Security:         X/100
- Performance:      X/100
- Law compliance:   X/100
- World-class gap:  X/100 (100 = nothing missing, 0 = prototype quality)
- OVERALL:          X/100

### SECTION 8: PRIORITY ACTION PLAN
Every fix and improvement, sorted by impact. Be specific — cite file and line.
Format exactly as:
P0 CRITICAL | [what] | [file:line] | [why it will break production]
P1 HIGH     | [what] | [file:line] | [why it degrades quality]
P2 MEDIUM   | [what] | [file:line] | [enhancement that matters]
P3 LOW      | [what] | [file:line] | [polish]

### SECTION 9: THE ONE THING
If you could only tell the developer one thing to make this dramatically better,
what would it be? One sentence. Make it count.

### SECTION 10: FINAL VERDICT
In 2-3 sentences: is this code ready for production? What must change first?
"""
    return package


# ─── LLM CALLERS ─────────────────────────────────────────────────────────────

def call_gemini(prompt: str, results: dict, errors: dict):
    try:
        from google import genai as google_genai
        client = google_genai.Client(api_key=os.environ["GEMINI_API_KEY"])
        GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-pro")
        resp = client.models.generate_content(model=GEMINI_MODEL, contents=prompt)
        results["gemini"] = resp.text
        score_hint = "?"
        for line in resp.text.split("\n"):
            if "OVERALL" in line.upper() and "/100" in line:
                score_hint = line.strip()
                break
        print(f"  [GEMINI] ✅ Done — {score_hint}")
    except Exception as e:
        errors["gemini"] = str(e)
        print(f"  [GEMINI] ❌ ERROR: {e}")

def call_gpt4o(prompt: str, results: dict, errors: dict):
    try:
        from openai import OpenAI
        client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
        resp = client.chat.completions.create(
            model="gpt-5.4",
            messages=[{"role": "user", "content": prompt}],
            max_completion_tokens=6000,
            temperature=0.3,
        )
        results["gpt4o"] = resp.choices[0].message.content
        print(f"  [GPT-4o] ✅ Done")
    except Exception as e:
        errors["gpt4o"] = str(e)
        print(f"  [GPT-4o] ❌ ERROR: {e}")

def call_grok(prompt: str, results: dict, errors: dict):
    try:
        from openai import OpenAI
        client = OpenAI(
            api_key=os.environ["XAI_API_KEY"],
            base_url="https://api.x.ai/v1"
        )
        resp = client.chat.completions.create(
            model="grok-3-latest",
            messages=[{"role": "user", "content": prompt}],
            max_completion_tokens=6000,
            temperature=0.3,
        )
        results["grok"] = resp.choices[0].message.content
        print(f"  [GROK]   ✅ Done")
    except Exception as e:
        errors["grok"] = str(e)
        print(f"  [GROK]   ❌ ERROR: {e}")

def fire_all_llms(prompt: str) -> tuple[dict, dict]:
    """Fire all 3 LLMs in parallel threads. Returns (results, errors)."""
    results, errors = {}, {}
    threads = [
        threading.Thread(target=call_gemini, args=(prompt, results, errors)),
        threading.Thread(target=call_gpt4o,  args=(prompt, results, errors)),
        threading.Thread(target=call_grok,   args=(prompt, results, errors)),
    ]
    for t in threads: t.start()
    for t in threads: t.join()
    return results, errors


# ─── CONSENSUS SYNTHESIS ─────────────────────────────────────────────────────

def synthesize_consensus(feature: str, cycle: int, results: dict, errors: dict,
                          prev_results: dict = None) -> str:
    """Claude synthesizes all LLM outputs into consensus report."""
    import anthropic
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    models_output = []
    for name, text in results.items():
        models_output.append(f"## {name.upper()} OUTPUT\n{text[:8000]}")

    prev_section = ""
    if prev_results:
        prev_section = "\n\n## CYCLE 1 RESULTS (for context)\n"
        for name, text in prev_results.items():
            prev_section += f"### {name.upper()} CYCLE 1\n{text[:3000]}\n\n"

    synthesis_prompt = f"""You are synthesizing a Cycle {cycle} multi-LLM code audit for Protocol Pulse feature: {feature}

Three independent AI models (Gemini 2.5 Pro, GPT-4o, Grok-3) reviewed the same code.
{prev_section}

Their Cycle {cycle} outputs:

{"".join(models_output)}

Errors/failures: {json.dumps(errors) if errors else "None"}

Produce the CONSENSUS REPORT with these exact sections:

# CONSENSUS REPORT — {feature.upper()} — CYCLE {cycle}
Generated: {datetime.now().strftime("%Y-%m-%d %H:%M")}
Models: {", ".join(results.keys())} {"(+" + str(len(errors)) + " failed)" if errors else ""}

## SCORES
| Subsystem       | Gemini | GPT-4o | Grok | Consensus |
|-----------------|--------|--------|------|-----------|
[extract scores from each model's output and populate the table]

## UNANIMOUS FINDINGS (all {len(results)} models agree — implement unconditionally)
[List every issue flagged by ALL models. These are the highest-confidence fixes.]
For each: what it is, which file/line, what to change.

## MAJORITY FINDINGS (2 of {len(results)} models agree)
[Issues flagged by 2+ models. Implement unless there's a compelling reason not to.]

## UNIQUE INSIGHTS (only 1 model caught this — evaluate carefully)
[Novel observations from a single model. Some will be the most valuable findings.]
Your assessment of each: implement / skip / investigate further.

## CONFLICTS (models disagree — your tiebreaker)
[Where models gave contradictory recommendations. State who is right and why.]

## VALIDATED STRENGTHS (all models agree this is already excellent)
[These areas are strong. Do NOT change them in the second pass.]

## LAW COMPLIANCE CONSENSUS
Which laws are violated? Which are fully compliant? Final determination.

## SECURITY CONSENSUS
Any security issues all/most models flagged? Priority order.

## WORLD-CLASS GAP CONSENSUS
What does the combined intelligence of 3 models say is missing from a
truly world-class product? Only include items 2+ models mentioned.

## FINAL ACTION PLAN (sorted by consensus priority)
P0 CRITICAL | [change] | [file:line] | [models: all/2/unique] | [why]
P1 HIGH     | [change] | [file:line] | [models] | [why]
P2 MEDIUM   | [change] | [file:line] | [models] | [why]

## CYCLE {cycle} VERDICT
{'Is the code ready for a second build pass, or does it need fundamental rework?' if cycle == 1 else 'After two full cycles of 3-model review: is this code production-ready? What is the absolute final blocker if any?'}

## SECOND PASS PROMPT (ready to fire into Claude Code)
```
Read ~/protocol_pulse/docs/gospels/{FEATURE_MAP.get(feature, ('GOSPEL.md',''))[0]}.
Read ~/protocol_pulse/docs/audits/{feature}_CONSENSUS_C{cycle}.md.

This is the {'SECOND' if cycle == 1 else 'FINAL'} PASS for {feature}.
The first build was reviewed by {len(results)} independent AI models across {cycle} cycle(s).
Implement every P0 and P1 item from the consensus. Use judgment on P2.

PRIORITY ACTION PLAN:
[copy the action plan from above]

VALIDATED (do NOT touch — all models confirmed excellent):
[copy validated strengths]

After implementing: regression_test.sh must show zero FAILs.
git add -A && git commit -m "feat({feature}): post-audit pass — consensus improvements"
git push origin {FEATURE_MAP.get(feature, ('','feature/'+feature))[1]}
```
"""

    msg = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=6000,
        messages=[{"role": "user", "content": synthesis_prompt}]
    )
    return msg.content[0].text


# ─── CYCLE 2 PACKAGE BUILDER ─────────────────────────────────────────────────

def build_cycle2_prompt(feature: str, original_package: str,
                         c1_results: dict, c1_consensus: str) -> str:
    """Build the Cycle 2 prompt where each LLM sees what the others said."""
    others_text = "\n\n".join(
        f"## {name.upper()} — CYCLE 1 OUTPUT\n{text[:5000]}"
        for name, text in c1_results.items()
    )
    return f"""# PROTOCOL PULSE — CYCLE 2 CODE AUDIT
# Feature: {feature}
# You are performing your SECOND review of this code.
# You now have access to what the other AI models said in Cycle 1.

---

## YOUR CYCLE 1 OUTPUT (what you said before)
[See below — you wrote this]

## WHAT THE OTHER MODELS SAID (Cycle 1)
{others_text}

## CLAUDE'S CYCLE 1 CONSENSUS
{c1_consensus[:3000]}

---

## ORIGINAL CODE (same code as Cycle 1)
{original_package[original_package.find("## THE CODE"):original_package.find("## YOUR REVIEW TASK")]}

---

## CYCLE 2 INSTRUCTIONS

You've now seen what the other models said. This is your final review.

1. WHAT DID THEY CATCH THAT YOU MISSED?
   Review their findings. Be honest about what you overlooked.

2. WHERE DO YOU AGREE OR DISAGREE?
   For each of their key findings: agree / disagree / partially agree + why.

3. NEW FINDINGS FROM THIS REVIEW
   Anything the combined analysis revealed that nobody caught in Cycle 1?

4. REVISED SCORES
   Update your scores from Cycle 1. Did anything change your assessment?
   | Subsystem | Cycle 1 | Cycle 2 | Why changed |

5. FINAL PRIORITY LIST
   Your definitive list of what must change before this ships.
   P0 CRITICAL | P1 HIGH | P2 MEDIUM — cite file and line numbers.

6. THE SINGLE HIGHEST-LEVERAGE CHANGE
   After seeing everything — one sentence. What matters most?

7. PRODUCTION READY?
   Yes / No / Yes with conditions. State your conditions precisely.
"""


# ─── MAIN RUNNER ─────────────────────────────────────────────────────────────

def run_audit(feature: str, start_cycle: int = 1, c1_results_path: str = None):
    print(f"\n{'='*60}")
    print(f"PROTOCOL PULSE CROSS-LLM AUDIT — {feature.upper()}")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}\n")

    # Verify API keys
    missing_keys = [k for k in ["GEMINI_API_KEY", "OPENAI_API_KEY", "XAI_API_KEY", "ANTHROPIC_API_KEY"]
                    if not os.environ.get(k)]
    if missing_keys:
        print(f"❌ MISSING API KEYS: {missing_keys}")
        print("Add them to ~/protocol_pulse/.env and re-run.")
        sys.exit(1)
    print(f"✅ All API keys present\n")

    audit_dir = AUDITS / feature
    audit_dir.mkdir(parents=True, exist_ok=True)

    # ── CYCLE 1 ───────────────────────────────────────────────────────────────
    if start_cycle == 1:
        print("── CYCLE 1: BUILDING AUDIT PACKAGE ────────────────────────────")
        package = build_audit_package(feature)
        (audit_dir / "AUDIT_PACKAGE.md").write_text(package)
        print(f"  Package written: {len(package):,} chars\n")

        print("── CYCLE 1: FIRING 3 LLMs IN PARALLEL ─────────────────────────")
        c1_results, c1_errors = fire_all_llms(package)
        (audit_dir / "C1_GEMINI.md").write_text(c1_results.get("gemini", f"FAILED: {c1_errors.get('gemini')}"))
        (audit_dir / "C1_GPT4O.md").write_text(c1_results.get("gpt4o",  f"FAILED: {c1_errors.get('gpt4o')}"))
        (audit_dir / "C1_GROK.md").write_text(c1_results.get("grok",   f"FAILED: {c1_errors.get('grok')}"))
        print(f"\n  Cycle 1 complete: {list(c1_results.keys())} succeeded, {list(c1_errors.keys())} failed\n")

        print("── CYCLE 1: SYNTHESIZING CONSENSUS ─────────────────────────────")
        c1_consensus = synthesize_consensus(feature, 1, c1_results, c1_errors)
        (audit_dir / "C1_CONSENSUS.md").write_text(c1_consensus)
        print("  Consensus written\n")
    else:
        # Load from previous run
        print("── LOADING CYCLE 1 RESULTS ─────────────────────────────────────")
        c1_results = {
            "gemini": (audit_dir / "C1_GEMINI.md").read_text(),
            "gpt4o":  (audit_dir / "C1_GPT4O.md").read_text(),
            "grok":   (audit_dir / "C1_GROK.md").read_text(),
        }
        c1_consensus = (audit_dir / "C1_CONSENSUS.md").read_text()
        package = (audit_dir / "AUDIT_PACKAGE.md").read_text()
        print("  Loaded from previous run\n")

    # Check if we need Cycle 2 (skip for low-stakes if high score)
    run_cycle2 = feature in HIGH_STAKES
    if not run_cycle2:
        # Check if overall score > 85 across all models
        scores = []
        for text in c1_results.values():
            for line in text.split("\n"):
                if "OVERALL" in line.upper() and "/100" in line:
                    try:
                        score = int(''.join(filter(str.isdigit, line.split("/")[0].split()[-1])))
                        scores.append(score)
                    except: pass
        avg_score = sum(scores) / len(scores) if scores else 0
        run_cycle2 = avg_score < 85
        print(f"  Average Cycle 1 score: {avg_score:.0f}/100 — {'Running Cycle 2' if run_cycle2 else 'Score high enough, skipping Cycle 2'}\n")

    if run_cycle2:
        # ── CYCLE 2 ───────────────────────────────────────────────────────────
        print("── CYCLE 2: BUILDING CROSS-REVIEW PROMPT ───────────────────────")
        c2_prompt = build_cycle2_prompt(feature, package, c1_results, c1_consensus)
        (audit_dir / "C2_PROMPT.md").write_text(c2_prompt)

        print("── CYCLE 2: FIRING 3 LLMs WITH CROSS-VISIBILITY ────────────────")
        c2_results, c2_errors = fire_all_llms(c2_prompt)
        (audit_dir / "C2_GEMINI.md").write_text(c2_results.get("gemini", f"FAILED: {c2_errors.get('gemini')}"))
        (audit_dir / "C2_GPT4O.md").write_text(c2_results.get("gpt4o",  f"FAILED: {c2_errors.get('gpt4o')}"))
        (audit_dir / "C2_GROK.md").write_text(c2_results.get("grok",   f"FAILED: {c2_errors.get('grok')}"))
        print(f"\n  Cycle 2 complete: {list(c2_results.keys())} succeeded\n")

        print("── CYCLE 2: FINAL CONSENSUS + WINNER ───────────────────────────")
        final_consensus = synthesize_consensus(feature, 2, c2_results, c2_errors, c1_results)

        # Determine "winner" — the model whose Cycle 1 findings had the most
        # items validated by Cycle 2 consensus
        winner_prompt = f"""Based on this 2-cycle cross-LLM audit, determine which model (Gemini, GPT-4o, or Grok)
provided the highest-quality analysis overall.

Criteria:
1. Accuracy — did their findings prove correct in Cycle 2?
2. Depth — did they find issues others missed?
3. Actionability — were their recommendations specific and implementable?
4. Completeness — did they cover all sections thoroughly?

CYCLE 1 OUTPUTS: {json.dumps({k: v[:2000] for k,v in c1_results.items()})}
CYCLE 2 OUTPUTS: {json.dumps({k: v[:2000] for k,v in c2_results.items()})}
FINAL CONSENSUS: {final_consensus[:2000]}

State: WINNER: [model name] — [2 sentence justification]
Then: FINAL SECOND-PASS PRIORITY LIST — the definitive ordered list of what to implement."""

        import anthropic
        client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
        winner_msg = client.messages.create(
            model="claude-sonnet-4-6", max_tokens=2000,
            messages=[{"role": "user", "content": winner_prompt}]
        )
        winner_text = winner_msg.content[0].text

        final_report = final_consensus + "\n\n---\n\n# WINNER DETERMINATION\n\n" + winner_text
        (audit_dir / "FINAL_CONSENSUS.md").write_text(final_report)
    else:
        final_report = c1_consensus
        (audit_dir / "FINAL_CONSENSUS.md").write_text(final_report)

    # ── SUMMARY ───────────────────────────────────────────────────────────────
    print(f"\n{'='*60}")
    print(f"AUDIT COMPLETE — {feature.upper()}")
    print(f"{'='*60}")
    print(f"\nOutputs at: {audit_dir}/")
    print(f"  AUDIT_PACKAGE.md    — code package sent to LLMs")
    if run_cycle2:
        print(f"  C1_*.md             — Cycle 1 individual outputs")
        print(f"  C1_CONSENSUS.md     — Cycle 1 synthesis")
        print(f"  C2_*.md             — Cycle 2 individual outputs")
    print(f"  FINAL_CONSENSUS.md  — final action plan + second-pass prompt")
    print(f"\nNEXT: Fire the second-pass Claude Code session using the prompt")
    print(f"      in FINAL_CONSENSUS.md → '## SECOND PASS PROMPT' section")
    print(f"\n{'='*60}\n")

    # Print the second-pass prompt for immediate use
    for line in final_report.split("\n"):
        if "SECOND PASS PROMPT" in line.upper():
            idx = final_report.find(line)
            print("READY TO FIRE — SECOND PASS PROMPT:")
            print("-"*40)
            print(final_report[idx:idx+2000])
            break

    return final_report


# ─── ENTRY POINT ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    # Load .env
    env_path = Path.home() / "protocol_pulse/.env"
    if env_path.exists():
        for line in env_path.read_text().split("\n"):
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, val = line.partition("=")
                os.environ.setdefault(key.strip(), val.strip())

    parser = argparse.ArgumentParser(description="Cross-LLM code audit engine")
    parser.add_argument("--feature", required=True,
                        help=f"Feature to audit. Options: {list(FEATURE_MAP.keys()) + ['all']}")
    parser.add_argument("--cycle", type=int, default=1,
                        help="Start from cycle 1 (default) or 2 (resume)")
    parser.add_argument("--cycle1-results", help="Path to existing cycle 1 results dir")
    args = parser.parse_args()

    if args.feature == "all":
        for feat in FEATURE_MAP:
            if feat != "video-audio-fix":  # skip until PBX provides notes
                run_audit(feat, start_cycle=1)
                time.sleep(10)  # avoid API rate limits between features
    elif args.feature in FEATURE_MAP:
        run_audit(args.feature, start_cycle=args.cycle)
    else:
        print(f"Unknown feature: {args.feature}")
        print(f"Options: {list(FEATURE_MAP.keys())}")
        sys.exit(1)
