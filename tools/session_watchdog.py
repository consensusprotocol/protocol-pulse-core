#!/usr/bin/env python3
"""tools/session_watchdog.py: the SESSION WATCHDOG (orchestrator order 05:55 ET Nov 16; PBX: guard against loops and
wasted tokens). Plain code: no model, no money. Run in its own tmux session, pipeline_pp_sessionwatch (no cron):
    python3 tools/session_watchdog.py            # a pass every PASS_S (300 s), for ever
    python3 tools/session_watchdog.py --once     # one pass ( --dry-run: no Telegram line)
It reads ITS OWN tree's logs/ and word-pass worker (store and rows): run it from the main tree, ~/protocol_pulse. From a
worktree it would read that worktree's empty store (measured: 34 rows 'waiting' where the live worker picks 0).

READ ONLY, with one exception: the only tmux commands it reads with are list-panes and capture-pane (tmux() refuses any
other before it runs). It never sends keys, kills or signals anything. RULING 159 (b) (23:42 ET Nov 23): it STARTS a dead
kept-alive service, at any hour, and logs it (restart_dead): only when the service's heartbeat has been dead or missing
for heartbeat.STALE_S AND no process of that service runs, at most once per RESTART_GAP_S each, and only with that
service's own fixed launch line (LAUNCH) in a NEW tmux window (or a new session when the session is gone).

Every pass, for each tmux session whose name starts with 'pipeline_', its active pane is read. A Claude Code pane (its
command is 'claude') is read in parts: the input box (between its two rules) and the footer under it; the spinner
line above the box while a turn runs ('<glyph> <Verb>… (13m 6s · ...'), whose timer is the turn's own; and the
CONTENT above those. Claude Code runs in the alternate screen, which keeps no scrollback (measured 05:40 ET Nov 16:
history_size 0 on every claude pane), so a pass sees the visible screen only; the current turn's lines are therefore
gathered pass by pass (joined on their overlap, at most HISTORY lines).
(1) STUCK: a turn in progress (the footer says 'esc to interrupt') whose last 15 content lines (timers and token
    counts masked) have not changed for 45 min, or whose latest action is the same shell command for 45 min.
(2) LOOP: in the current turn, the same shell command (or tool action line), or the same error line, in 5 or more
    separate blocks ('●' entries). The generic 'Error: Exit code N' header is not an error line by itself.
(3) LONG TURN: the spinner's timer over 150 min.
(5) CONTEXT: the input box's surroundings show 'until auto-compact' at 3 % or less, or 'Context low'. The
    conversation above is never read for these words (it can quote them).
A claude pane with no input box on screen (another view, or a changed UI) is NOT judged: its state is unknown, and the
status and the pass line name it (input_box false), so a UI change cannot blind the watchdog silently.
(4) IDLE WITH WORK:
    - pipeline_pp_selectid idle at its prompt while pp-ingest's moments ledger changed more than 40 min ago and no
      build of the builder (a tests/package/proof/ledger_* dir) followed;
    - pipeline_pp_wordpass or pipeline_pp_ingest_watch missing;
    - the word pass: its log silent for 30 min (no cycle) with rows waiting (what its own pick() would take now).
(6) SPEND: the builder's own outside-vendor dollars today: its ruling 118 day record, tests/package/proof/
    DAY118_LEDGER.json, field "outside" (the figure its day-cap guard enforces), for its "day" window [start, end]
    when that holds now (read only; the builder, 06:2x ET Nov 16), at 80 % and at 100 % of ruling 118's $1.00 day cap:
    one line per level per day. Its batch ledger's 'all_in' is no longer kept since ruling 118 and is never read.
Each finding: one line in logs/session_watchdog.log; every pass's view and findings in /tmp/session_watchdog_status.json;
ONE Telegram line per session per hour, headed 'WATCHDOG' (telegram.send_watchdog holds the hour and the night,
00:00-07:00 ET, when only (4) and (6) go). A missing session, a failing read or any error of its own is logged and
the watchdog carries on."""
import argparse
import datetime as dt
import glob
import hashlib
import json
import math
import os
import re
import subprocess
import sys
import time
from difflib import SequenceMatcher
from zoneinfo import ZoneInfo

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PIPELINE = os.path.join(REPO, "pipeline")
ET = ZoneInfo("America/New_York")
sys.path.insert(0, PIPELINE)
import heartbeat  # noqa: E402  (ruling 133 R16)

