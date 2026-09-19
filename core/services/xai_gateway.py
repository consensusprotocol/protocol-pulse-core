"""
xai_gateway.py — Single gateway for ALL Grok/xAI API calls.
=============================================================
Every Grok call in Protocol Pulse MUST go through this gateway.
It enforces daily budget limits, gates search tool usage, provides
graceful degradation, and alerts on budget/error events.

Budget defaults (overridable via data/xai_budget_config.json):
  max_requests_per_day:     400
  max_search_calls_per_day: 40
  max_usd_per_day:          1.00

Two API keys supported:
  XAI_API_KEY        — intel pipeline (story_engine, x_reader, etc.)
  XAI_AUDIT_API_KEY  — trifecta audits (cross_llm_audit.py); falls
                       back to XAI_API_KEY if unset and logs a warning.

Search tools (web_search, x_search) are OFF by default. Only callers
that pass allow_search=True get them attached. Only article generators
for named-person/brand pieces should pass allow_search=True.

When any budget limit is hit, returns a BudgetExceeded result instead
of calling the API. Callers degrade gracefully.

On HTTP 402/429 or budget stop, writes an alert file and sends ONE
Telegram message per day.

Counters persist in data/xai_budget.json with daily auto-reset.
"""

import json
import logging
import os
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock

log = logging.getLogger("xai_gateway")
if not log.handlers:
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(name)s %(levelname)s %(message)s")

BASE_DIR = Path(__file__).resolve().parent.parent.parent  # protocol_pulse/
DATA_DIR = BASE_DIR / "data"
BUDGET_PATH = DATA_DIR / "xai_budget.json"
CONFIG_PATH = DATA_DIR / "xai_budget_config.json"
ALERT_PATH = DATA_DIR / "xai_budget_alert.json"
ENV_PATH = BASE_DIR / ".env"

XAI_CHAT_URL = "https://api.x.ai/v1/chat/completions"
XAI_RESPONSES_URL = "https://api.x.ai/v1/responses"

# xAI list prices (USD per 1M tokens) as of Sept 2026
TOKEN_PRICES = {
    "grok-3":           {"input": 3.00,  "output": 15.00},
    "grok-3-latest":    {"input": 3.00,  "output": 15.00},
    "grok-3-mini":      {"input": 0.30,  "output": 1.50},
    "grok-3-mini-fast": {"input": 0.30,  "output": 1.50},
    "grok-3-fast":      {"input": 3.00,  "output": 15.00},
    "grok-4":           {"input": 3.00,  "output": 15.00},
    "grok-4-latest":    {"input": 3.00,  "output": 15.00},
    "grok-4-0709":      {"input": 3.00,  "output": 15.00},
    "grok-4.3":         {"input": 3.00,  "output": 15.00},
    "grok-2-latest":    {"input": 2.00,  "output": 10.00},
}
SEARCH_COST_PER_CALL = 0.005  # $5.09/1K ≈ $0.005/call

DEFAULT_CONFIG = {
    "max_requests_per_day": 400,
    "max_search_calls_per_day": 40,
    "max_usd_per_day": 1.00,
    "enabled": True,
}

_lock = Lock()
_tg_sent_today = None  # date string of last Telegram alert


# ─── Config ──────────────────────────────────────────────────────────────────

def _load_config():
    cfg = dict(DEFAULT_CONFIG)
    try:
        if CONFIG_PATH.exists():
            cfg.update(json.loads(CONFIG_PATH.read_text()))
    except Exception as e:
        log.warning("bad xai_budget_config.json: %s; using defaults", e)
    return cfg


def _get_key(for_audit=False):
    """Get the appropriate API key. Audit callers get XAI_AUDIT_API_KEY if set."""
    if for_audit:
        audit_key = os.environ.get("XAI_AUDIT_API_KEY", "").strip()
        if audit_key:
            return audit_key
        log.warning("XAI_AUDIT_API_KEY not set; falling back to XAI_API_KEY for audit")
    key = os.environ.get("XAI_API_KEY", "").strip()
    if key:
        return key
    # Try .env file
    try:
        for line in ENV_PATH.read_text().splitlines():
            line = line.strip()
            if line.startswith("XAI_API_KEY=") and not line.startswith("#"):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    except Exception:
        pass
    return ""


# ─── Budget counters ─────────────────────────────────────────────────────────

