# Heimdall audit

**Question:** Batch 24 = the stand-alone SUBJECT of a moments-first package (law L-q; pp-selectid REQUESTS R7 item 4: "stand_alone's topic check stays: its subject for a Bitcoin package is Bitcoin, and every segment names it by rule"). Context: pipeline/pinned.build_edl sets edl["topic"] = pin["label"] ("bitcoin" for every moments-first pin) and edl["angle"] = "Pinned: " + pin["headline"], where a moments-first pin's headline is the package's model-written title (<= 70 chars, no rule that it names Bitcoin); a moments-first EDL is the only kind carrying "moments_package_sha256" (set by build_edl only after the strict moments_package validation). stand_alone.subject_terms(affected_object, headline) returns {"bitcoin","btc"} when either names Bitcoin, else the content words of the object, else of the headline (an empty set fails closed). Before this change a moments-first EDL whose title does not name Bitcoin would be checked against the words of "Pinned: <title>" (including "pinned"). The change: run_fresh.stand_alone_subject(edl, story) uses the pin label for a moments-first EDL; every other run computes exactly what it computed before.
FIND: any run whose subject is now WIDER (accepts a segment the old rule refused) other than a moments-first EDL with a Bitcoin label; any way a non-moments EDL could carry moments_package_sha256; tests that do not test what they claim. Quote file and line; if uncertain, say so; do not guess. At most 5 findings.

**Panel:** deepseek, qwen27b  |  **Cost:** $0.0068
## Consensus findings (majority of panel agrees)
- none

## Raised but not agreed
- none

## Added in cross-examination (not voted on)
- none
