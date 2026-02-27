#!/usr/bin/env python3
"""
LLM Council — Multi-AI Arbitrage System
Queries OpenAI, Grok, Claude, Gemini for proposals/reviews.
Runs 2 rounds of cross-review. Votes winner. Merges best.
"""
import os, json, time, requests
from pathlib import Path
from datetime import datetime

COUNCIL_DIR = Path("data/council_decisions")
COUNCIL_DIR.mkdir(parents=True, exist_ok=True)

def query_openai(prompt, model="gpt-4o"):
    key = os.environ.get("OPENAI_API_KEY", "")
    if not key: return "[OPENAI UNAVAILABLE]"
    try:
        r = requests.post("https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {key}"},
            json={"model": model, "messages": [{"role": "user", "content": prompt}], "max_tokens": 3000},
            timeout=120)
        return r.json()["choices"][0]["message"]["content"]
    except Exception as e: return f"[OPENAI ERROR: {e}]"

def query_grok(prompt, model="grok-3-fast"):
    key = os.environ.get("XAI_API_KEY", "")
    if not key: return "[GROK UNAVAILABLE]"
    try:
        r = requests.post("https://api.x.ai/v1/chat/completions",
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            json={"model": model, "messages": [{"role": "user", "content": prompt}], "max_tokens": 3000},
            timeout=120)
        return r.json()["choices"][0]["message"]["content"]
    except Exception as e: return f"[GROK ERROR: {e}]"

def query_claude(prompt, model="claude-sonnet-4-5-20250929"):
    key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not key: return "[CLAUDE UNAVAILABLE]"
    try:
        r = requests.post("https://api.anthropic.com/v1/messages",
            headers={"x-api-key": key, "anthropic-version": "2023-06-01", "content-type": "application/json"},
            json={"model": model, "max_tokens": 3000, "messages": [{"role": "user", "content": prompt}]},
            timeout=120)
        return r.json()["content"][0]["text"]
    except Exception as e: return f"[CLAUDE ERROR: {e}]"

def query_gemini(prompt):
    key = os.environ.get("GEMINI_API_KEY", "")
    if not key: return "[GEMINI UNAVAILABLE]"
    try:
        r = requests.post(f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={key}",
            json={"contents": [{"parts": [{"text": prompt}]}]},
            timeout=120)
        return r.json()["candidates"][0]["content"]["parts"][0]["text"]
    except Exception as e: return f"[GEMINI ERROR: {e}]"

def run_council(feature_name, brief, stage="pre_build"):
    """Run full LLM Council: proposals, 2x cross-review, vote, merge."""
    print(f"\n{'='*60}")
    print(f"LLM COUNCIL — {stage.upper()} — {feature_name}")
    print(f"{'='*60}\n")

    session = {
        "feature": feature_name, "stage": stage,
        "date": datetime.now().isoformat(),
        "rounds": {}
    }

    # Round 1: Initial proposals/reviews
    print("ROUND 1: Gathering proposals from all LLMs...")
    r1 = {}
    for name, fn in [("openai", query_openai), ("grok", query_grok), ("claude", query_claude), ("gemini", query_gemini)]:
        print(f"  Querying {name}...")
        r1[name] = fn(brief)
        time.sleep(1)
    session["rounds"]["round1"] = r1

    # Round 2: Cross-review
    all_proposals = "\n\n".join([f"=== {k.upper()} ===\n{v}" for k,v in r1.items() if not v.startswith("[")])
    cross_prompt = f"Here are proposals/reviews from multiple AI systems for '{feature_name}':\n\n{all_proposals}\n\nReview ALL of them. Score each 1-10. Identify the strongest ideas from each. Identify weaknesses. What would the IDEAL implementation look like combining the best of all?"

    print("\nROUND 2: Cross-review...")
    r2 = {}
    for name, fn in [("openai", query_openai), ("grok", query_grok), ("claude", query_claude), ("gemini", query_gemini)]:
        print(f"  {name} reviewing all proposals...")
        r2[name] = fn(cross_prompt)
        time.sleep(1)
    session["rounds"]["round2"] = r2

    # Final synthesis
    all_reviews = "\n\n".join([f"=== {k.upper()} REVIEW ===\n{v}" for k,v in r2.items() if not v.startswith("[")])
    final_prompt = f"Based on these cross-reviews for '{feature_name}':\n\n{all_reviews}\n\nProduce the FINAL merged recommendation. Include: specific implementation details, architecture decisions, key innovations, and what makes this miles ahead of anything else. Be concrete and actionable."

    print("\nFINAL: Synthesizing merged spec...")
    r3 = {}
    for name, fn in [("openai", query_openai), ("grok", query_grok), ("claude", query_claude), ("gemini", query_gemini)]:
        print(f"  {name} final recommendation...")
        r3[name] = fn(final_prompt)
        time.sleep(1)
    session["rounds"]["final"] = r3

    # Save
    safe_name = feature_name.replace(" ", "_").lower()
    path = COUNCIL_DIR / f"{safe_name}_{stage}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    path.write_text(json.dumps(session, indent=2))
    print(f"\nCouncil decision saved: {path}")

    return session

def post_build_review(feature_name, code_text):
    """Run post-build Council review on actual code."""
    brief = f"""POST-BUILD REVIEW for '{feature_name}'.

Review this completed implementation. Score 1-10 on each:
- Correctness: Does it work? Edge cases handled?
- Architecture: Clean design? Proper separation of concerns?
- Error handling: Graceful failures? Proper logging?
- Security: Any vulnerabilities? Input validation?
- Performance: Efficient? Any bottlenecks?
- Production readiness: Can this ship today?
- Innovation: Is this miles ahead of industry standard?

THE CODE:
{code_text[:8000]}

List EVERY specific issue that must be fixed. Be ruthless. No half-assed code ships."""
    return run_council(feature_name, brief, stage="post_build")

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        feature = sys.argv[1]
        brief = sys.argv[2] if len(sys.argv) > 2 else f"Review the implementation of {feature}"
        run_council(feature, brief)
    else:
        print("Usage: python llm_council.py 'feature name' 'brief/code'")
