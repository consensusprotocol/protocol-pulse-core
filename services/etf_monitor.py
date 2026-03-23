"""
ETF Flow Monitor — Phase 2 Feature F4
Tracks custodian wallet balance deltas via mempool.space
and Deribit funding rates for ETF flow intelligence.
"""

import json
import time
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

CUSTODIAN_WALLETS_PATH = Path(__file__).resolve().parent.parent / "data" / "custodian_wallets.json"
MEMPOOL_ADDRESS_URL = "https://mempool.space/api/address/{address}"
DERIBIT_FUNDING_URL = "https://www.deribit.com/api/v2/public/get_funding_rate_value"

HISTORY_WINDOW_S = 24 * 3600   # keep 24h of snapshots
DELTA_WINDOW_S = 6 * 3600      # compute deltas over 6h


class ETFMonitor:
    def __init__(self):
        self._balance_history: dict[str, list[tuple[float, int]]] = {}
        self._last_result: dict | None = None
        self._wallets: list[dict] = []
        self._load_wallets()

    # ------------------------------------------------------------------
    # Wallet config
    # ------------------------------------------------------------------
    def _load_wallets(self):
        try:
            raw = json.loads(CUSTODIAN_WALLETS_PATH.read_text())
            self._wallets = raw.get("wallets", [])
            logger.info("ETFMonitor: loaded %d custodian wallets", len(self._wallets))
        except Exception as exc:
            logger.error("ETFMonitor: failed to load custodian wallets: %s", exc)
            self._wallets = []

    # ------------------------------------------------------------------
    # Mempool balance fetch
    # ------------------------------------------------------------------
    async def _fetch_balance(self, session, address: str) -> int | None:
        """Return total balance in satoshis for *address*, or None on error."""
        url = MEMPOOL_ADDRESS_URL.format(address=address)
        try:
            async with session.get(url, timeout=15) as resp:
                if resp.status != 200:
                    logger.warning("ETFMonitor: mempool %s returned %s", address[:12], resp.status)
                    return None
                data = await resp.json()
                chain = data.get("chain_stats", {})
                mempool = data.get("mempool_stats", {})
                funded = chain.get("funded_txo_sum", 0) + mempool.get("funded_txo_sum", 0)
                spent = chain.get("spent_txo_sum", 0) + mempool.get("spent_txo_sum", 0)
                return funded - spent
        except Exception as exc:
            logger.warning("ETFMonitor: mempool fetch error for %s: %s", address[:12], exc)
            return None

    # ------------------------------------------------------------------
    # Deribit funding rate
    # ------------------------------------------------------------------
    async def _fetch_funding_rate(self, session) -> float:
        now_ms = int(time.time() * 1000)
        start_ms = now_ms - 8 * 3600 * 1000
        params = {
            "instrument_name": "BTC-PERPETUAL",
            "start_timestamp": start_ms,
            "end_timestamp": now_ms,
        }
        try:
            async with session.get(DERIBIT_FUNDING_URL, params=params, timeout=15) as resp:
                if resp.status != 200:
                    logger.warning("ETFMonitor: Deribit returned %s", resp.status)
                    return 0.0
                data = await resp.json()
                return float(data.get("result", 0.0))
        except Exception as exc:
            logger.warning("ETFMonitor: Deribit fetch error: %s", exc)
            return 0.0

    # ------------------------------------------------------------------
    # History management
    # ------------------------------------------------------------------
    def _record_balance(self, address: str, balance_sat: int, ts: float):
        if address not in self._balance_history:
            self._balance_history[address] = []
        self._balance_history[address].append((ts, balance_sat))
        # prune entries older than 24h
        cutoff = ts - HISTORY_WINDOW_S
        self._balance_history[address] = [
            (t, b) for t, b in self._balance_history[address] if t >= cutoff
        ]

    def _compute_delta(self, address: str, now: float) -> int:
        """Return balance change (sat) over the last 6h. Positive = inflow."""
        history = self._balance_history.get(address, [])
        if len(history) < 2:
            return 0
        current_balance = history[-1][1]
        cutoff = now - DELTA_WINDOW_S
        # find the oldest entry within the 6h window (or closest before it)
        baseline = None
        for ts, bal in history:
            if ts <= cutoff:
                baseline = bal
            else:
                break
        if baseline is None:
            # all entries are within 6h — use the oldest one
            baseline = history[0][1]
        return current_balance - baseline

    # ------------------------------------------------------------------
    # Main cycle
    # ------------------------------------------------------------------
    async def run_cycle(self, session, btc_price_usd: float = 0) -> dict:
        now = time.time()
        first_run = len(self._balance_history) == 0

        # Fetch balances for all wallets
        for wallet in self._wallets:
            addr = wallet["address"]
            balance = await self._fetch_balance(session, addr)
            if balance is not None:
                self._record_balance(addr, balance, now)

        # Compute aggregate deltas
        if first_run:
            inflow_sat = 0
            outflow_sat = 0
        else:
            inflow_sat = 0
            outflow_sat = 0
            for wallet in self._wallets:
                addr = wallet["address"]
                delta = self._compute_delta(addr, now)
                if delta > 0:
                    inflow_sat += delta
                elif delta < 0:
                    outflow_sat += abs(delta)

        inflow_btc = inflow_sat / 1e8
        outflow_btc = outflow_sat / 1e8
        net_btc = inflow_btc - outflow_btc
        net_usd = net_btc * btc_price_usd

        if abs(net_btc) < 0.001:
            direction = "neutral"
        elif net_btc > 0:
            direction = "inflow"
        else:
            direction = "outflow"

        # Funding rate
        funding_rate = await self._fetch_funding_rate(session)

        result = {
            "inflow_6h_btc": round(inflow_btc, 8),
            "outflow_6h_btc": round(outflow_btc, 8),
            "net_6h_btc": round(net_btc, 8),
            "net_6h_usd": round(net_usd, 2),
            "net_6h_direction": direction,
            "deribit_funding_rate": funding_rate,
            "wallets_monitored": len(self._wallets),
            "is_proxy": True,
            "updated_at": now,
        }
        self._last_result = result
        return result

    def get_last_result(self) -> dict:
        """Return last known result or zeros if never run."""
        if self._last_result is not None:
            return self._last_result
        return {
            "inflow_6h_btc": 0.0,
            "outflow_6h_btc": 0.0,
            "net_6h_btc": 0.0,
            "net_6h_usd": 0.0,
            "net_6h_direction": "neutral",
            "deribit_funding_rate": 0.0,
            "wallets_monitored": len(self._wallets),
            "is_proxy": True,
            "updated_at": 0,
        }

    # ------------------------------------------------------------------
    # F-P3-5: DeFi BTC Collateralization Monitor
    # ------------------------------------------------------------------

    async def fetch_defi_btc(self, session) -> dict:
        """Fetch WBTC + cbBTC supply from DeFiLlama.

        Returns
        -------
        dict
            wbtc_supply_btc, cbbtc_supply_btc, total_btc_in_defi,
            delta_24h_btc, signal, updated_at
        """
        now = time.time()
        wbtc = await self._fetch_defi_protocol(session, "wrapped-bitcoin")
        cbbtc = await self._fetch_defi_protocol(session, "coinbase-wrapped-btc")

        total = wbtc + cbbtc

        # Compute 24h delta from history
        delta = self._compute_defi_delta(total, now)

        if delta > 100:
            signal = "ACCUMULATING"
        elif delta < -100:
            signal = "DECLINING"
        else:
            signal = "NEUTRAL"

        return {
            "wbtc_supply_btc": round(wbtc, 2),
            "cbbtc_supply_btc": round(cbbtc, 2),
            "total_btc_in_defi": round(total, 2),
            "delta_24h_btc": round(delta, 2),
            "signal": signal,
            "updated_at": now,
        }

    async def _fetch_defi_protocol(self, session, slug: str) -> float:
        """Fetch TVL in BTC terms from DeFiLlama."""
        url = f"https://api.llama.fi/protocol/{slug}"
        try:
            async with session.get(url, timeout=15) as resp:
                if resp.status != 200:
                    return 0.0
                data = await resp.json()
                # currentChainTvls has chain -> USD TVL
                chain_tvls = data.get("currentChainTvls", {})
                eth_tvl = chain_tvls.get("Ethereum", 0)
                # Convert USD to BTC (rough: use ~$80k)
                return eth_tvl / 80000 if eth_tvl else 0.0
        except Exception as e:
            logger.warning("DeFiLlama fetch failed for %s: %s", slug, e)
            return 0.0

    def _compute_defi_delta(self, current_total: float, now: float) -> float:
        """Track DeFi BTC total over time and return 24h delta."""
        if not hasattr(self, '_defi_history'):
            self._defi_history: list[tuple[float, float]] = []

        self._defi_history.append((now, current_total))
        # Keep 48h of history
        cutoff = now - 48 * 3600
        self._defi_history = [(t, v) for t, v in self._defi_history if t >= cutoff]

        # Find value ~24h ago
        target = now - 24 * 3600
        closest = None
        for t, v in self._defi_history:
            if t <= target:
                closest = v
        if closest is not None:
            return current_total - closest
        return 0.0
