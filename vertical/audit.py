#!/usr/bin/env python3
"""Trifecta cross-LLM audit for vertical/*.py — adapted from segment_v1/audit/cycle2_run.py.

Usage:
    python3 -m vertical.audit gpt       # run OpenAI audit
    python3 -m vertical.audit gemini     # run Gemini audit
    python3 -m vertical.audit grok       # run xAI audit
    python3 -m vertical.audit all        # run all three sequentially
    python3 -m vertical.audit cycle2 gpt # cycle 2 cross-examination

Keys read from ~/protocol_pulse/.env, never printed.
Prompt: "find defects that would put the wrong face on screen or bake debug artifacts into output"
"""
import json, os, sys, time, pathlib, urllib.request, urllib.error

BASE = pathlib.Path(__file__).resolve().parent
WORK = BASE / "work"
WORK.mkdir(exist_ok=True)

ENV = {}
for line in open(os.path.expanduser("~/protocol_pulse/.env")):
    if "=" in line and not line.startswith("#"):
        k, v = line.rstrip("\n").split("=", 1)
        ENV[k.strip()] = v.strip().strip('"').strip("'")


def _read_module(name):
    p = BASE / name
    if p.exists():
        return p.read_text(encoding="utf-8", errors="replace")
    return ""


def _code_bundle():
    parts = []
    for name in sorted(os.listdir(BASE)):
        if name.endswith(".py"):
            code = _read_module(name)
            parts.append(f"\n===== vertical/{name} =====\n{code}")
    return "".join(parts)


AUDIT_PROMPT = """You are auditing the Protocol Pulse vertical reframing module (vertical/*.py).

TASK: Find defects that would:
1. Put the wrong face on screen (wrong tile, wrong band, subset of visible faces)
2. Bake debug artifacts (cv2.rectangle, colored boxes, text overlays) into render output
3. Cause a face to be cut off at composition boundaries
4. Apply animated panning instead of fixed crops
5. Break QA gate thresholds (face count mismatch, wrong dimensions)

Only report issues you can verify from the code provided. Do not speculate.
If uncertain, say so. Do not guess.

Rank findings:
- CRITICAL: wrong face on screen, debug artifacts in render, gate bypass
- HIGH: face partially cut, composition rule violation
- MEDIUM: edge case handling, potential off-by-one
- LOW: style, naming, minor improvement

Wrap each finding in <critical>, <high>, <medium>, or <low> tags.

CODE BUNDLE:
"""


