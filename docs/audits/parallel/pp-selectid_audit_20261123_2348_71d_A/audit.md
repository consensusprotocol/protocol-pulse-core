# Heimdall audit

**Question:** pp-selectid (Protocol Pulse clip-video builder), RULING 156's PLAIN FALLBACK LINES and RULING 157 (2)(b), as pushed in 71d3d0363 (diff below, from 591403d71). Context you cannot see in the hunks: pipeline/package_pin.py gate_problems (line 458) refuses any FLAGGED row whose gate is not in SOFT_GATES with a non-empty list of plain-word flags (flagged_ok, line 403); review_problems (line 419) refuses a pin whose review_flags differ from its FLAGGED rows' flags or whose KINDS of flag (content_flags, line 449) exceed flags_cap (line 428, always REVIEW_FLAGS_MAX = 3). Fidelity (our lines must state nothing the clips do not say) is a HARD gate elsewhere in package.py and is NOT changed here.
WHAT THE CODE MUST DO: (a) when every writer fails a line after its retries, fallback_fields builds the closing line, title, caption and bridges from fixed templates that state NO fact (only the subject said in two or more clips, or 'Bitcoin', and channel names); (b) that fallback is gated like any line (fidelity still HARD) and is ALWAYS flagged on the pin with FALLBACK_FLAG naming the line; (c) package_pin.OUR_LINES_KIND makes the fallback row and the closing line's value row ONE kind; (d) fallback_vo_soft (package.py line 616) lets a coherence verdict pass ONLY when the sealed closing line IS the fallback, the pass is the never-empty pass, the verdict is measured, a through-line exists, every clip rating is at its floor and the hook passes its own bar.
CHECK, quoting the code: can a fallback line or title state a number, a claim or a name not in the clips; can the fallback be sealed WITHOUT its flag or without passing fidelity; can fallback_vo_soft pass an unmeasured verdict, a clip under its floor, a missing through-line, a model-written line, or the clean pass; can OUR_LINES_KIND or flag_kind merge two flags that are NOT about our lines into one kind; can any input make fallback_fields raise or return text with an empty name list. Report only what the code shows.

**Panel:** qwen27b, gptoss, glm  |  **Cost:** $0.1064
## Consensus findings (majority of panel agrees)
- none

## Raised but not agreed
- qwen27b:F1 [high] fallback_fields can raise KeyError/ValueError from str.format when a channel name contains braces, because channel names are used directly as the names argument. (agree: 0)
- qwen27b:F2 [high] fallback_fields can raise IndexError if join is not None and join[0] + 1 is outside segs. (agree: 1)
- qwen27b:F3 [medium] fallback_fields can raise KeyError if a segment lacks moment_id or duration_s, or angle lacks angle. (agree: 1)

## Added in cross-examination (not voted on)
- qwen27b: [high] fallback_fields can put a channel_id into viewer-facing text when channel_name is missing, so a title/caption/closing line can state a numeric or otherwise non-clip name/ID, violating the requirement that fallback text use only the subject and channel names.
- qwen27b: [medium] fallback_fields does not enforce LINE_CHARS for the takeaway, caption, or the second title form; it only checks the takeaway word budget and checks the first title, so long subject/names can return over-length fields that fail hard length gates.
- qwen27b: [low] A whitespace-only channel_name is treated as a non-empty name, so fallback text can contain an effectively empty name.