PREFIX = "pipeline_"
PASS_S = 300
HISTORY = 300                          # the order's window: the last 300 pane lines (of the turn)
STUCK_S, STUCK_LINES = 45 * 60, 15
LOOP_N = 5
LONG_S = 150 * 60
CONTEXT_PCT = 3
LEDGER_IDLE_S = 40 * 60
WORDPASS_IDLE_S = 30 * 60
DAY_CAP_USD, SPEND_LEVELS = 1.00, (1.0, 0.8)           # ruling 118; the highest level reached is the one said
NIGHT_KINDS = ("IDLE_WITH_WORK", "SPEND")              # the order: the only lines sent 00:00-07:00 ET
BUILDER_SESSION, WORDPASS_SESSION = "pipeline_pp_selectid", "pipeline_pp_wordpass"
REQUIRED = (WORDPASS_SESSION, "pipeline_pp_ingest_watch")
READ_ONLY = ("list-panes", "capture-pane")             # the ONLY tmux subcommands this file runs

INGEST_ROOT = os.environ.get("PP_INGEST_ROOT", "/home/ultron/worktrees/pp-ingest")
BUILDER_ROOT = os.environ.get("PP_SELECTID_ROOT", "/home/ultron/worktrees/pp-selectid")
PATHS = {
    "log": os.path.join(REPO, "logs", "session_watchdog.log"),
    "status": "/tmp/session_watchdog_status.json",
    "state": "/tmp/session_watchdog_state.json",
    "moment_ledger": os.path.join(INGEST_ROOT, "data", "editorial", "moments", "moment_ledger.jsonl"),
    "builds": os.path.join(BUILDER_ROOT, "tests", "package", "proof", "ledger_*"),
    "spend": os.path.join(BUILDER_ROOT, "tests", "package", "proof", "DAY118_LEDGER.json"),
    "wordpass_log": os.path.join(REPO, "logs", "word_pass_worker.log"),
    "heartbeats": heartbeat.DIR,
    "transcript_log": os.path.join(REPO, "logs", "transcript_ingest.log"),
}
# ruling 133 R16: the kept-alive services (heartbeat name, its tmux session) and the transcript run (cron */30), whose
# sign of life is its log: stale after two missed runs
HEARTBEATS = (("scorer", "pipeline_pp_scorer"), ("judge", "pipeline_pp_judge"),
              ("lock_precheck", "pipeline_pp_lockcheck"), ("word_pass", WORDPASS_SESSION))
TRANSCRIPT_KEY, TRANSCRIPT_STALE_S = "transcript_ingest", 65 * 60
# ruling 159 (b): what restart_dead may start, per service: the command-line markers that mean it runs, its launch line
_CANDS = os.path.join(BUILDER_ROOT, "docs", "audits", "parallel", "pp-selectid_SCORER_CANDIDATES.json")
LAUNCH = {
    "scorer": (("stand_alone_scorer.py serve",),
               f"cd {REPO} && while true; do CUDA_VISIBLE_DEVICES=0 python3 pipeline/stand_alone_scorer.py serve "
               f"--candidates {_CANDS} 2>&1 | tee -a logs/stand_alone_scorer.log; echo \"$(date +%H:%M:%S) scorer exited; "
               f"restart in 30 s\" | tee -a logs/stand_alone_scorer.log; sleep 30; done"),
    "judge": (("judge_serve.py", "local_judge.py serve"),
              f"cd {REPO} && CUDA_VISIBLE_DEVICES=0 python3 pipeline/judge_serve.py 2>&1 | tee -a data/local_judge/serve.log"),
    "lock_precheck": (("lock_precheck.py once", "lock_precheck.py serve"),
                      f"cd {REPO} && while true; do CUDA_VISIBLE_DEVICES=0 python3 pipeline/lock_precheck.py once 2>&1 | "
                      f"grep --line-buffered -v 'lock pre-check: decoder_sha' | tee -a data/lock_precheck/serve.log; sleep 5; "
                      f"done"),
    "word_pass": (("word_pass_worker.py",),
                  f"cd {REPO} && CUDA_VISIBLE_DEVICES=1 python3 pipeline/word_pass_worker.py 2>&1 | tee -a "
                  f"logs/word_pass_worker.log; exec sh"),
}
RESTART_GAP_S = 30 * 60

BORDER = re.compile(r"^\s*─{8,}")
PROMPT = re.compile(r"^\s*❯(?:\s|$)")
SPINNER = re.compile(r"^\s*[^\w\s]\s+\S.*…\s*\(")
TIMER = re.compile(r"…\s*\((?:(\d+)h\s*)?(?:(\d+)m\s*)?(?:(\d+)s)?\s*(?=[·)])")
NOTICE = re.compile(r"^\s*(?:✔\s|⎿\s+Tip:)")
BLOCK = re.compile(r"^\s*●\s")
RESULT = re.compile(r"^\s*⎿")
SHELL = re.compile(r"^\s*⎿\s+\$\s+(\S.*)$")
BASH = re.compile(r"^\s*●\s+Bash\((.*?)\)?\s*$")
ERROR = re.compile(r"\b[A-Z][A-Za-z]*(?:Error|Exception)\b|\bTraceback \(most recent call last\)|^\s*(?:⎿\s+)?[Ee]rror:"
                   r"|\bFAILED\b|\bfatal:")