def _today_str():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _load_budget():
    try:
        if BUDGET_PATH.exists():
            data = json.loads(BUDGET_PATH.read_text())
            if data.get("date") == _today_str():
                return data
    except Exception:
        pass
    # Reset for new day
    return {
        "date": _today_str(),
        "requests": 0,
        "search_calls": 0,
        "est_usd": 0.0,
        "blocked_requests": 0,
        "errors_402": 0,
        "errors_429": 0,
    }


def _save_budget(data):
    try:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        BUDGET_PATH.write_text(json.dumps(data, indent=2))
    except Exception as e:
        log.warning("failed to save budget: %s", e)


def _estimate_cost(model, input_tokens, output_tokens, search_calls):
    prices = TOKEN_PRICES.get(model, TOKEN_PRICES.get("grok-3"))
    cost = (input_tokens * prices["input"] + output_tokens * prices["output"]) / 1_000_000
    cost += search_calls * SEARCH_COST_PER_CALL
    return round(cost, 6)


# ─── Telegram alert ──────────────────────────────────────────────────────────

def _send_telegram(message):
    global _tg_sent_today
    today = _today_str()
    if _tg_sent_today == today:
        log.info("Telegram alert already sent today; skipping")
        return
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "").strip()
    if not token or not chat_id:
        log.warning("Telegram creds missing; alert not sent: %s", message[:80])
        return
    try:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        payload = json.dumps({"chat_id": chat_id, "text": message}).encode()
        req = urllib.request.Request(url, data=payload,
                                    headers={"Content-Type": "application/json"})
        urllib.request.urlopen(req, timeout=15)
        _tg_sent_today = today
        log.info("Telegram alert sent")
    except Exception as e:
        log.warning("Telegram send failed: %s", e)


def _write_alert(reason, budget_data):
    try:
        alert = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "reason": reason,
            "budget": budget_data,
        }
        ALERT_PATH.write_text(json.dumps(alert, indent=2))
    except Exception as e:
        log.warning("failed to write alert file: %s", e)


# ─── BudgetExceeded result ───────────────────────────────────────────────────

class BudgetExceeded:
    """Returned instead of API response when budget is hit.
    Callers check: if isinstance(result, BudgetExceeded): degrade gracefully.
    """
    def __init__(self, reason, budget_data):
        self.reason = reason
        self.budget = budget_data
        self.text = ""
        self.usage = {}

    def __repr__(self):
        return f"BudgetExceeded({self.reason})"

    def __bool__(self):
        return False


# ─── Main API ────────────────────────────────────────────────────────────────

