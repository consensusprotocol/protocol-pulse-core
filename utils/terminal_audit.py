#!/usr/bin/env python3
"""Cross-LLM audit of signal_terminal.html with 8 Bloomberg-grade questions."""
import os, json, sys, concurrent.futures
from pathlib import Path
from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

TEMPLATE = (Path(__file__).resolve().parent.parent / "templates" / "signal_terminal.html").read_text()
DESIGN_SYSTEM = (Path(__file__).resolve().parent.parent / "VISUAL_DESIGN_SYSTEM.md").read_text()[:3000]

QUESTIONS = """
1. What data sources would a $24,000/yr Bloomberg terminal subscriber expect that we're missing?
2. What is the single most impressive real-time data visualization a Bitcoin terminal could show?
3. What open-source 2025-2026 algorithms (GitHub) should we incorporate for predictive precision?
4. What makes our current terminal look amateur vs professional — what are the top 3 design failures?
5. What proprietary data streams does Protocol Pulse have that Bloomberg does NOT have?
6. What would make a sophisticated investor stay on this terminal for hours vs close in 30 seconds?
7. What real-time WebSocket feeds exist (free or cheap) that we haven't leveraged?
8. What would make this terminal viral — what would make a Bitcoiner share it on Twitter?
"""

PROMPT = f"""You are a senior product designer and quantitative finance engineer reviewing a Bitcoin intelligence terminal.
This terminal aims to rival Bloomberg Terminal ($24,000/yr) at $49/mo.

Here is the CURRENT template (signal_terminal.html):
```html
{TEMPLATE[:25000]}
```

Here is our VISUAL DESIGN SYSTEM (excerpt):
```
{DESIGN_SYSTEM}
```

Answer each question with SPECIFIC, ACTIONABLE recommendations. Code snippets welcome. Be brutal — this is a flagship product review.

{QUESTIONS}

Format: Answer each question as ## Q1, ## Q2, etc. with 3-5 bullet points each. End with ## VERDICT: a 1-paragraph overall assessment and letter grade (A-F).
"""

def query_gemini():
    import google.generativeai as genai
    genai.configure(api_key=os.environ["GEMINI_API_KEY"])
    model = genai.GenerativeModel("gemini-2.0-flash")
    resp = model.generate_content(PROMPT, generation_config={"max_output_tokens": 4000, "temperature": 0.7})
    return ("GEMINI", resp.text)

def query_openai():
    from openai import OpenAI
    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    resp = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": PROMPT}],
        max_tokens=4000, temperature=0.7
    )
    return ("GPT-4O", resp.choices[0].message.content)

def query_grok():
    from openai import OpenAI
    client = OpenAI(api_key=os.environ["XAI_API_KEY"], base_url="https://api.x.ai/v1")
    resp = client.chat.completions.create(
        model="grok-3-latest",
        messages=[{"role": "user", "content": PROMPT}],
        max_tokens=4000, temperature=0.7
    )
    return ("GROK", resp.choices[0].message.content)

def main():
    out_dir = Path(__file__).resolve().parent.parent / "docs" / "audits" / "terminal-rebuild"
    out_dir.mkdir(parents=True, exist_ok=True)

    results = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as ex:
        futures = [ex.submit(fn) for fn in [query_gemini, query_openai, query_grok]]
        for f in concurrent.futures.as_completed(futures):
            try:
                name, text = f.result()
                results[name] = text
                print(f"[OK] {name} — {len(text)} chars")
                (out_dir / f"{name}.md").write_text(f"# {name} Terminal Audit\n\n{text}")
            except Exception as e:
                print(f"[FAIL] {e}", file=sys.stderr)

    # Synthesize consensus
    if len(results) >= 2:
        consensus = "# CROSS-LLM TERMINAL AUDIT CONSENSUS\n\n"
        for name, text in sorted(results.items()):
            consensus += f"---\n## {name}\n\n{text}\n\n"
        (out_dir / "CONSENSUS.md").write_text(consensus)
        print(f"\n[DONE] {len(results)} audits saved to {out_dir}")

if __name__ == "__main__":
    main()
