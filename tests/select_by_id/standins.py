#!/usr/bin/env python3
"""Proof-only stand-ins for the local gemma3:27b behind select_by_id.Model (GPU0 is leased to the live run; this
session never calls Ollama). Keys are read by name from the env file inside code and never printed or logged. Each
stand-in prices its usage at an assumed UPPER BOUND and adds it to one cumulative spend ledger; at limit_usd every
further call raises SpendLimit (the order's ~$40 guard).

  OpenAIStandIn     gpt-6.1-sol (the order's named stand-in; its account ran out of credit about 01:20 ET Nov 12: HTTP 429
                    insufficient_quota / credit_balance_exhausted; it answered again from 02:07 ET)
  AnthropicStandIn  claude-opus-5-5 (the 01:44 substitute), then claude-fable-5-2 (the orchestrator's 02:00 note: the
                    generator while OpenAI is out), streaming, adaptive effort
  GrokJudge         the blind judge for ModelChecks on another vendor (orchestrator 02:00): the current Grok reasoning
                    model on XAI_API_KEY_MEDLEY, told it has no tools and must answer in one message
  GeminiStandIn     kept for completeness, never used: GEMINI_API_KEY is not in the permitted env file
Spend is accounted per successful reply from the provider's own usage counts (failed HTTP calls are not billed); the
guard reads the ledger under the same lock the writers take, so parallel proof processes cannot overshoot unseen.
"""
import json
import os
import sys
import time
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(HERE)), "pipeline"))
from select_by_id import Model, ModelError, SpendLimit  # noqa: E402

BACKOFF_S = (20, 40, 80, 160)          # rate limits / server errors only; an exhausted account is final
try:
    import httpx
    _TRANSPORT = (OSError, TimeoutError, httpx.HTTPError)
except ImportError:                    # pragma: no cover
    _TRANSPORT = (OSError, TimeoutError)


def env_value(path, name):
    """One key's value from an env file, read by name inside code (never printed or logged)."""
    try:
        with open(path) as f:
            for line in f:
                k, sep, v = line.strip().partition("=")
                k = k.strip()
                k = k[len("export "):].strip() if k.startswith("export ") else k
                if sep and k == name:
                    return v.strip().strip('"').strip("'")
    except OSError:
        pass
    return None


class _Spend:
    PRICE_IN = PRICE_OUT = 0.0

    def __init__(self, spend_path, limit_usd):
        self.spend_path, self.limit_usd = spend_path, limit_usd

    def spent(self):
        try:
            with open(self.spend_path) as f:
                return float(json.load(f).get("usd_estimate", 0.0))
        except (OSError, ValueError):
            return 0.0

    def guard(self):
        import fcntl
        os.makedirs(os.path.dirname(self.spend_path), exist_ok=True)
        with open(self.spend_path + ".lock", "w") as lk:
            fcntl.flock(lk, fcntl.LOCK_SH)              # the writers' lock (audit C2, sonnet B N6)
            spent = self.spent()
        if spent >= self.limit_usd:
            raise SpendLimit(f"stand-in spend estimate {spent:.2f} USD >= {self.limit_usd} USD")

    def account(self, prompt_tokens, completion_tokens):
        import fcntl
        os.makedirs(os.path.dirname(self.spend_path), exist_ok=True)
        with open(self.spend_path + ".lock", "w") as lk:
            fcntl.flock(lk, fcntl.LOCK_EX)              # parallel proof processes share one ledger
            self._account(prompt_tokens, completion_tokens)

    def _account(self, prompt_tokens, completion_tokens):
        d = {"usd_estimate": 0.0, "calls": 0, "prompt_tokens": 0, "completion_tokens": 0, "by_model": {}}
        try:
            with open(self.spend_path) as f:
                d.update(json.load(f))
        except (OSError, ValueError):
            pass
        cost = prompt_tokens * self.PRICE_IN / 1e6 + completion_tokens * self.PRICE_OUT / 1e6
        m = d.setdefault("by_model", {}).setdefault(self.name, {"calls": 0, "usd_estimate": 0.0,
                                                                "price_usd_per_1m": [self.PRICE_IN, self.PRICE_OUT]})
        m.update(calls=m["calls"] + 1, usd_estimate=round(m["usd_estimate"] + cost, 4))
        d.update(calls=d["calls"] + 1, prompt_tokens=d["prompt_tokens"] + prompt_tokens,
                 completion_tokens=d["completion_tokens"] + completion_tokens,
                 usd_estimate=round(d["usd_estimate"] + cost, 4))
        os.makedirs(os.path.dirname(self.spend_path), exist_ok=True)
        tmp = f"{self.spend_path}.{os.getpid()}.tmp"
        with open(tmp, "w") as f:
            json.dump(d, f, indent=1)
        os.replace(tmp, self.spend_path)


