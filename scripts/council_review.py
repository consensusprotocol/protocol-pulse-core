#!/usr/bin/env python3
"""
LLM Council Code Reviewer — Stage 2 (mid-build) & Stage 3 (post-build) reviews.

Sends actual code to all available LLMs for scoring on:
  architecture, error handling, edge cases, security, performance, maintainability

Usage:
    # Review a single file (post-build)
    python scripts/council_review.py services/video_engine/self_healing.py

    # Review with feature context
    python scripts/council_review.py services/video_engine/monitoring.py \
        --feature "Production monitoring with anomaly detection"

    # Mid-build review (before commit)
    python scripts/council_review.py services/new_module.py --stage mid

    # Review multiple files
    python scripts/council_review.py services/video_engine/*.py --feature "Video pipeline"

    # Set minimum passing score (default 7)
    python scripts/council_review.py routes.py --min-score 8

As a module:
    from scripts.council_review import review_code, review_file
    result = review_file("services/video_engine/self_healing.py", feature="Self-healing pipeline")
"""

import os
import sys
import json
import glob
import argparse
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional

logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
log = logging.getLogger("council_review")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
REVIEWS_DIR = PROJECT_ROOT / "data" / "council_reviews"
REVIEWS_DIR.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# Review prompts
# ---------------------------------------------------------------------------

MID_BUILD_SYSTEM = """You are a senior code reviewer for Protocol Pulse — a production Bitcoin
intelligence platform. You review code BEFORE it is committed.

Tech stack: Python 3.11, Flask, SQLAlchemy, SQLite (WAL mode), Jinja2, vanilla JS.
Standards: Production-grade, OWASP-secure, fully tested, zero-downtime capable.

Score each dimension 1-10 and list specific improvements."""

POST_BUILD_SYSTEM = """You are a senior code reviewer performing a FINAL production review for
Protocol Pulse — a Bitcoin intelligence platform running on dual RTX 4090s.

This code has been committed. Your job is to determine if it is truly production-ready
and miles ahead of industry standard. Be rigorous. Be specific.

Score each dimension 1-10 and list EVERY issue that must be fixed before this ships."""

REVIEW_TEMPLATE = """Review this code for: {feature}

## Code ({filepath})
```python
{code}
```

Score 1-10 on each dimension:
1. **Architecture** — Clean structure, separation of concerns, extensibility
2. **Error Handling** — Graceful failures, proper exception types, recovery
3. **Edge Cases** — Boundary conditions, empty inputs, concurrent access
4. **Security** — Input validation, injection prevention, secrets handling
5. **Performance** — Efficiency, caching strategy, resource management
6. **Maintainability** — Readability, documentation, naming, testability

For each dimension:
- State the score
- List specific issues (with line references if possible)
- Suggest concrete improvements

End with:
- **Overall Score**: (average of all dimensions)
- **Production Ready**: YES / NO / WITH_FIXES
- **Critical Issues**: (list any blockers)
- **Recommended Improvements**: (prioritized list)
"""

CROSS_REVIEW_TEMPLATE = """You are cross-reviewing other reviewers' assessments of this code.

## Original Code ({filepath})
```python
{code}
```

## Reviews from other LLMs:
{reviews}

Evaluate:
1. Do you agree with the scores? Adjust where needed.
2. Did any reviewer miss critical issues?
3. Are any suggested improvements wrong or unnecessary?

Produce a FINAL CONSENSUS REVIEW with:
- Adjusted scores for each dimension
- Complete list of issues (merged from all reviews)
- Prioritized fix list
- Final verdict: SHIP / FIX_THEN_SHIP / REWRITE
"""

# ---------------------------------------------------------------------------
# LLM provider wrappers (reuse from llm_council.py)
# ---------------------------------------------------------------------------

