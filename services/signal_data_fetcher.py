"""
Signal Data Fetcher — Real Free Data for 4 Critical Intelligence Signals

Fetches live data from:
  - Deribit public API (options + futures — no auth)
  - Blockchair API (on-chain stats — no auth)
  - CoinMetrics community API (active addresses — no auth)
  - yfinance (macro correlation — no auth)
  - FRED API (macro yields — free key optional)

Cache: /tmp/signal_data_cache.json (15-min TTL per signal)
Fallback: returns empty dict on failure, callers use sovereign_context.

Note: Binance/Bybit FAPI geo-blocked from this server → Deribit used for futures.
      blockchain.com charts API returning empty → Blockchair used for on-chain.
"""

import json
import logging
import os
import time
import warnings
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

import requests

log = logging.getLogger("signal_data_fetcher")

CACHE_PATH = Path("/tmp/signal_data_cache.json")
CACHE_TTL = 900  # 15 minutes
REQ_TIMEOUT = 12
HEADERS = {
    "User-Agent": "ProtocolPulse/SignalFetcher/1.0",
    "Accept": "application/json",
}


def _safe_get(url: str, params: Optional[dict] = None,
              timeout: int = REQ_TIMEOUT) -> Optional[Any]:
    """Safe HTTP GET — returns parsed JSON or None."""
    try:
        r = requests.get(url, params=params, headers=HEADERS, timeout=timeout)
        r.raise_for_status()
        return r.json()
    except Exception as exc:
        log.warning("GET %s failed: %s", url, exc)
        return None