class OpenAIStandIn(_Spend, Model):
    PRICE_IN, PRICE_OUT = 15.0, 120.0

    def __init__(self, env_path, spend_path, model="gpt-6.1-sol", limit_usd=40.0, effort="medium", timeout=600):
        _Spend.__init__(self, spend_path, limit_usd)
        self.model, self.env_path, self.effort, self.timeout = model, env_path, effort, timeout
        self.name = f"openai:{model}"

    def complete(self, prompt, max_tokens, seed):
        self.guard()
        key = env_value(self.env_path, "OPENAI_API_KEY")
        if not key:
            raise ModelError("OPENAI_API_KEY not found")
        body = {"model": self.model, "messages": [{"role": "user", "content": prompt}],
                "max_completion_tokens": max(4000, max_tokens * 8), "reasoning_effort": self.effort,
                "response_format": {"type": "json_object"}}
        req = urllib.request.Request("https://api.openai.com/v1/chat/completions", data=json.dumps(body).encode(),
                                     headers={"Content-Type": "application/json", "Authorization": "Bearer " + key})
        for wait in BACKOFF_S + (None,):
            try:
                j = json.loads(urllib.request.urlopen(req, timeout=self.timeout).read())
                break
            except urllib.error.HTTPError as e:        # status + the API's error type / code only
                try:
                    err = json.loads(e.read() or b"{}").get("error") or {}
                except (ValueError, AttributeError, OSError):
                    err = {}
                final = err.get("type") == "insufficient_quota"
                if (e.code == 429 or e.code >= 500) and wait is not None and not final:
                    time.sleep(wait)
                    continue
                raise ModelError(f"HTTP {e.code} {err.get('type') or ''} {err.get('code') or ''}".strip()) from None
            except (urllib.error.URLError, TimeoutError, ValueError) as e:
                if wait is not None:
                    time.sleep(wait)
                    continue
                raise ModelError(type(e).__name__) from None
        usage = j.get("usage") or {}
        self.account(int(usage.get("prompt_tokens") or 0), int(usage.get("completion_tokens") or 0))
        try:
            content = j["choices"][0]["message"].get("content") or ""
        except (KeyError, IndexError, TypeError):
            raise ModelError("no choices in the reply") from None
        return content, {"model": j.get("model"), "usage": usage, "finish_reason": j["choices"][0].get("finish_reason")}


class GeminiStandIn(_Spend, Model):
    PRICE_IN, PRICE_OUT = 2.5, 15.0

    def __init__(self, env_path, spend_path, model=None, limit_usd=40.0, timeout_s=600):
        _Spend.__init__(self, spend_path, limit_usd)
        self.env_path = env_path
        self.model = model or env_value(env_path, "GEMINI_MODEL") or "gemini-2.5-pro"
        self.timeout_s = timeout_s
        self.name = f"gemini:{self.model}"

    def complete(self, prompt, max_tokens, seed):
        self.guard()
        from google import genai
        from google.genai import errors, types
        key = env_value(self.env_path, "GEMINI_API_KEY")
        if not key:
            raise ModelError("GEMINI_API_KEY not found")
        client = genai.Client(api_key=key)
        cfg = types.GenerateContentConfig(response_mime_type="application/json", temperature=0,
                                          max_output_tokens=max(8192, max_tokens * 16))
        for wait in BACKOFF_S + (None,):
            try:
                resp = client.models.generate_content(model=self.model, contents=prompt, config=cfg)
                break
            except errors.APIError as e:               # code + status only (never the request)
                code, status = getattr(e, "code", None), getattr(e, "status", None)
                if (code == 429 or (isinstance(code, int) and code >= 500)) and wait is not None:
                    time.sleep(wait)
                    continue
                raise ModelError(f"HTTP {code} {status or ''}".strip()) from None
            except _TRANSPORT as e:                    # transport errors only (an adapter bug must raise), by type
                if wait is not None:
                    time.sleep(wait)
                    continue
                raise ModelError(type(e).__name__) from None
        u = resp.usage_metadata
        pt = int(getattr(u, "prompt_token_count", 0) or 0)
        ct = int(getattr(u, "candidates_token_count", 0) or 0) + int(getattr(u, "thoughts_token_count", 0) or 0)
        self.account(pt, ct)
        try:
            text = resp.text or ""
        except (ValueError, AttributeError):
            text = ""
        fr = None
        try:
            fr = str(resp.candidates[0].finish_reason)
        except (AttributeError, IndexError, TypeError):
            pass
        return text, {"model": self.model, "usage": {"prompt_tokens": pt, "completion_tokens": ct}, "finish_reason": fr}


