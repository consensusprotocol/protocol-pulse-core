# PROTOCOL PULSE — CODE AUDIT PACKAGE
# Feature: pulse-sentence-law
# Branch: combo-letterbox-quoteonly-v2
# Generated: 2026-11-11 03:09 UTC
# Purpose: Pre-merge quality gate. 3 independent AI models will review this.
# You are one of: Gemini 2.5 Pro / GPT-4o / Grok-3
# Other top AI models will also review this same code. Put your best work forward.

---

## WHAT THIS FEATURE DOES
The automated Protocol Pulse "Pulse Check" medley (pipeline/run_fresh.py) cuts hooks and clips from
partner YouTube videos, renders 16:9 and 9:16, and runs QA gates. PBX watched the 2026-11-10 cut and
found editorial errors every gate had passed: the opening word sounded clipped (D1), clips started or
ended mid-sentence (D2/D3), credit avatars were warped (D4), the vertical was letterboxed (D5) and
channel changes were abrupt (D6). This work makes the gates catch what a human caught, proves it on
yesterday's files (tests/fixtures/pulse_20261110, pipeline/test_pulse_20261110_mustfail.py), fixes the
causes, then requires three clean fresh videos in a row with no code edits between them.

---

## GOVERNING LAWS (this code MUST comply with every law below — flag any violation)
## THE LAWS
- SENTENCE LAW: a clip's first word is the first word of a sentence and its last word the last word of
  a sentence. Boundary = transcript punctuation (or a cached, logged local-model adjudication when the
  transcript has no punctuation) AND an acoustic pause >= 80 ms between the two words
  (pipeline/sentence_law.py states every constant).
- SELECTION LOCK: the words a clip must contain are fixed at selection time (selection_lock in edl.json,
  sha256-sealed). No later stage may recompute expected first/last words from a moved cut.
- SNAP LIMIT: a cut may move only inside the silence between the chosen sentence and its neighbour; it
  may never add or drop a word. No legal boundary in that gap = the window is rejected.
- ONSET/TAIL: every rendered segment keeps >= 80 ms of genuine sub-speech audio before its first onset
  and after its last offset; codec zero/padding is not room tone; a source that starts speaking at its
  file head without lead-in needs a declared room-tone lead-in pad. Edge words keep >= 85 % of their
  duration in the render.
- CREDITS: round avatars of the channels actually used; the avatar is the channel's real square avatar,
  never a video thumbnail, never a generated placeholder; G12/G15 unchanged.
- LAW 20 / M2: gate thresholds are constants; a failed gate is a hard stop; never change what a check
  accepts to make a render pass; never reclassify a failing gate as a false positive.
- M12 FAIL CLOSED: missing data, model failure or an exception rejects; it never produces a pass.
- LAW 22: the frozen v2f reference (references/v2f_2026-11-06) must keep re-rendering byte-identically.
- Smallest diff; no new renderer, compositor or selector (M1); GPU0 only; no publishing.



---

## TECHNOLOGY STACK
- Python 3.12, Flask 3.x, SQLite via SQLAlchemy ORM
- Ubuntu 24.04 on Ultron server (2x RTX 4090, 93GB RAM)
- All UI animations: CSS/SVG only — NO Three.js, no WebGL, no Canvas
- External services: ElevenLabs TTS, HeyGen avatars, Wav2Lip GPU lip-sync
- ~1000 concurrent users at peak — every route must handle load
- Every DB query on a sort/filter column MUST have an index

---

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

## YOUR REVIEW TASK: PULSE CHECK SENTENCE LAW / ONSET / CREDITS (Python pipeline, no UI, no DB)

The only file is the exact staged diff of ONE commit. Review that diff, nothing else.
Only state what you can verify from the diff shown. If uncertain, say so. Do not guess. Cite diff lines.

### Q1: CORRECTNESS
Does each changed function do what its docstring and the laws above say? Off-by-one in time/index
handling, wrong units (seconds vs ms), wrong comparisons, silent exceptions, state that leaks between
clips. Can any path produce a PASS (or a cut, a lock, a window) when data is missing or a model failed?

### Q2: LAW COMPLIANCE
For each law above: COMPLIANT / VIOLATION / PARTIAL with the diff line. In particular: can a cut move
outside the locked sentence's silence, can expected words be recomputed after selection, can a gate
threshold have been loosened, can the v2f reference path behave differently?

### Q3: TESTS
Do the tests prove the claim (must-fail fixtures FAIL for the right reason; controls PASS for the right
reason)? Any assertion that could pass vacuously?

### Q4: VERDICT
List every defect as: SEVERITY | diff line | issue | fix. End with READY or NOT READY.