def chat(messages, model="grok-3-mini-fast", max_tokens=2000, temperature=0.3,
         allow_search=False, search_tools=None, for_audit=False,
         timeout=60, dry_run=False):
    """Send a chat completion request through the gateway.

    Args:
        messages: list of {role, content} dicts
        model: Grok model name
        max_tokens: max completion tokens
        temperature: sampling temperature
        allow_search: if True, attach search_tools (web_search/x_search)
        search_tools: list of tool dicts, e.g. [{"type": "web_search"}]
                      Only used when allow_search=True
        for_audit: if True, use XAI_AUDIT_API_KEY
        timeout: request timeout in seconds
        dry_run: if True, count against budget but don't call API

    Returns:
        str (response text) on success
        BudgetExceeded on budget hit
        None on API error
    """
    cfg = _load_config()
    if not cfg.get("enabled"):
        log.warning("xAI gateway disabled via config")
        return BudgetExceeded("gateway_disabled", {})

    with _lock:
        budget = _load_budget()

        # Count search calls
        n_search = 0
        actual_tools = None
        if allow_search and search_tools:
            actual_tools = search_tools
            n_search = len(search_tools)

        # Budget checks
        if budget["requests"] >= cfg["max_requests_per_day"]:
            budget["blocked_requests"] += 1
            _save_budget(budget)
            reason = f"max_requests_per_day ({cfg['max_requests_per_day']}) exceeded"
            _write_alert(reason, budget)
            _send_telegram(f"[xAI BUDGET] {reason}. Day total: {budget['requests']} req, ${budget['est_usd']:.2f}")
            return BudgetExceeded(reason, budget)

        if n_search > 0 and budget["search_calls"] + n_search > cfg["max_search_calls_per_day"]:
            budget["blocked_requests"] += 1
            _save_budget(budget)
            reason = f"max_search_calls_per_day ({cfg['max_search_calls_per_day']}) exceeded"
            _write_alert(reason, budget)
            _send_telegram(f"[xAI BUDGET] {reason}. Day total: {budget['search_calls']} searches, ${budget['est_usd']:.2f}")
            return BudgetExceeded(reason, budget)

        if budget["est_usd"] >= cfg["max_usd_per_day"]:
            budget["blocked_requests"] += 1
            _save_budget(budget)
            reason = f"max_usd_per_day (${cfg['max_usd_per_day']:.2f}) exceeded"
            _write_alert(reason, budget)
            _send_telegram(f"[xAI BUDGET] {reason}. Day total: ${budget['est_usd']:.2f}")
            return BudgetExceeded(reason, budget)

        # Pre-increment counters
        budget["requests"] += 1
        budget["search_calls"] += n_search
        _save_budget(budget)

    if dry_run:
        est = _estimate_cost(model, 1000, 500, n_search)
        with _lock:
            budget = _load_budget()
            budget["est_usd"] += est
            _save_budget(budget)
        return f"[DRY_RUN] model={model} search={n_search} est_cost=${est:.4f}"

    key = _get_key(for_audit=for_audit)
    if not key:
        log.error("No XAI API key available")
        return None

    body = {
        "model": model,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
    }
    if actual_tools:
        body["tools"] = actual_tools

    try:
        req = urllib.request.Request(
            XAI_CHAT_URL,
            data=json.dumps(body).encode(),
            headers={
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json",
            },
        )
        resp = urllib.request.urlopen(req, timeout=timeout)
        data = json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        code = e.code
        detail = ""
        try:
            detail = e.read().decode()[:300]
        except Exception:
            pass
        log.error("xAI HTTP %s: %s", code, detail)
        with _lock:
            budget = _load_budget()
            if code == 402:
                budget["errors_402"] += 1
            elif code == 429:
                budget["errors_429"] += 1
            _save_budget(budget)
            _write_alert(f"HTTP {code}", budget)
            _send_telegram(f"[xAI ERROR] HTTP {code} on {model}. Budget: ${budget['est_usd']:.2f}/{cfg['max_usd_per_day']:.2f}")
        return None
    except Exception as e:
        log.error("xAI request failed: %s", e)
        return None

    # Extract response text
    text = ""
    usage = data.get("usage", {}) or {}
    for choice in data.get("choices", []):
        msg = choice.get("message", {})
        text += msg.get("content", "") or ""

    # Update cost estimate
    input_tokens = usage.get("prompt_tokens", 0) or usage.get("input_tokens", 0)
    output_tokens = usage.get("completion_tokens", 0) or usage.get("output_tokens", 0)
    est = _estimate_cost(model, input_tokens, output_tokens, n_search)
    with _lock:
        budget = _load_budget()
        budget["est_usd"] += est
        _save_budget(budget)
        if budget["est_usd"] >= cfg["max_usd_per_day"]:
            _write_alert(f"USD ceiling hit after request", budget)
            _send_telegram(f"[xAI BUDGET] Daily USD ceiling hit: ${budget['est_usd']:.2f}/{cfg['max_usd_per_day']:.2f}")

    return text