EXIT_ONLY = re.compile(r"^\s*(?:⎿\s+)?Error:\s*Exit code \d+\s*$")
COMPACT = re.compile(r"until auto-compact:?\s*(\d+)\s*%")
CONTEXT_LOW = re.compile(r"\bContext low\b")
VOLATILE = ((re.compile(r"\b\d+h\s*\d+m\s*\d+s\b|\b\d+m\s*\d+s\b|\b\d+(?:\.\d+)?s\b"), "<t>"),
            (re.compile(r"[↓↑]\s*[\d.,]+k?\s*tokens"), "<n> tokens"))


# ── tmux, read only ──

def tmux(*args, timeout=15):
    """A READ-ONLY tmux call: anything but list-panes / capture-pane is refused before it runs. -> stdout; LookupError
    when tmux refuses (a session that is gone)."""
    if not args or args[0] not in READ_ONLY:
        raise PermissionError(f"the watchdog runs only {READ_ONLY}, never {args[:1]}")
    r = subprocess.run(["tmux", *args], capture_output=True, text=True, timeout=timeout)
    if r.returncode != 0:
        raise LookupError((r.stderr or "").strip()[:200] or f"tmux {args[0]} exit {r.returncode}")
    return r.stdout


def list_sessions():
    """{session: its active pane's command} for every pipeline_ session (one tmux call)."""
    out = {}
    for line in tmux("list-panes", "-a", "-F",
                     "#{session_name}\t#{window_active}\t#{pane_active}\t#{pane_current_command}").splitlines():
        p = line.split("\t")
        if len(p) == 4 and p[0].startswith(PREFIX) and p[1] == "1" and p[2] == "1":
            out[p[0]] = p[3]
    return out


def capture(session):
    """The active pane's lines: its screen plus up to HISTORY lines of scrollback (a claude pane has none)."""
    return tmux("capture-pane", "-p", "-t", f"={session}:", "-S", f"-{HISTORY}").splitlines()


# ── reading a Claude Code pane ──

def parse_pane(lines):
    """{"in_turn", "timer_s", "bottom", "content", "turn", "turn_key"} of a Claude Code pane. bottom: the input box,
    the footer under it and the two lines above it (never the conversation); content: everything above the spinner
    (or the box); turn: the content after the last user prompt on screen (all of it when the prompt is off screen)."""
    lines = [x.rstrip() for x in lines]
    while lines and not lines[-1].strip():
        lines.pop()
    box = None
    for i in range(len(lines) - 2, 0, -1):
        if PROMPT.match(lines[i]) and BORDER.match(lines[i - 1]) and BORDER.match(lines[i + 1]):
            box = i - 1
            break
    if box is None:                    # no input box (another view, or a new UI): its state is unknown, never read
        end, bottom, footer = len(lines), [], []          # from the last lines (they can be quoted conversation)
    else:
        end = box
        bottom, footer = lines[max(0, box - 2):], lines[box + 3:]
    in_turn = any("esc to interrupt" in x for x in footer)
    timer_s = None
    for j in (range(end - 1, max(-1, end - 13), -1) if in_turn else ()):     # an idle pane has no spinner
        if SPINNER.match(lines[j]):
            m = TIMER.search(lines[j])
            if m and any(m.groups()):
                h, mi, s = (int(g or 0) for g in m.groups())
                timer_s = h * 3600 + mi * 60 + s
            end = j
            break
    content = lines[:end]
    while content and (not content[-1].strip() or NOTICE.match(content[-1])):
        content.pop()
    start = max((k for k, x in enumerate(content) if PROMPT.match(x)), default=None)
    turn = content[start + 1:] if start is not None else list(content)
    key = hashlib.sha1(content[start].encode()).hexdigest()[:12] if start is not None else None
    return {"in_turn": in_turn, "timer_s": timer_s, "bottom": bottom, "content": content, "turn": turn,
            "turn_key": key, "input_box": box is not None}


def _norm(s):
    for rx, sub in VOLATILE:
        s = rx.sub(sub, s)
    return re.sub(r"\s+", " ", s.strip())


