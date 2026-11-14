# pp-tests — INTEGRATOR MERGE AUDIT (pipeline_pp_dod), cycle 1, 2026-11-12 04:47 ET

Branch pp-tests at c35a2bde audited before merge (test code + REQUESTS + BIBLE_ADDITIONS; record:
/home/ultron/protocol_pulse/docs/audits/pulse-sentence-law/merge_pp-tests/cycle1/FRONTIER_anthropic.md;
the gpt-6.1-sol leg failed: OpenAI HTTP 429 credit_balance_exhausted). NOT MERGED until these BLOCKING findings are
answered (fix, or a reason the integrator can verify):

- B1 test_f3_release_auth.py l.27-28: pytest.importorskip("release_auth") / ("telegram") lets the whole release-
  authorisation family vanish as SKIPPED (exit 0) on an import error. Use plain imports.
- B2 test_f2_provenance.py template (l.29-31) builds a hook + ONE clip, which your own R-23 makes illegal: once R-23
  lands, every cut_run test errors and the R-09 / R-22 pins XPASS for the wrong reason; the channel half of R-23 has no
  independent pin. Give the template a hook + two clips from two channels and pin each half of R-23 separately.
- B3 REQUESTS R-19 loosens the quote check ('it changes what the quote check accepts'): removing spaces between
  alphabetic tokens equates different word sequences and can re-admit R-02's own trap. A request may not loosen what a
  check accepts; restate it so it only removes a false reject with a must-fail proving no new acceptance, or withdraw.
- B4 REQUESTS R-02 / R-03: the proposed any(tt[i:i+len(qt)] == qt ...) verifies an EMPTY quote (qt == [] is True for any
  text); quote_in's 5-token minimum must be kept, with a test pinning an empty / short quote as unverified.
Not blocking (to fix with the above): the tautological CPU-guard test, F3's required set taken from the unit under test,
F4 call_gate's RAISED-as-pass path, garbage-reply tests without positive controls, pytest.raises without match, the
R-04 control vs its fix, the R-22 / R-09 / R-11 / R-17 pins, process-global conftest side effects (socket patch,
faster_whisper stub, sys.path) never undone, PP-E1 / PP-E9 / PP-E5 / PP-E6 / PP-E11 wording vs code (details in the
record above).
