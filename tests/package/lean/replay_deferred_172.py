#!/usr/bin/env python3
"""THE DEMONSTRATION (the owner's approval, 15:55 ET Nov 25, item 5: "Use build 172's recorded responses to demonstrate
the revised ordering and calculate the remaining budget at each stage. Never fabricate missing verdicts."). Offline:
every socket is refused before anything runs; no model is asked; nothing is written.

Reads: build 172's recorded replies and build 171's (tests/package/fixtures/replies, by their recorded_at windows), build
172's record (its hook pool and its completion reserve, $0.8651, as it logged it), and, read only, the day's one ledger
for the lock service's three Scribe calls. Each call's reservation is the router's own (providers: upper_usd x the
spec's reserve_list_fraction, rulings 121 / 123 / 130; Scribe: its audio + 5 s); each bill is the cap's basis (the
vendor's figure; Gemini and Scribe report none: the recorded list-price estimate and the metered audio; Heimdall is
uncapped and counts nothing).

Part 1 walks build 172's calls in the REVISED order (A: no second-vendor step A before the line-up) and prints, after
each stage, at $1.50 and at $3.00: spent, held (the most one call of the stage reserved while in flight), the
completion reserve, and the room the search has left. A branch whose answer was never recorded STOPS: UNMEASURED.
Part 2 is the line-up arithmetic from build 171's recorded join table, clips-alone and Gemini calls. Part 3 is the
billing exposure. Usage: python3 -B tests/package/lean/replay_deferred_172.py"""
import glob
import json
import os
import re
import socket
import sys


def _offline(*a, **k):
    raise OSError("offline: this demonstration makes no network call")


for _o, _n in ((socket.socket, "connect"), (socket.socket, "connect_ex"), (socket, "create_connection"),
               (socket, "getaddrinfo"), (socket, "gethostbyname")):
    setattr(_o, _n, _offline)

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, os.path.join(REPO, "pipeline"))
import package as PK  # noqa: E402
import providers as P  # noqa: E402

B172 = os.path.join(REPO, "tests", "package", "proof", "ledger_20261125_180553")
REPLIES = os.path.join(REPO, "tests", "package", "fixtures", "replies")
DAY_LEDGER = "/home/ultron/pp_spend/SPEND_D20261124.json"   # read only
W172 = ("2026-11-25T18:05:41", "2026-11-25T18:28:38")
W171 = ("2026-11-24T17:56:00", "2026-11-24T18:31:00")
NEVER_EMPTY_172 = "2026-11-25T18:17:00"   # build 172's never-empty pass: its first step-A call is 18:17:24Z
CLIPS_ALONE_171 = "2026-11-24T18:07:55"   # build 171's one clips-alone verdict; after it, that line-up's completion
CEILINGS = (1.50, 3.00)
RESERVE = 0.8651                          # build 172's completion reserve (package.log line 17)
VISION_RESERVED = 0.1801                  # one vision call's reservation, the same line: 0f140b0d's 2 were refused at it
OUTSIDE_RESERVED = 3 * 0.0101 + 0.0500    # the reserve's parts outside the router: the lock's Scribe per span, the
#   render's sign-off (reserved; no recorded build billed them for a sealing line-up)
R = P.Router(env_path=os.devnull)         # the router's own prices and reserve rules; no ledger, no key, no file


def load(window):
    out = []
    for p in glob.glob(os.path.join(REPLIES, "*", "*.json")):
        with open(p) as f:
            r = json.load(f)
        if window[0] <= str(r.get("recorded_at") or "") <= window[1]:
            out.append(r)
    return sorted(out, key=lambda r: r["recorded_at"])


def text_of(r):
    pr = r.get("prompt")
    return pr if isinstance(pr, str) else str((pr or {}).get("text", "")) if isinstance(pr, dict) else ""


def kind(r):
    role, be, t = r["role"], r["backend"], text_of(r)
    if role == "context_verdict":
        return "step A, second vendor" if be.startswith("google:") else "step A, first vendor"
    if role == "coherence_verdict":
        return ("hooks" if t.startswith("You judge OPENING") else "join table" if t.startswith("You judge JOINS")
                else "clips-alone" if t.startswith("You watch a short video") else "coherence")
    if role.startswith("shadow86:"):
        return "shadow"
    return {"transcribe": "second ear", "out_edge": "out edge", "visual_check": "vision", "angle_write": "angle",
            "exclusion_verdict": "exclusion"}.get(role, role)