def signature(content):
    """The last STUCK_LINES non-empty content lines, timers and token counts masked, as one digest."""
    keep = [_norm(x) for x in content if x.strip()][-STUCK_LINES:]
    return hashlib.sha1("\n".join(keep).encode()).hexdigest()


def blocks(lines):
    """The lines cut into '●' entries (an action, a reply, a notification), each with what follows it."""
    out, cur = [], []
    for x in lines:
        if BLOCK.match(x) and cur:
            out.append(cur)
            cur = []
        cur.append(x)
    if cur:
        out.append(cur)
    return out


def commands(block):
    """The shell commands of one block: a '⎿ $ ...' line with up to 4 continuation lines (so two heredocs sharing a
    first line differ), or an older 'Bash(...)' line; and the block's header when the block is a tool action (it has a
    '⎿' result line) and shows no command."""
    out = []
    for i, x in enumerate(block):
        m = SHELL.match(x) or BASH.match(x)
        if m:
            cont = []
            for y in block[i + 1:i + 5]:
                if not y.strip() or RESULT.match(y) or BLOCK.match(y):
                    break
                cont.append(y.strip())
            out.append(_norm(" ".join([m.group(1)] + cont)))
    if not out and len(block) > 1 and any(RESULT.match(y) for y in block[1:]):
        out.append(_norm(block[0].lstrip().lstrip("●")))
    return out


def loops(turn):
    """[(kind, text, n)]: a command, or an error line, in LOOP_N or more SEPARATE blocks of the turn (a line repeated
    inside one block's output counts once)."""
    cmds, errs = {}, {}
    for b in blocks(turn):
        for c in set(commands(b)):
            cmds[c] = cmds.get(c, 0) + 1
        for e in {_norm(x.lstrip().lstrip("⎿")) for x in b if ERROR.search(x) and not EXIT_ONLY.match(x)}:
            errs[e] = errs.get(e, 0) + 1
    out = [("command", c, n) for c, n in cmds.items() if n >= LOOP_N] + \
          [("error line", e, n) for e, n in errs.items() if n >= LOOP_N]
    return sorted(out, key=lambda x: (-x[2], x[1]))


def last_command(turn):
    """(identity, command, latest) of the turn's latest shell command: its block's header with the command's FIRST
    line (output streaming under a running command never changes it), the command, and whether its block is the last
    on screen; (None, None, False) when the screen shows none."""
    bs = blocks(turn)
    for k in range(len(bs) - 1, -1, -1):
        for x in reversed(bs[k]):
            m = SHELL.match(x) or BASH.match(x)
            if m:
                cmd = _norm(m.group(1))
                return f"{_norm(bs[k][0])} | {cmd}", cmd, k == len(bs) - 1
    return None, None, False


def join(acc, new):
    """The turn so far: acc, then the lines of new past their overlap (new wins where the screen re-drew a line). No
    overlap of at least 3 lines: new alone, so nothing is ever counted twice."""
    if not new:
        return list(acc)
    if not acc:
        return list(new)
    tail = acc[-(len(new) + 40):]
    found = [b for b in SequenceMatcher(None, tail, new, autojunk=False).get_matching_blocks() if b.size >= 3]
    if not found:
        return list(new)
    b = found[-1]
    return acc[:len(acc) - len(tail) + b.a + b.size] + new[b.b + b.size:]


def context(bottom):
    """The context warning shown around the input box, or None."""
    text = "\n".join(bottom)
    m = COMPACT.search(text)
    if m and int(m.group(1)) <= CONTEXT_PCT:
        return f"{m.group(1)} % of context left until auto-compact"
    if CONTEXT_LOW.search(text):
        return "'Context low' shown"
    return None


# ── findings ──

def hm(t):
    return dt.datetime.fromtimestamp(t, ET).strftime("%H:%M ET")


def finding(session, kind, what, since, key=None, **extra):
    return {"session": session, "key": key or session, "kind": kind, "what": what, "since": round(since, 1),
            "since_et": hm(since), **extra}