class AnthropicStandIn(_Spend, Model):
    """The generator stand-in while OpenAI is out of credit (orchestrator note 02:00 ET Nov 12: generator / stand-in =
    claude-fable-5-2, generous max tokens; the blind judge on another vendor). List prices per 1M tokens: Fable 5.2
    $8 / $40, Opus 5.5 $4 / $20 (thinking billed as output). Thinking is always on for these models; effort explicit;
    streamed (large max_tokens). No server-side refusal fallback on purpose: every recorded reply must come from ONE
    identified model; a refusal is a ModelError (nothing selected)."""
    PRICES = {"claude-fable-5-2": (8.0, 40.0), "claude-opus-5-5": (4.0, 20.0), "claude-sonnet-5-5": (2.0, 10.0)}

    def __init__(self, env_path, spend_path, model="claude-fable-5-2", limit_usd=40.0, effort="medium",
                 max_tokens=32000):
        _Spend.__init__(self, spend_path, limit_usd)
        self.env_path, self.model, self.effort, self.max_out = env_path, model, effort, max_tokens
        self.PRICE_IN, self.PRICE_OUT = self.PRICES.get(model, (8.0, 40.0))
        self.name = f"anthropic:{model}@{effort}"

    def complete(self, prompt, max_tokens, seed):
        self.guard()
        import anthropic
        key = env_value(self.env_path, "ANTHROPIC_API_KEY")
        if not key:
            raise ModelError("ANTHROPIC_API_KEY not found")
        client = anthropic.Anthropic(api_key=key, max_retries=4, timeout=1800.0)
        try:
            with client.messages.stream(model=self.model, max_tokens=self.max_out, output_config={"effort": self.effort},
                                        messages=[{"role": "user", "content": prompt}]) as stream:
                resp = stream.get_final_message()
        except anthropic.RateLimitError:
            raise ModelError("HTTP 429 rate_limit") from None
        except anthropic.APIStatusError as e:              # status only, never the request
            raise ModelError(f"HTTP {e.status_code}") from None
        except anthropic.APIConnectionError:
            raise ModelError("connection error") from None
        u = resp.usage
        pt = int(u.input_tokens or 0) + int(getattr(u, "cache_creation_input_tokens", 0) or 0) + \
            int(getattr(u, "cache_read_input_tokens", 0) or 0)
        self.account(pt, int(u.output_tokens or 0))
        if resp.stop_reason == "refusal":
            raise ModelError("refusal")
        text = "".join(b.text for b in resp.content if b.type == "text")
        return text, {"model": resp.model, "usage": {"prompt_tokens": pt, "completion_tokens": int(u.output_tokens or 0)},
                      "stop_reason": resp.stop_reason, "request_id": getattr(resp, "_request_id", None)}


