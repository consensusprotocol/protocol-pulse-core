# PROTOCOL PULSE — CYCLE 2 CODE AUDIT
# Feature: pulse-sentence-law
# You are performing your SECOND review of this code.
# You now have access to what the other AI models said in Cycle 1.

---

## YOUR CYCLE 1 OUTPUT (what you said before)
[See below — you wrote this]

## WHAT THE OTHER MODELS SAID (Cycle 1)
## GROK — CYCLE 1 OUTPUT
**Q1: CORRECTNESS**  
The avatar_onboard.py functions match their docstrings (fetch square YouTube avatars via yt-dlp + PIL, write ONBOARD_REPORT + CONTACT_SHEET, then register only after manual verification). The new _find_avatar + validate_avatar in shoutout.py (lines 970-987, 863-873) correctly rejects non-square images and enforces channels.json-only lookup with SHA prefix check. No silent exceptions or state leakage between clips. No sentence/onset code present, so no off-by-one or unit errors to evaluate.

**Q2: LAW COMPLIANCE**  
- CREDITS: COMPLIANT (lines 970-987, 863-873, 58-71). Real square channel avatars only; no thumbnails, placeholders, or on-demand generation.  
- SENTENCE LAW / SELECTION LOCK / SNAP LIMIT / ONSET/TAIL / LAW 20 / M12 / LAW 22: No changes in this diff, so no violations introduced.  
- No path allows cut movement outside locked silence or recomputation of words.

**Q3: TESTS**  
No test files or assertions appear in the diff. The must-fail fixtures and pulse_20261110 tests referenced in the header are not present, so vacuous-pass risk cannot be assessed from this diff.

**Q4: VERDICT**  
Defects:  
- SEVERITY: Low | diff lines 126-134 | regex-based in-place edit of channels.json is brittle (edge-case JSON structure changes could corrupt file) | replace with proper JSON load/dump or jq.  
- SEVERITY: Low | diff line 575 | Saylor entry set to enabled:false with no avatar (intentional but undocumented) | add comment.  
- SEVERITY: None | duplicate SHA prefix check in fetch (lines 108-111) works but is only advisory.  

No defects affect sentence law, onset, or gate thresholds. The diff is narrowly scoped to the D4 avatar fix and is correct for that scope.  
**READY**

## GPT4O — CYCLE 1 OUTPUT
### Q1: CORRECTNESS

1. **Function `_sha(path)` (lines 38-39):** Correctly computes the SHA-256 hash of the file at the given path. The function reads the file in binary mode and computes the hash, which matches the expected behavior.

2. **Function `avatar_url(channel_id)` (lines 42-56):** Fetches the YouTube channel metadata using `yt-dlp` and extracts the URL of the square avatar, channel title, and follower count. The function handles errors correctly by raising exceptions when the metadata is missing or no square avatar is found. The logic for selecting the largest square avatar is sound.

3. **Function `fetch_one(ch)` (lines 59-71):** Downloads the avatar image, checks its dimensions, and saves it as a 512x512 PNG. It raises an exception if the avatar is not square or too small, which aligns with the requirements. The function returns a dictionary with relevant metadata, including the SHA-256 hash.

4. **Function `contact_sheet(rows)` (lines 74-85):** Creates a contact sheet of avatars for visual verification. The function uses PIL to draw the images and text, and it handles both successful and failed avatar fetches.

5. **Function `cmd_fetch(all_channels=False)` (lines 88-114):** Fetches avatars for channels listed in `channels.json`, skipping those already fetched unless `--all` is specified. It logs errors and generates a report and contact sheet. The function correctly identifies duplicate avatars by SHA-256 hash and marks them as errors.

6. **Function `cmd_register()` (lines 117-140):** Updates `channels.json` with the paths and SHA-256 prefixes of successfully fetched avatars. It ensures the JSON remains valid after modifications.

7. **Function `validate_avatar(path)` (lines 863-873):** Validates that an avatar is square and meets the minimum size requirement. It raises exceptions for non-compliant avatars, ensuring adherence to the requirements.

8. **Function `_find_avatar(segment_dir, channel_name)` (lines 970-987):** Retrieves the verified avatar from `channels.json` and checks its SHA-256 prefix. It raises exceptions if the avatar is missing or does not match the registered hash, ensuring compliance with the requirements.

Overall, the functions are correctly implemented according to their docstrings and the laws. There are no paths that produce a PASS when data is missing or a model failed.

### Q2: LAW COMPLIANCE

1. **SENTENCE LAW:** Not directly applicable to the diff provided, as it deals with avatars and not sentence boundaries.

2. **SELECTION LOCK:** Compliant. No evidence in the diff suggests that expected words are recomputed after selection.

3. **SNAP LIMIT:** Not directly applicable to the diff provided, as it deals with avatars and not sentence boundaries.

4. **ONSET/TAIL:** Not directly applicable to the diff provided, as it deals with avatars and not audio segments.

5. **CREDITS:** Compliant. The code ensures that only real, verified avatars are used, as per lines 970-987.

6. **LAW 20 / M2:** Compliant. The code does not change gate thresholds or reclassify failing gates.

7. **M12 FAIL CLOSED:** Compliant. The code raises exceptions when data is missing or validation fails, as seen in lines 980-985.

8. **LAW 22:** Not directly applicable to the diff provided, as it deals with avatars and not the v2f reference path.

### Q3: TESTS

The diff does not include explicit test cases or test results. However, the implementation of `cmd_fetch` and `cmd_register` suggests that there is a mechanism to verify the correctness of avatar fetching and registration through the generation of a contact sheet and JSON report. Without the actual test files, it's unclear if the must-fail fixtures fail for the right reasons or if controls pass for the right reasons.

### Q4: VERDICT

- **SEVERITY: LOW | Line 829 | Issue: Channel is disabled without explanation. | Fix: Ensure that disabling a channel is intentional and documented.**
- **SEVERITY: LOW | General | Issue: Lack of explicit test cases in the diff. | Fix: Ensure that test cases are included and verify compliance with the laws.**

Overall, the code appears to be compliant with the requirements and laws, with minor issues noted. The implementation is robust in handling errors and validating inputs. However, the absence of explicit test cases in the diff makes it difficult to fully assess the testing coverage.

**VERDICT: READY**

## GEMINI — CYCLE 1 OUTPUT
An audit of the `pulse-sentence-law` feature follows.

### Q1: CORRECTNESS

The provided diff focuses exclusively on fixing defect D4 (warped credit avatars) by overhauling the avatar management system. The code related to this goal is largely correct, but there are areas of concern.

-   **`pipeline/avatar_onboard.py`**: This new script provides a robust, two-step process for fetching and registering channel avatars.
    -   `avatar_url()` (lines 42-57) correctly uses `yt-dlp` to find the highest-resolution *square* channel avatar, and correctly raises an exception if none is found. This correctly prevents non-square images (like video thumbnails) from entering the pipeline at the source.
    -   `fetch_one()` (lines 59-71) includes a secondary check for squareness (`SQUARE_TOL`, line 65) before resizing and saving the image. This is a good redundant check.
    -   `cmd_register()` (lines 117-141) modifies `channels.json` using regular expressions. While the code is clever (e.g., iterating in reverse to keep string indices valid), this is a brittle approach. It is dependent on the specific formatting of the JSON file and could fail in unexpected ways. The final `json.loads(text)` check (line 136) is a necessary safety net but does not make the method robust.
-   **`pipeline/shoutout.py`**: The changes here correctly harden the rendering pipeline against incorrect avatars.
    -   The old, permissive `_find_avatar` function, which included on-demand fetching and placeholder generation (the likely cause of D4), has been completely removed.
    -   The new `_find_avatar` (lines 970-987) is strict. It only accepts avatars registered in `channels.json`, verifies the file exists, checks its hash against a stored prefix (line 984), and validates its dimensions.
    -   The new `validate_avatar` gate (lines 863-873) correctly enforces that avatars are square and meet a minimum size, raising a `ValueError` (a hard stop) if they do not.
-   **Fail-Closed Behavior**: The new logic is a strong example of the M12 FAIL CLOSED law. Any issue—missing registry entry, missing file, hash mismatch, or invalid image dimensions—results in a raised exception, stopping the pipeline. This correctly prevents a render with bad data.

### Q2: LAW COMPLIANCE

