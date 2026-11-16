# C1 CONSENSUS — pp-selectid audit 20261116_1300 (RULING 122 (3): the no-hook line)

Seats (Heimdall only): qwen3.8-27b, gemma-4-31b-it, mimo-v2.6-flash-rl. SEATS ANSWERED: 3 of 3. P1_OR_WORSE: gemma 0,
mimo 0, qwen 1. Cycle 1 $0.0074 of Heimdall, not capped.

qwen's P1 ("a hook that passes the bar but is refused by a DIFFERENT gate would be misattributed to the visual check")
CANNOT HAPPEN on this path; the unchanged code, in order (dev44's package.py):
- :3050 openers = the cleared moments can_open() takes before any rating (eligibility, G17a onset, the render's opener rule);
- ratings are set; :3059 rated_open = the cleared moments can_open() takes NOW: for a moment of on_bar (in openers, rated,
  hook_own passes) every condition of _can_open holds as it did for openers, plus the bar: so every on_bar moment is in
  rated_open;
- see(rated_open) judges each one's frames; :3066 sets visual_hook_block (and blocked[id]) when its own frames refuse it;
- :3079 passing = hook_order(the cleared moments can_open() takes) with that flag set; can_open's FIRST line (:1556) refuses
  a flagged moment; hook_order (:1600) only sorts, it never drops one.
So when passing is empty, every on_bar moment carries visual_hook_block: the visual check is the one refusal left, and the
line is true. The 'not seen' fallback is unreachable in this branch (kept: a line never raises). qwen's P2 (a test of a
non-visual refusal of a bar-passing hook) has no reachable case to test. No change.
