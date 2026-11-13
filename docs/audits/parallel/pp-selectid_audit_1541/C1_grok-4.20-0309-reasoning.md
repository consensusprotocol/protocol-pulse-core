# grok-4.20-0309-reasoning (grok-4.20-0309-reasoning) 51 s finish=stop usage in 27153 / out 488 usd~0.148 (upper-bound price)

**P0: None verifiable from diff.**  
**P1: None verifiable from diff.**  
**P2: pipeline/visual_pin.py:659 (and :676)**  
Broad `except Exception as e: # noqa: BLE001` on sheet/verdict paths (including router.call, check, JSON parse, PIL, ffmpeg). Matches style of surrounding providers.py changes but would mask unexpected failures (e.g. OOM on large sheet, router SpendLimit) as "not measured". Concrete: a transient Heimdall 429 on first try + bad JSON on retry seed+1 yields measured=False with generic why; no tighter exception list is present.  

**P2: pipeline/providers.py:275**  
`prompt_text` does `hashlib.sha256(i.encode())` on the *base64 string* (not decoded JPEG bytes). Recording/logs contain only the hex digest (test at :996 confirms image bytes never written). Verifiably unique per image for cache key but not a literal byte hash of the visual data sent to the model.  

**P2: pipeline/package.py:153 (and :175, :210)**  
`see(order)` / visual row requires *every* clip measured for PASS (and drops unmeasured before write or blocks hook). Matches ruling's "fail closed" and L-m/L-j but the visual gate is now in MEDLEY_GATES/REQUIRED_GATES for all new medleys; old pins untouched only because visual is in SEALED_LATER and check_pin_only still uses pre-ruling REQUIRED list (verified in updated test_medley.py:731 and test_no_voice).  

No other concrete violations of the supplied ruling text, K1–K4, or governing laws (sentence/selection/snap/edge/credits/L-a..L-l, release-on-bytes, one-canon, model-whole-reply, fail-closed, v2f byte-identical re-render) can be verified from the diff alone. Router vision/text separation, upper_usd image token charging, XAIVision/Heimdall request bodies, cache-per-span+VERSION, sealed() subset (no path/cost), hook_block on third_person, parallel see() before angle/write, and all 14 test cases match the described behavior exactly. Uncertain on router thread-safety under ThreadPoolExecutor(4) for concurrent visual calls (not shown in diff).  

SHIP: yes