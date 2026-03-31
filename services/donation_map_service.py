#!/usr/bin/env python3
"""
OpenFEC Donation Map Service — Political contribution data for Panopticon.
Uses the free OpenFEC API to track federal political donations by state/zip.
"""
import requests
import logging
import os
import json
import time
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class DonationMapService:
    def __init__(self):
        self.base_url = "https://api.open.fec.gov/v1"
        self.api_key = os.environ.get("OPENFEC_API_KEY", "DEMO_KEY")
        self._cache = {}
        self._cache_ttl = 3600  # 1 hour cache

    def _get(self, endpoint, params=None):
        """Make a cached GET request to OpenFEC."""
        cache_key = f"{endpoint}:{json.dumps(params or {}, sort_keys=True)}"
        now = time.time()
        if cache_key in self._cache:
            data, ts = self._cache[cache_key]
            if now - ts < self._cache_ttl:
                return data

        if params is None:
            params = {}
        params["api_key"] = self.api_key

        try:
            r = requests.get(f"{self.base_url}{endpoint}", params=params, timeout=10)
            if r.ok:
                result = r.json().get("results", [])
                self._cache[cache_key] = (result, now)
                return result
            else:
                logger.warning(f"OpenFEC API {r.status_code}: {r.text[:200]}")
                return []
        except Exception as e:
            logger.warning(f"OpenFEC API error: {e}")
            return []

    def get_contributions_by_state(self, state=None, per_page=100):
        """Fetch recent individual contributions, optionally filtered by state."""
        params = {
            "per_page": per_page,
            "sort": "-contribution_receipt_date",
            "is_individual": "true",
        }
        if state and state != "US":
            params["contributor_state"] = state
        return self._get("/schedules/schedule_a/", params)

    def get_contributions_by_zip(self, zip_code, per_page=50):
        """Fetch contributions by zip code."""
        params = {
            "contributor_zip": zip_code,
            "per_page": per_page,
            "sort": "-contribution_receipt_date",
            "is_individual": "true",
        }
        return self._get("/schedules/schedule_a/", params)

    def get_crypto_related_committees(self, per_page=20):
        """Search for committees with crypto/bitcoin in their name."""
        results = []
        for keyword in ["bitcoin", "crypto", "blockchain", "digital asset"]:
            params = {"q": keyword, "per_page": per_page}
            committees = self._get("/committees/", params)
            results.extend(committees)
        return results

    def get_state_summary(self):
        """Get aggregate donation data by state for map visualization."""
        # Use totals endpoint for state-level aggregation
        params = {
            "per_page": 50,
            "sort": "-total",
            "cycle": datetime.now().year if datetime.now().year % 2 == 0 else datetime.now().year - 1,
        }
        return self._get("/schedules/schedule_a/by_state/", params)

    def get_donation_pulse(self):
        """Get a pulse score (0-100) based on recent crypto-related donation activity."""
        try:
            committees = self.get_crypto_related_committees(10)
            state_data = self.get_state_summary()

            crypto_committees = len(committees)
            total_states_active = len(state_data) if state_data else 0

            # Simple pulse score based on activity
            pulse = min(100, max(0,
                (crypto_committees * 5) +
                (total_states_active * 2)
            ))

            return {
                "score": pulse,
                "crypto_committees": crypto_committees,
                "states_active": total_states_active,
                "label": "HIGH" if pulse > 70 else ("MODERATE" if pulse > 40 else "LOW"),
                "updated": datetime.utcnow().isoformat(),
            }
        except Exception as e:
            logger.warning(f"Donation pulse error: {e}")
            return {"score": 0, "label": "UNAVAILABLE", "crypto_committees": 0, "states_active": 0}
