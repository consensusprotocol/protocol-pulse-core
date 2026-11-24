# Heimdall audit

**Question:** pp-selectid (Protocol Pulse clip-video builder), RULING 156's PLAIN FALLBACK LINES and RULING 157 (2)(b), as pushed in 71d3d0363 (diff below, from 591403d71). Context you cannot see in the hunks: pipeline/package_pin.py gate_problems (line 458) refuses any FLAGGED row whose gate is not in SOFT_GATES with a non-empty list of plain-word flags (flagged_ok, line 403); review_problems (line 419) refuses a pin whose review_flags differ from its FLAGGED rows' flags or whose KINDS of flag (content_flags, line 449) exceed flags_cap (line 428, always REVIEW_FLAGS_MAX = 3). Fidelity (our lines must state nothing the clips do not say) is a HARD gate elsewhere in package.py and is NOT changed here.
WHAT THE CODE MUST DO: (a) when every writer fails a line after its retries, fallback_fields builds the closing line, title, caption and bridges from fixed templates that state NO fact (only the subject said in two or more clips, or 'Bitcoin', and channel names); (b) that fallback is gated like any line (fidelity still HARD) and is ALWAYS flagged on the pin with FALLBACK_FLAG naming the line; (c) package_pin.OUR_LINES_KIND makes the fallback row and the closing line's value row ONE kind; (d) fallback_vo_soft (package.py line 616) lets a coherence verdict pass ONLY when the sealed closing line IS the fallback, the pass is the never-empty pass, the verdict is measured, a through-line exists, every clip rating is at its floor and the hook passes its own bar.
CHECK, quoting the code: can a fallback line or title state a number, a claim or a name not in the clips; can the fallback be sealed WITHOUT its flag or without passing fidelity; can fallback_vo_soft pass an unmeasured verdict, a clip under its floor, a missing through-line, a model-written line, or the clean pass; can OUR_LINES_KIND or flag_kind merge two flags that are NOT about our lines into one kind; can any input make fallback_fields raise or return text with an empty name list. Report only what the code shows.

**Panel:** qwen27b, gptoss, gemma  |  **Cost:** $0.0913
## Consensus findings (majority of panel agrees)
- **[medium] pipeline/package.py:0** fallback_fields can raise IndexError when join is not None and join[0] + 1 is not a valid index into segs, including when segs is empty.
  - evidence: `nxt = segs[join[0] + 1]`
  - fix: Guard the index before building the bridge, e.g. only use segs[join[0] + 1] when join is not None and 0 <= join[0] + 1 < len(segs); otherwise set bridge to None.
  - raised by qwen27b:F1; agree: qwen27b, gemma
- **[high] pipeline/package.py:0** fallback_fields can put a raw channel_id into the generated title/caption when channel_name is absent; the code does not verify that channel_id is a display name or appears in the clips, so an opaque or numeric channel_id can make the fallback state a number/name not in the clips.
  - evidence: `c = m.get("channel_name") or m.get("channel_id")`
  - fix: Use only channel_name for names; if no channel_name is available, fall back to a safe generic such as 'the channels' or validate that channel_id is a known display name before using it.
  - raised by qwen27b:F2; agree: qwen27b, gemma
- **[medium] pipeline/package.py:0** The shortened fallback title is not re-checked, so a long subject can make 'subject, in their words' still exceed HS.TITLE_MAX_WORDS or LINE_CHARS['title'].
  - evidence: `title = f"{subject}: {names}"
if len(title.split()) > HS.TITLE_MAX_WORDS or len(title) > LINE_CHARS["title"]:
    title = f"{subject}, in their words"`
  - fix: After choosing the shortened title, verify it fits the same limits and, if not, use a further safe truncation or a fixed short title that cannot exceed the limits.
  - raised by qwen27b:F3; agree: qwen27b, gemma

## Raised but not agreed
- gemma:F1 [critical] UnboundLocalError: local variable 'fields' referenced before assignment. The variable 'fields' is only defined within the 'if fb_state == "due":' block inside the 'while True' loop. If the loop terminates without 'fb_state' ever becoming 'due' (e.g., if 'soft' is False or the loop breaks early due to 'over_budget'), 'fields' remains unbound, causing a crash when passed to 'fallback_vo_soft'. (agree: 1)

## Added in cross-examination (not voted on)
- qwen27b: [medium] fallback_fields does not enforce the character limits for the takeaway or caption; it only checks the takeaway word budget and the first title's word/char limits.
- qwen27b: [low] fallback_fields can raise KeyError if a segment dict lacks moment_id or duration_s.