def responses(input_content, model="grok-4.3", allow_search=False,
              search_tools=None, for_audit=False, timeout=80, dry_run=False):
    """Send a request to the /v1/responses endpoint (Agent Tools API).

    Args:
        input_content: string or list of message dicts
        model: Grok model name
        allow_search: if True, attach search_tools
        search_tools: list of tool dicts, e.g. [{"type": "x_search"}]
        for_audit: if True, use XAI_AUDIT_API_KEY
        timeout: request timeout in seconds
        dry_run: if True, count against budget but don't call API

    Returns:
        tuple (text, raw_data) on success
        BudgetExceeded on budget hit
        (None, {}) on API error
    """
    cfg = _load_config()
    if not cfg.get("enabled"):
        return BudgetExceeded("gateway_disabled", {})

    with _lock:
        budget = _load_budget()
        n_search = 0
        actual_tools = None
        if allow_search and search_tools:
            actual_tools = search_tools
            n_search = len(search_tools)

        if budget["requests"] >= cfg["max_requests_per_day"]:
            budget["blocked_requests"] += 1
            _save_budget(budget)
            reason = f"max_requests_per_day ({cfg['max_requests_per_day']}) exceeded"
            _write_alert(reason, budget)
            _send_telegram(f"[xAI BUDGET] {reason}")
            return BudgetExceeded(reason, budget)

        if n_search > 0 and budget["search_calls"] + n_search > cfg["max_search_calls_per_day"]:
            budget["blocked_requests"] += 1
            _save_budget(budget)
            reason = f"max_search_calls_per_day ({cfg['max_search_calls_per_day']}) exceeded"
            _write_alert(reason, budget)
            _send_telegram(f"[xAI BUDGET] {reason}")
            return BudgetExceeded(reason, budget)

        if budget["est_usd"] >= cfg["max_usd_per_day"]:
            budget["blocked_requests"] += 1
            _save_budget(budget)
            reason = f"max_usd_per_day (${cfg['max_usd_per_day']:.2f}) exceeded"
            _write_alert(reason, budget)
            _send_telegram(f"[xAI BUDGET] {reason}")
            return BudgetExceeded(reason, budget)

        budget["requests"] += 1
        budget["search_calls"] += n_search
        _save_budget(budget)

    if dry_run:
        est = _estimate_cost(model, 1000, 500, n_search)
        with _lock:
            budget = _load_budget()
            budget["est_usd"] += est
            _save_budget(budget)
        return f"[DRY_RUN] model={model} search={n_search}", {}

    key = _get_key(for_audit=for_audit)
    if not key:
        log.error("No XAI API key available")
        return None, {}

    body = {"model": model, "input": input_content}
    if actual_tools:
        body["tools"] = actual_tools

    try:
        req = urllib.request.Request(
            XAI_RESPONSES_URL,
            data=json.dumps(body).encode(),
            headers={
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json",
            },
        )
        resp = urllib.request.urlopen(req, timeout=timeout)
        data = json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        code = e.code
        log.error("xAI HTTP %s on /responses", code)
        with _lock:
            budget = _load_budget()
            if code == 402:
                budget["errors_402"] += 1
            elif code == 429:
                budget["errors_429"] += 1
            _save_budget(budget)
            _write_alert(f"HTTP {code} on /responses", budget)
            _send_telegram(f"[xAI ERROR] HTTP {code} on {model} (/responses)")
        return None, {}
    except Exception as e:
        log.error("xAI /responses failed: %s", e)
        return None, {}

    usage = data.get("usage", {}) or {}
    input_tokens = usage.get("input_tokens", 0)
    output_tokens = usage.get("output_tokens", 0)
    est = _estimate_cost(model, input_tokens, output_tokens, n_search)

    with _lock:
        budget = _load_budget()
        budget["est_usd"] += est
        _save_budget(budget)

    # Extract text from Agent Tools response
    text = ""
    for item in data.get("output", []):
        if item.get("type") == "message":
            for c in item.get("content", []):
                if c.get("type") in ("output_text", "text"):
                    text += c.get("text", "")

    return text, data


def status():
    """Return current budget status for watchdog/dashboard consumption."""
    cfg = _load_config()
    with _lock:
        budget = _load_budget()
    return {
        "date": budget.get("date"),
        "requests": budget.get("requests", 0),
        "max_requests": cfg["max_requests_per_day"],
        "search_calls": budget.get("search_calls", 0),
        "max_search_calls": cfg["max_search_calls_per_day"],
        "est_usd": budget.get("est_usd", 0),
        "max_usd": cfg["max_usd_per_day"],
        "blocked": budget.get("blocked_requests", 0),
        "errors_402": budget.get("errors_402", 0),
        "errors_429": budget.get("errors_429", 0),
        "enabled": cfg.get("enabled", True),
        "pct_requests": round(budget.get("requests", 0) / max(cfg["max_requests_per_day"], 1) * 100, 1),
        "pct_usd": round(budget.get("est_usd", 0) / max(cfg["max_usd_per_day"], 0.01) * 100, 1),
    }


# ─── CLI smoke test ──────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    if "--status" in sys.argv:
        print(json.dumps(status(), indent=2))
    elif "--dry-run" in sys.argv:
        r = chat([{"role": "user", "content": "test"}], dry_run=True)
        print(r)
        print(json.dumps(status(), indent=2))
    else:
        r = chat([{"role": "user", "content": "Reply with ALIVE"}],
                 model="grok-3-mini-fast", max_tokens=10)
        print(f"Response: {r}")
        print(json.dumps(status(), indent=2))
