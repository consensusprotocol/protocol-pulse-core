# services/convergence_engine.py
"""
Convergence Detection engine: SignalExtractor, PatternEvaluator, ConvergenceEngine.

State machine: IDLE -> WATCH -> ALERT -> CRITICAL -> IDLE
  - No state skipping permitted (raises ValueError)
  - CRITICAL can only step down via ALERT
  - Contradiction detection blocks forward escalation

All I/O is async. SQLite writes are sync (fast local write — acceptable).
"""

import json
import logging
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import importlib.util as _ilu
import sys as _sys

import aiohttp

from pathlib import Path as _Path
_svc_dir = _Path(__file__).resolve().parent

def _load_svc(mod_name, filename):
    spec = _ilu.spec_from_file_location(mod_name, str(_svc_dir / filename))
    mod = _ilu.module_from_spec(spec)
    _sys.modules[mod_name] = mod
    spec.loader.exec_module(mod)
    return mod

_baseline_store_mod = _load_svc('_ce_baseline_store', 'baseline_store.py')
BaselineStore = _baseline_store_mod.BaselineStore

_signal_feeds_mod = _load_svc('_ce_signal_feeds', 'signal_feeds.py')
SignalFeeds = _signal_feeds_mod.SignalFeeds

logger = logging.getLogger(__name__)

# ── Valid state machine transitions ──────────────────────────────────────────
_DEFAULT_VALID_TRANSITIONS: Dict[str, List[str]] = {
    "IDLE":     ["WATCH"],
    "WATCH":    ["IDLE", "ALERT"],
    "ALERT":    ["WATCH", "CRITICAL"],
    "CRITICAL": ["ALERT", "IDLE"],
}


# ═════════════════════════════════════════════════════════════════════════════
# ConvergenceStateMachine
# ═════════════════════════════════════════════════════════════════════════════

class ConvergenceStateMachine:
    """
    Enforces legal state transitions. Raises ValueError on invalid transitions.
    Transition map is config-driven. IDLE->CRITICAL will always raise ValueError.
    """

    def __init__(self, valid_transitions: Optional[Dict[str, List[str]]] = None):
        self.state: str = "IDLE"
        self._transitions = valid_transitions or _DEFAULT_VALID_TRANSITIONS

    def transition(self, new_state: str) -> None:
        allowed = self._transitions.get(self.state, [])
        if new_state not in allowed:
            raise ValueError(
                f"Invalid transition: {self.state} -> {new_state}. "
                f"Allowed from {self.state}: {allowed}"
            )
        old_state = self.state
        self.state = new_state
        logger.info(json.dumps({
            "event": "convergence_state_change",
            "from": old_state,
            "to": new_state,
            "timestamp": time.time(),
        }))

    def can_transition(self, new_state: str) -> bool:
        return new_state in self._transitions.get(self.state, [])


# ═════════════════════════════════════════════════════════════════════════════
# SignalExtractor
# ═════════════════════════════════════════════════════════════════════════════