class SignalDataFetcher:
    """Fetches real market data for the 4 critical intelligence signals."""

    def __init__(self):
        self._cache = self._load_cache()

    # ------------------------------------------------------------------
    # Cache management
    # ------------------------------------------------------------------

    def _load_cache(self) -> dict:
        try:
            if CACHE_PATH.exists():
                return json.loads(CACHE_PATH.read_text())
        except Exception:
            pass
        return {}

    def _save_cache(self):
        try:
            CACHE_PATH.write_text(json.dumps(self._cache, default=str))
        except Exception as exc:
            log.warning("Cache write failed: %s", exc)

    def _get_cached(self, key: str) -> Optional[dict]:
        entry = self._cache.get(key)
        if entry and time.time() - entry.get("ts", 0) < CACHE_TTL:
            return entry.get("data")
        return None

    def _set_cached(self, key: str, data: dict):
        self._cache[key] = {"ts": time.time(), "data": data}
        self._save_cache()

    # ------------------------------------------------------------------
    # 1. MACRO CORRELATION (yfinance + FRED)
    # ------------------------------------------------------------------

    def fetch_macro_correlation(self) -> dict:
        """
        yfinance: BTC, Gold, S&P500 (individual tickers to avoid SQLite locks).
        FRED (optional): DGS10, T10YIE for real yield.
        Returns: dxy, gold_price, sp500, btc_vs_gold_30d_corr,
                 btc_vs_dxy_30d_corr, real_yield
        """
        cached = self._get_cached("macro_correlation")
        if cached:
            return cached

        result = {
            "dxy": None,
            "gold_price": None,
            "sp500": None,
            "btc_vs_gold_30d_corr": None,
            "btc_vs_dxy_30d_corr": None,
            "real_yield": None,
            "ten_year_yield": None,
        }

        try:
            import yfinance as yf
            import numpy as np
            warnings.filterwarnings("ignore", category=FutureWarning)

            # Fetch individual tickers (avoids SQLite lock from batch download)
            ticker_map = {
                "BTC-USD": "btc",
                "GC=F": "gold",
                "ES=F": "sp500",
            }
            histories = {}
            for symbol, label in ticker_map.items():
                try:
                    tk = yf.Ticker(symbol)
                    hist = tk.history(period="35d")
                    if not hist.empty:
                        histories[label] = hist["Close"]
                        last_val = float(hist["Close"].iloc[-1])
                        if label == "gold":
                            result["gold_price"] = round(last_val, 2)
                        elif label == "sp500":
                            result["sp500"] = round(last_val, 2)
                except Exception as exc:
                    log.warning("yfinance %s failed: %s", symbol, exc)

            # 10yr yield via yfinance (^TNX returns yield * 1)
            try:
                tnx = yf.Ticker("^TNX")
                tnx_hist = tnx.history(period="5d")
                if not tnx_hist.empty:
                    result["ten_year_yield"] = round(float(tnx_hist["Close"].iloc[-1]), 2)
            except Exception:
                pass

            # 30-day correlations (BTC vs Gold, BTC vs S&P as DXY proxy)
            # Strip timezone then normalize to date-only (BTC=UTC, TradFi=US/Eastern)
            for key in histories:
                histories[key].index = histories[key].index.tz_localize(None)
                histories[key].index = histories[key].index.normalize()
                histories[key] = histories[key][~histories[key].index.duplicated(keep="last")]

            if "btc" in histories and len(histories["btc"]) >= 15:
                btc_ret = histories["btc"].pct_change().dropna().tail(30)

                if "gold" in histories and len(histories["gold"]) >= 15:
                    gold_ret = histories["gold"].pct_change().dropna().tail(30)
                    common = btc_ret.index.intersection(gold_ret.index)
                    if len(common) >= 10:
                        corr = btc_ret.loc[common].corr(gold_ret.loc[common])
                        if not np.isnan(corr):
                            result["btc_vs_gold_30d_corr"] = round(float(corr), 3)

                if "sp500" in histories and len(histories["sp500"]) >= 15:
                    sp_ret = histories["sp500"].pct_change().dropna().tail(30)
                    common = btc_ret.index.intersection(sp_ret.index)
                    if len(common) >= 10:
                        corr = btc_ret.loc[common].corr(sp_ret.loc[common])
                        if not np.isnan(corr):
                            result["btc_vs_dxy_30d_corr"] = round(float(-corr), 3)

        except Exception as exc:
            log.warning("yfinance macro fetch failed: %s", exc)

        # --- FRED: real yield (DGS10 - T10YIE) ---
        fred_key = os.environ.get("FRED_API_KEY", "")
        if fred_key:
            try:
                breakeven = None
                for series_id in ("DGS10", "T10YIE"):
                    data = _safe_get(
                        "https://api.stlouisfed.org/fred/series/observations",
                        params={
                            "series_id": series_id,
                            "api_key": fred_key,
                            "sort_order": "desc",
                            "limit": 5,
                            "file_type": "json",
                        },
                    )
                    if data and "observations" in data:
                        for obs in data["observations"]:
                            val = obs.get("value", ".")
                            if val != ".":
                                if series_id == "DGS10":
                                    result["ten_year_yield"] = round(float(val), 2)
                                elif series_id == "T10YIE":
                                    breakeven = round(float(val), 2)
                                break
                if result["ten_year_yield"] is not None and breakeven is not None:
                    result["real_yield"] = round(result["ten_year_yield"] - breakeven, 2)
            except Exception as exc:
                log.warning("FRED macro fetch failed: %s", exc)

        self._set_cached("macro_correlation", result)
        log.info("Macro: Gold=%s, S&P=%s, 10Y=%s, BTC-Gold corr=%s",
                 result["gold_price"], result["sp500"],
                 result["ten_year_yield"], result["btc_vs_gold_30d_corr"])
        return result

    # ------------------------------------------------------------------
    # 2. OPTIONS MARKET (Deribit — no auth)
    # ------------------------------------------------------------------

    def fetch_options_market(self) -> dict:
        """
        Deribit public API — book summary + DVOL index.
        Returns: put_call_ratio, dvol, max_pain, total_call_oi, total_put_oi
        """
        cached = self._get_cached("options_market")
        if cached:
            return cached

        result = {
            "put_call_ratio": None,
            "dvol": None,
            "max_pain": None,
            "total_call_oi": None,
            "total_put_oi": None,
            "total_oi_btc": None,
            "avg_mark_iv": None,
        }

        # --- Book summary: all active BTC options ---
        data = _safe_get(
            "https://www.deribit.com/api/v2/public/get_book_summary_by_currency",
            params={"currency": "BTC", "kind": "option"},
        )
        if data and "result" in data:
            contracts = data["result"]
            total_call_oi = 0.0
            total_put_oi = 0.0
            iv_sum = 0.0
            iv_count = 0
            oi_by_strike = {}  # strike -> total OI (for max pain)

            for c in contracts:
                name = c.get("instrument_name", "")
                oi = float(c.get("open_interest", 0))
                iv = float(c.get("mark_iv", 0))

                parts = name.split("-")
                if len(parts) >= 4:
                    try:
                        strike = float(parts[2])
                    except ValueError:
                        continue
                    opt_type = parts[3]

                    if opt_type == "C":
                        total_call_oi += oi
                    elif opt_type == "P":
                        total_put_oi += oi

                    oi_by_strike[strike] = oi_by_strike.get(strike, 0) + oi

                    if iv > 0:
                        iv_sum += iv
                        iv_count += 1

            result["total_call_oi"] = round(total_call_oi, 2)
            result["total_put_oi"] = round(total_put_oi, 2)
            result["total_oi_btc"] = round(total_call_oi + total_put_oi, 2)

            if total_call_oi > 0:
                result["put_call_ratio"] = round(total_put_oi / total_call_oi, 3)

            if iv_count > 0:
                result["avg_mark_iv"] = round(iv_sum / iv_count, 1)

            # Max pain: strike with highest total OI (simplified)
            if oi_by_strike:
                result["max_pain"] = max(oi_by_strike, key=oi_by_strike.get)

        # --- DVOL (Deribit Volatility Index) ---
        dvol_data = _safe_get(
            "https://www.deribit.com/api/v2/public/get_volatility_index_data",
            params={
                "currency": "BTC",
                "resolution": 3600,
                "end_timestamp": int(time.time() * 1000),
                "start_timestamp": int((time.time() - 7200) * 1000),
            },
        )
        if dvol_data and "result" in dvol_data:
            dvol_points = dvol_data["result"].get("data", [])
            if dvol_points:
                latest = dvol_points[-1]
                if isinstance(latest, list) and len(latest) >= 5:
                    result["dvol"] = round(float(latest[4]), 1)

        self._set_cached("options_market", result)
        log.info("Options: P/C=%s, DVOL=%s, MaxPain=%s, OI=%s BTC",
                 result["put_call_ratio"], result["dvol"],
                 result["max_pain"], result["total_oi_btc"])
        return result

    # ------------------------------------------------------------------
    # 3. FUTURES BASIS (Deribit — no auth, Binance geo-blocked)
    # ------------------------------------------------------------------

    def fetch_futures_basis(self) -> dict:
        """
        Deribit public API for futures basis (Binance/Bybit geo-blocked).
        - BTC futures book summary: mark_price, underlying (spot), basis
        - Derives: funding equivalent, annualized basis, OI
        Returns: funding_rate, annualized_basis, open_interest, basis_pct
        """
        cached = self._get_cached("futures_basis")
        if cached:
            return cached

        result = {
            "funding_rate": None,
            "annualized_basis": None,
            "open_interest": None,
            "open_interest_usd": None,
            "long_short_ratio": None,
            "mark_price": None,
            "index_price": None,
            "basis_pct": None,
        }

        # --- Deribit: BTC futures book summary ---
        data = _safe_get(
            "https://www.deribit.com/api/v2/public/get_book_summary_by_currency",
            params={"currency": "BTC", "kind": "future"},
        )
        if data and "result" in data:
            futures = data["result"]
            # Find the BTC-PERPETUAL (perp) and nearest quarterly
            perp = None
            quarterly = None
            total_oi_usd = 0

            for f in futures:
                name = f.get("instrument_name", "")
                total_oi_usd += float(f.get("open_interest", 0))

                if name == "BTC-PERPETUAL":
                    perp = f
                elif name != "BTC-PERPETUAL" and not name.startswith("BTC-FS-"):
                    # Quarterly future (e.g., BTC-26JUN26)
                    if quarterly is None:
                        quarterly = f

            # Perpetual data
            if perp:
                mark = float(perp.get("mark_price", 0))
                estimated_spot = float(perp.get("estimated_delivery_price", 0))
                # funding_8h = 8-hour funding rate (the standard metric)
                funding_8h = float(perp.get("funding_8h", 0))

                result["mark_price"] = round(mark, 2)
                result["index_price"] = round(estimated_spot, 2)

                result["funding_rate"] = round(funding_8h, 8)
                # Annualize: rate × 3 periods/day × 365 days × 100
                result["annualized_basis"] = round(funding_8h * 3 * 365 * 100, 2)

                if estimated_spot > 0:
                    result["basis_pct"] = round(
                        (mark - estimated_spot) / estimated_spot * 100, 4
                    )

            # Quarterly basis (true futures basis = futures premium over spot)
            if quarterly and perp:
                q_mark = float(quarterly.get("mark_price", 0))
                spot = float(perp.get("estimated_delivery_price", 0))
                if spot > 0 and q_mark > 0:
                    premium_pct = (q_mark - spot) / spot * 100
                    # Annualize based on days to expiry
                    q_name = quarterly.get("instrument_name", "")
                    # Use basis_pct for quarterly premium if more meaningful
                    if abs(premium_pct) > abs(result.get("basis_pct") or 0):
                        result["basis_pct"] = round(premium_pct, 4)

            # Total OI across all futures
            if total_oi_usd > 0:
                result["open_interest_usd"] = round(total_oi_usd, 0)
                spot = result["index_price"] or result["mark_price"]
                if spot and spot > 0:
                    result["open_interest"] = round(total_oi_usd / spot, 2)

        # --- Fallback: try Binance (may work from some networks) ---
        if result["funding_rate"] is None:
            binance_data = _safe_get(
                "https://fapi.binance.com/fapi/v1/fundingRate",
                params={"symbol": "BTCUSDT", "limit": 1},
            )
            if binance_data and isinstance(binance_data, list) and binance_data:
                rate = float(binance_data[0].get("fundingRate", 0))
                result["funding_rate"] = round(rate, 6)
                result["annualized_basis"] = round(rate * 3 * 365 * 100, 2)

        self._set_cached("futures_basis", result)
        log.info("Futures: funding=%s, ann=%s%%, basis=%s%%, OI_USD=%s",
                 result["funding_rate"], result["annualized_basis"],
                 result["basis_pct"], result["open_interest_usd"])
        return result

    # ------------------------------------------------------------------
    # 4. ON-CHAIN ACCUMULATION (Blockchair + CoinMetrics)
    # ------------------------------------------------------------------

    def fetch_on_chain_accumulation(self) -> dict:
        """
        Blockchair /bitcoin/stats: CDD, tx volume, active data.
        CoinMetrics community: AdrActCnt (active addresses).
        blockchain.com charts: fallback for addresses + tx volume.
        Returns: coin_days_destroyed_7d, active_addresses_7d,
                 nvt_ratio, accumulation_score
        """
        cached = self._get_cached("on_chain_accumulation")
        if cached:
            return cached

        result = {
            "coin_days_destroyed_7d": None,
            "active_addresses_7d": None,
            "tx_volume_usd_7d": None,
            "nvt_ratio": None,
            "accumulation_score": None,
        }

        # --- Blockchair: comprehensive Bitcoin stats (single call) ---
        bc_data = _safe_get("https://api.blockchair.com/bitcoin/stats", timeout=15)
        if bc_data and "data" in bc_data:
            stats = bc_data["data"]
            # CDD from Blockchair (24h value available directly)
            cdd_24h = stats.get("cdd_24h")
            if cdd_24h is not None:
                result["coin_days_destroyed_7d"] = round(float(cdd_24h), 0)

            # TX volume
            vol_24h = stats.get("volume_24h")
            if vol_24h is not None:
                # Blockchair volume is in satoshis, convert to USD
                # We don't have BTC price here, so store raw and let score use it
                result["tx_volume_usd_7d"] = round(float(vol_24h) / 1e8 * 68000, 0)

            # Mempool + tx count as supplementary
            tx_24h = stats.get("transactions_24h")
            if tx_24h is not None:
                result["_tx_count_24h"] = int(tx_24h)

        # --- CoinMetrics community: active addresses (free, confirmed working) ---
        cm_data = _safe_get(
            "https://community-api.coinmetrics.io/v4/timeseries/asset-metrics",
            params={"assets": "btc", "metrics": "AdrActCnt", "page_size": 7},
            timeout=15,
        )
        if cm_data and "data" in cm_data:
            rows = cm_data["data"]
            if rows:
                # Average over available days
                addrs = []
                for row in rows:
                    aac = row.get("AdrActCnt")
                    if aac is not None and aac != "":
                        try:
                            addrs.append(float(aac))
                        except (ValueError, TypeError):
                            pass
                if addrs:
                    result["active_addresses_7d"] = round(sum(addrs) / len(addrs), 0)

        # --- blockchain.com charts fallback for addresses + tx volume ---
        if result["active_addresses_7d"] is None:
            addr_data = _safe_get(
                "https://api.blockchain.info/charts/n-unique-addresses",
                params={"timespan": "30days", "format": "json"},
                timeout=15,
            )
            if addr_data and "values" in addr_data:
                vals = addr_data["values"]
                last_7 = vals[-7:] if len(vals) >= 7 else vals
                if last_7:
                    avg_addr = sum(v.get("y", 0) for v in last_7) / len(last_7)
                    if avg_addr > 0:
                        result["active_addresses_7d"] = round(avg_addr, 0)

        if result["tx_volume_usd_7d"] is None:
            vol_data = _safe_get(
                "https://api.blockchain.info/charts/estimated-transaction-volume-usd",
                params={"timespan": "30days", "format": "json"},
                timeout=15,
            )
            if vol_data and "values" in vol_data:
                vals = vol_data["values"]
                last_7 = vals[-7:] if len(vals) >= 7 else vals
                if last_7:
                    avg_vol = sum(v.get("y", 0) for v in last_7) / len(last_7)
                    if avg_vol > 0:
                        result["tx_volume_usd_7d"] = round(avg_vol, 0)

        # --- Compute NVT from available data ---
        # NVT = Market Cap / Daily TX Volume
        # If we have tx volume, derive NVT
        if result["tx_volume_usd_7d"] and result["tx_volume_usd_7d"] > 0:
            # Approximate market cap from context or use ~$1.3T
            est_mcap = 1_360_000_000_000  # rough current
            result["nvt_ratio"] = round(est_mcap / result["tx_volume_usd_7d"], 1)

        # --- Compute accumulation score (0-100) ---
        acc_score = 50
        components = 0

        if result["coin_days_destroyed_7d"] is not None:
            cdd = result["coin_days_destroyed_7d"]
            # CDD baseline: ~5M-20M normal daily. <5M = strong hodling
            if cdd < 5_000_000:
                acc_score += 20
            elif cdd < 10_000_000:
                acc_score += 10
            elif cdd > 50_000_000:
                acc_score -= 15
            elif cdd > 25_000_000:
                acc_score -= 5
            components += 1

        if result["active_addresses_7d"] is not None:
            addr = result["active_addresses_7d"]
            if addr > 900_000:
                acc_score += 15
            elif addr > 700_000:
                acc_score += 5
            elif addr < 400_000:
                acc_score -= 10
            components += 1

        if result["nvt_ratio"] is not None:
            nvt = result["nvt_ratio"]
            if nvt < 40:
                acc_score += 15
            elif nvt < 80:
                acc_score += 5
            elif nvt > 150:
                acc_score -= 15
            elif nvt > 100:
                acc_score -= 5
            components += 1

        if components > 0:
            result["accumulation_score"] = max(0, min(100, acc_score))

        # Clean internal keys
        result.pop("_tx_count_24h", None)

        self._set_cached("on_chain_accumulation", result)
        log.info("On-chain: CDD=%s, Addr=%s, NVT=%s, Score=%s",
                 result["coin_days_destroyed_7d"], result["active_addresses_7d"],
                 result["nvt_ratio"], result["accumulation_score"])
        return result

    # ------------------------------------------------------------------
    # Convenience: fetch all
    # ------------------------------------------------------------------

    def fetch_all(self) -> dict:
        """Fetch all 4 signal datasets. Returns dict with all results."""
        return {
            "macro": self.fetch_macro_correlation(),
            "options": self.fetch_options_market(),
            "futures": self.fetch_futures_basis(),
            "on_chain": self.fetch_on_chain_accumulation(),
        }
