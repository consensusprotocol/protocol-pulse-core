"""
Sovereign Engine — CBDC & Sovereign Intelligence Layer (Phase 2, F3)

Monitors global jurisdiction posture toward Bitcoin, CBDC rollout risk,
self-custody health indicators, and capital-flight signals.

NO `from services.*` imports — uses importlib.util / pathlib only.
"""

import asyncio
import importlib.util
import json
import logging
import time
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
JURISDICTION_DB_PATH = DATA_DIR / "jurisdiction_db.json"
CBDC_WATCHLIST_PATH = DATA_DIR / "cbdc_watchlist.json"

BIS_RSS_URL = "https://www.bis.org/rss.htm"

CBDC_KEYWORDS = [
    "cbdc", "central bank digital currency", "digital currency",
    "e-cny", "digital euro", "digital ruble", "digital rupee",
    "digital dollar", "enaira", "sand dollar", "jam-dex",
    "programmable money", "digital yuan", "britcoin", "e-krona",
    "digital won", "digital yen", "digital baht", "real digital",
]


class SovereignEngine:
    """Async engine for CBDC & sovereign intelligence monitoring."""

    def __init__(self):
        self._jurisdiction_cache: List[Dict[str, Any]] = []
        self._cbdc_watchlist: List[Dict[str, Any]] = []
        self._last_bis_results: List[Dict[str, Any]] = []
        self._last_cycle_result: Optional[Dict[str, Any]] = None
        self._load_jurisdiction_db()
        self._load_cbdc_watchlist()

    # ------------------------------------------------------------------
    # Data loading
    # ------------------------------------------------------------------

    def _load_jurisdiction_db(self) -> None:
        """Load jurisdiction database from JSON file once on init."""
        try:
            with open(JURISDICTION_DB_PATH, "r", encoding="utf-8") as f:
                self._jurisdiction_cache = json.load(f)
            logger.info(
                "Sovereign engine: loaded %d jurisdictions",
                len(self._jurisdiction_cache),
            )
        except FileNotFoundError:
            logger.warning(
                "jurisdiction_db.json not found at %s — running with empty cache",
                JURISDICTION_DB_PATH,
            )
            self._jurisdiction_cache = []
        except json.JSONDecodeError as exc:
            logger.error("jurisdiction_db.json parse error: %s", exc)
            self._jurisdiction_cache = []

    def _load_cbdc_watchlist(self) -> None:
        """Load CBDC watchlist from JSON file."""
        try:
            with open(CBDC_WATCHLIST_PATH, "r", encoding="utf-8") as f:
                self._cbdc_watchlist = json.load(f)
            logger.info(
                "Sovereign engine: loaded %d CBDC watchlist entries",
                len(self._cbdc_watchlist),
            )
        except FileNotFoundError:
            logger.warning(
                "cbdc_watchlist.json not found at %s", CBDC_WATCHLIST_PATH
            )
            self._cbdc_watchlist = []
        except json.JSONDecodeError as exc:
            logger.error("cbdc_watchlist.json parse error: %s", exc)
            self._cbdc_watchlist = []

    # ------------------------------------------------------------------
    # BIS RSS feed
    # ------------------------------------------------------------------

    async def fetch_bis_cbdc_rss(self, session) -> List[Dict[str, Any]]:
        """Fetch BIS RSS feed and filter for CBDC-related items.

        Parameters
        ----------
        session : aiohttp.ClientSession
            An active aiohttp session for HTTP requests.

        Returns
        -------
        list[dict]
            Each dict: {title, link, published, is_critical}
        """
        try:
            async with session.get(BIS_RSS_URL, timeout=15) as resp:
                if resp.status != 200:
                    logger.warning(
                        "BIS RSS returned HTTP %d — using cached results",
                        resp.status,
                    )
                    return self._last_bis_results

                raw_xml = await resp.text()

            root = ET.fromstring(raw_xml)

            # RSS 2.0 items live under <channel><item>
            items: List[Dict[str, Any]] = []
            for item_el in root.iter("item"):
                title_el = item_el.find("title")
                link_el = item_el.find("link")
                pub_el = item_el.find("pubDate")

                title = title_el.text.strip() if title_el is not None and title_el.text else ""
                link = link_el.text.strip() if link_el is not None and link_el.text else ""
                published = pub_el.text.strip() if pub_el is not None and pub_el.text else ""

                title_lower = title.lower()
                desc_el = item_el.find("description")
                desc_text = (
                    desc_el.text.strip().lower()
                    if desc_el is not None and desc_el.text
                    else ""
                )

                combined = f"{title_lower} {desc_text}"

                if any(kw in combined for kw in CBDC_KEYWORDS):
                    is_critical = any(
                        kw in combined
                        for kw in [
                            "programmable",
                            "mandatory",
                            "surveillance",
                            "ban",
                            "restrict",
                            "freeze",
                            "confiscat",
                        ]
                    )
                    items.append(
                        {
                            "title": title,
                            "link": link,
                            "published": published,
                            "is_critical": is_critical,
                        }
                    )

            self._last_bis_results = items
            logger.info("BIS RSS: found %d CBDC-related items", len(items))
            return items

        except asyncio.TimeoutError:
            logger.warning("BIS RSS fetch timed out — returning cached data")
            return self._last_bis_results
        except ET.ParseError as exc:
            logger.error("BIS RSS XML parse error: %s", exc)
            return self._last_bis_results
        except Exception as exc:
            logger.error("BIS RSS unexpected error: %s", exc)
            return self._last_bis_results

    # ------------------------------------------------------------------
    # Self-custody health metrics
    # ------------------------------------------------------------------

    def compute_custody_health(
        self, sentinel_state: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Compute self-custody health indicators.

        Parameters
        ----------
        sentinel_state : dict or None
            Optional external state from sentinel/on-chain monitors.

        Returns
        -------
        dict
            exchange_reserve_ratio, cdd_signal, coinjoin_signal, taproot_pct
        """
        state = sentinel_state or {}

        # Exchange reserve ratio — placeholder until Glassnode/CryptoQuant
        # integration ships.  Use sentinel override if provided.
        exchange_reserve_ratio = state.get("exchange_reserve_ratio", 58.2)

        # Coin Days Destroyed signal
        cdd_raw = state.get("cdd_90d_zscore")
        if cdd_raw is not None:
            if cdd_raw > 2.0:
                cdd_signal = "ELEVATED"
            elif cdd_raw < -1.0:
                cdd_signal = "DORMANT"
            else:
                cdd_signal = "STABLE"
        else:
            cdd_signal = "STABLE"

        # CoinJoin activity signal
        coinjoin_vol = state.get("coinjoin_volume_btc")
        if coinjoin_vol is not None:
            if coinjoin_vol > 500:
                coinjoin_signal = "HIGH"
            elif coinjoin_vol < 50:
                coinjoin_signal = "LOW"
            else:
                coinjoin_signal = "NORMAL"
        else:
            coinjoin_signal = "NORMAL"

        # Taproot adoption percentage — from mempool.space stats if available
        taproot_pct = state.get("taproot_adoption_pct", 5.0)

        return {
            "exchange_reserve_ratio": round(exchange_reserve_ratio, 1),
            "cdd_signal": cdd_signal,
            "coinjoin_signal": coinjoin_signal,
            "taproot_pct": round(taproot_pct, 1),
        }

    # ------------------------------------------------------------------
    # Capital flight detection
    # ------------------------------------------------------------------

    def detect_capital_flight(
        self, sentinel_state: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Detect potential capital-flight signals.

        Returns True if anomalies detected, False otherwise.

        Current heuristics (expanded as on-chain feeds ship):
        - Exchange inflow spike > 3 std devs (from sentinel)
        - P2P premium > 15% in any hostile jurisdiction
        - Stablecoin outflow spike
        """
        if sentinel_state is None:
            return False

        # Check exchange inflow anomaly
        inflow_zscore = sentinel_state.get("exchange_inflow_zscore")
        if inflow_zscore is not None and inflow_zscore > 3.0:
            logger.warning(
                "Capital flight signal: exchange inflow z-score %.1f",
                inflow_zscore,
            )
            return True

        # Check P2P premium
        p2p_premium = sentinel_state.get("p2p_premium_pct")
        if p2p_premium is not None and p2p_premium > 15.0:
            logger.warning(
                "Capital flight signal: P2P premium %.1f%%", p2p_premium
            )
            return True

        # Check stablecoin outflow
        stablecoin_outflow_zscore = sentinel_state.get(
            "stablecoin_outflow_zscore"
        )
        if (
            stablecoin_outflow_zscore is not None
            and stablecoin_outflow_zscore > 2.5
        ):
            logger.warning(
                "Capital flight signal: stablecoin outflow z-score %.1f",
                stablecoin_outflow_zscore,
            )
            return True

        return False

    # ------------------------------------------------------------------
    # Jurisdiction summary
    # ------------------------------------------------------------------

    def _compute_jurisdiction_summary(self) -> Dict[str, int]:
        """Summarize jurisdiction counts by Bitcoin status."""
        friendly = 0
        neutral = 0
        hostile = 0

        for j in self._jurisdiction_cache:
            status = j.get("bitcoin_status", "").lower()
            if status == "legal":
                friendly += 1
            elif status in ("restricted",):
                neutral += 1
            elif status in ("hostile", "banned"):
                hostile += 1

        return {
            "friendly_count": friendly,
            "neutral_count": neutral,
            "hostile_count": hostile,
        }

    # ------------------------------------------------------------------
    # Main cycle
    # ------------------------------------------------------------------

    async def run_cycle(
        self, session, sentinel_state: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Execute one intelligence cycle.

        Parameters
        ----------
        session : aiohttp.ClientSession
            Active HTTP session.
        sentinel_state : dict or None
            On-chain / sentinel state for custody & flight signals.

        Returns
        -------
        dict
            top_alerts, jurisdiction_summary, custody_health,
            capital_flight_signal, updated_at
        """
        # Fetch BIS alerts
        bis_items = await self.fetch_bis_cbdc_rss(session)
        top_alerts = bis_items[:5]

        # Jurisdiction summary
        jurisdiction_summary = self._compute_jurisdiction_summary()

        # Custody health
        custody_health = self.compute_custody_health(sentinel_state)

        # Capital flight
        capital_flight_signal = self.detect_capital_flight(sentinel_state)

        result = {
            "top_alerts": top_alerts,
            "jurisdiction_summary": jurisdiction_summary,
            "custody_health": custody_health,
            "capital_flight_signal": capital_flight_signal,
            "updated_at": time.time(),
        }

        self._last_cycle_result = result
        return result

    # ------------------------------------------------------------------
    # Convenience accessors
    # ------------------------------------------------------------------

    @property
    def jurisdictions(self) -> List[Dict[str, Any]]:
        """Return the full jurisdiction cache."""
        return self._jurisdiction_cache

    @property
    def cbdc_watchlist(self) -> List[Dict[str, Any]]:
        """Return the CBDC watchlist."""
        return self._cbdc_watchlist

    @property
    def last_result(self) -> Optional[Dict[str, Any]]:
        """Return the last cycle result, if any."""
        return self._last_cycle_result