def _query_openai(prompt: str, system: str) -> Optional[str]:
    api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not api_key:
        return None
    try:
        import openai
        client = openai.OpenAI(api_key=api_key)
        resp = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
            max_tokens=4096,
            temperature=0.3,
        )
        return resp.choices[0].message.content
    except Exception as e:
        log.error("OpenAI failed: %s", e)
        return None


def _query_xai(prompt: str, system: str) -> Optional[str]:
    api_key = os.environ.get("XAI_API_KEY", "").strip()
    if not api_key:
        return None
    try:
        import openai
        client = openai.OpenAI(api_key=api_key, base_url="https://api.x.ai/v1")
        resp = client.chat.completions.create(
            model="grok-3",
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
            max_tokens=4096,
            temperature=0.3,
        )
        return resp.choices[0].message.content
    except Exception as e:
        log.error("xAI/Grok failed: %s", e)
        return None


def _query_anthropic(prompt: str, system: str) -> Optional[str]:
    api_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if not api_key:
        return None
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)
        resp = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4096,
            system=system,
            messages=[{"role": "user", "content": prompt}],
        )
        return resp.content[0].text
    except Exception as e:
        log.error("Anthropic/Claude failed: %s", e)
        return None


def _query_gemini(prompt: str, system: str) -> Optional[str]:
    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not api_key:
        return None
    try:
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("gemini-2.0-flash", system_instruction=system)
        resp = model.generate_content(prompt)
        return resp.text
    except Exception as e:
        log.error("Gemini failed: %s", e)
        return None


PROVIDERS = {
    "openai": _query_openai,
    "grok": _query_xai,
    "claude": _query_anthropic,
    "gemini": _query_gemini,
}

# ---------------------------------------------------------------------------
# Local analysis (always available, no API keys needed)
# ---------------------------------------------------------------------------