def claude_findings(name, lines, st, now):
    """(findings, parsed pane) for one Claude Code pane; st: this session's tracking, updated in place."""
    p = parse_pane(lines)
    out = []
    sig = signature(p["content"])
    if st.get("sig") != sig:
        st["sig"], st["sig_since"] = sig, now
    ident, cmd, latest = last_command(p["turn"])
    if st.get("cmd") != ident:
        st["cmd"], st["cmd_since"] = ident, now
    if p["in_turn"]:                                                    # (1)
        if now - st["sig_since"] >= STUCK_S:
            out.append(finding(name, "STUCK", f"a turn in progress, its last {STUCK_LINES} lines unchanged for "
                                              f"{int((now - st['sig_since']) // 60)} min", st["sig_since"]))
        elif cmd and latest and now - st["cmd_since"] >= STUCK_S:
            out.append(finding(name, "STUCK", f"the same shell command for {int((now - st['cmd_since']) // 60)} min: "
                                              f"'{cmd[:120]}'", st["cmd_since"]))
    turn = track_turn(st, p)                                            # (2)
    if p["in_turn"]:
        since = st.setdefault("loop_since", {})
        for kind, text, n in loops(turn)[:3]:
            out.append(finding(name, "LOOP", f"the same {kind} {n} times in this turn: '{text[:120]}'",
                               since.setdefault(text, now)))
    if p["in_turn"] and p["timer_s"] is not None and p["timer_s"] > LONG_S:   # (3)
        h, m = divmod(p["timer_s"] // 60, 60)
        out.append(finding(name, "LONG_TURN", f"one turn at {h} h {m:02d} min by its own timer", now - p["timer_s"]))
    ctx = context(p["bottom"])                                          # (5)
    if ctx:
        out.append(finding(name, "CONTEXT", ctx, st.setdefault("context_since", now)))
    else:
        st.pop("context_since", None)
    return out, p


def track_turn(st, p):
    """The current turn's lines seen so far (at most HISTORY), kept across passes; reset by an idle pane or a new
    prompt."""
    if not p["in_turn"]:
        st.pop("turn", None)
        st.pop("loop_since", None)
        return p["turn"]
    t = st.get("turn")
    if not t or (p["turn_key"] is not None and t.get("key") != p["turn_key"]):
        t = {"key": p["turn_key"], "lines": list(p["turn"])}
        st.pop("loop_since", None)
    else:
        t["lines"] = join(t["lines"], p["turn"])
    t["lines"] = t["lines"][-HISTORY:]
    st["turn"] = t
    return t["lines"]


def mtime(path):
    try:
        return os.path.getmtime(path)
    except OSError:
        return None


def rows_waiting(now):
    """(the rows the word pass's own pick() would take now, None) or (None, why): read only, no GPU, no model."""
    try:
        if PIPELINE not in sys.path:
            sys.path.insert(0, PIPELINE)
        import word_pass_worker as W
        utc = dt.datetime.fromtimestamp(now, dt.timezone.utc)
        rows, _ = W.ledger_rows(utc, timeout=60)
        return len(W.pick(rows, W.passed_ids(), now=utc)[0]), None
    except Exception as e:
        return None, f"{type(e).__name__}: {str(e)[:120]}"


def idle_with_work(sessions, panes, state, now, paths, waiting=rows_waiting):
    """(4): the required sessions present; the builder not idle on a changed ledger; the word pass not silent on work."""
    out, miss = [], state.setdefault("missing", {})
    for name in REQUIRED:
        if name in sessions:
            miss.pop(name, None)
        else:
            out.append(finding(name, "IDLE_WITH_WORK", "the session is missing", miss.setdefault(name, now)))
    p = panes.get(BUILDER_SESSION)
    if p is not None and not p["in_turn"]:
        changed = mtime(paths["moment_ledger"])
        built = max((t for t in (mtime(d) for d in glob.glob(paths["builds"])) if t is not None), default=None)
        if changed is not None and now - changed > LEDGER_IDLE_S and (built is None or built < changed):
            out.append(finding(BUILDER_SESSION, "IDLE_WITH_WORK",
                               f"idle at its prompt; the moments ledger changed at {hm(changed)} and no build followed",
                               changed))
    last = mtime(paths["wordpass_log"])
    if last is None or now - last > WORDPASS_IDLE_S:
        n, why = waiting(now)
        if n is None or n > 0:
            rows = f"{n} rows waiting" if n is not None else f"rows waiting unknown ({why})"
            out.append(finding(WORDPASS_SESSION, "IDLE_WITH_WORK",
                               f"{rows}, no word-pass cycle since {hm(last) if last else 'its log began'}",
                               last if last is not None else now))
    return out


def _aware(s):
    """An ISO time WITH its offset -> epoch (a time without one is refused: never read as local)."""
    t = dt.datetime.fromisoformat(str(s))
    if t.tzinfo is None:
        raise ValueError(f"no UTC offset in {s!r}")
    return t.timestamp()


def day_spend(path, now):
    """((usd, window), None) from the builder's ruling 118 day record (read only): "outside", the day's all-in
    outside-vendor dollars (the figure its guard enforces), for its "day" [start, end] when that window holds now and
    spans at most a day; else (None, why). Between 21:10 and the builder's first STATE line of a new day the record
    still holds the old day: then today has no figure (said in the status), never the old day's."""
    try:
        with open(path) as f:
            d = json.load(f)
        t0, t1 = (_aware(x) for x in d["day"])
        usd = d["outside"]
        if isinstance(usd, bool) or not isinstance(usd, (int, float)) or not math.isfinite(usd):
            raise TypeError(f"outside is {usd!r}, not a number of dollars")
    except (OSError, ValueError, KeyError, TypeError) as e:
        return None, f"the builder's day record {os.path.basename(path)} is unreadable ({type(e).__name__}: {e})"
    window = f"{os.path.basename(path)} {d['day'][0]} to {d['day'][1]}"
    if not t0 <= now < t1:
        return None, f"the builder's day record holds {window}, not now (its first line of a new day rewrites it)"
    if t1 - t0 > 86400 + 60:
        return None, f"the builder's day record spans more than a day ({window})"
    return (float(usd), window), None


def spend_findings(state, now, paths):
    """(6): one finding, the highest level reached, never said twice in one day window."""
    rec, why = day_spend(paths["spend"], now)
    if rec is None:
        return [], {"readable": False, "why": why}
    usd, window = rec
    sp = state.setdefault("spend", {})
    if sp.get("window") != window:
        sp.clear()
        sp["window"] = window
    view = {"readable": True, "usd": round(usd, 4), "cap_usd": DAY_CAP_USD, "window": window}
    for level in SPEND_LEVELS:
        if usd >= level * DAY_CAP_USD - 1e-9:
            if sp.get("said", 0) >= level:
                return [], view
            since = sp.setdefault(f"since_{level}", now)
            return [finding(BUILDER_SESSION, "SPEND", f"the builder's outside-vendor dollars today ${usd:.2f}, at "
                            f"{level:.0%} of ruling 118's ${DAY_CAP_USD:.2f} day cap", since, key=f"spend:{level:.0%}",
                            level=level)], view
    return [], view


# ── a pass ──

def _alive(pid):
    try:
        os.kill(int(pid), 0)                       # signal 0: nothing is sent, the pid is only looked up
        return True
    except PermissionError:
        return True
    except (OSError, TypeError, ValueError):
        return False


def heartbeat_findings(state, now, paths):
    """R16 (ruling 133): a service whose heartbeat is older than heartbeat.STALE_S, or missing that long, or alive
    with no finished pass for heartbeat.PASS_STALE_S; the transcript run's log older than TRANSCRIPT_STALE_S.
    -> (findings, the view for the status)."""
    out, view, miss = [], {}, state.setdefault("heartbeat_missing", {})
    for name, session in (HEARTBEATS if paths.get("heartbeats") else ()):     # a paths map without them checks none
        try:
            with open(os.path.join(paths["heartbeats"], f"{name}.json")) as f:
                rec = json.load(f)
            at, pid = float(rec["at"]), rec.get("pid")
            pass_at = None if rec.get("pass_at") is None else float(rec["pass_at"])
            if not all(0 < t < 1e11 for t in (at, pass_at) if t is not None):     # NaN, inf, out of range (cycle 2)
                raise ValueError("a time out of range")
        except (OSError, ValueError, KeyError, TypeError, AttributeError):
            since = miss.setdefault(name, now)
            view[name] = {"missing_since": hm(since)}
            if now - since > heartbeat.STALE_S:
                out.append(finding(session, "HEARTBEAT", f"{name}: no heartbeat written", since, service=name,
                                   dead=True))
            continue
        miss.pop(name, None)
        alive = _alive(pid)
        view[name] = {"pid": pid, "alive": alive, "age_s": round(now - at),
                      "pass_age_s": round(now - pass_at) if pass_at is not None else None,
                      "passes": rec.get("passes")}
        if now - at > heartbeat.STALE_S:
            out.append(finding(session, "HEARTBEAT", f"{name}: no heartbeat since {hm(at)} (pid {pid} "
                                                     f"{'still there' if alive else 'gone'})", at, service=name,
                               dead=True))
        elif pass_at is not None and now - pass_at > heartbeat.PASS_STALE_S:
            out.append(finding(session, "HEARTBEAT", f"{name}: alive (pid {pid}) but no finished pass since "
                                                     f"{hm(pass_at)}", pass_at, service=name, dead=False))
    if not paths.get("transcript_log"):
        return out, view
    last = mtime(paths["transcript_log"])
    view[TRANSCRIPT_KEY] = {"log_age_s": round(now - last) if last is not None else None}
    if last is None or now - last > TRANSCRIPT_STALE_S:
        out.append(finding(TRANSCRIPT_KEY, "HEARTBEAT",
                           f"the transcript run (cron */30) last wrote its log {hm(last) if last else 'never'}",
                           last if last is not None else now))
    return out, view


def running(markers):
    """True when any process's command line holds one of the markers (python or the shell loop that starts it)."""
    me = os.getpid()
    for d in glob.glob("/proc/[0-9]*/cmdline"):
        try:
            if int(d.split("/")[2]) == me:
                continue
            with open(d, "rb") as f:
                cmd = f.read().replace(b"\0", b" ").decode(errors="replace")
        except (OSError, ValueError):
            continue
        if any(m in cmd for m in markers):
            return True
    return False


def start_service(name, session, present):
    """The ONE write the watchdog makes (ruling 159 (b)): the service's fixed launch line in a new window of its
    session, or a new detached session when the session is gone. Never a kill, a signal or keys."""
    cmd = LAUNCH[name][1]
    argv = (["tmux", "new-window", "-t", f"={session}:", "-n", f"{name}-restarted", cmd] if present
            else ["tmux", "new-session", "-d", "-s", session, cmd])
    r = subprocess.run(argv, capture_output=True, text=True, timeout=15)
    if r.returncode != 0:
        raise RuntimeError((r.stderr or "").strip()[:200] or f"tmux exit {r.returncode}")


def restart_dead(findings, state, now, paths, sessions, is_running=None, start=None):
    """RULING 159 (b): every HEARTBEAT finding of a kept-alive service (dead or missing past heartbeat.STALE_S) whose
    process does not run is started again, at any hour, at most once per RESTART_GAP_S; a service still running
    (frozen, or slow) is never touched. -> [what was done], also logged; the finding's line says it."""
    is_running, start = is_running or running, start or start_service      # looked up per call (tests patch them)
    done, last = [], state.setdefault("restarts", {})
    for f in findings:
        name = f.get("service")
        if f.get("kind") != "HEARTBEAT" or name not in LAUNCH or not f.get("dead"):
            continue
        if now - float(last.get(name, 0)) < RESTART_GAP_S:
            done.append({"service": name, "held": f"restarted at {hm(float(last[name]))}, within {RESTART_GAP_S // 60} min"})
            continue
        if is_running(LAUNCH[name][0]):
            done.append({"service": name, "held": "a process of it still runs: never touched"})
            continue
        session = dict(HEARTBEATS)[name]
        try:
            start(name, session, session in (sessions or ()))
        except Exception as e:
            done.append({"service": name, "error": f"{type(e).__name__}: {str(e)[:160]}"})
            log_line(paths["log"], f"RESTART FAILED {name} in {session}: {type(e).__name__}: {str(e)[:160]}")
            continue
        last[name] = now
        f["what"] += f"; restarted by the watchdog at {hm(now)}"
        done.append({"service": name, "restarted": hm(now), "session": session})
        log_line(paths["log"], f"RESTARTED {name} in {session} (ruling 159 (b)): {f['what']}")
    return done


def default_send(key, kinds, line, now):
    if PIPELINE not in sys.path:
        sys.path.insert(0, PIPELINE)
    import telegram
    return telegram.send_watchdog(key, kinds, line, now=now)


def dispatch(findings, state, now, send):
    """ONE line per key per pass: its findings joined ('<session>: <KIND>: <what> (since <time>); ...'); at night only
    (4) and (6). The hour and the night are held again by telegram.send_watchdog. -> what happened to each line."""
    by, out = {}, []
    night = dt.datetime.fromtimestamp(now, ET).hour < 7
    for f in findings:
        if not night or f["kind"] in NIGHT_KINDS:
            by.setdefault(f["key"], []).append(f)
    for key, fs in sorted(by.items()):
        line = f"{fs[0]['session']}: " + "; ".join(f"{f['kind'].replace('_', ' ')}: {f['what']} (since {f['since_et']})"
                                                   for f in fs)
        try:
            out.append({"key": key, "sent": send(key, [f["kind"] for f in fs], line, now), "line": line})
            counted = True
        except Exception as e:
            how = {"WatchdogRefused": "held", "SendRejected": "refused"}.get(type(e).__name__, "unknown")
            out.append({"key": key, how: f"{type(e).__name__}: {str(e)[:160]}", "line": line})
            counted = how == "unknown"             # an unknown outcome counts as said (never repeated)
        for f in fs:
            if f["kind"] == "SPEND" and counted:
                sp = state.setdefault("spend", {})
                sp["said"] = max(sp.get("said", 0), f["level"])
    return out


def log_line(path, text):
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "a") as f:
            f.write(f"{dt.datetime.now(ET).strftime('%Y-%m-%d %H:%M:%S ET')} {text}\n")
    except OSError as e:
        print(f"session_watchdog: cannot write {path}: {e}", file=sys.stderr)