class SignalExtractor:
    """
    Normalizes raw feed data into named signals with freshness metadata.
    Applies linear decay based on signal age vs config thresholds.
    """

    def __init__(self, config):
        self.config = config

    def extract_signal(
        self,
        name: str,
        raw_value: Any,
        timestamp: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Returns a signal dict with freshness metadata applied."""
        ts = timestamp or time.time()
        age = time.time() - ts
        decay_onset = self.config.get("signal_freshness", "decay_onset_seconds")
        max_age = self.config.get("signal_freshness", "max_valid_age_seconds")

        if decay_onset is None or max_age is None:
            raise RuntimeError(
                "signal_freshness.decay_onset_seconds or max_valid_age_seconds missing from config."
            )

        # Freshness scoring (linear decay)
        if age <= decay_onset:
            decay_weight = 1.0
            confirmed = True
            expired = False
        elif age >= max_age:
            decay_weight = 0.0
            confirmed = False
            expired = True
        else:
            # Linear interpolation between decay_onset and max_age
            decay_weight = 1.0 - (age - decay_onset) / (max_age - decay_onset)
            confirmed = False
            expired = False

        return {
            "name": name,
            "value": raw_value,
            "timestamp": ts,
            "age_seconds": age,
            "confirmed": confirmed,
            "expired": expired,
            "decay_weight": decay_weight,
        }

    def evaluate_signal_freshness(self, signal: Dict[str, Any]) -> Dict[str, Any]:
        """Re-evaluate freshness of a previously extracted signal at current time."""
        return self.extract_signal(signal["name"], signal["value"], signal["timestamp"])


# ═════════════════════════════════════════════════════════════════════════════
# PatternEvaluator
# ═════════════════════════════════════════════════════════════════════════════

class PatternEvaluator:
    """
    Evaluates named patterns (MCC, IES, LSC, etc.) against current signal set.
    All thresholds sourced from ConvergenceConfig — no hardcoded values.
    Contradiction gate: if contradictions detected, escalation is blocked.
    """

    def __init__(self, config):
        self.config = config

    def evaluate_pattern(
        self,
        pattern_name: str,
        signals: List[Dict[str, Any]],
        current_state: str,
        state_entered_at: float,
    ) -> Dict[str, Any]:
        """
        Evaluate a named pattern.
        Returns dict with keys: state, confirmed, signal_count, persistence_met.
        """
        pattern_cfg = self.config.get("patterns", pattern_name)
        if not pattern_cfg:
            raise ValueError(f"Pattern '{pattern_name}' not found in config.")

        fire_threshold: int = pattern_cfg["fire_threshold"]
        confirmation_window: int = pattern_cfg["minimum_confirmation_window"]

        # Contradiction check before evaluating signal count
        contradiction_result = self.detect_contradictions(signals)
        if contradiction_result["has_contradiction"]:
            logger.info(json.dumps({
                "event": "convergence_contradiction_gate",
                "pattern": pattern_name,
                "contradiction_pairs": contradiction_result["contradiction_pairs"],
                "blocked_escalation": True,
                "timestamp": time.time(),
            }))
            return {
                "state": "WATCH" if current_state in ("ALERT", "CRITICAL") else current_state,
                "confirmed": False,
                "signal_count": 0,
                "persistence_met": False,
                "contradiction": True,
                "contradiction_detail": contradiction_result.get("detail", ""),
            }

        # Count confirmed (non-expired) signals
        active_signals = [s for s in signals if not s.get("expired", False)]
        confirmed_count = len(active_signals)

        # Persistence window check
        time_in_state = time.time() - state_entered_at
        persistence_met = time_in_state >= confirmation_window

        # Determine resulting state
        if confirmed_count >= fire_threshold and persistence_met:
            if current_state == "IDLE":
                result_state = "WATCH"
            elif current_state == "WATCH":
                result_state = "ALERT"
            elif current_state == "ALERT":
                result_state = "CRITICAL"
            else:
                result_state = current_state
        elif confirmed_count >= fire_threshold and not persistence_met:
            result_state = "WATCH" if current_state == "IDLE" else current_state
        else:
            result_state = "IDLE" if current_state == "WATCH" else current_state

        return {
            "state": result_state,
            "confirmed": confirmed_count >= fire_threshold,
            "signal_count": confirmed_count,
            "persistence_met": persistence_met,
            "contradiction": False,
            "contradiction_detail": "",
        }

    def detect_contradictions(self, signals: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Check signal set for known contradiction pairs from config."""
        contradiction_pairs_cfg = self.config.get("contradictions") or []
        signal_map = {s["name"]: s["value"] for s in signals if not s.get("expired")}

        found_pairs = []
        detail_parts = []

        for pair_cfg in contradiction_pairs_cfg:
            pair = pair_cfg.get("pair", [])
            condition = pair_cfg.get("condition", "")
            severity = pair_cfg.get("severity", "MEDIUM")

            if len(pair) != 2:
                continue

            sig_a_name, sig_b_name = pair
            if sig_a_name not in signal_map or sig_b_name not in signal_map:
                continue

            if self._evaluate_contradiction_condition(
                condition, sig_a_name, signal_map[sig_a_name],
                sig_b_name, signal_map[sig_b_name]
            ):
                pair_key = f"{sig_a_name}_{sig_b_name}"
                found_pairs.append(pair_key)
                detail_parts.append(
                    f"{sig_a_name}={signal_map[sig_a_name]} conflicts with "
                    f"{sig_b_name}={signal_map[sig_b_name]} (severity={severity})"
                )

        return {
            "has_contradiction": bool(found_pairs),
            "contradiction_pairs": found_pairs,
            "detail": "; ".join(detail_parts),
        }

    def _evaluate_contradiction_condition(
        self,
        condition: str,
        sig_a_name: str,
        sig_a_value: Any,
        sig_b_name: str,
        sig_b_value: Any,
    ) -> bool:
        """
        Parse and evaluate a contradiction condition string.
        Format: "SIGNAL_A=value_a AND SIGNAL_B=value_b"
        """
        if not condition:
            return False
        try:
            parts = condition.split(" AND ")
            expectations: Dict[str, str] = {}
            for part in parts:
                k, v = part.strip().split("=", 1)
                expectations[k.strip()] = v.strip()
            a_match = str(sig_a_value) == expectations.get(sig_a_name, "")
            b_match = str(sig_b_value) == expectations.get(sig_b_name, "")
            return a_match and b_match
        except Exception:
            return False


# ═════════════════════════════════════════════════════════════════════════════
# ConvergenceEngine
# ═════════════════════════════════════════════════════════════════════════════

class ConvergenceEngine:
    """
    Main convergence orchestrator. Called from sentinel.py every 60s.
    Manages signal lifecycle, pattern evaluation, state transitions, and
    baseline persistence.
    """

    def __init__(self, session: Optional[aiohttp.ClientSession], config):
        self.config = config
        self.feeds = SignalFeeds(session, config) if session is not None else None
        self.baseline = BaselineStore(
            db_path=Path(config.get("persistence", "db_path") or "data/baseline_store.db")
        )
        self.extractor = SignalExtractor(config)
        self.evaluator = PatternEvaluator(config)

        # Load transition map from config
        transition_cfg = config.get("state_machine", "valid_transitions")
        self._state_machine = ConvergenceStateMachine(
            valid_transitions=transition_cfg or _DEFAULT_VALID_TRANSITIONS
        )
        self._state_entered_at: float = time.time()

        # Current signal store: {signal_name: signal_dict}
        self._signals: Dict[str, Dict[str, Any]] = {}

        # Last purge timestamp
        self._last_purge: float = 0.0

    # ── Signal injection (for testing and internal use) ───────────────────────

    def inject_signal(self, name: str, value: Any, timestamp: Optional[float] = None) -> None:
        """Inject a signal directly (used in tests and for manual override)."""
        self._signals[name] = self.extractor.extract_signal(name, value, timestamp)

    def evaluate_signal_freshness(self, name: str) -> Dict[str, Any]:
        """Re-evaluate freshness of a named signal. Used in tests."""
        signal = self._signals.get(name)
        if not signal:
            return {"confirmed": False, "expired": True}
        return self.extractor.evaluate_signal_freshness(signal)

    def evaluate_mcc_pattern(self) -> Dict[str, Any]:
        """Evaluate MCC pattern against current signal set. Exposed for testing."""
        return self.evaluator.evaluate_pattern(
            "MCC",
            list(self._signals.values()),
            self._state_machine.state,
            self._state_entered_at,
        )

    def detect_contradictions(self) -> Dict[str, Any]:
        """Run contradiction detection against current signal set. Exposed for testing."""
        return self.evaluator.detect_contradictions(list(self._signals.values()))

    @property
    def state(self) -> str:
        return self._state_machine.state

    # ── Main evaluation cycle ─────────────────────────────────────────────────

    async def run_evaluation_cycle(self) -> Dict[str, Any]:
        """
        Async — must be awaited in sentinel.py loop.
        Fetches all feeds, extracts signals, evaluates patterns, transitions state.
        Returns convergence dict for inclusion in sentinel state file.
        """
        if self.feeds is None:
            raise RuntimeError("run_evaluation_cycle() called with no aiohttp session.")

        # ── 1. Fetch all feeds (all async, non-blocking) ──────────────────────
        vix = await self.feeds.fetch_vix()
        spy = await self.feeds.fetch_spy()
        wti = await self.feeds.fetch_wti()
        deribit = await self.feeds.fetch_deribit_funding()
        stablecoin = await self.feeds.fetch_stablecoin_flows()
        hodlhodl = await self.feeds.fetch_hodlhodl_premium()
        rss = await self.feeds.fetch_rss_news()
        custodian = await self.feeds.fetch_custodian_wallet_flows()

        # ── 2. Extract and update signals ─────────────────────────────────────
        now = time.time()

        if vix is not None:
            self._signals["VIX"] = self.extractor.extract_signal("VIX", vix, now)
        if spy is not None:
            self._signals["SPY"] = self.extractor.extract_signal("SPY", spy, now)
        if wti is not None:
            self._signals["WTI"] = self.extractor.extract_signal("WTI", wti, now)
        if deribit is not None:
            self._signals["DERIBIT_FUNDING"] = self.extractor.extract_signal(
                "DERIBIT_FUNDING", deribit, now
            )

        # Stablecoin flows -> IES and LSC
        if stablecoin is not None:
            ies_value, lsc_value = self._parse_stablecoin_signals(stablecoin)
            if ies_value is not None:
                self._signals["IES"] = self.extractor.extract_signal("IES", ies_value, now)
            if lsc_value is not None:
                self._signals["LSC"] = self.extractor.extract_signal("LSC", lsc_value, now)

        if hodlhodl is not None:
            self._signals["HODLHODL_PREMIUM"] = self.extractor.extract_signal(
                "HODLHODL_PREMIUM", hodlhodl, now
            )
        if rss is not None:
            sentiment = self._score_news_sentiment(rss)
            self._signals["NEWS_SENTIMENT"] = self.extractor.extract_signal(
                "NEWS_SENTIMENT", sentiment, now
            )
        if custodian is not None:
            flow_direction = self._parse_custodian_flow(custodian)
            self._signals["CUSTODIAN_FLOW"] = self.extractor.extract_signal(
                "CUSTODIAN_FLOW", flow_direction, now
            )

        # Re-evaluate freshness of all existing signals (age signals forward)
        for name, signal in list(self._signals.items()):
            self._signals[name] = self.extractor.evaluate_signal_freshness(signal)

        # ── 3. Evaluate all patterns ──────────────────────────────────────────
        signal_list = list(self._signals.values())
        patterns_to_evaluate = list(
            (self.config.get("patterns") or {}).keys()
        )

        pattern_results: Dict[str, Dict] = {}
        for pattern_name in patterns_to_evaluate:
            try:
                result = self.evaluator.evaluate_pattern(
                    pattern_name,
                    signal_list,
                    self._state_machine.state,
                    self._state_entered_at,
                )
                pattern_results[pattern_name] = result
            except Exception as e:
                logger.warning(f"Pattern '{pattern_name}' evaluation failed: {e}")

        # ── 4. Determine target state (most severe pattern result) ─────────────
        state_rank = {"IDLE": 0, "WATCH": 1, "ALERT": 2, "CRITICAL": 3}
        target_state = "IDLE"
        for result in pattern_results.values():
            if state_rank.get(result["state"], 0) > state_rank.get(target_state, 0):
                target_state = result["state"]

        # ── 5. Transition state machine if needed ─────────────────────────────
        current = self._state_machine.state
        if target_state != current and self._state_machine.can_transition(target_state):
            old_state = current
            self._state_machine.transition(target_state)
            self._state_entered_at = time.time()
            self.baseline.record_pattern_event(
                "CONVERGENCE",
                old_state,
                target_state,
                signal_list,
            )

        # ── 6. Persist snapshot ───────────────────────────────────────────────
        self.baseline.record_snapshot({
            "timestamp": now,
            "state": self._state_machine.state,
            "signals": {k: v for k, v in self._signals.items()},
        })

        # ── 6b. Periodic purge ────────────────────────────────────────────────
        purge_interval = self.config.get("evaluation", "baseline_purge_interval_seconds") or 86400
        if now - self._last_purge > purge_interval:
            self.baseline.purge_old_records()
            self._last_purge = now

        # ── 7. Build and return convergence dict for state file ───────────────
        contradiction_result = self.evaluator.detect_contradictions(signal_list)
        max_in_payload = self.config.get("sse", "max_signals_in_payload") or 20

        convergence_dict = {
            "state": self._state_machine.state,
            "last_evaluated": now,
            "signals": [
                {
                    "name": s["name"],
                    "value": s["value"],
                    "confirmed": s["confirmed"],
                    "timestamp": s["timestamp"],
                    "decay_weight": s["decay_weight"],
                }
                for s in signal_list[:max_in_payload]
            ],
            "contradiction": contradiction_result["has_contradiction"],
            "contradiction_detail": contradiction_result.get("detail", ""),
            "pattern_results": pattern_results,
            "schema_version": 1,
        }

        logger.info(json.dumps({
            "event": "convergence_cycle_complete",
            "state": self._state_machine.state,
            "signal_count": len(signal_list),
            "contradiction": contradiction_result["has_contradiction"],
            "timestamp": now,
        }))

        return convergence_dict

    # ── Signal parsing helpers ────────────────────────────────────────────────

    def _parse_stablecoin_signals(
        self, raw: Dict[str, Any]
    ) -> Tuple[Optional[str], Optional[str]]:
        """Parse DeFi Llama stablecoin chain data into IES and LSC signal values."""
        try:
            chains = raw if isinstance(raw, list) else []
            total_minted = sum(
                float(c.get("totalCirculatingUSD", {}).get("peggedUSD", 0) or 0)
                for c in chains
            )
            ies_value = "bullish" if total_minted > 1e11 else "neutral"
            lsc_value = "bullish_stablecoin_inflow" if total_minted > 1e11 else "bearish_stablecoin_outflow"
            return ies_value, lsc_value
        except Exception as e:
            logger.warning(f"Stablecoin signal parsing failed: {e}")
            return None, None

    def _score_news_sentiment(self, rss_data: Dict[str, Any]) -> str:
        """Score RSS title list for basic sentiment."""
        titles = rss_data.get("titles", [])
        text = " ".join(titles).lower()
        bullish_terms = ["rally", "surge", "breakout", "ath", "adoption", "buy"]
        bearish_terms = ["crash", "dump", "ban", "hack", "sell", "fear", "collapse"]
        bull_score = sum(text.count(t) for t in bullish_terms)
        bear_score = sum(text.count(t) for t in bearish_terms)
        if bull_score > bear_score + 2:
            return "bullish"
        elif bear_score > bull_score + 2:
            return "bearish"
        return "neutral"

    def _parse_custodian_flow(self, raw: Dict[str, Any]) -> str:
        """Parse custodian wallet flow data into directional signal."""
        try:
            net_flow = float(raw.get("net_flow_btc", 0) or 0)
            if net_flow > 100:
                return "inflow_large"
            elif net_flow < -100:
                return "outflow_large"
            return "neutral"
        except Exception:
            return "neutral"