def _local_analysis(code: str, filepath: str) -> dict:
    """Static analysis that runs without any API keys."""
    issues = []
    warnings = []
    lines = code.split("\n")
    scores = {
        "architecture": 7,
        "error_handling": 7,
        "edge_cases": 7,
        "security": 7,
        "performance": 7,
        "maintainability": 7,
    }

    # --- Architecture checks ---
    if len(lines) > 500:
        warnings.append(f"File is {len(lines)} lines — consider splitting into smaller modules")
        scores["architecture"] -= 1
    if len(lines) > 1000:
        issues.append(f"File is {len(lines)} lines — too large for single module")
        scores["architecture"] -= 1

    class_count = sum(1 for l in lines if l.strip().startswith("class "))
    if class_count > 5:
        warnings.append(f"{class_count} classes in one file — consider splitting")

    # --- Error handling checks ---
    bare_excepts = sum(1 for i, l in enumerate(lines)
                       if "except:" in l and "except:" == l.strip())
    if bare_excepts:
        issues.append(f"{bare_excepts} bare except clauses — catch specific exceptions")
        scores["error_handling"] -= 2

    broad_excepts = sum(1 for l in lines if "except Exception:" in l or "except Exception as" in l)
    if broad_excepts > 3:
        warnings.append(f"{broad_excepts} broad 'except Exception' — consider narrower types")
        scores["error_handling"] -= 1

    # --- Security checks ---
    if "eval(" in code:
        issues.append("CRITICAL: eval() usage detected — potential code injection")
        scores["security"] -= 3
    if "exec(" in code and "replit_exec" not in filepath:
        issues.append("WARNING: exec() usage detected — review for injection risk")
        scores["security"] -= 2
    if "subprocess" in code and "shell=True" in code:
        issues.append("WARNING: subprocess with shell=True — potential command injection")
        scores["security"] -= 2
    if "os.system(" in code:
        issues.append("WARNING: os.system() — use subprocess with shell=False instead")
        scores["security"] -= 1

    # SQL injection checks — look for f-strings directly inside .execute() calls
    import re as _re
    sql_injection_hits = _re.findall(r'\.execute\(\s*f["\']', code)
    # Also check .format() used to build SQL
    sql_format_hits = _re.findall(r'\.execute\([^)]*\.format\(', code)
    if sql_injection_hits or sql_format_hits:
        issues.append(f"CRITICAL: Possible SQL injection — {len(sql_injection_hits) + len(sql_format_hits)} f-string/format in .execute()")
        scores["security"] -= 3

    # Hardcoded secrets
    for i, line in enumerate(lines):
        lower = line.lower()
        if any(p in lower for p in ["password =", "secret =", "api_key ="]):
            if "os.environ" not in line and "getenv" not in line and '""' not in line and "''" not in line:
                issues.append(f"Line {i+1}: Possible hardcoded secret")
                scores["security"] -= 2

    # --- Performance checks ---
    if "time.sleep" in code:
        sleep_count = code.count("time.sleep")
        if sleep_count > 3:
            warnings.append(f"{sleep_count} time.sleep calls — consider async or event-driven")
            scores["performance"] -= 1

    if "SELECT *" in code.upper():
        warnings.append("SELECT * usage — specify columns for better performance")
        scores["performance"] -= 1

    # --- Maintainability checks ---
    has_docstrings = '"""' in code or "'''" in code
    if not has_docstrings and len(lines) > 50:
        warnings.append("No docstrings found in a substantial module")
        scores["maintainability"] -= 1

    # Type hints
    def_lines = [l for l in lines if l.strip().startswith("def ")]
    typed_defs = [l for l in def_lines if "->" in l or ("(" in l and ": " in l.split("(", 1)[-1])]
    if def_lines and len(typed_defs) / max(len(def_lines), 1) < 0.3:
        warnings.append(f"Only {len(typed_defs)}/{len(def_lines)} functions have type hints")

    # --- Edge case checks ---
    if "open(" in code and "with " not in code:
        warnings.append("File open without context manager — risk of resource leak")
        scores["edge_cases"] -= 1

    # Thread safety
    if "threading" in code or "Thread(" in code:
        if "Lock(" not in code and "lock" not in code.lower():
            warnings.append("Threading used without visible Lock — check thread safety")
            scores["edge_cases"] -= 1

    # Clamp scores
    for k in scores:
        scores[k] = max(1, min(10, scores[k]))

    avg_score = sum(scores.values()) / len(scores)

    return {
        "scores": scores,
        "average_score": round(avg_score, 1),
        "issues": issues,
        "warnings": warnings,
        "line_count": len(lines),
        "class_count": class_count,
        "function_count": len(def_lines),
        "production_ready": len(issues) == 0 and avg_score >= 7,
    }


# ---------------------------------------------------------------------------
# Review orchestration
# ---------------------------------------------------------------------------