class GrokJudge(_Spend, Model):
    """The blind judge on another vendor (orchestrator note 02:00 ET Nov 12): xAI's reasoning model on the medley key
    (XAI_API_KEY_MEDLEY, read by name in code). Model chosen from GET /v1/language-models: grok-4.20-0309-reasoning, the
    listed reasoning model (grok-4.7 returned under 60 output tokens in the red-team runs). It is told it has no tools
    and must answer in one message. Prices are an assumed upper bound ($5 / $25 per 1M)."""
    PRICE_IN, PRICE_OUT = 5.0, 25.0
    SYSTEM = ("You have no tools and no internet access. Answer in ONE message containing only the JSON object the "
              "user asks for.")

    def __init__(self, env_path, spend_path, model="grok-4.20-0309-reasoning", limit_usd=40.0, timeout=600,
                 temperature=None):
        """temperature=0 (with the attempt's seed) is production parity: LocalLLM runs every check at temperature 0 with
        a fixed seed (story_semantics.py:190-195). None leaves the API default (the first phase-1 proof column, whose
        verdicts varied across attempts). The name carries the setting so recordings of the two never mix."""
        _Spend.__init__(self, spend_path, limit_usd)
        self.env_path, self.model, self.timeout, self.temperature = env_path, model, timeout, temperature
        self.name = f"xai:{model}" + ("" if temperature is None else f"@t{temperature:g}")

    def complete(self, prompt, max_tokens, seed):
        self.guard()
        key = env_value(self.env_path, "XAI_API_KEY_MEDLEY")
        if not key:
            raise ModelError("XAI_API_KEY_MEDLEY not found")
        body = {"model": self.model, "max_tokens": max(8000, max_tokens * 8),
                "messages": [{"role": "system", "content": self.SYSTEM}, {"role": "user", "content": prompt}]}
        if self.temperature is not None:
            body.update(temperature=self.temperature, seed=seed)
        req = urllib.request.Request("https://api.x.ai/v1/chat/completions", data=json.dumps(body).encode(),
                                     headers={"Content-Type": "application/json", "Authorization": "Bearer " + key})
        for wait in BACKOFF_S + (None,):
            try:
                j = json.loads(urllib.request.urlopen(req, timeout=self.timeout).read())
                break
            except urllib.error.HTTPError as e:
                if (e.code == 429 or e.code >= 500) and wait is not None:
                    time.sleep(wait)
                    continue
                raise ModelError(f"HTTP {e.code}") from None
            except (urllib.error.URLError, TimeoutError, ValueError) as e:
                if wait is not None:
                    time.sleep(wait)
                    continue
                raise ModelError(type(e).__name__) from None
        usage = j.get("usage") or {}
        out_tokens = int(usage.get("completion_tokens") or 0)
        reasoning = int((usage.get("completion_tokens_details") or {}).get("reasoning_tokens") or 0)
        self.account(int(usage.get("prompt_tokens") or 0), out_tokens + reasoning)   # upper bound: a guard may only overcount
        try:
            content = j["choices"][0]["message"].get("content") or ""
        except (KeyError, IndexError, TypeError):
            raise ModelError("no choices in the reply") from None
        return content, {"model": j.get("model"), "usage": usage}


def openai_alive(env_path):
    """One tiny call (orchestrator: re-probe every ~20 min). Returns (True, 'ok') or (False, the error type/code)."""
    key = env_value(env_path, "OPENAI_API_KEY")
    # json_object mode needs the word JSON in the messages, or the API answers HTTP 400 invalid_request_error (the
    # probe's own wording failed this way from 01:44 to 02:30 ET, which is not the account being out of credit)
    body = {"model": "gpt-6.1-sol", "messages": [{"role": "user", "content": "Reply with the JSON object {\"ok\": 1}"}],
            "max_completion_tokens": 2000, "reasoning_effort": "low", "response_format": {"type": "json_object"}}
    req = urllib.request.Request("https://api.openai.com/v1/chat/completions", data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json", "Authorization": "Bearer " + (key or "")})
    try:
        urllib.request.urlopen(req, timeout=60).read()
        return True, "ok"
    except urllib.error.HTTPError as e:
        try:
            err = json.loads(e.read() or b"{}").get("error") or {}
        except (ValueError, AttributeError, OSError):
            err = {}
        return False, f"HTTP {e.code} {err.get('type') or ''} {err.get('code') or ''}".strip()
    except (urllib.error.URLError, TimeoutError) as e:
        return False, type(e).__name__
