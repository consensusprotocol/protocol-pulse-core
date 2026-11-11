# Heimdall audit

**Question:** Protocol Pulse news-video pipeline (no publishing). Changes: (1) a replay harness: run_fresh.main's tail (prepare, layout, render, gates, verify, verdict) moved into run_tail(run, cuts, start), and replay.py runs it on a COPY of an existing run dir (sources hard-linked, outputs removed); (2) a stand-alone + topic rule checked at validate for every run and at auto selection on final windows: a hook may not open on a pronoun, conjunction or reply fragment; a clip may open on a conjunction only if the clip scorer affirms it stands alone; every segment names the story subject (Bitcoin for a Bitcoin story) or completes the previous segment's claim with a back-reference and a figure; (3) the word-diff canonicaliser keeps a decimal as ONE token and maps 'one point three' / 'five and a half' to it (before, '5.5' became '5 5' and a repeat-collapser merged it to '5', so 5.5% and 5% compared equal); (4) shot_snap: a hard shot change after the last word (or before the first word) of a prepared clip is replaced by a hold of the speaker's shot, audio copied unchanged, frame count unchanged; (5) the wrapper sends Telegram only when every gate passed. Find real bugs: a check that can pass when it should fail, a replay that differs from production, a snap that moves audio or changes timing, a canonicalisation that hides a real word difference. Only state what you can verify from the diff. (this chunk: pipeline/replay.py)

**Panel:** deepseek, qwen27b  |  **Cost:** $0.0152
## Consensus findings (majority of panel agrees)
- **[high] pipeline/replay.py:72** If rf.run_tail raises any exception other than rf.Hold (e.g. FileNotFoundError on a missing clip, a render crash), the except block does not catch it. The finally block then executes and accesses run.status["verdict"], which was never set (only the except-rf.Hold branch sets it). This raises a KeyError that replaces the original exception in the traceback, masking the real failure. The script exits with code 1 (unhandled exception) instead of the documented 0 or 3, and VERDICT.txt is never written.
  - evidence: `    except rf.Hold:
        run.status["verdict"] = rf.VERDICT_HOLD
    finally:
        run.status["elapsed_s"] = round(time.time() - t0, 1)
        run.status["ended"] = rf.now_iso()
        run.sav`
  - fix: Add a catch-all except before the finally (or inside it) to set a default verdict on unexpected exceptions, e.g.:
    except rf.Hold:
        run.status["verdict"] = rf.VERDICT_HOLD
    except Exception as exc:
        run.status["verdict"] = rf.VERDICT_HOLD
        run.status["holds"] = run.status.get("holds", []) + [f"UNCAUGHT: {exc}"]
    finally:
        ...
        verdict = run.status.get("verdict", "ERROR")
        with open(...) as f:
            f.write(str(verdict) + "\n")
  - raised by qwen27b:F1; agree: deepseek, qwen27b

## Raised but not agreed
- qwen27b:F2 [medium] os.link is called on every entry returned by os.listdir of the sources/ directory without checking whether the entry is a regular file. If sources/ contains a subdirectory (e.g. a folder of reference images), os.link raises OSError (EPERM/EISDIR on Linux) and the replay aborts before any stage runs. The docstring states sources are 'hard links (read-only inputs)' implying flat files, but the code does not enforce or verify this. (agree: 1)

## Added in cross-examination (not voted on)
- none