def review_code(code: str, filepath: str, feature: str = "",
                stage: str = "post", min_score: float = 7.0) -> dict:
    """
    Run a full council review on code.

    Returns dict with: local_analysis, llm_reviews, cross_review,
                       consensus_score, production_ready, issues, filepath
    """
    if not feature:
        feature = f"Module: {filepath}"

    system = POST_BUILD_SYSTEM if stage == "post" else MID_BUILD_SYSTEM
    timestamp = datetime.utcnow().isoformat()

    result = {
        "filepath": filepath,
        "feature": feature,
        "stage": stage,
        "timestamp": timestamp,
        "local_analysis": None,
        "llm_reviews": {},
        "cross_review": None,
        "consensus_score": 0,
        "production_ready": False,
        "issues": [],
        "fix_list": [],
    }

    # --- Local static analysis (always runs) ---
    log.info("Running local analysis on %s...", filepath)
    local = _local_analysis(code, filepath)
    result["local_analysis"] = local
    log.info("  Local score: %.1f | Issues: %d | Warnings: %d",
             local["average_score"], len(local["issues"]), len(local["warnings"]))

    # --- LLM reviews ---
    review_prompt = REVIEW_TEMPLATE.format(
        feature=feature, filepath=filepath, code=code[:12000]  # cap at ~12k chars
    )

    llm_reviews = {}
    for name, query_fn in PROVIDERS.items():
        log.info("Querying %s for review...", name)
        resp = query_fn(review_prompt, system)
        if resp:
            llm_reviews[name] = resp
            log.info("  %s reviewed (%d chars)", name, len(resp))
        else:
            log.info("  %s skipped (no API key)", name)

    result["llm_reviews"] = llm_reviews

    # --- Cross-review if 2+ LLMs responded ---
    if len(llm_reviews) >= 2:
        reviews_text = "\n\n---\n\n".join(
            f"### {name.upper()} REVIEW:\n{review}"
            for name, review in llm_reviews.items()
        )
        cross_prompt = CROSS_REVIEW_TEMPLATE.format(
            filepath=filepath,
            code=code[:8000],
            reviews=reviews_text,
        )
        # Use first available provider for cross-review
        for name, query_fn in PROVIDERS.items():
            cross = query_fn(cross_prompt, POST_BUILD_SYSTEM)
            if cross:
                result["cross_review"] = cross
                log.info("Cross-review completed by %s", name)
                break

    # --- Compute consensus ---
    all_issues = list(local["issues"])
    all_warnings = list(local["warnings"])

    # Parse LLM scores if available (best-effort)
    llm_scores = []
    for name, review in llm_reviews.items():
        try:
            # Try to find "Overall Score: X" pattern
            for line in review.split("\n"):
                lower = line.lower()
                if "overall score" in lower or "average" in lower:
                    import re
                    nums = re.findall(r'(\d+(?:\.\d+)?)\s*/?\s*10', line)
                    if nums:
                        llm_scores.append(float(nums[0]))
                        break
                    nums = re.findall(r':\s*(\d+(?:\.\d+)?)', line)
                    if nums:
                        score = float(nums[0])
                        if 1 <= score <= 10:
                            llm_scores.append(score)
                            break
        except (ValueError, IndexError):
            pass

    if llm_scores:
        consensus = (local["average_score"] + sum(llm_scores)) / (1 + len(llm_scores))
    else:
        consensus = local["average_score"]

    result["consensus_score"] = round(consensus, 1)
    result["issues"] = all_issues
    result["warnings"] = all_warnings
    result["production_ready"] = consensus >= min_score and len(all_issues) == 0

    verdict = "SHIP" if result["production_ready"] else (
        "FIX_THEN_SHIP" if consensus >= min_score - 1 else "REWRITE"
    )
    result["verdict"] = verdict

    log.info("")
    log.info("=" * 60)
    log.info("COUNCIL REVIEW: %s", filepath)
    log.info("  Consensus Score: %.1f / 10", consensus)
    log.info("  Local Score:     %.1f / 10", local["average_score"])
    if llm_scores:
        log.info("  LLM Scores:      %s", ", ".join(f"{s:.1f}" for s in llm_scores))
    log.info("  Issues:          %d critical, %d warnings", len(all_issues), len(all_warnings))
    log.info("  Verdict:         %s", verdict)
    log.info("=" * 60)

    # Save review
    _save_review(result)
    return result


def review_file(filepath: str, **kwargs) -> dict:
    """Review a file by path."""
    path = Path(filepath)
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    if not path.exists():
        log.error("File not found: %s", path)
        return {"error": f"File not found: {path}"}
    code = path.read_text()
    return review_code(code, str(path.relative_to(PROJECT_ROOT)), **kwargs)


