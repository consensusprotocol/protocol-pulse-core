"""
TEMPORAL PREDICTIVE ANALYTICS — Scenario Simulation Engine
============================================================
Monte Carlo simulation with Bayesian-calibrated priors. Models Bitcoin's
probable futures as 5 named scenarios with precursor signal detection.

CPU only — no GPU needed. Runs every 6 hours from sentinel.

IMPORT RULE: Load via importlib.util — never `from pp_services.tpa_engine import ...`
"""

import base64
import hashlib
import json
import logging
import time
from pathlib import Path

import numpy as np

logger = logging.getLogger("tpa_engine")

_DATA_DIR = Path(__file__).resolve().parent.parent / "data"

# State machine levels for comparison
_STATE_LEVELS = {"IDLE": 0, "WATCH": 1, "ALERT": 2, "CRITICAL": 3}


class TPAEngine:
    """Monte Carlo scenario simulation engine."""

    def __init__(self):
        self.scenarios = []
        self.correlations = {}
        self.calibration = {}
        self._last_evaluation = 0.0
        self._signal_confirmations = {}  # signal_id -> {confirmed_at, strength}
        self._snapshots = {}  # snapshot_id -> snapshot_data
        self._load_config()

    def _load_config(self):
        """Load scenarios, correlations, calibration from data/."""
        try:
            with open(_DATA_DIR / "tpa_scenarios.json") as f:
                data = json.load(f)
            self.scenarios = data.get("scenarios", [])

            with open(_DATA_DIR / "tpa_scenario_correlations.json") as f:
                corr_data = json.load(f)
            self.correlations = corr_data.get("correlations", {})

            with open(_DATA_DIR / "tpa_calibration.json") as f:
                self.calibration = json.load(f)

            # Validate
            assert len(self.scenarios) == 5, f"Expected 5 scenarios, got {len(self.scenarios)}"
            total = sum(s["base_probability"] for s in self.scenarios)
            assert 99 <= total <= 101, f"Base probabilities sum to {total}, expected ~100"

            logger.info("TPA config loaded: %d scenarios, %d correlations",
                        len(self.scenarios), len(self.correlations))

        except Exception as e:
            logger.error("Failed to load TPA config: %s", e)
            self.scenarios = []

    def check_signal(self, signal: dict, state: dict) -> tuple:
        """
        Check if a signal is confirmed in the current state.
        Returns (confirmed: bool, strength: float 0-1).
        """
        path = signal.get("sentinel_state_path", "")
        threshold = signal.get("threshold")
        comparison = signal.get("comparison", "gte")

        # Navigate state dict using dot notation
        value = self._get_nested(state, path)
        if value is None:
            return False, 0.0

        try:
            if comparison == "gte":
                threshold_f = float(threshold)
                if threshold_f == 0:
                    return False, 0.0
                strength = min(float(value) / threshold_f, 1.0) if threshold_f > 0 else 0.0
                return float(value) >= threshold_f, max(strength, 0.0)

            elif comparison == "lte":
                threshold_f = float(threshold)
                if float(value) <= threshold_f:
                    return True, min(abs(threshold_f - float(value)) / max(abs(threshold_f), 1e-10) + 0.5, 1.0)
                return False, 0.0

            elif comparison == "eq":
                if str(value) == str(threshold):
                    return True, 1.0
                return False, 0.0

            elif comparison == "eq_or_above":
                val_level = _STATE_LEVELS.get(str(value), 0)
                thresh_level = _STATE_LEVELS.get(str(threshold), 0)
                if val_level >= thresh_level and val_level > 0:
                    return True, min(val_level / 3.0, 1.0)
                return False, 0.0

            elif comparison == "contains":
                # Check if any item in a list contains the threshold string
                if isinstance(value, list):
                    for item in value:
                        item_str = json.dumps(item) if isinstance(item, dict) else str(item)
                        if str(threshold) in item_str.lower():
                            return True, 0.8
                elif isinstance(value, str) and str(threshold) in value.lower():
                    return True, 0.8
                return False, 0.0

            elif comparison == "contains_count":
                count_needed = signal.get("count_threshold", 1)
                matches = 0
                if isinstance(value, list):
                    for item in value:
                        item_str = json.dumps(item) if isinstance(item, dict) else str(item)
                        if str(threshold) in item_str.lower():
                            matches += 1
                strength = min(matches / max(count_needed, 1), 1.0)
                return matches >= count_needed, strength

            elif comparison == "gte_delta":
                # For tracking changes over time (not implemented in v1 — use current value)
                return float(value) >= float(threshold), 0.5 if float(value) >= float(threshold) else 0.0

        except (ValueError, TypeError) as e:
            logger.debug("Signal check error for %s: %s", signal.get("signal_id"), e)
            return False, 0.0

        return False, 0.0

    def evaluate_scenarios(self, state: dict) -> list:
        """Evaluate all scenarios against current state. Returns updated scenario list."""
        results = []

        for scenario in self.scenarios:
            sid = scenario["id"]
            base_prob = scenario["base_probability"]
            current_prob = base_prob

            confirmed_signals = []
            total_signals = len(scenario.get("signals", []))
            total_strength = 0.0

            # Check each precursor signal
            for signal in scenario.get("signals", []):
                confirmed, strength = self.check_signal(signal, state)

                if confirmed:
                    # Apply temporal decay
                    sig_id = signal["signal_id"]
                    decay_days = signal.get("decay_days", 30)
                    confirmation = self._signal_confirmations.get(sig_id)

                    if confirmation:
                        age_days = (time.time() - confirmation["confirmed_at"]) / 86400
                        if age_days > decay_days:
                            decay_factor = 0.5  # 50% decay after expiry
                        else:
                            decay_factor = 1.0
                    else:
                        decay_factor = 1.0
                        self._signal_confirmations[sig_id] = {
                            "confirmed_at": time.time(),
                            "strength": strength,
                        }

                    delta = signal["probability_delta"] * strength * decay_factor
                    current_prob += delta
                    confirmed_signals.append(sig_id)
                    total_strength += strength

            # Apply contradiction penalties
            for other_scenario in self.scenarios:
                if other_scenario["id"] == sid:
                    continue
                key1 = f"{sid}:{other_scenario['id']}"
                key2 = f"{other_scenario['id']}:{sid}"
                corr = self.correlations.get(key1, self.correlations.get(key2, 0))

                if corr < 0:
                    # Negative correlation: if other scenario has confirmed signals, penalize this one
                    other_confirmed = sum(1 for s in other_scenario.get("signals", [])
                                          if self.check_signal(s, state)[0])
                    if other_confirmed > 0:
                        penalty = abs(corr) * (other_confirmed / max(len(other_scenario.get("signals", [])), 1)) * 100
                        current_prob -= penalty

            # Clip to [1, 95]
            current_prob = max(1.0, min(95.0, current_prob))

            # Compute trend
            prev = self._get_prev_probability(sid)
            delta = current_prob - prev if prev is not None else 0.0
            if delta > 0.5:
                trend = "rising"
            elif delta < -0.5:
                trend = "falling"
            else:
                trend = "stable"

            results.append({
                "id": sid,
                "name": scenario["name"],
                "probability": round(current_prob, 1),
                "base_probability": base_prob,
                "delta_since_last": round(delta, 1),
                "trend": trend,
                "signals_confirmed": len(confirmed_signals),
                "signals_total": total_signals,
                "confirmed_signal_ids": confirmed_signals,
                "total_strength": round(total_strength, 2),
            })

        # Normalize to sum to 100%
        total = sum(r["probability"] for r in results)
        if total > 0:
            for r in results:
                r["probability"] = round(r["probability"] / total * 100, 1)
                r["probability_p10"] = 0.0  # placeholder until MC runs
                r["probability_p90"] = 0.0

        # Store for trend tracking
        for r in results:
            self._store_probability(r["id"], r["probability"])

        return results

    def run_monte_carlo(self, scenarios: list, state: dict, n_iter: int = 10000) -> dict:
        """
        Monte Carlo confidence intervals.
        Jitter: Normal distribution, sigma = 0.15 * signal_strength (per audit recommendation).
        Returns {scenario_id: {p10, p50, p90}}.
        """
        np.random.seed(int(time.time()) % 2**31)
        results = {}

        for scenario_def, scenario_result in zip(self.scenarios, scenarios):
            sid = scenario_def["id"]
            samples = np.zeros(n_iter)

            for i in range(n_iter):
                prob = scenario_def["base_probability"]

                for signal in scenario_def.get("signals", []):
                    confirmed, strength = self.check_signal(signal, state)
                    if confirmed:
                        # Jitter the strength
                        sigma = 0.15 * max(strength, 0.1)
                        jittered_strength = np.clip(
                            np.random.normal(strength, sigma), 0.0, 1.0)
                        prob += signal["probability_delta"] * jittered_strength

                prob = max(1.0, min(95.0, prob))
                samples[i] = prob

            results[sid] = {
                "p10": round(float(np.percentile(samples, 10)), 1),
                "p50": round(float(np.percentile(samples, 50)), 1),
                "p90": round(float(np.percentile(samples, 90)), 1),
            }

        # Normalize p50s to sum to 100
        total_p50 = sum(v["p50"] for v in results.values())
        if total_p50 > 0:
            for sid in results:
                ratio = results[sid]["p50"] / total_p50
                results[sid]["p10"] = round(results[sid]["p10"] / total_p50 * 100, 1)
                results[sid]["p50"] = round(ratio * 100, 1)
                results[sid]["p90"] = round(results[sid]["p90"] / total_p50 * 100, 1)

        return results

    def run_cycle(self, state: dict) -> dict:
        """
        Full TPA evaluation cycle. Called every 6h from sentinel.
        Returns complete tpa state dict.
        """
        if not self.scenarios:
            return self._empty_state("no_config")

        try:
            # Evaluate scenarios
            scenarios = self.evaluate_scenarios(state)

            # Run Monte Carlo for confidence intervals
            mc = self.run_monte_carlo(scenarios, state)

            # Merge MC intervals into scenario results
            for s in scenarios:
                mc_data = mc.get(s["id"], {})
                s["probability_p10"] = mc_data.get("p10", s["probability"] - 5)
                s["probability_p90"] = mc_data.get("p90", s["probability"] + 5)
                s["last_updated"] = time.time()

            self._last_evaluation = time.time()

            return {
                "scenarios": scenarios,
                "last_evaluated_at": self._last_evaluation,
                "next_evaluation_at": self._last_evaluation + 21600,  # 6 hours
                "calibration_date": self.calibration.get("calibration_date", ""),
                "data_quality": "good",
            }

        except Exception as e:
            logger.error("TPA cycle failed: %s", e)
            return self._empty_state("error")

    def get_share_snapshot(self, scenario_id: str = None) -> dict:
        """Generate a shareable snapshot of current TPA state or specific scenario."""
        snapshot = {
            "timestamp": time.time(),
            "scenarios": [],
        }

        # Build state from last evaluation
        for s_def in self.scenarios:
            sid = s_def["id"]
            prob = self._get_prev_probability(sid) or s_def["base_probability"]
            confirmed = [sig_id for sig_id, conf in self._signal_confirmations.items()
                         if sig_id.startswith(sid[:2])]

            entry = {
                "id": sid,
                "name": s_def["name"],
                "probability": prob,
                "signals_confirmed": len(confirmed),
                "signals_total": len(s_def.get("signals", [])),
            }

            if scenario_id and sid == scenario_id:
                entry["highlighted"] = True

            snapshot["scenarios"].append(entry)

        # Generate snapshot ID
        raw = json.dumps(snapshot, sort_keys=True).encode()
        snapshot_id = hashlib.sha256(raw).hexdigest()[:12]
        snapshot["snapshot_id"] = snapshot_id

        # Store for retrieval
        self._snapshots[snapshot_id] = snapshot

        return snapshot

    def get_snapshot_by_id(self, snapshot_id: str) -> dict:
        """Retrieve a stored snapshot by ID."""
        return self._snapshots.get(snapshot_id, {})

    def _get_nested(self, d: dict, path: str):
        """Navigate a dict using dot-notation path."""
        parts = path.split(".")
        current = d
        for part in parts:
            if isinstance(current, dict):
                current = current.get(part)
            else:
                return None
            if current is None:
                return None
        return current

    _prev_probs = {}  # class-level storage for trend tracking

    def _store_probability(self, scenario_id: str, prob: float):
        TPAEngine._prev_probs[scenario_id] = prob

    def _get_prev_probability(self, scenario_id: str):
        return TPAEngine._prev_probs.get(scenario_id)

    def _empty_state(self, quality: str = "initializing") -> dict:
        return {
            "scenarios": [],
            "last_evaluated_at": 0.0,
            "next_evaluation_at": 0.0,
            "calibration_date": "",
            "data_quality": quality,
        }