def reservation(r, prompt=None):
    b = R.backends[r["backend"]]
    if r["backend"].startswith("heimdall:"):
        return 0.0                                          # uncapped (ruling 118 (b))
    if r["role"] == "transcribe":
        return round(b.usd({"seconds": float(r["usage"]["seconds"]) + 5.0}), 6)
    up = b.upper_usd(prompt if prompt is not None else r["prompt"], int(r["max_tokens"]), r.get("system"))
    f = b.spec.get("reserve_list_fraction")
    return round(up * float(f), 6) if f else up


def bill(r):
    if r["backend"].startswith("heimdall:"):
        return 0.0
    u = r.get("usage") or {}
    return float(u["usd_reported"]) if u.get("usd_reported") is not None else float(r.get("usd") or 0.0)


def room_line(spent, held, extra=""):
    return "  ".join(f"${c:.2f}: spent {spent[c]:.4f}{extra if c == 3.00 else ''} held {held:.4f} reserve {RESERVE:.4f}"
                     f" room {c - spent[c] - RESERVE:+.4f}" for c in CEILINGS)


def part1():
    print("PART 1: build 172 in the revised order (A), stage by stage; recorded calls only")
    calls = load(W172)
    with open(DAY_LEDGER) as f:
        led = json.load(f)
    lock = round(sum(v.get("usd_estimate", 0.0) for k, v in led["by_role"].items() if k.startswith("scribe ")), 6)
    spent = {c: lock for c in CEILINGS}
    print(f"  0 start: the lock service's Scribe, 3 calls on 2 stale Nov 14 requests (the day's ledger): {lock:.4f}")
    print(f"      {room_line(spent, 0.0)}")
    groups, order = {}, []
    for r in calls:
        k = kind(r)
        k = {"out edge": "second ear + out edge", "second ear": "second ear + out edge", "shadow": "hooks + shadow",
             "hooks": "hooks + shadow"}.get(k, k)
        key = ("clean pass: " if r["recorded_at"] < NEVER_EMPTY_172 else "never-empty pass: ") + k
        if key not in groups:
            groups[key] = []
            order.append(key)
        groups[key].append(r)
    unmeasured_3 = 0.0
    for i, key in enumerate(order, 1):
        rs = groups[key]
        if key.endswith("step A, second vendor"):
            print(f"  {i} {key}: NOT ASKED before the line-up (A): its recorded call (${sum(map(bill, rs)):.4f}, "
                  f"{text_of(rs[0]).count('<excerpt label=')} moments) and its 2 refused calls (15 moments) drop out")
            continue
        held = max(reservation(r) for r in rs)
        for r in rs:
            for c in CEILINGS:
                if spent[c] + reservation(r) + RESERVE > c + 1e-9:
                    print(f"      at ${c:.2f} REFUSED: {kind(r)} (would leave no completion reserve)")
                spent[c] += bill(r)
        free = sum(1 for r in rs if r["backend"].startswith("heimdall:"))
        print(f"  {i} {key}: {len(rs)} calls ({free} on Heimdall, uncapped), billed {sum(map(bill, rs)):.4f}")
        print(f"      {room_line(spent, held)}")
        if key == "never-empty pass: vision":
            for c in CEILINGS:
                fits = spent[c] + VISION_RESERVED + RESERVE <= c + 1e-9
                print(f"      0f140b0d's 2 vision calls (${VISION_RESERVED:.4f} reserved each) at ${c:.2f}: " +
                      ("ALLOWED: their answers were never recorded: UNMEASURED: this opener's branch STOPS (it may "
                       "not open until its vision is measured)" if fits else
                       "REFUSED by the completion reserve, as recorded (no spend; the opener may not open)"))
                if fits:
                    unmeasured_3 = 2 * VISION_RESERVED
    with open(os.path.join(B172, "package.json")) as f:
        rec = json.load(f)
    passing = rec["never_empty"]["soft_record"]["hook_pool"]["passing"]
    print(f"  {len(order) + 1} the line-up: the hook pool holds {', '.join(passing)} (the bar's 2; their second "
          f"verdicts PENDING, A); the angle writer's answer for them was never recorded: UNMEASURED: STOP")
    extra = f" + UNMEASURED (<= {unmeasured_3:.4f} reserved)" if unmeasured_3 else ""
    print(f"      {room_line(spent, 0.0, extra)}")
    print("  never recorded, so not shown: any angle, join table, clips-alone, deferred second verdict, coherence or "
          "lock verdict on these openers; the spotlight's step A (refused for money in 172)")
    return spent, unmeasured_3