def _save_review(result: dict):
    """Save review to disk."""
    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    safe_name = result["filepath"].replace("/", "_").replace(".", "_")

    # JSON log
    json_path = REVIEWS_DIR / f"review_{ts}_{safe_name}.json"
    with open(json_path, "w") as f:
        json.dump(result, f, indent=2, default=str)

    # Human-readable summary
    md_path = REVIEWS_DIR / f"review_{ts}_{safe_name}.md"
    with open(md_path, "w") as f:
        f.write(f"# Council Code Review — {result['filepath']}\n\n")
        f.write(f"**Date**: {result['timestamp']}\n")
        f.write(f"**Stage**: {result['stage']}\n")
        f.write(f"**Feature**: {result['feature']}\n\n")

        f.write(f"## Scores\n\n")
        f.write(f"- **Consensus**: {result['consensus_score']} / 10\n")
        if result["local_analysis"]:
            la = result["local_analysis"]
            f.write(f"- **Local Analysis**: {la['average_score']} / 10\n")
            for dim, score in la["scores"].items():
                f.write(f"  - {dim}: {score}/10\n")
        f.write(f"\n## Verdict: {result.get('verdict', 'UNKNOWN')}\n\n")

        if result["issues"]:
            f.write("## Critical Issues\n\n")
            for issue in result["issues"]:
                f.write(f"- {issue}\n")

        if result.get("warnings"):
            f.write("\n## Warnings\n\n")
            for w in result["warnings"]:
                f.write(f"- {w}\n")

        if result["llm_reviews"]:
            f.write("\n## LLM Reviews\n\n")
            for name, review in result["llm_reviews"].items():
                f.write(f"### {name.upper()}\n\n{review}\n\n")

        if result["cross_review"]:
            f.write(f"\n## Cross-Review\n\n{result['cross_review']}\n")

    log.info("Review saved: %s", md_path)


# ---------------------------------------------------------------------------
# Batch review
# ---------------------------------------------------------------------------

def review_batch(filepaths: list, feature: str = "", **kwargs) -> dict:
    """Review multiple files and produce aggregate report."""
    results = []
    for fp in filepaths:
        r = review_file(fp, feature=feature, **kwargs)
        results.append(r)

    passing = [r for r in results if r.get("production_ready")]
    failing = [r for r in results if not r.get("production_ready") and "error" not in r]
    errors = [r for r in results if "error" in r]

    all_issues = []
    for r in results:
        for issue in r.get("issues", []):
            all_issues.append(f"[{r.get('filepath', '?')}] {issue}")

    avg_score = sum(r.get("consensus_score", 0) for r in results if "error" not in r)
    count = len([r for r in results if "error" not in r])
    avg_score = round(avg_score / max(count, 1), 1)

    log.info("")
    log.info("=" * 60)
    log.info("BATCH REVIEW SUMMARY")
    log.info("  Files reviewed:  %d", len(results))
    log.info("  Passing:         %d", len(passing))
    log.info("  Failing:         %d", len(failing))
    log.info("  Errors:          %d", len(errors))
    log.info("  Average Score:   %.1f / 10", avg_score)
    log.info("  Total Issues:    %d", len(all_issues))
    log.info("=" * 60)

    return {
        "results": results,
        "passing": len(passing),
        "failing": len(failing),
        "errors": len(errors),
        "average_score": avg_score,
        "all_issues": all_issues,
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="LLM Council Code Reviewer (Stage 2/3)")
    parser.add_argument("files", nargs="+", help="File(s) to review (supports globs)")
    parser.add_argument("--feature", "-f", default="", help="Feature description for context")
    parser.add_argument("--stage", "-s", choices=["mid", "post"], default="post",
                        help="Review stage: mid (before commit) or post (after commit)")
    parser.add_argument("--min-score", type=float, default=7.0,
                        help="Minimum passing score (default: 7.0)")
    args = parser.parse_args()

    # Expand globs
    expanded = []
    for pattern in args.files:
        matches = glob.glob(pattern)
        if matches:
            expanded.extend(matches)
        else:
            expanded.append(pattern)

    if len(expanded) == 1:
        result = review_file(expanded[0], feature=args.feature,
                             stage=args.stage, min_score=args.min_score)
        sys.exit(0 if result.get("production_ready") else 1)
    else:
        batch = review_batch(expanded, feature=args.feature,
                             stage=args.stage, min_score=args.min_score)
        sys.exit(0 if batch["failing"] == 0 else 1)


if __name__ == "__main__":
    main()
