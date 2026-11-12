"""pipeline/oracle — the editorial supply backtest (order pp-backtest, 2026-11-12).

Did a legal line-up exist on a saved day, and did the selector find it? Four parts, each its own module:
  export   BITCOIN_STATEMENTS_<run>.jsonl, the frozen candidate sentences of one saved universe
  lineup   the written product rules, the reply schemas (fail closed) and the deterministic line-up checks
  llm      the two frontier calls (blind oracle, blind judge), keys read by name from the main .env, spend guard
  score    the selector's recorded decision path against the judged line-ups: availability, recall, precision,
           the first stage that lost a legal line-up
Always imported as `pipeline.oracle` (the repo root has an unrelated `oracle/` folder: E-FAIL-021 class).
The pipeline's own modules (transcript_store, canon, sentence_law, editorial_select, ...) are imported flat,
exactly as the pipeline imports them, so there is one copy of each in a process.
"""
import os
import sys

PIPELINE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PIPELINE_DIR not in sys.path:
    sys.path.insert(0, PIPELINE_DIR)
