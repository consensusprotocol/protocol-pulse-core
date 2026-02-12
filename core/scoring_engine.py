from __future__ import annotations

from typing import Dict


def _norm(v: float) -> float:
    return round(max(0.0, min(1.0, v)), 3)


def score_text_artifact(text: str) -> Dict[str, float]:
    t = (text or "").strip().lower()
    words = [w for w in t.split() if w]
    wc = len(words)
    uniq = len(set(words))
    clarity = 0.4 + min(0.35, wc / 120.0)
    novelty = 0.2 + (uniq / max(1, wc)) * 0.6
    signal_hits = sum(1 for k in ("whale", "btc", "risk", "custody", "mempool", "flow", "liquidity", "oracle") if k in t)
    signal_density = 0.2 + min(0.75, signal_hits / 8.0)
    predicted_retention = 0.3 + min(0.6, (wc / 180.0)) + (0.1 if "?" in t else 0.0)
    return {
        "clarity": _norm(clarity),
        "novelty": _norm(novelty),
        "signal_density": _norm(signal_density),
        "predicted_retention": _norm(predicted_retention),
    }


def score_sentry_draft(text: str) -> Dict[str, float]:
    return score_text_artifact(text)


def score_medley_script(text: str) -> Dict[str, float]:
    return score_text_artifact(text)


def score_onboarding_path(text: str) -> Dict[str, float]:
    return score_text_artifact(text)

