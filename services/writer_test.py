#!/usr/bin/env python3
"""
writer_test.py — RENDERING TEST ONLY. Posts nothing. POSTING_PAUSED stays on.
Reads writer-eligible stories from candidate_stories.json, passes ONLY the evidence
packet to the writer, generates 3 register variants each (cold / deadpan / investigative).
Firewall: writer may introduce NO new fact/number/causation/motive/comparison/superlative.
NO_POST is a valid output — the writer may not manufacture interestingness.
"""
import os, json, re, urllib.request
from pathlib import Path
from datetime import datetime, timezone

BASE = Path("/home/ultron/protocol_pulse")
STORIES = BASE / "data" / "intelligence" / "candidate_stories.json"
OUT = BASE / "data" / "intelligence" / "writer_test_output.json"
OPENAI_KEY = os.environ.get("OPENAI_API_KEY", "")

REGISTERS = {
    "cold_forensic": (
        "COLD/FORENSIC register. Pure receipt, almost no personality. State the claim at its "
        "correct epistemic level (see PERMISSION LADDER). No wit, no lesson. Under 120 chars."
    ),
    "native_deadpan": (
        "NATIVE/DEADPAN register. CRITICAL LESSON: deadpan does NOT mean 'add a joke.' It means "
        "recognize when the fact is ALREADY funny, strange, or absurd — and RESIST explaining it. "
        "'The Fed put is just a group of guys' works because the insight IS the joke. Adding a "
        "quip AFTER the fact (e.g. 'the net could use a few more holes') is the model reaching for "
        "wit — forbidden. Present the absurd ratio or contrast and STOP. The reader gets it. "
        "Example of the right instinct: 'Chainalysis estimates $457B in taxable crypto activity. "
        "The OECD framework covers 14% of it' — then stop. The absurdity of the ratio is the "
        "punchline; do not spell it out. PBX voice: compressed, lowercase energy, under 120 chars, "
        "attributed/hedged per the ladder. If the fact isn't already interesting, NO_POST — do not "
        "manufacture wit to rescue it."
    ),
    "investigative": (
        "INVESTIGATIVE register. LONGER IS EARNED, NOT REQUIRED. A 2-3 sentence version may ONLY "
        "exist when sentence two contains NEW verified context from the packet — never when you're "
        "just stretching sentence one. Every sentence must point back to the evidence packet. "
        "SAFE WORKED PATTERN:\n"
        "  Sentence 1: 'Company X estimates Y.' (attributed fact)\n"
        "  Sentence 2: 'Its report defines Y as [verified methodology/context from packet].'\n"
        "  Sentence 3 (optional): 'That leaves Z outside the framework, under the report's own "
        "assumptions.' (inference explicitly tied to the source's own logic)\n"
        "If sentence two would require creative synthesis NOT explicitly in the packet, return "
        "NO_POST. Attribution stays attached to the exact claim it qualifies. Up to 240 chars."
    ),
}


FIREWALL = (
    "EPISTEMIC PERMISSION LADDER — the verification status of THIS story sets what you may do:\n"
    "- VERIFIED_PRIMARY: may state the fact directly.\n"
    "- VERIFIED_SECONDARY: may state with normal attribution where useful.\n"
    "- ESTIMATE_ATTRIBUTED: MUST say 'X estimates...' / 'according to X...' — never bare.\n"
    "- INFERENCE_SUPPORTED: MUST use qualified language: 'suggests', 'would imply', 'appears "
    "consistent with'. The inference may NEVER be stated as fact.\n"
    "- UNVERIFIED / CONTRADICTED / STALE: cannot be used at all.\n\n"
    "HARD RULES:\n"
    "1. Use ONLY facts, numbers, and framings in the EVIDENCE PACKET. Introduce NO new number, "
    "date, fact, causation, motive, historical comparison, or superlative.\n"
    "2. ATTRIBUTION MUST STAY ATTACHED TO THE EXACT CLAIM IT QUALIFIES. Never let a verified fact "
    "in one sentence launder an inference into fact in the next. "
    "BAD: 'Chainalysis estimates $457B. This means authorities miss 86%.' "
    "(second sentence turns interpretation into fact). "
    "GOOD: 'Chainalysis estimates $457B sits outside the reporting net — its methodology implies "
    "current reporting captures only a fraction.' (inference stays hedged and attributed).\n"
    "3. Obey every DO-NOT-SAY item exactly.\n"
    "4. No hashtags, no emoji, no motive attribution.\n"
    "5. If the story cannot be made genuinely interesting WITHIN these rules, return exactly: NO_POST\n"
    "6. Do not manufacture interestingness. Boring-but-true should return NO_POST."
)