def save_json(path, obj):
    tmp = f"{path}.tmp{os.getpid()}"
    with open(tmp, "w") as f:
        json.dump(obj, f, indent=1, default=str)
    os.replace(tmp, path)


def run_pass(state, now=None, paths=None, send=default_send, waiting=rows_waiting, dry_run=False):
    """One pass: read, find, log, tell, write the status. Every session and check is guarded: an error is recorded
    and the pass goes on. -> the status written."""
    paths, now = paths or PATHS, time.time() if now is None else now
    state["pass"] = state.get("pass", 0) + 1
    status = {"at": dt.datetime.fromtimestamp(now, ET).isoformat(timespec="seconds"), "pass": state["pass"],
              "sessions": {}, "findings": [], "telegram": [], "errors": []}
    findings, panes, ss = [], {}, state.setdefault("sessions", {})
    try:
        sessions = list_sessions()
    except Exception as e:
        sessions = None
        status["errors"].append(f"tmux list-panes: {type(e).__name__}: {e}")
    for name, cmd in sorted((sessions or {}).items()):
        view = {"command": cmd}
        if cmd == "claude":
            try:
                f, p = claude_findings(name, capture(name), ss.setdefault(name, {}), now)
                panes[name] = p
                findings += f
                view.update(input_box=p["input_box"], in_turn=p["in_turn"], turn_timer_s=p["timer_s"],
                            turn_lines_seen=len((ss[name].get("turn") or {}).get("lines") or []))
            except Exception as e:
                status["errors"].append(f"{name}: {type(e).__name__}: {e}")
        status["sessions"][name] = view
    if sessions is not None:
        for name in [n for n in ss if n not in sessions]:
            ss.pop(name)                           # a session that is gone takes its tracking with it
        try:
            findings += idle_with_work(set(sessions), panes, state, now, paths, waiting)
        except Exception as e:
            status["errors"].append(f"idle with work: {type(e).__name__}: {e}")
    try:
        f, status["spend"] = spend_findings(state, now, paths)
        findings += f
    except Exception as e:
        status["errors"].append(f"spend: {type(e).__name__}: {e}")
    try:
        f, status["heartbeats"] = heartbeat_findings(state, now, paths)
        findings += f
        if not dry_run:
            status["restarts"] = restart_dead(f, state, now, paths, sessions)    # ruling 159 (b): any hour
    except Exception as e:
        status["errors"].append(f"heartbeats: {type(e).__name__}: {e}")
    status["findings"] = findings
    for f in findings:
        log_line(paths["log"], f"{f['session']} {f['kind']}: {f['what']} (since {f['since_et']})")
    write_status(paths, status)                    # the findings are on disk before any line is sent
    if findings and not dry_run:
        try:
            status["telegram"] = dispatch(findings, state, now, send)
        except Exception as e:
            status["errors"].append(f"telegram: {type(e).__name__}: {e}")
    for e in status["errors"]:
        log_line(paths["log"], f"ERROR {e}")
    blind = [n for n, v in status["sessions"].items() if v.get("input_box") is False]
    log_line(paths["log"], f"pass {state['pass']}: {len(status['sessions'])} sessions, {len(findings)} findings, "
                           f"{sum('sent' in t for t in status['telegram'])} lines sent"
                           + (f", no input box on {', '.join(blind)} (not judged)" if blind else "")
                           + (" (dry run)" if dry_run else ""))
    write_status(paths, status)
    return status


def write_status(paths, status):
    try:
        save_json(paths["status"], status)
    except Exception as e:                         # never the end of a pass
        log_line(paths["log"], f"ERROR status: {type(e).__name__}: {e}")


def main(argv=None):
    a = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    a.add_argument("--once", action="store_true")
    a.add_argument("--dry-run", action="store_true", help="no Telegram line")
    a.add_argument("--interval", type=float, default=PASS_S)
    a = a.parse_args(argv)
    try:
        with open(PATHS["state"]) as f:
            state = json.load(f)
        state = state if isinstance(state, dict) else {}
    except (OSError, ValueError):
        state = {}
    while True:
        t0 = time.time()
        try:
            run_pass(state, now=t0, dry_run=a.dry_run)
        except Exception as e:                     # its own error: logged, and the next pass comes
            log_line(PATHS["log"], f"ERROR pass: {type(e).__name__}: {e}")
        try:
            save_json(PATHS["state"], state)
        except Exception as e:
            log_line(PATHS["log"], f"ERROR state: {type(e).__name__}: {e}")
        if a.once:
            return 0
        time.sleep(max(1.0, a.interval - (time.time() - t0)))


if __name__ == "__main__":
    sys.exit(main())
