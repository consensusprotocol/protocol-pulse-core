# Consensus finding refuted against the code (00:50 ET Nov 24)
Seats: qwen27b and gemma answered (effort high, 65,536 tokens); gpt-oss answered out of contract (no JSON).

1. [high] "a hook stage 2b marks soft because hook_unrated() is truthy can still open unflagged when its cached rating passes the bar (ok true)": REFUTED. hook_bar.passes (pipeline/hook_bar.py line 101) returns False when there is no valid calibration or when the rating's backend is not the bar's rater, and hook_unrated is truthy only in exactly those cases or when the rating lacks a part (then passes is False too). So ok True implies hook_unrated(m) is None: a hook marked for its missing rating never passes unflagged. (A calibration that turns valid mid-build makes such a hook pass the bar; then it needs no flag.)
No code change.
