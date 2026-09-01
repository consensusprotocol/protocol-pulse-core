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

def _load_persona():
    """Reuse the existing PBX voice material from tweet_machine.py verbatim (frozen baseline).
    Extracted as text so importing this module never triggers tweet_machine side effects."""
    try:
        src = (BASE / "services" / "tweet_machine.py").read_text()
        persona = re.search(r'PBX_PERSONA = """(.*?)"""', src, re.S).group(1).strip()
        laws = re.search(r'TWEET_VOICE_LAWS = """(.*?)"""', src, re.S).group(1).strip()
        return persona, laws
    except Exception as e:
        print(f"[writer] persona load failed: {e}")
        return "You are the voice of @ProtocolPulseHQ, a sharp Bitcoin/markets intelligence account.", ""

PBX_PERSONA, TWEET_VOICE_LAWS = _load_persona()

# The persona and laws are the frozen baseline. Where they conflict with the evidence firewall
# (e.g. persona says 'no hedging' but tier is INFERENCE_SUPPORTED), the FIREWALL WINS. Recorded,
# not resolved: voice conflicts are for PBX/GPT after the first reviewed batch.
PRECEDENCE = ("PRECEDENCE: The EPISTEMIC PERMISSION LADDER and HARD RULES below override the persona "
              "and voice laws above wherever they conflict. A required attribution or hedge is never "
              "dropped for voice. A joke is never added; deadpan means stopping when the fact is already absurd.")

EDGE_PROMPT = (
    "From the EVIDENCE PACKET ONLY, state the Protocol Pulse edge in at most 2 plain sentences: "
    "what is the non-obvious observation here, and which receipt supports it? Name the receipt "
    "(filing, dataset, statement, outlet). If verified evidence contains no non-obvious observation, "
    "output exactly: NONE. No tweet voice; this is an editor's note.\n\n"
)

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
    "- REPORTED_ATTRIBUTED: a credible outlet reports this; you MUST attribute to them ('The FT reports...', 'Per Reuters...', 'According to The Block...'). Real and postable, but the attribution is mandatory and must stay attached to the claim.\n"
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
    if vs in ("INFERENCE_SUPPORTED","REPORTED_ATTRIBUTED") and ("estimate" in facts_text):
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
        f"- UNDERLYING EVENT AGE: {story.get('event_age_hours','?')} hours\n"
        f"- REPORTS / INDEPENDENT ORIGINS: {story.get('report_count',1)} / {story.get('independent_corroboration',1)}"
        f"{(' (relaying: ' + ', '.join(story.get('syndicated_from') or []) + ')') if story.get('syndicated_from') else ''}\n"
        f"- RECEIPTS: {json.dumps([{k: c.get(k) for k in ('claim','result','observed_value','source_url','original_date')} for c in ((story.get('external_verification') or {}).get('claims') or []) if c.get('result') in ('VERIFIED','STALE')])}\n"
    )

def write_story(story):
    """Edge note + 3 register variants for one story. Returns a review-queue-ready record."""
    packet = build_packet(story)
    try:
        edge = call_gpt(EDGE_PROMPT + packet, temp=0.3)
    except Exception as e:
        edge = f"ERROR: {e}"
    variants = {}
    for reg_key, reg_desc in REGISTERS.items():
        prompt = (
            PBX_PERSONA + "\n\n" + TWEET_VOICE_LAWS + "\n\n" + PRECEDENCE + "\n\n"
            + FIREWALL + "\n\n" + packet + "\n\n"
            + "REGISTER FOR THIS VERSION: " + reg_desc + "\n\n"
            + "Write ONE tweet in this register, or return NO_POST. Output only the tweet text or NO_POST."
        )
        try:
            out = call_gpt(prompt)
        except Exception as e:
            out = f"ERROR: {e}"
        variants[reg_key] = out
    postable = {k: v for k, v in variants.items() if v and v.strip() != "NO_POST" and not v.startswith("ERROR")}
    return {
        "story_id": story.get("story_id"),
        "headline": story["headline"],
        "summary": story.get("summary", ""),
        "editorial_type": story.get("suggested_editorial_type", ""),
        "verification_status": story.get("verification_status", ""),
        "effective_tier": _effective_tier(story),
        "edge": edge,
        "facts": story.get("facts", []),
        "inferences": story.get("inferences", []),
        "do_not_say": story.get("do_not_say", []),
        "receipts": [c for c in ((story.get("external_verification") or {}).get("claims") or []) if c.get("result") in ("VERIFIED", "STALE")],
        "sources": story.get("sources", []),
        "report_count": story.get("report_count", 1),
        "independent_corroboration": story.get("independent_corroboration", 1),
        "syndicated_from": story.get("syndicated_from", []),
        "event_age_hours": story.get("event_age_hours"),
        "underlying_event_ts": story.get("underlying_event_ts"),
        "discovered_at": datetime.now(timezone.utc).isoformat(),
        "freshness_minutes": story.get("freshness_minutes"),
        "presentation": "QT" if story.get("suggested_editorial_type", "").lower().startswith("quote") else "text",
        "variants": variants,
        "postable_count": len(postable),
        "proposed": next(iter(postable.values()), "NO_POST"),
        "proposed_register": next(iter(postable.keys()), None),
    }

def run():
    data = json.load(open(STORIES))
    eligible = [s for s in data["stories"] if s.get("writer_eligible")]
    print(f"Writer-eligible stories: {len(eligible)}")

    results = []
    for story in eligible:
        results.append(write_story(story))
        print(f"  done: {story['headline'][:50]}")

    json.dump({"generated_at": datetime.now(timezone.utc).isoformat(), "results": results},
              open(OUT, "w"), indent=2)
    print(f"Wrote {OUT}")

if __name__ == "__main__":
    run()