def gemini_3(c172):
    """The deferred call's reservation on a REAL 3-segment prompt: build 172's recorded 8-moment second-screen prompt
    cut to its first three excerpts (same header, same instructions)."""
    g = next(r for r in c172 if kind(r) == "step A, second vendor")
    t = text_of(g)
    starts = [m.start() for m in re.finditer(r'<excerpt label="', t)]
    end = t.rfind("</excerpt>") + len("</excerpt>")
    cut = t[:starts[3]] + t[end:]
    return reservation(g, cut), len(cut)


def part2(spent, unmeasured_3):
    print("\nPART 2: what a provisional line-up costs, from build 171's recorded calls (and 172's Gemini)")
    c171, c172 = load(W171), load(W172)
    joins = [r for r in c171 if kind(r) == "join table" and r["recorded_at"] < CLIPS_ALONE_171]
    alone = [r for r in c171 if kind(r) == "clips-alone"]
    after = [r for r in c171 if r["recorded_at"] > CLIPS_ALONE_171 + "Z" and bill(r) > 0]
    for r in joins + alone:
        print(f"  {kind(r):12} {r['recorded_at'][11:19]} reserved {reservation(r):.4f} billed {bill(r):.4f} "
              f"({r['seconds']:.0f} s)")
    gem = []
    for p in glob.glob(os.path.join(REPLIES, "*", "*.json")):
        with open(p) as f:
            r = json.load(f)
        if r.get("backend") == "google:gemini-2.5-pro" and r.get("role") == "context_verdict":
            gem.append((text_of(r).count('<excerpt label="'), bill(r), reservation(r), r["seconds"], r["recorded_at"]))
    gem.sort()
    print("  Gemini step A, every recorded call (moments: billed / reserved / seconds): " +
          "; ".join(f"{n}: {b:.4f} / {res:.4f} / {s:.0f}" for n, b, res, s, _ in gem))
    n_, b_ = [g[0] for g in gem], [g[1] for g in gem]
    mx, my = sum(n_) / len(n_), sum(b_) / len(b_)
    slope = sum((x - mx) * (y - my) for x, y in zip(n_, b_)) / sum((x - mx) ** 2 for x in n_)
    g3_bill = round(my + slope * (3 - mx), 4)
    g3_res, g3_chars = gemini_3(c172)
    print(f"  the deferred call on 3 segments: reserved {g3_res:.4f} (build 172's prompt cut to 3 excerpts, {g3_chars} "
          f"characters; Gemini's 8,000-token output floor is ~$0.10 of it, so 1 segment reserves nearly as much); billed "
          f"ESTIMATED {g3_bill:.4f} (the line through the {len(gem)} recorded bills at 3 moments; not recorded)")
    j = max(joins, key=reservation)
    seq = [("join table", reservation(j), bill(j)), ("clips-alone", reservation(alone[0]), bill(alone[0])),
           ("deferred second verdict", g3_res, g3_bill)]
    e_res, e_bill = sum(s[1] for s in seq), sum(s[2] for s in seq)
    print(f"  one evaluation (the larger recorded join table): reserved {e_res:.4f} in all, at most "
          f"{max(s[1] for s in seq):.4f} at once; billed {e_bill:.4f} (recorded join and clips-alone + the estimated "
          f"deferred call)")

    def evals(room, worst, bound):
        n = 0
        while bound is None or n < bound:
            for name, res, b in seq:
                if res > room + 1e-9:
                    return n, f"stops at the next {name} (${res:.4f} reserved > ${room:.4f} room)"
                room -= res if worst else b
            n += 1
        return n, f"stops at the bound F ({bound} line-ups)"
    pre = {c: spent[c] for c in CEILINGS}
    for c in CEILINGS:
        less = unmeasured_3 if c == 3.00 else 0.0      # at $3.00 0f140b0d's vision is asked first: its bills UNMEASURED,
        room = c - pre[c] - RESERVE - less             # so its reservations come off the room (their upper bound)
        for worst in (False, True):
            for bound in (None, PK.DEFERRED_LINEUPS_MAX):
                n, why = evals(room, worst, bound)
                print(f"  ${c:.2f}, room {room:.4f}{' (less 0f140b0d vision, reserved)' if less else ''}, "
                      f"{'every call billed at its reservation' if worst else 'recorded bills'}, "
                      f"{'bound F' if bound else 'no bound'}: {n} line-up(s) fully evaluated; {why}")
    secs = {name: [r["seconds"] for r in rs] for name, rs in (("join table", joins), ("clips-alone", alone))}
    g_s = [g[3] for g in gem if g[0] <= 4]
    print(f"  time, one call in flight: join table {'/'.join(f'{x:.0f}' for x in secs['join table'])} s, clips-alone "
          f"{secs['clips-alone'][0]:.0f} s, Gemini on 1-4 moments {min(g_s):.0f}-{max(g_s):.0f} s (recorded): the deferred "
          f"call adds {min(g_s):.0f}-{max(g_s):.0f} s to each line-up")
    comp = sum(bill(r) for r in after)
    print(f"  completion, build 171's one passed line-up (did not seal): {len(after)} paid calls billed {comp:.4f} "
          f"({', '.join(sorted({kind(r) for r in after}))}); outside the router reserved {OUTSIDE_RESERVED:.4f}")
    for c in CEILINGS:
        room = c - pre[c] - RESERVE - (unmeasured_3 if c == 3.00 else 0.0)
        reach = evals(room, False, PK.DEFERRED_LINEUPS_MAX)[0]
        for k in (1, 2, 3):
            if k > reach:
                print(f"  ${c:.2f}: a build whose line-up {k} would seal: NOT REACHED in one build (BUDGET_REFUSED "
                      f"first); the build makes no video")
                continue
            cost = pre[c] + k * e_bill + comp + OUTSIDE_RESERVED
            print(f"  ${c:.2f}: a build that seals on line-up {k}: expected spend {cost:.4f} (pre-line-up {pre[c]:.4f}"
                  + (f" + 0f140b0d's vision UNMEASURED, <= {unmeasured_3:.4f} reserved" if c == 3.00 else "") +
                  f" + {k} x {e_bill:.4f} + completion {comp:.4f} billed in 171 + {OUTSIDE_RESERVED:.4f} reserved)")
        fail = pre[c] + reach * e_bill
        print(f"  ${c:.2f}: a build none of whose {reach} evaluated line-up(s) seals: about {fail:.4f}"
              + (f" + 0f140b0d's vision (UNMEASURED)" if c == 3.00 else "") + " for no video (+ the spotlight, "
              "UNMEASURED, where it fits)")
    return seq


