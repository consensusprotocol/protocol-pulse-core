# RUNBOOK — Pulse Check (DEC-8 c, written 2026-11-11 ET)

A Pulse Check is a ~45-60 s video on the story engine's own top Bitcoin story: a hook and two clips from
approved partner channels (pipeline/channels.json), the credits card (round avatars of the channels used),
the locked outro; rendered 16:9 (1920x1080) and 9:16 (1080x1920). Nothing is ever published: every run
ends in the Telegram APPROVAL chat for PBX.

## One command

```
scripts/pulse_check_run.sh                     # AUTO: today's top story (run_fresh.py, no pin, no hand step)
scripts/pulse_check_run.sh --pinned PIN.json   # PINNED: a human/orchestrator decision (pipeline/pinned.py)
scripts/pulse_check_run.sh --no-telegram       # everything except the drop
```
- Runs in its own detached tmux session `pipeline_pulse_check_<UTC stamp>` (the cron'd
  scripts/tmux_cleanup.sh keeps `pipeline*` sessions; nothing else is touched). `--foreground` runs inline.
- One run at a time: `flock /tmp/pulse_check_run.lock` (a second call exits 75 immediately).
- GPU0 only (`CUDA_VISIBLE_DEVICES=0`). GPU1 is never used (Ollama :11435 is quarantined there).
- Log: `logs/pulse_check/run_<stamp>.log` (git HEAD, run dir, exit code, Telegram message ids).
- Exit: 0 = every gate passed; 3 = HOLD (see the run's REPORT.md); 75 = locked; 64 = usage.
- NOT installed in cron. Installing it is PBX's decision.

## What a run does (run_fresh.py stages; any failure = HOLD, never a silent fallback)

env -> editorial (top story, same-event coverage across approved channels; candidates resting on the same
counted statement merged into one event and re-judged; events already delivered skipped, see the story
ledger below) -> select (sentence windows)
-> review -> validate -> cut -> sentence_law (G16) -> voice -> prepare (+ D1 lead-in pad) -> layout
(9:16 per-shot plan) -> render (16:9 + 9:16, transitions) -> gates -> verify (pack) ; then the wrapper
delivers to Telegram. The run dir is `runs/fresh_<UTC stamp>/` (or `pinned_...`).

## The laws the gates enforce (details: docs/audits/DEFINITION_OF_DONE_PULSE_CHECK.md)

- SENTENCE LAW: a clip is 1-3 whole sentences; each edge is punctuation AND a >= 80 ms pause in the
  source audio; cuts sit inside those pauses (>= 80 ms lead-in / tail, 60 ms guard), never moved to
  add or drop a word. Unpunctuated transcript stretches have no boundaries; punctuation comes from a
  second, prompted whisper decode of the same audio onto aligned verbatim words (pipeline/punctuation.py).
  No language model decides a boundary.
- SELECTION LOCK: the expected words are sealed at selection (sha256) and never recomputed.
- Budgets: hook 8-12 s, clips 12-20 s, measured on the words actually locked.
- A rejected window is replaced by the next-ranked legal window; never forced.
- Vertical: speaker-centred crop; 2-3 people = stacked bands; the safe frame (whole 16:9 picture) only for
  a shared screen or an unidentifiable speaker, and then named in the caption (layout=screen).
- Transitions only between different channels, only over measured non-speech; default a 6-frame
  cross-dissolve + matching audio crossfade (DEC-4). Nothing at the open.
- Credits: the channels' real square avatars from the registry (pipeline/avatar_onboard.py); no
  thumbnails, no placeholders.

## Reading the drop

- `HOLD FOR APPROVAL - all gates passed, no waivers`: every gate row of BOTH formats is PASS and the
  verification pack is complete. Review and approve or reject; nothing else happens automatically.
- `REVIEW ONLY - N failing`: the caption lists every failing row; the video is for diagnosis only.
- The verification pack (VERIFY/ in the run dir): frames at every join (last / mid dissolve / first), the
  credits card frames, G18's word-for-word rows, and ONE contact sheet per format (qa/contact_sheet_*.jpg,
  sent with the drop): a still every 2 s, +-3 frames at every boundary, full-resolution credits and 9:16
  first frames. V1_visual_checklist = six fixed questions answered from the sheet by two Heimdall vision
  models, plus (9:16) the letterbox question asked of ONE frame per shot; any no / missing answer = FAIL.
- The 9:16 caption names every safe-frame shot (`9:16 SAFE FRAME ... layout=screen`).

## Transition options (Phase 3, for PBX's choice; never release candidates)

```
cd pipeline && CUDA_VISIBLE_DEVICES=0 python3 transition_options.py ../runs/<run> A B C
python3 -c "import telegram; telegram.deliver_run('../runs/<run>_optionA', option='A', sheets=False)"
```
Each option is the SAME cut re-rendered in a copy of the run dir (`<run>_option<X>`), gated and packed
like production: A clean cut + audio dip, B dissolve + soft pulse thump, C ECG line sweep on black.
The caption starts `OPTION X (transition choice, not a release candidate)` and carries the gate verdict.

## Story ledger (DEC-9: three in a row = three genuinely different stories)

`data/pulse_check/story_ledger.jsonl`, one line per AUTO run whose two finals went out as HOLD FOR
APPROVAL (written by the wrapper after the drop; pinned runs, REVIEW ONLY drops and options never enter
it). Each line holds the story's counted evidence statements (video, chunk, quote); the next auto run marks
any candidate resting on one of them `already delivered (story ledger: <run>)` and takes the engine's next
story. A story held for a defect is not recorded, so it can be produced again once the defect is fixed.
To re-produce a delivered story on purpose, remove its line (and say so in the run notes).

## Common HOLDs and what they mean

| HOLD | Meaning | Action |
|---|---|---|
| `editorial: no candidate is producible` | no story has two approved channels covering it with legal windows | none; the run ledger (TOPIC_SELECTION.json) records why; does not count against three-in-a-row |
| `select: ... rejected: OUT no pause >= 80 ms` | the editor's sentence runs into the next with no pause; next-ranked tried | none (fail closed by design) |
| `... no point inside the locked pauses passes cut_accept` | a music bed under the speech (E-FAIL-009) | none; the window is rejected |
| `shoutout: STOP: no verified avatar` | a channel without an onboarded avatar | `python3 pipeline/avatar_onboard.py fetch <slug>`, look at the contact sheet, then `register` |
| `vertical reframe failed` | ffmpeg failed on a 9:16 shot | read render_9x16.log; never letterbox by hand |
| G12/G15 on a correct card | content-sensitive ring detection (OD-1) | evidence to the orchestrator; never re-specify the gate locally |

## Never

- Publish anything, or send to any chat but the approval chat (pipeline/telegram.py is the only path).
- Change what a gate accepts to make a render pass (DEC-1 calibration to the approved v2f reference is the
  one recorded exception). Record the evidence instead.
- Touch references/v2f_2026-11-06 (Law 22): after any render change, re-render it and compare sha256.
- Use GPU1, Gunicorn, or kill avatar_server.py; print .env or keys.

## After a code change

1. py_compile; the change's must-fail test fails before the fix and passes after.
2. `bash regression_test.sh` (0 FAIL) and `bash pipeline/regression.sh` (PASS).
3. Audit the staged diff (utils/cross_llm_audit.py + heimdall-audit); implement the consensus.
4. Law 22 re-render if any render path changed; commit + push.
5. Any code change restarts the three-in-a-row count (DEC-8 b).