def call_gpt(prompt, temp=0.7):
    payload = json.dumps({"model":"gpt-4o","messages":[{"role":"user","content":prompt}],
                          "max_tokens":150,"temperature":temp}).encode()
    req = urllib.request.Request("https://api.openai.com/v1/chat/completions", data=payload,
        headers={"Authorization":"Bearer "+OPENAI_KEY,"Content-Type":"application/json"})
    resp = json.loads(urllib.request.urlopen(req, timeout=30).read().decode())
    return resp["choices"][0]["message"]["content"].strip()

def _effective_tier(story):
    """Refine verification_status into a writer permission tier."""
    vs = story.get("verification_status", "UNVERIFIED")
    facts_text = " ".join(story.get("facts", [])).lower()
    if vs == "INFERENCE_SUPPORTED" and ("estimate" in facts_text or "estimates" in facts_text):
        return "ESTIMATE_ATTRIBUTED"
    return vs

def build_packet(story):
    return (
        "EVIDENCE PACKET (this is the ONLY information you may use):\n"
        f"- HEADLINE: {story['headline']}\n"
        f"- EDITORIAL TYPE: {story.get('suggested_editorial_type','')}\n"
        f"- VERIFIED FACTS: {json.dumps(story.get('facts', []))}\n"
        f"- SUPPORTED INFERENCES (must hedge): {json.dumps(story.get('inferences', []))}\n"
        f"- DO-NOT-SAY: {json.dumps(story.get('do_not_say', []))}\n"
        f"- RED FLAGS: {json.dumps(story.get('red_flags', []))}\n"
        f"- WHY IT MATTERS: {story.get('why_interesting','')}\n"
        f"- SOURCE: {story.get('source_domain','')} | {story.get('freshness_minutes','?')} min old\n"
        f"- VERIFICATION: {story.get('verification_status','')}\n"
        f"- EFFECTIVE TIER: {_effective_tier(story)}\n"
    )

def run():
    data = json.load(open(STORIES))
    eligible = [s for s in data["stories"] if s.get("writer_eligible")]
    print(f"Writer-eligible stories: {len(eligible)}")

    results = []
    for story in eligible:
        packet = build_packet(story)
        variants = {}
        for reg_key, reg_desc in REGISTERS.items():
            prompt = (
                "You are the voice of @ProtocolPulseHQ, a sharp Bitcoin/markets intelligence account.\n\n"
                + FIREWALL + "\n\n" + packet + "\n\n"
                + "REGISTER FOR THIS VERSION: " + reg_desc + "\n\n"
                + "Write ONE tweet in this register, or return NO_POST. Output only the tweet text or NO_POST."
            )
            try:
                out = call_gpt(prompt)
            except Exception as e:
                out = f"ERROR: {e}"
            variants[reg_key] = out
        results.append({
            "headline": story["headline"],
            "editorial_type": story.get("suggested_editorial_type",""),
            "verification_status": story.get("verification_status",""),
            "variants": variants,
        })
        print(f"  done: {story['headline'][:50]}")

    json.dump({"generated_at": datetime.now(timezone.utc).isoformat(), "results": results},
              open(OUT, "w"), indent=2)
    print(f"Wrote {OUT}")

if __name__ == "__main__":
    run()
