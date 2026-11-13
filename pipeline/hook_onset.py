#!/usr/bin/env python3
"""pipeline/hook_onset.py: G17a at the PIN stage. The render holds a medley whose HOOK keeps less than
HEAD_LEAD_MIN_S (80 ms, D1: the hook starts playback) of GENUINE quiet before its first onset in the prepared clip
(sentence_law.gate_g17_prepared).

Batch pin #1, held 01:39 ET Nov 13: the word record put a 400 ms gap before the hook's first word. The source audio
holds breath, then a run of digital zeros (a hard edit), then speech. Zeros are not room tone, so the genuine lead
was 30 ms. The word record's timestamps cannot see an edit; only the audio can.

So before a moment may OPEN a medley:
- its cut is planned on the SOURCE audio (the L-v 2 window that transcript_truth.audio_window already fetched for the
  second recogniser) with the render's own sentence_law.edge_plan;
- the planned prepared clip's head (the source's 10 ms envelope from the planned cut on, a lead-in pad added only
  where edge_plan allows one: a file head) is measured with the render's own sentence_law.head_tail.

The envelope is sliced from the source, so it can differ from the render's decode of the prepared file by up to one
10 ms frame. A hook therefore passes here only with HEAD_LEAD_MIN_S + MARGIN_MS (one frame): a pass here cannot be a
G17a hold at render by that frame (audit 0155 C1: glm P0-1 / P1-1, qwen). The render's 20 ms fade-in is not
applied, which can only make this check stricter.

measure(...) -> {"pass", "measured", "lead_ms", "cut_in", "pad_s", "why"}. Not measured (no audio, no plan) is never
a pass (law L-m).
"""
import sentence_law as SL
import transcript_truth as TT

MARGIN_MS = int(round(SL.HOP_S * 1000))     # one 10 ms envelope frame: the slice vs the render's own decode


class _Slice(SL.SourceAudio):
    """[t0, t1] of a decoded source's envelope on its own clock (from 0): the planned prepared clip, before fades."""

    def __init__(self, sa, t0, t1):                     # no decode: SourceAudio's methods read t / db / dur only
        m = (sa.t >= t0 - 1e-9) & (sa.t < t1 - 1e-9)
        self.path, self.t, self.db, self.dur = sa.path, sa.t[m] - t0, sa.db[m], max(0.0, t1 - t0)


def measure(src, w0, w1, video_id, start, end, work_dir, audio=None):
    """The hook moment's planned prepared clip: does it keep >= HEAD_LEAD_MIN_S of genuine quiet before its first
    onset? src: the moment's eligibility Source; w0 / w1: its first / last word indices in src.tokens; start / end:
    the clip's times (video seconds). audio: (SourceAudio, window start s) to reuse (tests); else the L-v 2 window."""
    need = SL.HEAD_LEAD_MIN_S * 1000 + MARGIN_MS
    try:
        if audio is None:
            wav, a = TT.audio_window(video_id, float(start), float(end), work_dir)
            sa = SL.SourceAudio(wav)
        else:
            sa, a = audio
    except Exception as e:
        return {"pass": False, "measured": False, "why": f"no source audio: {type(e).__name__}: {str(e)[:120]}"}
    toks = src.tokens
    idx = [i for i, t in enumerate(toks) if isinstance(t.get("start"), (int, float)) and
           isinstance(t.get("end"), (int, float)) and float(t["start"]) >= a and float(t["end"]) <= a + sa.dur]
    if w0 not in idx or w1 not in idx:
        return {"pass": False, "measured": False, "why": "the clip's words are not inside its audio window"}
    words = [{"word": toks[i]["word"], "start": float(toks[i]["start"]) - a, "end": float(toks[i]["end"]) - a}
             for i in idx]
    i0, i1 = idx.index(w0), idx.index(w1)
    try:
        plan = SL.edge_plan(sa, words, i0, i1)
    except Exception as e:                               # LawError: no audio to read levels from, and the like
        return {"pass": False, "measured": False, "why": f"no cut plan: {type(e).__name__}: {str(e)[:120]}"}
    cin = plan.get("in") or {}
    if not cin.get("cuttable"):
        return {"pass": False, "measured": True, "lead_ms": 0, "why": f"no cut before the hook: "
                f"{cin.get('reason') or 'not cuttable'}"}
    cut_in = float(cin["cut"])
    out = plan.get("out") or {}
    cut_out = float(out["cut"]) if out.get("cuttable") else words[i1]["end"]
    try:
        ht = SL.head_tail(_Slice(sa, cut_in, cut_out))
    except Exception as e:
        return {"pass": False, "measured": False, "why": f"no head measured: {type(e).__name__}: {str(e)[:120]}"}
    pad = float(cin.get("lead_in_pad_s") or 0.0)         # a room-tone pad: edge_plan allows one only at a file head
    lead = int(round(ht["lead_ms"] + pad * 1000))
    ok = lead >= need
    return {"pass": ok, "measured": True, "lead_ms": lead, "cut_in": round(a + cut_in, 3), "pad_s": pad,
            "why": "ok" if ok else f"{lead} ms of genuine quiet before the hook's first onset < {need:.0f} ms "
                                    f"(G17a's {SL.HEAD_LEAD_MIN_S * 1000:.0f} ms + one {MARGIN_MS} ms frame)"}