def post(url, headers, body, timeout=900):
    req = urllib.request.Request(
        url, data=json.dumps(body).encode(),
        headers={**headers, "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())


def openai_call(text):
    last = None
    for model in ["gpt-4.1", "gpt-4o", "o3"]:
        try:
            r = post(
                "https://api.openai.com/v1/chat/completions",
                {"Authorization": "Bearer " + ENV["OPENAI_API_KEY"]},
                {"model": model, "messages": [{"role": "user", "content": text}]})
            return model, r["choices"][0]["message"]["content"]
        except urllib.error.HTTPError as e:
            last = f"{model}: {e.code} {e.read()[:200]!r}"
            time.sleep(20)
            if e.code not in (400, 402, 404, 429):
                raise
    raise RuntimeError(last)


def xai_call(text):
    last = None
    for model in ["grok-4", "grok-4-0709", "grok-3"]:
        try:
            r = post(
                "https://api.x.ai/v1/chat/completions",
                {"Authorization": "Bearer " + ENV["XAI_API_KEY_MEDLEY"]},
                {"model": model, "messages": [{"role": "user", "content": text}]})
            return model, r["choices"][0]["message"]["content"]
        except urllib.error.HTTPError as e:
            last = f"{model}: {e.code} {e.read()[:200]!r}"
            time.sleep(20)
            if e.code not in (400, 402, 404, 429):
                raise
    raise RuntimeError(last)


def gemini_call(text):
    last = None
    for model in ["gemini-3-pro-preview", "gemini-2.5-pro", "gemini-2.5-flash"]:
        try:
            r = post(
                f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key="
                + ENV["GEMINI_API_KEY"], {},
                {"contents": [{"parts": [{"text": text}]}],
                 "generationConfig": {"temperature": 0.2}})
            return model, r["candidates"][0]["content"]["parts"][0]["text"]
        except urllib.error.HTTPError as e:
            last = f"{model}: {e.code} {e.read()[:200]!r}"
            time.sleep(20)
            if e.code not in (400, 402, 404, 429):
                raise
    raise RuntimeError(last)


CALLS = {"gpt": openai_call, "gemini": gemini_call, "grok": xai_call}


def run_audit(which):
    bundle = _code_bundle()
    text = AUDIT_PROMPT + bundle
    t0 = time.time()
    out_path = WORK / f"audit_{which}.md"
    try:
        model, out = CALLS[which](text)
        out_path.write_text(f"<!-- model: {model}, {time.time()-t0:.0f}s -->\n" + out)
        print(f"{which} OK model={model} chars={len(out)} {time.time()-t0:.0f}s")
        return True
    except Exception as e:
        err_path = WORK / f"audit_{which}.err"
        err_path.write_text(str(e)[:2000])
        print(f"{which} FAIL {str(e)[:300]}")
        return False


def run_cycle2(which):
    """Cycle 2: each model gets all three cycle-1 audits + code bundle."""
    audits = {}
    for k in ("gpt", "gemini", "grok"):
        p = WORK / f"audit_{k}.md"
        if p.exists():
            audits[k] = p.read_text(encoding="utf-8", errors="replace")

    if len(audits) < 2:
        print(f"Need at least 2 cycle-1 audits, found {len(audits)}. Run cycle 1 first.")
        return False

    prompt = (
        "You are in CYCLE 2 of a cross-LLM code audit.\n\n"
        "Below are cycle-1 audit results from all models, plus the full code bundle.\n"
        "Your task: cross-examine the other models' findings. Confirm real defects, "
        "dismiss false positives, and add any defects you missed in cycle 1.\n"
        "Focus on: wrong face on screen, debug artifacts in render output.\n"
        f"Your own cycle-1 audit is audit_{which}.md.\n\n"
    )
    for k, v in audits.items():
        prompt += f"\n===== audit_{k}.md =====\n{v}\n"
    prompt += f"\n===== CODE BUNDLE =====\n{_code_bundle()}"

    t0 = time.time()
    out_path = WORK / f"cycle2_{which}.md"
    try:
        model, out = CALLS[which](prompt)
        out_path.write_text(f"<!-- model: {model}, {time.time()-t0:.0f}s -->\n" + out)
        print(f"cycle2 {which} OK model={model} chars={len(out)} {time.time()-t0:.0f}s")
        return True
    except Exception as e:
        err_path = WORK / f"cycle2_{which}.err"
        err_path.write_text(str(e)[:2000])
        print(f"cycle2 {which} FAIL {str(e)[:300]}")
        return False


def write_audit_md():
    """Synthesize audit results into AUDIT.md."""
    parts = ["# Vertical Module Audit Results\n\n"]
    parts.append(f"Generated: {time.strftime('%Y-%m-%dT%H:%M:%S%z')}\n\n")

    for cycle in ("audit", "cycle2"):
        parts.append(f"## {'Cycle 1' if cycle == 'audit' else 'Cycle 2'}\n\n")
        for provider in ("gpt", "gemini", "grok"):
            p = WORK / f"{cycle}_{provider}.md"
            if p.exists():
                content = p.read_text()[:3000]
                parts.append(f"### {provider}\n{content}\n\n")
            else:
                err = WORK / f"{cycle}_{provider}.err"
                if err.exists():
                    parts.append(f"### {provider}\nFAILED: {err.read_text()[:500]}\n\n")
                else:
                    parts.append(f"### {provider}\nNot run.\n\n")

    out = BASE / "AUDIT.md"
    out.write_text("".join(parts))
    print(f"Wrote {out}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 -m vertical.audit [gpt|gemini|grok|all|cycle2|summary]")
        sys.exit(1)

    cmd = sys.argv[1]
    if cmd == "all":
        for p in ("gpt", "gemini", "grok"):
            run_audit(p)
        write_audit_md()
    elif cmd == "cycle2":
        which = sys.argv[2] if len(sys.argv) > 2 else "all"
        if which == "all":
            for p in ("gpt", "gemini", "grok"):
                run_cycle2(p)
        else:
            run_cycle2(which)
        write_audit_md()
    elif cmd == "summary":
        write_audit_md()
    elif cmd in CALLS:
        run_audit(cmd)
    else:
        print(f"Unknown: {cmd}")
        sys.exit(1)