def part3():
    print("\nPART 3: billing exposure (the calibrated model: rulings 121 / 123 / 130)")
    rows = []
    for r in load(W171) + load(W172):
        b = R.backends[r["backend"]]
        f = b.spec.get("reserve_list_fraction")
        if not f or r["role"] == "transcribe":
            continue
        up = b.upper_usd(r["prompt"], int(r["max_tokens"]), r.get("system"))
        rows.append((r["backend"], kind(r), up, up * float(f), bill(r)))
    heim = sum(float((r.get("usage") or {}).get("usd_reported") or 0.0) for r in load(W172)
               if r["backend"].startswith("heimdall:"))
    print(f"  Heimdall, uncapped (ruling 118 (b)): build 172's recorded replies report ${heim:.4f}; never counted "
          f"against the ceiling")
    for be in sorted({x[0] for x in rows}):
        xs = [x for x in rows if x[0] == be]
        big = max(xs, key=lambda x: x[2])
        f = float(R.backends[be].spec["reserve_list_fraction"])
        over = big[2] / P.RESERVE_MARGIN - big[3]
        print(f"  {be}: {len(xs)} recorded calls; largest list bound {big[2]:.4f} ({big[1]}), reserved {big[3]:.4f} "
              f"({f:.0%}); highest recorded bill / reservation {max(x[4] / x[3] for x in xs):.2f}; one call billed at "
              f"its whole list price within its output cap would pass its reservation by {over:.4f}")
    return rows


if __name__ == "__main__":
    s, u = part1()
    part2(s, u)
    part3()