-   **SENTENCE LAW**: NOT ADDRESSED. The diff contains no code related to sentence boundaries, acoustics, or transcripts.
-   **SELECTION LOCK**: NOT ADDRESSED.
-   **SNAP LIMIT**: NOT ADDRESSED.
-   **ONSET/TAIL**: NOT ADDRESSED.
-   **CREDITS**: **COMPLIANT**. The new system is designed to comply with this law. `avatar_onboard.py` fetches real, square channel avatars, and the new gates in `shoutout.py` (lines 863-873, 970-987) ensure only these verified avatars are used, explicitly rejecting non-square images that could be video thumbnails.
-   **LAW 20 / M2**: **COMPLIANT**. The new avatar validation gate (`validate_avatar`) uses constants for its thresholds (`AVATAR_SQUARE_TOL`, `AVATAR_MIN_PX` on lines 852-853) and constitutes a hard stop by raising exceptions on failure.
-   **M12 FAIL CLOSED**: **COMPLIANT**. The new `_find_avatar` implementation (lines 970-987) is a textbook case of failing closed. It raises exceptions for missing data, missing files, and integrity check failures, preventing a pass.
-   **LAW 22**: **UNCERTAIN**. This law requires a frozen reference file (`v2f_2026-11-06`) to re-render byte-identically. The avatar fix will change the visual output of the credits scene. If the reference video includes channels whose avatars were previously warped (or missing), this fix will alter the render, likely violating this law. Without understanding how this law is handled during bug fixes that change output, compliance cannot be confirmed.
-   **Other Laws**: The changes appear to comply with "Smallest diff" (for the logic change) and "no new renderer".

### Q3: TESTS

The diff does not contain any test files. The feature description explicitly mentions `pipeline/test_pulse_20261110_mustfail.py`, which is intended to prove that the new gates catch the errors from the problematic run. Without this file, it is impossible to verify the central claim that the fix is proven on the faulty fixtures.

### Q4: VERDICT

The code in this diff successfully and robustly fixes the avatar-warping defect (D4). The new avatar pipeline is well-designed, secure, and adheres to the fail-closed principle. However, several significant issues prevent a "READY" verdict.

-   **HIGH** | N/A | Incomplete Scope | The feature is named `pulse-sentence-law` and its description covers a range of defects (D1-D6). This diff exclusively addresses the avatar issue (D4). There is a major disconnect between the stated scope and the provided code, and the most prominent part of the feature name ("sentence-law") is not implemented.
-   **HIGH** | N/A | Missing Tests | The test file (`test_pulse_20261110_mustfail.py`) that allegedly proves the fix works is not included in the diff. This is a critical omi

## CLAUDE'S CYCLE 1 CONSENSUS
# CONSENSUS REPORT — PULSE-SENTENCE-LAW — CYCLE 1
Generated: 2026-11-11 03:10
Models: grok, gpt4o, gemini

---

## SCORES

| Subsystem | Gemini | GPT-4o | Grok | Consensus |
|---|---|---|---|---|
| Correctness — Avatar Pipeline | 7/10 | 9/10 | 8/10 | **8/10** |
| Correctness — Sentence Law | N/A | N/A | N/A | **N/A (not in diff)** |
| Law: CREDITS | COMPLIANT | COMPLIANT | COMPLIANT | **COMPLIANT** |
| Law: M12 FAIL CLOSED | COMPLIANT | COMPLIANT | COMPLIANT | **COMPLIANT** |
| Law: SENTENCE LAW | NOT ADDRESSED | NOT ADDRESSED | NOT ADDRESSED | **NOT ADDRESSED** |
| Law: LAW 22 | UNCERTAIN | NOT ADDRESSED | NOT ADDRESSED | **UNCERTAIN** |
| Law: SELECTION LOCK | NOT ADDRESSED | COMPLIANT | COMPLIANT | **DEFERRED** |
| Law: LAW 20 / M2 | COMPLIANT | COMPLIANT | COMPLIANT | **COMPLIANT** |
| Tests | MISSING | MISSING | MISSING | **MISSING** |
| Overall Verdict | NOT READY | READY | READY | **NOT READY** |

> **Score note:** Gemini is correct to flag NOT READY. The 2-to-1 "READY" votes from GPT-4o and Grok evaluate only the D4 avatar sub-scope in isolation; Gemini correctly evaluates the full stated scope. Consensus defers to the stricter assessment when scope completeness is in question.

---

## UNANIMOUS FINDINGS (all 3 models agree — implement unconditionally)

### U1 — Missing test file is a critical gap
- **What:** The feature description explicitly requires `pipeline/test_pulse_20261110_mustfail.py`. All three models noted its complete absence. Without it there is no machine-verifiable proof that the new avatar gates catch the exact errors from the problematic run.
- **File/Line:** `pipeline/test_pulse_20261110_mustfail.py` — does not exist in diff
- **Change:** Create the must-fail fixture suite. It must include at minimum: (a) a test that feeds a non-square image and asserts `validate_avatar` raises `ValueError`; (b) a test that feeds a hash-mismatched avatar and asserts `_find_avatar` raises; (c) a test that feeds a missing `channels.json` entry and asserts `_find_avatar` raises; (d) a test that feeds the original warped-avatar fixture from `pulse_20261110` and asserts the render aborts.

### U2 — `cmd_register` uses brittle regex in-place JSON editing
- **What:** All three models independently flagged `cmd_register` (lines 117–141 of `avatar_onboard.py`) as modifying `channels.json` via regular-expression string surgery. If the file's whitespace, key ordering, or structure changes by even one character, the regex may corrupt the file or silently produce invalid JSON. The final `json.loads(text)` sanity check catches corruption but does not make the approach robust.
- **File/Line:** `pipeline/avatar_onboard.py:117–141`
- **Change:** Replace the regex loop with: `data = json.loads(path.read_text())` → modify `data` as a Python dict → `path.write_text(json.dumps(data, indent=2, ensure_ascii=False))`. This is atomic, encoding-safe, and immune to formatting drift.

### U3 — Sentence-Law code is entirely absent from the diff
- **What:** The fea

---

## ORIGINAL CODE (same code as Cycle 1)
## THE CODE (every new and modified file)

### File: docs/audits/pulse-sentence-law/CURRENT.diff (991 lines)
```
   1 | diff --git a/pipeline/avatar_onboard.py b/pipeline/avatar_onboard.py
   2 | new file mode 100644
   3 | index 00000000..075e235c
   4 | --- /dev/null
   5 | +++ b/pipeline/avatar_onboard.py
   6 | @@ -0,0 +1,141 @@
   7 | +#!/usr/bin/env python3
   8 | +"""pipeline/avatar_onboard.py — real channel avatars for the credits card (M6, D4 2026-11-11).
   9 | +
  10 | +The shout-out card shows each credited channel's REAL YouTube avatar: the square channel picture
  11 | +from the channel page metadata (yt-dlp), never a video thumbnail and never a generated placeholder.
  12 | +D4: on 2026-11-10 the card showed 1280x720 video thumbnails squashed into circles.
  13 | +
  14 | +  fetch    python3 pipeline/avatar_onboard.py fetch [--all]   -> pipeline/avatars/<slug>_512.png +
  15 | +           avatars/ONBOARD_REPORT.json + avatars/CONTACT_SHEET.png (for visual verification)
  16 | +  register python3 pipeline/avatar_onboard.py register          -> channels.json avatar_path +
  17 | +           avatar_sha256_prefix for every fetched avatar listed in ONBOARD_REPORT.json as ok
  18 | +Only `register` writes the registry, and only after the contact sheet was looked at (M6).
  19 | +"""
  20 | +import hashlib
  21 | +import io
  22 | +import json
  23 | +import os
  24 | +import subprocess
  25 | +import sys
  26 | +import urllib.request
  27 | +
  28 | +PIPELINE_DIR = os.path.dirname(os.path.abspath(__file__))
  29 | +CHANNELS_PATH = os.path.join(PIPELINE_DIR, "channels.json")
  30 | +AVATAR_DIR = os.path.join(PIPELINE_DIR, "avatars")
  31 | +REPORT = os.path.join(AVATAR_DIR, "ONBOARD_REPORT.json")
  32 | +SHEET = os.path.join(AVATAR_DIR, "CONTACT_SHEET.png")
  33 | +SIZE = 512
  34 | +MIN_SOURCE_PX = 176
  35 | +SQUARE_TOL = 0.01
  36 | +
  37 | +
  38 | +def _sha(path):
  39 | +    return hashlib.sha256(open(path, "rb").read()).hexdigest()
  40 | +
  41 | +
  42 | +def avatar_url(channel_id):
  43 | +    """(URL of the channel's square avatar, channel title, follower count) from yt-dlp channel
  44 | +    metadata. Raises if none is square. Title/followers are for the identity check (E-FAIL-010)."""
  45 | +    r = subprocess.run(["yt-dlp", "--flat-playlist", "--dump-single-json", "--playlist-items", "0",
  46 | +                        "--no-warnings", f"https://www.youtube.com/channel/{channel_id}"],
  47 | +                       capture_output=True, text=True, timeout=120)
  48 | +    if r.returncode != 0 or not r.stdout.strip():
  49 | +        raise RuntimeError(f"yt-dlp channel metadata failed: {r.stderr.strip()[-200:]}")
  50 | +    meta = json.loads(r.stdout)
  51 | +    thumbs = meta.get("thumbnails") or []
  52 | +    sq = [t for t in thumbs if t.get("width") and t.get("width") == t.get("height")
  53 | +          and t["width"] >= MIN_SOURCE_PX and t.get("url")]
  54 | +    if not sq:
  55 | +        raise RuntimeError("channel metadata has no square avatar")
  56 | +    return max(sq, key=lambda t: t["width"])["url"], meta.get("channel"), meta.get("channel_follower_count")
  57 | +
  58 | +
  59 | +def fetch_one(ch):
  60 | +    from PIL import Image
  61 | +    url, title, followers = avatar_url(ch["channel_id"])
  62 | +    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
  63 | +    img = Image.open(io.BytesIO(urllib.request.urlopen(req, timeout=60).read())).convert("RGB")
  64 | +    w, h = img.size
  65 | +    if abs(w - h) > SQUARE_TOL * max(w, h) or min(w, h) < MIN_SOURCE_PX:
  66 | +        raise RuntimeError(f"avatar is not a square >= {MIN_SOURCE_PX} px: {w}x{h}")
  67 | +    path = os.path.join(AVATAR_DIR, f"{ch['slug']}_{SIZE}.png")
  68 | +    img.resize((SIZE, SIZE), Image.LANCZOS).save(path)
  69 | +    return {"slug": ch["slug"], "display_name": ch["display_name"], "youtube_title": title,
  70 | +            "followers": followers, "source_px": [w, h],
  71 | +            "path": path, "sha256": _sha(path), "ok": True}
  72 | +
  73 | +
  74 | +def contact_sheet(rows):
  75 | +    from PIL import Image, ImageDraw
  76 | +    cell, cols = 160, 10
  77 | +    n = len(rows)
  78 | +    sheet = Image.new("RGB", (cols * cell, ((n + cols - 1) // cols) * (cell + 24)), (20, 20, 20))
  79 | +    d = ImageDraw.Draw(sheet)
  80 | +    for i, r in enumerate(rows):
  81 | +        x, y = (i % cols) * cell, (i // cols) * (cell + 24)
  82 | +        if r.get("ok"):
  83 | +            sheet.paste(Image.open(r["path"]).resize((cell - 8, cell - 8)), (x + 4, y + 4))
  84 | +        d.text((x + 4, y + cell), r["display_name"][:22], fill=(255, 255, 255) if r.get("ok") else (255, 80, 80))
  85 | +    sheet.save(SHEET)
  86 | +
  87 | +
  88 | +def cmd_fetch(all_channels=False):
  89 | +    os.makedirs(AVATAR_DIR, exist_ok=True)
  90 | +    reg = json.load(open(CHANNELS_PATH))
  91 | +    rows = []
  92 | +    for ch in reg:
  93 | +        if not ch.get("channel_id"):
  94 | +            continue
  95 | +        if ch.get("avatar_path") and os.path.exists(ch["avatar_path"]) and not all_channels:
  96 | +            continue
  97 | +        try:
  98 | +            rows.append(fetch_one(ch))
  99 | +        except Exception as e:
 100 | +            rows.append({"slug": ch["slug"], "display_name": ch["display_name"], "ok": False,
 101 | +                         "error": f"{type(e).__name__}: {e}"[:300]})
 102 | +        r = rows[-1]
 103 | +        print(f"  {ch['display_name']}: " + (f"ok (youtube: {r['youtube_title']!r}, {r['followers']} followers)"
 104 | +                                             if r["ok"] else r["error"]), flush=True)
 105 | +    shas = [r["sha256"] for r in rows if r.get("ok")] + \
 106 | +           [_sha(c["avatar_path"]) for c in reg if c.get("avatar_path") and os.path.exists(c["avatar_path"])
 107 | +            and not any(r["slug"] == c["slug"] for r in rows)]
 108 | +    dup = {h for h in shas if shas.count(h) > 1}
 109 | +    for r in rows:
 110 | +        if r.get("ok") and r["sha256"] in dup:
 111 | +            r.update(ok=False, error="avatar sha256 not unique (R6)")
 112 | +    json.dump(rows, open(REPORT, "w"), indent=1)
 113 | +    contact_sheet(rows)
 114 | +    print(f"fetched {sum(r['ok'] for r in rows)}/{len(rows)}; sheet {SHEET}")
 115 | +
 116 | +
 117 | +def cmd_register():
 118 | +    """In-place text edit of each channel's avatar_path / avatar_sha256_prefix (minimal registry diff)."""
 119 | +    import re
 120 | +    rows = {r["slug"]: r for r in json.load(open(REPORT)) if r.get("ok")}
 121 | +    text = open(CHANNELS_PATH).read()
 122 | +    n = 0
 123 | +    for slug, r in rows.items():
 124 | +        if not (os.path.exists(r["path"]) and _sha(r["path"]) == r["sha256"]):
 125 | +            continue
 126 | +        for m in reversed(list(re.finditer(re.escape(f'"slug": "{slug}",'), text))):   # every entry
 127 | +            i = m.start()
 128 | +            j = text.find('"slug": "', i + 1)
 129 | +            j = len(text) if j < 0 else j
 130 | +            block = text[i:j]
 131 | +            block = re.sub(r'"avatar_path": "[^"]*"', f'"avatar_path": "{r["path"]}"', block, count=1)
 132 | +            block = re.sub(r'"avatar_sha256_prefix": "[^"]*"', f'"avatar_sha256_prefix": "{r["sha256"][:16]}"',
 133 | +                           block, count=1)
 134 | +            text = text[:i] + block + text[j:]
 135 | +            n += 1
 136 | +    json.loads(text)                       # still valid JSON
 137 | +    with open(CHANNELS_PATH + ".tmp", "w") as f:
 138 | +        f.write(text)
 139 | +    os.replace(CHANNELS_PATH + ".tmp", CHANNELS_PATH)
 140 | +    print(f"registered {n} avatars")
 141 | +
 142 | +
 143 | +if __name__ == "__main__":
 144 | +    if len(sys.argv) > 1 and sys.argv[1] == "register":
 145 | +        cmd_register()
 146 | +    else:
 147 | +        cmd_fetch(all_channels="--all" in sys.argv)
 148 | diff --git a/pipeline/channels.json b/pipeline/channels.json
 149 | index e6d2f966..9edd0a4e 100644
 150 | --- a/pipeline/channels.json
 151 | +++ b/pipeline/channels.json
 152 | @@ -7,8 +7,8 @@
 153 |      "tier": 1,
 154 |      "priority": 1,
 155 |      "enabled": true,
 156 | -    "avatar_path": "",
 157 | -    "avatar_sha256_prefix": "",
 158 | +    "avatar_path": "/home/ultron/protocol_pulse/pipeline/avatars/andreas_antonopoulos_512.png",
 159 | +    "avatar_sha256_prefix": "f072d69be091e377",
 160 |      "has_chyron": false,
 161 |      "layout_table_key": "",
 162 |      "layout_status": "pending",
 163 | @@ -69,8 +69,8 @@
 164 |      "tier": 1,
 165 |      "priority": 1,
 166 |      "enabled": true,
 167 | -    "avatar_path": "",
 168 | -    "avatar_sha256_prefix": "",
 169 | +    "avatar_path": "/home/ultron/protocol_pulse/pipeline/avatars/base58_512.png",
 170 | +    "avatar_sha256_prefix": "2846a569c15fd8c0",
 171 |      "has_chyron": false,
 172 |      "layout_table_key": "",
 173 |      "layout_status": "pending",
 174 | @@ -85,8 +85,8 @@
 175 |      "tier": 1,
 176 |      "priority": 1,
 177 |      "enabled": true,
 178 | -    "avatar_path": "",
 179 | -    "avatar_sha256_prefix": "",
 180 | +    "avatar_path": "/home/ultron/protocol_pulse/pipeline/avatars/bitcoin_audible_512.png",
 181 | +    "avatar_sha256_prefix": "09e2ad1369cea88c",
 182 |      "has_chyron": false,
 183 |      "layout_table_key": "",
 184 |      "layout_status": "pending",
 185 | @@ -101,8 +101,8 @@
 186 |      "tier": 1,
 187 |      "priority": 1,
 188 |      "enabled": true,
 189 | -    "avatar_path": "",
 190 | -    "avatar_sha256_prefix": "",
 191 | +    "avatar_path": "/home/ultron/protocol_pulse/pipeline/avatars/bitcoin_explained_512.png",
 192 | +    "avatar_sha256_prefix": "591d5c523f214e24",
 193 |      "has_chyron": false,
 194 |      "layout_table_key": "",
 195 |      "layout_status": "pending",
 196 | @@ -148,8 +148,8 @@
 197 |      "tier": 1,
 198 |      "priority": 1,
 199 |      "enabled": true,
 200 | -    "avatar_path": "",
 201 | -    "avatar_sha256_prefix": "",
 202 | +    "avatar_path": "/home/ultron/protocol_pulse/pipeline/avatars/bitcoin_mechanic_512.png",
 203 | +    "avatar_sha256_prefix": "b2e10dd548bb5e48",
 204 |      "has_chyron": false,
 205 |      "layout_table_key": "",
 206 |      "layout_status": "pending",
 207 | @@ -164,8 +164,8 @@
 208 |      "tier": 1,
 209 |      "priority": 1,
 210 |      "enabled": true,
 211 | -    "avatar_path": "",
 212 | -    "avatar_sha256_prefix": "",
 213 | +    "avatar_path": "/home/ultron/protocol_pulse/pipeline/avatars/bitcoin_podcast_512.png",
 214 | +    "avatar_sha256_prefix": "727b01b70ca03e88",
 215 |      "has_chyron": false,
 216 |      "layout_table_key": "",
 217 |      "layout_status": "pending",
 218 | @@ -195,8 +195,8 @@
 219 |      "tier": 1,
 220 |      "priority": 1,
 221 |      "enabled": true,
 222 | -    "avatar_path": "",
 223 | -    "avatar_sha256_prefix": "",
 224 | +    "avatar_path": "/home/ultron/protocol_pulse/pipeline/avatars/guy_swann_512.png",
 225 | +    "avatar_sha256_prefix": "09e2ad1369cea88c",
 226 |      "has_chyron": false,
 227 |      "layout_table_key": "",
 228 |      "layout_status": "pending",
 229 | @@ -211,8 +211,8 @@
 230 |      "tier": 1,
 231 |      "priority": 1,
 232 |      "enabled": true,
 233 | -    "avatar_path": "",
 234 | -    "avatar_sha256_prefix": "",
 235 | +    "avatar_path": "/home/ultron/protocol_pulse/pipeline/avatars/jameson_lopp_512.png",
 236 | +    "avatar_sha256_prefix": "8a3487566357e238",
 237 |      "has_chyron": false,
 238 |      "layout_table_key": "",
 239 |      "layout_status": "pending",
 240 | @@ -227,8 +227,8 @@
 241 |      "tier": 1,
 242 |      "priority": 1,
 243 |      "enabled": true,
 244 | -    "avatar_path": "",
 245 | -    "avatar_sha256_prefix": "",
 246 | +    "avatar_path": "/home/ultron/protocol_pulse/pipeline/avatars/natalie_brunell_512.png",
 247 | +    "avatar_sha256_prefix": "bbf0deab624f81f2",
 248 |      "has_chyron": false,
 249 |      "layout_table_key": "",
 250 |      "layout_status": "pending",
 251 | @@ -243,8 +243,8 @@
 252 |      "tier": 1,
 253 |      "priority": 1,
 254 |      "enabled": true,
 255 | -    "avatar_path": "",
 256 | -    "avatar_sha256_prefix": "",
 257 | +    "avatar_path": "/home/ultron/protocol_pulse/pipeline/avatars/nathaniel_whittemore_512.png",
 258 | +    "avatar_sha256_prefix": "35faa925cf36b745",
 259 |      "has_chyron": false,
 260 |      "layout_table_key": "",
 261 |      "layout_status": "pending",
 262 | @@ -259,8 +259,8 @@
 263 |      "tier": 1,
 264 |      "priority": 1,
 265 |      "enabled": true,
 266 | -    "avatar_path": "",
 267 | -    "avatar_sha256_prefix": "",
 268 | +    "avatar_path": "/home/ultron/protocol_pulse/pipeline/avatars/preston_pysh_512.png",
 269 | +    "avatar_sha256_prefix": "c64701c89e93ef29",
 270 |      "has_chyron": false,
 271 |      "layout_table_key": "",
 272 |      "layout_status": "pending",
 273 | @@ -275,8 +275,8 @@
 274 |      "tier": 1,
 275 |      "priority": 1,
 276 |      "enabled": true,
 277 | -    "avatar_path": "",
 278 | -    "avatar_sha256_prefix": "",
 279 | +    "avatar_path": "/home/ultron/protocol_pulse/pipeline/avatars/robert_breedlove_512.png",
 280 | +    "avatar_sha256_prefix": "bcbbe9d4f695a167",
 281 |      "has_chyron": false,
 282 |      "layout_table_key": "",
 283 |      "layout_status": "pending",
 284 | @@ -291,8 +291,8 @@
 285 |      "tier": 1,
 286 |      "priority": 1,
 287 |      "enabled": true,
 288 | -    "avatar_path": "",
 289 | -    "avatar_sha256_prefix": "",
 290 | +    "avatar_path": "/home/ultron/protocol_pulse/pipeline/avatars/saifedean_ammous_512.png",
 291 | +    "avatar_sha256_prefix": "5e362ed141f6bab9",
 292 |      "has_chyron": false,
 293 |      "layout_table_key": "",
 294 |      "layout_status": "pending",
 295 | @@ -307,8 +307,8 @@
 296 |      "tier": 1,
 297 |      "priority": 1,
 298 |      "enabled": true,
 299 | -    "avatar_path": "",
 300 | -    "avatar_sha256_prefix": "",
 301 | +    "avatar_path": "/home/ultron/protocol_pulse/pipeline/avatars/stephan_livera_512.png",
 302 | +    "avatar_sha256_prefix": "7ac6f1eb5491b3d2",
 303 |      "has_chyron": false,
 304 |      "layout_table_key": "",
 305 |      "layout_status": "pending",
 306 | @@ -323,8 +323,8 @@
 307 |      "tier": 1,
 308 |      "priority": 1,
 309 |      "enabled": true,
 310 | -    "avatar_path": "",
 311 | -    "avatar_sha256_prefix": "",
 312 | +    "avatar_path": "/home/ultron/protocol_pulse/pipeline/avatars/swan_bitcoin_512.png",
 313 | +    "avatar_sha256_prefix": "b2aec803987197a1",
 314 |      "has_chyron": false,
 315 |      "layout_table_key": "",
 316 |      "layout_status": "pending",
 317 | @@ -339,8 +339,8 @@
 318 |      "tier": 1,
 319 |      "priority": 1,
 320 |      "enabled": true,
 321 | -    "avatar_path": "",
 322 | -    "avatar_sha256_prefix": "",
 323 | +    "avatar_path": "/home/ultron/protocol_pulse/pipeline/avatars/tftc_512.png",
 324 | +    "avatar_sha256_prefix": "9bbc5bb05758e0ef",
 325 |      "has_chyron": false,
 326 |      "layout_table_key": "",
 327 |      "layout_status": "pending",
 328 | @@ -372,8 +372,8 @@
 329 |      "tier": 1,
 330 |      "priority": 1,
 331 |      "enabled": true,
 332 | -    "avatar_path": "",
 333 | -    "avatar_sha256_prefix": "",
 334 | +    "avatar_path": "/home/ultron/protocol_pulse/pipeline/avatars/the_bitcoin_podcast_512.png",
 335 | +    "avatar_sha256_prefix": "26d0d939973d2480",
 336 |      "has_chyron": false,
 337 |      "layout_table_key": "",
 338 |      "layout_status": "pending",
 339 | @@ -403,8 +403,8 @@
 340 |      "tier": 1,
 341 |      "priority": 1,
 342 |      "enabled": true,
 343 | -    "avatar_path": "",
 344 | -    "avatar_sha256_prefix": "",
 345 | +    "avatar_path": "/home/ultron/protocol_pulse/pipeline/avatars/tone_vays_512.png",
 346 | +    "avatar_sha256_prefix": "c0b5f4f1653fb479",
 347 |      "has_chyron": false,
 348 |      "layout_table_key": "",
 349 |      "layout_status": "pending",
 350 | @@ -419,8 +419,8 @@
 351 |      "tier": 1,
 352 |      "priority": 1,
 353 |      "enabled": true,
 354 | -    "avatar_path": "",
 355 | -    "avatar_sha256_prefix": "",
 356 | +    "avatar_path": "/home/ultron/protocol_pulse/pipeline/avatars/unchained_512.png",
 357 | +    "avatar_sha256_prefix": "d5a105de2fff62f0",
 358 |      "has_chyron": false,
 359 |      "layout_table_key": "",
 360 |      "layout_status": "pending",
 361 | @@ -435,8 +435,8 @@
 362 |      "tier": 1,
 363 |      "priority": 1,
 364 |      "enabled": true,
 365 | -    "avatar_path": "",
 366 | -    "avatar_sha256_prefix": "",
 367 | +    "avatar_path": "/home/ultron/protocol_pulse/pipeline/avatars/what_bitcoin_did_512.png",
 368 | +    "avatar_sha256_prefix": "9cfe2b209f99b6c4",
 369 |      "has_chyron": false,
 370 |      "layout_table_key": "",
 371 |      "layout_status": "pending",
 372 | @@ -451,8 +451,8 @@
 373 |      "tier": 2,
 374 |      "priority": 1,
 375 |      "enabled": true,
 376 | -    "avatar_path": "",
 377 | -    "avatar_sha256_prefix": "",
 378 | +    "avatar_path": "/home/ultron/protocol_pulse/pipeline/avatars/coffeezilla_512.png",
 379 | +    "avatar_sha256_prefix": "cab8eba765603cc7",
 380 |      "has_chyron": false,
 381 |      "layout_table_key": "",
 382 |      "layout_status": "pending",
 383 | @@ -467,8 +467,8 @@
 384 |      "tier": 2,
 385 |      "priority": 1,
 386 |      "enabled": true,
 387 | -    "avatar_path": "",
 388 | -    "avatar_sha256_prefix": "",
 389 | +    "avatar_path": "/home/ultron/protocol_pulse/pipeline/avatars/coffeezilla_extras_512.png",
 390 | +    "avatar_sha256_prefix": "be7a2ec4baac7950",
 391 |      "has_chyron": false,
 392 |      "layout_table_key": "",
 393 |      "layout_status": "pending",
 394 | @@ -483,8 +483,8 @@
 395 |      "tier": 2,
 396 |      "priority": 2,
 397 |      "enabled": true,
 398 | -    "avatar_path": "",
 399 | -    "avatar_sha256_prefix": "",
 400 | +    "avatar_path": "/home/ultron/protocol_pulse/pipeline/avatars/altcoin_daily_512.png",
 401 | +    "avatar_sha256_prefix": "7a9a97aed3ea56c5",
 402 |      "has_chyron": false,
 403 |      "layout_table_key": "",
 404 |      "layout_status": "pending",
 405 | @@ -499,8 +499,8 @@
 406 |      "tier": 2,
 407 |      "priority": 2,
 408 |      "enabled": true,
 409 | -    "avatar_path": "",
 410 | -    "avatar_sha256_prefix": "",
 411 | +    "avatar_path": "/home/ultron/protocol_pulse/pipeline/avatars/anthony_pompliano_512.png",
 412 | +    "avatar_sha256_prefix": "1650105990ecc92f",
 413 |      "has_chyron": false,
 414 |      "layout_table_key": "",
 415 |      "layout_status": "pending",
 416 | @@ -530,8 +530,8 @@
 417 |      "tier": 2,
 418 |      "priority": 2,
 419 |      "enabled": true,
 420 | -    "avatar_path": "",
 421 | -    "avatar_sha256_prefix": "",
 422 | +    "avatar_path": "/home/ultron/protocol_pulse/pipeline/avatars/bitfarms_512.png",
 423 | +    "avatar_sha256_prefix": "10f775a47f3e9ba9",
 424 |      "has_chyron": false,
 425 |      "layout_table_key": "",
 426 |      "layout_status": "pending",
 427 | @@ -546,8 +546,8 @@
 428 |      "tier": 2,
 429 |      "priority": 2,
 430 |      "enabled": true,
 431 | -    "avatar_path": "",
 432 | -    "avatar_sha256_prefix": "",
 433 | +    "avatar_path": "/home/ultron/protocol_pulse/pipeline/avatars/bitstamp_512.png",
 434 | +    "avatar_sha256_prefix": "9074a6e2b49610a4",
 435 |      "has_chyron": false,
 436 |      "layout_table_key": "",
 437 |      "layout_status": "pending",
 438 | @@ -562,8 +562,8 @@
 439 |      "tier": 2,
 440 |      "priority": 2,
 441 |      "enabled": true,
 442 | -    "avatar_path": "",
 443 | -    "avatar_sha256_prefix": "",
 444 | +    "avatar_path": "/home/ultron/protocol_pulse/pipeline/avatars/blockware_solutions_512.png",
 445 | +    "avatar_sha256_prefix": "484e59b698db28a4",
 446 |      "has_chyron": false,
 447 |      "layout_table_key": "",
 448 |      "layout_status": "pending",
 449 | @@ -578,8 +578,8 @@
 450 |      "tier": 2,
 451 |      "priority": 2,
 452 |      "enabled": true,
 453 | -    "avatar_path": "",
 454 | -    "avatar_sha256_prefix": "",
 455 | +    "avatar_path": "/home/ultron/protocol_pulse/pipeline/avatars/clark_moody_512.png",
 456 | +    "avatar_sha256_prefix": "4667b979a3920bee",
 457 |      "has_chyron": false,
 458 |      "layout_table_key": "",
 459 |      "layout_status": "pending",
 460 | @@ -594,8 +594,8 @@
 461 |      "tier": 2,
 462 |      "priority": 2,
 463 |      "enabled": true,
 464 | -    "avatar_path": "",
 465 | -    "avatar_sha256_prefix": "",
 466 | +    "avatar_path": "/home/ultron/protocol_pulse/pipeline/avatars/coin_bureau_512.png",
 467 | +    "avatar_sha256_prefix": "efb85001521bdfc8",
 468 |      "has_chyron": false,
 469 |      "layout_table_key": "",
 470 |      "layout_status": "pending",
 471 | @@ -626,8 +626,8 @@
 472 |      "tier": 2,
 473 |      "priority": 2,
 474 |      "enabled": true,
 475 | -    "avatar_path": "",
 476 | -    "avatar_sha256_prefix": "",
 477 | +    "avatar_path": "/home/ultron/protocol_pulse/pipeline/avatars/coingecko_512.png",
 478 | +    "avatar_sha256_prefix": "6882363d604f98c2",
 479 |      "has_chyron": false,
 480 |      "layout_table_key": "",
 481 |      "layout_status": "pending",
 482 | @@ -642,8 +642,8 @@
 483 |      "tier": 2,
 484 |      "priority": 2,
 485 |      "enabled": true,
 486 | -    "avatar_path": "",
 487 | -    "avatar_sha256_prefix": "",
 488 | +    "avatar_path": "/home/ultron/protocol_pulse/pipeline/avatars/cointelegraph_512.png",
 489 | +    "avatar_sha256_prefix": "a60039b5908afcb1",
 490 |      "has_chyron": false,
 491 |      "layout_table_key": "",
 492 |      "layout_status": "pending",
 493 | @@ -658,8 +658,8 @@
 494 |      "tier": 2,
 495 |      "priority": 2,
 496 |      "enabled": true,
 497 | -    "avatar_path": "",
 498 | -    "avatar_sha256_prefix": "",
 499 | +    "avatar_path": "/home/ultron/protocol_pulse/pipeline/avatars/compass_mining_512.png",
 500 | +    "avatar_sha256_prefix": "1a4dba0fe1a44bb6",
 501 |      "has_chyron": false,
 502 |      "layout_table_key": "",
 503 |      "layout_status": "pending",
 504 | @@ -674,8 +674,8 @@
 505 |      "tier": 2,
 506 |      "priority": 2,
 507 |      "enabled": true,
 508 | -    "avatar_path": "",
 509 | -    "avatar_sha256_prefix": "",
 510 | +    "avatar_path": "/home/ultron/protocol_pulse/pipeline/avatars/datadash_512.png",
 511 | +    "avatar_sha256_prefix": "4796d4ffab615084",
 512 |      "has_chyron": false,
 513 |      "layout_table_key": "",
 514 |      "layout_status": "pending",
 515 | @@ -690,8 +690,8 @@
 516 |      "tier": 2,
 517 |      "priority": 2,
 518 |      "enabled": true,
 519 | -    "avatar_path": "",
 520 | -    "avatar_sha256_prefix": "",
 521 | +    "avatar_path": "/home/ultron/protocol_pulse/pipeline/avatars/digital_asset_news_512.png",
 522 | +    "avatar_sha256_prefix": "fe95098be5293b0e",
 523 |      "has_chyron": false,
 524 |      "layout_table_key": "",
 525 |      "layout_status": "pending",
 526 | @@ -736,8 +736,8 @@
 527 |      "tier": 2,
 528 |      "priority": 2,
 529 |      "enabled": true,
 530 | -    "avatar_path": "",
 531 | -    "avatar_sha256_prefix": "",
 532 | +    "avatar_path": "/home/ultron/protocol_pulse/pipeline/avatars/george_gammon_512.png",
 533 | +    "avatar_sha256_prefix": "21b0a7e411158f20",
 534 |      "has_chyron": false,
 535 |      "layout_table_key": "",
 536 |      "layout_status": "pending",
 537 | @@ -767,8 +767,8 @@
 538 |      "tier": 2,
 539 |      "priority": 2,
 540 |      "enabled": true,
 541 | -    "avatar_path": "",
 542 | -    "avatar_sha256_prefix": "",
 543 | +    "avatar_path": "/home/ultron/protocol_pulse/pipeline/avatars/investing_with_tom_512.png",
 544 | +    "avatar_sha256_prefix": "0033e0dd65096d96",
 545 |      "has_chyron": false,
 546 |      "layout_table_key": "",
 547 |      "layout_status": "pending",
 548 | @@ -798,8 +798,8 @@
 549 |      "tier": 2,
 550 |      "priority": 2,
 551 |      "enabled": true,
 552 | -    "avatar_path": "",
 553 | -    "avatar_sha256_prefix": "",
 554 | +    "avatar_path": "/home/ultron/protocol_pulse/pipeline/avatars/marty_bent_rabbit_hole_recap_512.png",
 555 | +    "avatar_sha256_prefix": "9f268c5748705340",
 556 |      "has_chyron": false,
 557 |      "layout_table_key": "",
 558 |      "layout_status": "pending",
 559 | @@ -814,8 +814,8 @@
 560 |      "tier": 2,
 561 |      "priority": 2,
 562 |      "enabled": true,
 563 | -    "avatar_path": "",
 564 | -    "avatar_sha256_prefix": "",
 565 | +    "avatar_path": "/home/ultron/protocol_pulse/pipeline/avatars/max_keiser_512.png",
 566 | +    "avatar_sha256_prefix": "5338b28baabb9ccf",
 567 |      "has_chyron": false,
 568 |      "layout_table_key": "",
 569 |      "layout_status": "pending",
 570 | @@ -829,7 +829,7 @@
 571 |      "url": "https://www.youtube.com/@Saylor",
 572 |      "tier": 2,
 573 |      "priority": 2,
 574 | -    "enabled": true,
 575 | +    "enabled": false,
 576 |      "avatar_path": "",
 577 |      "avatar_sha256_prefix": "",
 578 |      "has_chyron": false,
 579 | @@ -846,8 +846,8 @@
 580 |      "tier": 2,
 581 |      "priority": 2,
 582 |      "enabled": true,
 583 | -    "avatar_path": "",
 584 | -    "avatar_sha256_prefix": "",
 585 | +    "avatar_path": "/home/ultron/protocol_pulse/pipeline/avatars/once_bitten_512.png",
 586 | +    "avatar_sha256_prefix": "84a80347f18b90d5",
 587 |      "has_chyron": false,
 588 |      "layout_table_key": "",
 589 |      "layout_status": "pending",
 590 | @@ -862,8 +862,8 @@
 591 |      "tier": 2,
 592 |      "priority": 2,
 593 |      "enabled": true,
 594 | -    "avatar_path": "",
 595 | -    "avatar_sha256_prefix": "",
 596 | +    "avatar_path": "/home/ultron/protocol_pulse/pipeline/avatars/real_vision_512.png",
 597 | +    "avatar_sha256_prefix": "377b400995639233",
 598 |      "has_chyron": false,
 599 |      "layout_table_key": "",
 600 |      "layout_status": "pending",
 601 | @@ -878,8 +878,8 @@
 602 |      "tier": 2,
 603 |      "priority": 2,
 604 |      "enabled": true,
 605 | -    "avatar_path": "",
 606 | -    "avatar_sha256_prefix": "",
 607 | +    "avatar_path": "/home/ultron/protocol_pulse/pipeline/avatars/real_vision_finance_512.png",
 608 | +    "avatar_sha256_prefix": "377b400995639233",
 609 |      "has_chyron": false,
 610 |      "layout_table_key": "",
 611 |      "layout_status": "pending",
 612 | @@ -894,8 +894,8 @@
 613 |      "tier": 2,
 614 |      "priority": 2,
 615 |      "enabled": true,
 616 | -    "avatar_path": "",
 617 | -    "avatar_sha256_prefix": "",
 618 | +    "avatar_path": "/home/ultron/protocol_pulse/pipeline/avatars/riot_platforms_512.png",
 619 | +    "avatar_sha256_prefix": "9e1558ff41572226",
 620 |      "has_chyron": false,
 621 |      "layout_table_key": "",
 622 |      "layout_status": "pending",
 623 | @@ -910,8 +910,8 @@
 624 |      "tier": 2,
 625 |      "priority": 2,
 626 |      "enabled": true,
 627 | -    "avatar_path": "",
 628 | -    "avatar_sha256_prefix": "",
 629 | +    "avatar_path": "/home/ultron/protocol_pulse/pipeline/avatars/scott_melker_512.png",
 630 | +    "avatar_sha256_prefix": "05322977b211e582",
 631 |      "has_chyron": false,
 632 |      "layout_table_key": "",
 633 |      "layout_status": "pending",
 634 | @@ -926,8 +926,8 @@
 635 |      "tier": 2,
 636 |      "priority": 2,
 637 |      "enabled": true,
 638 | -    "avatar_path": "",
 639 | -    "avatar_sha256_prefix": "",
 640 | +    "avatar_path": "/home/ultron/protocol_pulse/pipeline/avatars/stacker_news_512.png",
 641 | +    "avatar_sha256_prefix": "f2faeba669ff26cf",
 642 |      "has_chyron": false,
 643 |      "layout_table_key": "",
 644 |      "layout_status": "pending",
 645 | @@ -942,8 +942,8 @@
 646 |      "tier": 2,
 647 |      "priority": 2,
 648 |      "enabled": true,
 649 | -    "avatar_path": "",
 650 | -    "avatar_sha256_prefix": "",
 651 | +    "avatar_path": "/home/ultron/protocol_pulse/pipeline/avatars/strategy_microstrategy_512.png",
 652 | +    "avatar_sha256_prefix": "18794b982b2d8254",
 653 |      "has_chyron": false,
 654 |      "layout_table_key": "",
 655 |      "layout_status": "pending",
 656 | @@ -958,8 +958,8 @@
 657 |      "tier": 2,
 658 |      "priority": 2,
 659 |      "enabled": true,
 660 | -    "avatar_path": "",
 661 | -    "avatar_sha256_prefix": "",
 662 | +    "avatar_path": "/home/ultron/protocol_pulse/pipeline/avatars/strike_512.png",
 663 | +    "avatar_sha256_prefix": "8423c1e7a3c4d48a",
 664 |      "has_chyron": false,
 665 |      "layout_table_key": "",
 666 |      "layout_status": "pending",
 667 | @@ -974,8 +974,8 @@
 668 |      "tier": 2,
 669 |      "priority": 2,
 670 |      "enabled": true,
 671 | -    "avatar_path": "",
 672 | -    "avatar_sha256_prefix": "",
 673 | +    "avatar_path": "/home/ultron/protocol_pulse/pipeline/avatars/wolf_of_all_streets_512.png",
 674 | +    "avatar_sha256_prefix": "8c24c60747900f27",
 675 |      "has_chyron": false,
 676 |      "layout_table_key": "",
 677 |      "layout_status": "pending",
 678 | @@ -1006,8 +1006,8 @@
 679 |      "tier": 3,
 680 |      "priority": 3,
 681 |      "enabled": true,
 682 | -    "avatar_path": "",
 683 | -    "avatar_sha256_prefix": "",
 684 | +    "avatar_path": "/home/ultron/protocol_pulse/pipeline/avatars/bankless_512.png",
 685 | +    "avatar_sha256_prefix": "2c0af7a099ed21aa",
 686 |      "has_chyron": false,
 687 |      "layout_table_key": "",
 688 |      "layout_status": "pending",
 689 | @@ -1022,8 +1022,8 @@
 690 |      "tier": 3,
 691 |      "priority": 3,
 692 |      "enabled": true,
 693 | -    "avatar_path": "",
 694 | -    "avatar_sha256_prefix": "",
 695 | +    "avatar_path": "/home/ultron/protocol_pulse/pipeline/avatars/bloomberg_television_512.png",
 696 | +    "avatar_sha256_prefix": "9c05313421b1579c",
 697 |      "has_chyron": false,
 698 |      "layout_table_key": "",
 699 |      "layout_status": "pending",
 700 | @@ -1038,8 +1038,8 @@
 701 |      "tier": 3,
 702 |      "priority": 3,
 703 |      "enabled": true,
 704 | -    "avatar_path": "",
 705 | -    "avatar_sha256_prefix": "",
 706 | +    "avatar_path": "/home/ultron/protocol_pulse/pipeline/avatars/cnbc_512.png",
 707 | +    "avatar_sha256_prefix": "8c316fd3ebac3e45",
 708 |      "has_chyron": false,
 709 |      "layout_table_key": "",
 710 |      "layout_status": "pending",
 711 | @@ -1054,8 +1054,8 @@
 712 |      "tier": 3,
 713 |      "priority": 3,
 714 |      "enabled": true,
 715 | -    "avatar_path": "",
 716 | -    "avatar_sha256_prefix": "",
 717 | +    "avatar_path": "/home/ultron/protocol_pulse/pipeline/avatars/cnbc_television_512.png",
 718 | +    "avatar_sha256_prefix": "c5a4e1bcd38ce01a",
 719 |      "has_chyron": false,
 720 |      "layout_table_key": "",
 721 |      "layout_status": "pending",
 722 | @@ -1070,8 +1070,8 @@
 723 |      "tier": 3,
 724 |      "priority": 3,
 725 |      "enabled": true,
 726 | -    "avatar_path": "",
 727 | -    "avatar_sha256_prefix": "",
 728 | +    "avatar_path": "/home/ultron/protocol_pulse/pipeline/avatars/financial_times_512.png",
 729 | +    "avatar_sha256_prefix": "8ad6e0ebc69f92ad",
 730 |      "has_chyron": false,
 731 |      "layout_table_key": "",
 732 |      "layout_status": "pending",
 733 | @@ -1086,8 +1086,8 @@
 734 |      "tier": 3,
 735 |      "priority": 3,
 736 |      "enabled": true,
 737 | -    "avatar_path": "",
 738 | -    "avatar_sha256_prefix": "",
 739 | +    "avatar_path": "/home/ultron/protocol_pulse/pipeline/avatars/fox_business_512.png",
 740 | +    "avatar_sha256_prefix": "37f4a1b05d3cf6d0",
 741 |      "has_chyron": false,
 742 |      "layout_table_key": "",
 743 |      "layout_status": "pending",
 744 | @@ -1102,8 +1102,8 @@
 745 |      "tier": 3,
 746 |      "priority": 3,
 747 |      "enabled": true,
 748 | -    "avatar_path": "",
 749 | -    "avatar_sha256_prefix": "",
 750 | +    "avatar_path": "/home/ultron/protocol_pulse/pipeline/avatars/kitco_news_512.png",
 751 | +    "avatar_sha256_prefix": "593e433193520f23",
 752 |      "has_chyron": false,
 753 |      "layout_table_key": "",
 754 |      "layout_status": "pending",
 755 | @@ -1118,8 +1118,8 @@
 756 |      "tier": 3,
 757 |      "priority": 3,
 758 |      "enabled": true,
 759 | -    "avatar_path": "",
 760 | -    "avatar_sha256_prefix": "",
 761 | +    "avatar_path": "/home/ultron/protocol_pulse/pipeline/avatars/kitco_news_512.png",
 762 | +    "avatar_sha256_prefix": "593e433193520f23",
 763 |      "has_chyron": false,
 764 |      "layout_table_key": "",
 765 |      "layout_status": "pending",
 766 | @@ -1134,8 +1134,8 @@
 767 |      "tier": 3,
 768 |      "priority": 3,
 769 |      "enabled": true,
 770 | -    "avatar_path": "",
 771 | -    "avatar_sha256_prefix": "",
 772 | +    "avatar_path": "/home/ultron/protocol_pulse/pipeline/avatars/the_block_512.png",
 773 | +    "avatar_sha256_prefix": "6d1dc24fbd156e10",
 774 |      "has_chyron": false,
 775 |      "layout_table_key": "",
 776 |      "layout_status": "pending",
 777 | @@ -1150,8 +1150,8 @@
 778 |      "tier": 3,
 779 |      "priority": 3,
 780 |      "enabled": true,
 781 | -    "avatar_path": "",
 782 | -    "avatar_sha256_prefix": "",
 783 | +    "avatar_path": "/home/ultron/protocol_pulse/pipeline/avatars/thestreet_512.png",
 784 | +    "avatar_sha256_prefix": "936433bc72dd1ee3",
 785 |      "has_chyron": false,
 786 |      "layout_table_key": "",
 787 |      "layout_status": "pending",
 788 | @@ -1166,8 +1166,8 @@
 789 |      "tier": 3,
 790 |      "priority": 3,
 791 |      "enabled": true,
 792 | -    "avatar_path": "",
 793 | -    "avatar_sha256_prefix": "",
 794 | +    "avatar_path": "/home/ultron/protocol_pulse/pipeline/avatars/wall_street_journal_512.png",
 795 | +    "avatar_sha256_prefix": "19711b0010b4d0ba",
 796 |      "has_chyron": false,
 797 |      "layout_table_key": "",
 798 |      "layout_status": "pending",
 799 | @@ -1182,8 +1182,8 @@
 800 |      "tier": 3,
 801 |      "priority": 3,
 802 |      "enabled": true,
 803 | -    "avatar_path": "",
 804 | -    "avatar_sha256_prefix": "",
 805 | +    "avatar_path": "/home/ultron/protocol_pulse/pipeline/avatars/yahoo_finance_512.png",
 806 | +    "avatar_sha256_prefix": "8665ccb20e94f2d4",
 807 |      "has_chyron": false,
 808 |      "layout_table_key": "",
 809 |      "layout_status": "pending",
 810 | diff --git a/pipeline/shoutout.py b/pipeline/shoutout.py
 811 | index 8202bdd1..b9663c40 100644
 812 | --- a/pipeline/shoutout.py
 813 | +++ b/pipeline/shoutout.py
 814 | @@ -131,145 +131,41 @@ def _validate_shoutout_frames(mp4_path, expected_size, fmt):
 815 |          )
 816 |  
 817 |  
 818 | -def _find_avatar(segment_dir, channel_name):
 819 | -    """Find avatar for a channel. Looks in channels.json registry, then local avatars/."""
 820 | -    # Try channels.json registry
 821 | -    channels_json = os.path.join(os.path.dirname(os.path.abspath(__file__)), "channels.json")
 822 | -    if os.path.exists(channels_json):
 823 | -        with open(channels_json) as f:
 824 | -            registry = json.load(f)
 825 | -        for entry in registry:
 826 | -            if entry.get("display_name") == channel_name:
 827 | -                avatar = entry.get("avatar_path", "")
 828 | -                if avatar and os.path.exists(avatar):
 829 | -                    return avatar
 830 | -
 831 | -    # Try local avatars dir
 832 | -    avatars_dir = os.path.join(segment_dir, "avatars")
 833 | -    if os.path.exists(avatars_dir):
 834 | -        slug = channel_name.lower().replace(" ", "_")
 835 | -        for ext in [".jpg", ".png", ".webp"]:
 836 | -            candidate = os.path.join(avatars_dir, f"{slug}{ext}")
 837 | -            if os.path.exists(candidate):
 838 | -                return candidate
 839 | -
 840 | -    # On-demand fetch: try to download from EDL video metadata
 841 | -    avatar = _fetch_avatar_on_demand(segment_dir, channel_name)
 842 | -    if avatar:
 843 | -        return avatar
 844 | -
 845 | -    raise FileNotFoundError(f"STOP: avatar missing for channel '{channel_name}'")
 846 | -
 847 | -
 848 | -def _fetch_avatar_on_demand(segment_dir, channel_name):
 849 | -    """Try to fetch channel avatar via yt-dlp from the EDL's video entries."""
 850 | -    import subprocess
 851 | -    import hashlib
 852 | +AVATAR_SQUARE_TOL = 0.01      # D4: the frozen renderer resizes to a square; a non-square image squashes
 853 | +AVATAR_MIN_PX = 128
 854 |  
 855 | -    avatars_dir = os.path.join(segment_dir, "avatars")
 856 | -    os.makedirs(avatars_dir, exist_ok=True)
 857 | -    slug = channel_name.lower().replace(" ", "_").replace("'", "")
 858 |  
 859 | -    # Find a video_id for this channel from EDL
 860 | -    edl_path = os.path.join(segment_dir, "edl.json")
 861 | -    if not os.path.exists(edl_path):
 862 | -        return None
 863 | +def validate_avatar(path):
 864 | +    """D4 (2026-11-11): a credit avatar must be the channel's square picture. A 16:9 video thumbnail
 865 | +    is refused (the frozen scene_shoutout resizes every avatar to a square and would squash it)."""
 866 | +    from PIL import Image
 867 | +    with Image.open(path) as im:
 868 | +        w, h = im.size
 869 | +    if abs(w - h) > AVATAR_SQUARE_TOL * max(w, h):
 870 | +        raise ValueError(f"avatar must be square, got {w}x{h} (a video thumbnail?): {path}")
 871 | +    if min(w, h) < AVATAR_MIN_PX:
 872 | +        raise ValueError(f"avatar too small ({w}x{h} < {AVATAR_MIN_PX} px square): {path}")
 873 | +    return w
 874 |  
 875 | -    with open(edl_path) as f:
 876 | -        edl = json.load(f)
 877 |  
 878 | -    video_id = None
 879 | -    hook = edl.get("hook", {})
 880 | -    if hook.get("channel") == channel_name:
 881 | -        video_id = hook.get("video_id")
 882 | -    for clip in edl.get("clips", []):
 883 | -        if clip.get("channel") == channel_name:
 884 | -            video_id = clip.get("video_id")
 885 | -            break
 886 | -
 887 | -    if not video_id:
 888 | -        return None
 889 | -
 890 | -    # Use yt-dlp to get channel thumbnail URL from video metadata
 891 | -    try:
 892 | -        result = subprocess.run(
 893 | -            ["yt-dlp", "--dump-json", "--skip-download", "--no-warnings",
 894 | -             f"https://www.youtube.com/watch?v={video_id}"],
 895 | -            capture_output=True, text=True, timeout=30,
 896 | -        )
 897 | -        if result.returncode != 0:
 898 | -            return None
 899 | -        meta = json.loads(result.stdout)
 900 | -
 901 | -        # Try direct thumbnail fields that are actual image URLs
 902 | -        avatar_url = None
 903 | -        for key in ("channel_url", "uploader_url"):
 904 | -            url = meta.get(key, "")
 905 | -            if url and "yt3.ggpht.com" in url:
 906 | -                avatar_url = url
 907 | -                break
 908 | -
 909 | -        # Search thumbnails list for avatar entries
 910 | -        if not avatar_url:
 911 | -            for t in meta.get("thumbnails", []):
 912 | -                url = t.get("url", "")
 913 | -                if "yt3.ggpht.com" in url:
 914 | -                    avatar_url = url
 915 | -                    break
 916 | -
 917 | -        # Construct from channel_id using known YouTube avatar URL pattern
 918 | -        if not avatar_url:
 919 | -            channel_id = meta.get("channel_id", "")
 920 | -            uploader_id = meta.get("uploader_id", "")
 921 | -            # Try video thumbnail as a safe fallback
 922 | -            avatar_url = meta.get("thumbnail")
 923 | -
 924 | -        if not avatar_url:
 925 | -            return None
 926 | -
 927 | -        # Download the image
 928 | -        import urllib.request
 929 | -        out_path = os.path.join(avatars_dir, f"{slug}.jpg")
 930 | -        urllib.request.urlretrieve(avatar_url, out_path)
 931 | -
 932 | -        # Verify it's actually an image
 933 | -        if os.path.exists(out_path) and os.path.getsize(out_path) > 500:
 934 | -            # Quick check: valid image header
 935 | -            with open(out_path, "rb") as fimg:
 936 | -                header = fimg.read(16)
 937 | -            if header[:3] in (b'\xff\xd8\xff', b'\x89PN') or b'WEBP' in header[:20]:
 938 | -                # Convert to PNG for PIL compatibility
 939 | -                try:
 940 | -                    from PIL import Image
 941 | -                    img = Image.open(out_path).convert("RGB")
 942 | -                    png_path = os.path.join(avatars_dir, f"{slug}.png")
 943 | -                    img.save(png_path)
 944 | -                    print(f"    Fetched avatar for {channel_name}: {png_path}")
 945 | -                    return png_path
 946 | -                except Exception:
 947 | -                    print(f"    Fetched avatar for {channel_name}: {out_path}")
 948 | -                    return out_path
 949 | -            else:
 950 | -                os.unlink(out_path)  # Not a real image
 951 | -    except Exception as e:
 952 | -        print(f"    WARN: avatar fetch failed for {channel_name}: {e}")
 953 | -
 954 | -    # Last resort: generate a placeholder
 955 | -    try:
 956 | -        from PIL import Image, ImageDraw, ImageFont
 957 | -        img = Image.new("RGB", (512, 512), (40, 40, 60))
 958 | -        draw = ImageDraw.Draw(img)
 959 | -        # Draw initials
 960 | -        initials = "".join(w[0].upper() for w in channel_name.split()[:3] if w)
 961 | -        draw.text((180, 180), initials, fill=(247, 147, 26))
 962 | -        out_path = os.path.join(avatars_dir, f"{slug}.png")
 963 | -        img.save(out_path)
 964 | -        print(f"    Generated placeholder avatar for {channel_name}")
 965 | -        return out_path
 966 | -    except Exception:
 967 | -        pass
 968 | -
 969 | -    return None
 970 | +def _find_avatar(segment_dir, channel_name):
 971 | +    """The channel's REAL avatar from pipeline/channels.json only (fetched + visually verified by
 972 | +    pipeline/avatar_onboard.py, M6), sha256-prefix checked and square. No on-demand fetch, no video
 973 | +    thumbnail, no generated stand-in (M12 fail closed)."""
 974 | +    import hashlib
 975 | +    channels_json = os.path.join(os.path.dirname(os.path.abspath(__file__)), "channels.json")
 976 | +    with open(channels_json) as f:
 977 | +        registry = json.load(f)
 978 | +    entry = next((e for e in registry if e.get("display_name") == channel_name), None)
 979 | +    avatar = (entry or {}).get("avatar_path", "")
 980 | +    if not avatar or not os.path.exists(avatar):
 981 | +        raise FileNotFoundError(f"STOP: no verified avatar for channel '{channel_name}' in channels.json "
 982 | +                                f"(pipeline/avatar_onboard.py fetch, verify the contact sheet, register)")
 983 | +    prefix = entry.get("avatar_sha256_prefix", "")
 984 | +    if prefix and not hashlib.sha256(open(avatar, "rb").read()).hexdigest().startswith(prefix):
 985 | +        raise RuntimeError(f"STOP: avatar for '{channel_name}' does not match its registered sha256 prefix")
 986 | +    validate_avatar(avatar)
 987 | +    return avatar
 988 |  
 989 |  
 990 |  def main():
 991 | 
```

---



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
