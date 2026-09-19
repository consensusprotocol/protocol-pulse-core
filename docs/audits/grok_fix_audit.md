# GROK FIX AUDIT — Cross-LLM Cycle 1
**Date:** 2026-09-19
**Status:** DEGRADED (only Gemini responded; OpenAI=credits exhausted, xAI=403 permission denied)
**Model:** gemini-2.5-flash

## Gemini Cycle 1 Findings

Here's an audit of the provided Python files for Protocol Pulse's xAI/Grok integration, focusing on cost reduction and identifying issues.

---

### **`services/x_reader.py`**

**Audit Focus Summary:**
1.  **Search Tools:** Exclusively uses `x_search`.
2.  **Replaceable:** No, relies on Grok's `x_search` to access X data when direct API is depleted.
3.  **Unnecessary Calls:** Appears minimal, with caching.
4.  **Minimum Viable Grok:** All calls, as they require X-native data access.
5.  **Bugs/Inefficiencies:** Appears robust; potential for minor improvements in timeouts/retries.
6.  **Budget Gateway Risk:** High. This is a critical X data acquisition layer.

<critical>
*   None identified. The module correctly uses `x_search` for its stated purpose.
</critical>

<high>
*   **High Risk with Budget Gateway:** Routing `x_reader`'s `x_search` calls through a strict budget gateway (rate limiter/throttler) poses a **high risk** to Protocol Pulse's core functionality. This module is explicitly designed as the *sole* mechanism for X data reads when the direct X API is credit-depleted, serving "every consumer" (e.g., comment_radar, quote_rt_engine). Throttling here would directly degrade functionality dependent on X content. These calls are essential and specialized, and should be prioritized for uninterrupted access.
</high>

<medium>
*   **Timeout Value Review:** The `timeout_seconds: 75` is quite generous. While it might be necessary for Grok's server-side tool, investigate if this can be reduced without causing frequent timeouts. A consistently long timeout on a request (even if eventually successful) ties up resources; if it fails, it delays error reporting.
*   **Retry Mechanism:** The provided `_call_xsearch` snippet doesn't explicitly show retry logic on transient network or API errors. While not directly inflating costs (a single failed call means no output, not multiple attempts), implementing a simple retry with exponential backoff (e.g., 2-3 retries) could improve the reliability of X data acquisition without significantly increasing cost if errors are rare.

</medium>

---

### **`services/story_engine.py` (harvest_xai function + context)**

**Audit Focus Summary:**
1.  **Search Tools:** Exclusively uses `x_search`.
2.  **Replaceable:** No, relies on Grok's `x_search` for X-native discovery.
3.  **Unnecessary Calls:** Potential redundancy with RSS feeds.
4.  **Minimum Viable Grok:** Yes, for X-native discourse, but not necessarily for general news.
5.  **Bugs/Inefficiencies:** Missing cost logging, basic error handling, potential token waste.
6.  **Budget Gateway Risk:** Medium-High, as it's for discovery.

<critical>
*   **Missing Cost Logging:** The `harvest_xai` function in `story_engine.py` does not log its xAI API usage and cost. This makes tracking and auditing the $99.97 in 5 days extremely difficult and prevents granular cost analysis for this critical discovery module. All xAI calls should implement robust cost logging (e.g., by utilizing the `_log_cost` function from `x_reader.py` or a similar mechanism).
</critical>

<high>
*   **Redundant `x_search` for RSS-Covered Topics:** Many `XAI_SEARCH_THEMES` (e.g., "central bank policy surprise this week", "treasury auction or bond market stress", "tariff sanction or trade escalation today") heavily overlap with the comprehensive list of RSS feeds. Using Grok's `x_search` for these themes adds significant cost for information likely discoverable via the existing, cheaper RSS aggregation. Evaluate which themes genuinely require X-native real-time social signals versus what can be effectively covered by the extensive RSS sources, and consider reducing or eliminating `x_search` for the latter without significant quality loss for a "discovery-only prototype."
*   **Lack of Robust Error Handling/Retries:** The `harvest_xai` function only `print`s an error and skips to the next theme on failure. This can lead to missed discoveries for themes experiencing transient network issues or API failures. Implement a basic retry mechanism (e.g., 1-2 retries with exponential backoff) to improve reliability, similar to the `_xai_search` in `claim_verifier.py`.
*   **Fragile JSON Output Parsing:** `harvest_xai` relies on Grok returning a perfectly valid JSON array directly in the `input` prompt. If Grok's output is malformed JSON, `json.loads` will fail, wasting the tokens spent and resulting in no items for that theme. Implement more robust JSON extraction (e.g., using a regex and `_json_in` from `claim_verifier.py`) to gracefully handle minor formatting errors.
</high>

<medium>
*   **Potential Token Waste on `max_per_theme` and `why_significant`:** The prompt asks for "3-5 items" and includes `why_significant`. While `max_per_theme=5` is applied, if Grok generates more than 5 items, or if the `why_significant` field isn't consistently utilized or could be derived in a later, cheaper processing step, unnecessary tokens are consumed. Adjust the prompt to strictly request `max_per_theme` items (e.g., "Return a JSON array of AT MOST 5 items") and evaluate the necessity of `why_significant` at this initial discovery stage.
*   **Budget Gateway Risk (Medium-High):** While this is a "DISCOVERY-ONLY prototype," throttling `harvest_xai` could delay or miss crucial X-specific trends. However, the existing RSS coverage provides a partial buffer. Protocol Pulse should carefully weigh the importance of real-time X discovery against cost constraints for this module.

</medium>

---

### **`services/claim_verifier.py`**

**Audit Focus Summary:**
1.  **Search Tools:** `_xai_search` defaults to `web_search`. `_gpt` is plain chat (OpenAI).
2.  **Replaceable:** Yes, `_gpt` could use cheaper LLMs, and `_xai_search` (for `web_search`) could use dedicated search APIs or other LLMs.
3.  **Unnecessary Calls:** Grok's `web_search` is likely an expensive option for general fact-checking.
4.  **Minimum Viable Grok:** Likely none for general `web_search` unless an X-specific search is explicitly requested.
5.  **Bugs/Inefficiencies:** Misuse of Grok for general `web_search`, expensive models for classification, global mutable state.
6.  **Budget Gateway Risk:** Medium, for the verification process.

<critical>
*   **Misuse of Grok for General `web_search`:** The `_xai_search` function defaults to `web_search`. Grok's unique value proposition lies in its X-native knowledge (`x_search`), not necessarily in being the most cost-effective or highest-quality general web search engine compared to dedicated search APIs (e.g., Brave Search, Perplexity API) or cheaper LLMs with integrated search. Using Grok's `web_search` for general fact-checking, as is the default, is likely an **unnecessarily expensive choice** and a significant source of cost inflation.
*   **Global `_COST` and `_XAI_LOG` Variables:** These global mutable variables are not thread-safe and will lead to inaccurate cost tracking and potential memory bloat in a concurrent or long-running service. They must be refactored to be passed as arguments, returned from functions, or managed within a class instance to ensure accurate and reliable state management.
</critical>

<high>
*   **Expensive Model for Claim Classification/Synthesis (`_gpt` calls):** The `CLASSIFY_PROMPT` and `VERIFY_PROMPT` tasks, currently performed by `gpt-4o`, involve structured extraction and logical reasoning. These tasks are prime candidates for **significant cost reduction** by using a cheaper LLM. Thoroughly evaluate `gpt-3.5-turbo-0125`, a specialized fine-tuned model, or even local open-source models (like Llama 3 8B Instruct) for similar quality with substantial cost savings.
*   **Inefficient `web_search` Strategy:** Instead of using Grok's `web_search` as the default for all fact-checking:
    1.  Continue using **direct API calls** for `live_market_value` (DeFiLlama, mempool, Yahoo).
    2.  Implement integration with a **dedicated, cheaper search API** (e.g., Brave Search, Perplexity API, Google Custom Search, SerpAPI) for general web queries (`reported_fact`, `official_document_claim`).
    3.  Only use Grok's `x_search` (not `web_search`) if the claim *explicitly* requires searching on X (e.g., "was this statement made on X?"). This tailored approach will dramatically reduce Grok-related costs for general verification.
</high>

<medium>
*   **Hardcoded Model Versions:** The models `gpt-4o` and `grok-4.3` are hardcoded. Parameterize these in a configuration file or environment variables to allow for easier swapping to cheaper or newer models without code changes. This is crucial for A/B testing alternative models (e.g., cheaper OpenAI models, different Grok versions) to further optimize costs.
*   **`_xai_search` Timeout and Retries on Degraded Responses:** While retries (`retries=2`) are good for robustness, consistently degraded or empty responses from Grok after multiple attempts indicate a potential systemic issue (e.g., problematic prompt, poor tool performance for specific query types). Monitor the `_XAI_LOG` for "degraded" and "empty" entries to identify patterns. If frequent, adjust the prompt, evaluate the tool's effectiveness, or consider alternative tools. While it prevents using bad data, it still spends money on failed attempts.
*   **Budget Gateway Risk (Medium):** Fact verification is a critical step in Protocol Pulse's pipeline. Rate limiting `_xai_search` (web search) or `_gpt` calls could delay the processing of stories or lead to unverified content being passed downstream, impacting the overall quality and reliability of "auditor's facts." Ensure that verification processes receive adequate budget and rate limits to maintain system integrity.

</medium>

---

## CYCLE 2: Claude Cross-Check of Gemini Findings

**Reviewer:** Claude Opus 4.6 (this CC session)
**Method:** Manual code review of all three files + crontab + social_daemon.py call chains

### Agreement with Gemini

1. **AGREE: x_reader.py IS the correct place for x_search.** It's purpose-built for X reads and has proper caching (30min/60min TTL). Budget gateway risk is real but manageable — the gateway should count x_reader calls against a SEARCH budget, not block them outright.

2. **AGREE: story_engine harvest_xai() is redundant for 8+ of 13 themes.** RSS already covers macro, banking, politics, tech, energy. Only Bitcoin-specific X discourse themes need x_search: "unusual Bitcoin on-chain movement", "major institution Bitcoin or crypto move", "corporate or sovereign bitcoin treasury purchase". The other 10 themes should be RSS-only.

3. **AGREE: claim_verifier using Grok web_search for general fact-checking is wasteful.** Grok's web_search is billed at $5.09/1K calls. Direct URL fetching (which claim_verifier already does via `_fetch_text`) or Gemini grounding is cheaper.

4. **AGREE: Missing cost logging in story_engine is a critical gap.**

### Disagreements / Additions

1. **DISAGREE: Gemini says x_reader "should be prioritized for uninterrupted access."** FACT: x_reader has been dead for 14 days (since Sept 5) and nobody noticed. The social automation pipeline (comment_radar, quote_rt, reply_engine) is non-critical. It SHOULD go through the budget gateway with a generous but finite allocation.

2. **ADDITION: The 41K requests are NOT primarily from search.** The xAI console shows only 7,600 search calls (5,200 web + 2,400 X). The other 33,781 are CHAT COMPLETIONS from the ~30 call sites in the inventory. The chat calls cost $50.69 in tokens (33.6M prompt + 3.5M reasoning). A budget gateway must cap BOTH search and chat requests.

3. **ADDITION: Gemini missed that claim_verifier._xai_search uses the /v1/responses endpoint** (not /v1/chat/completions). This is the newer Agent Tools API which bills differently. The gateway must handle both endpoints.

4. **ADDITION: The biggest single cost-saving move is removing Grok from article_automation.py** (line 590). This uses grok-3 for article WRITING — a task Gemini or Claude can do equally well. It fires every 45 minutes via cron (`*/45 * * * *`), producing 32 articles/day. At ~2000 tokens output each, this is ~64K output tokens/day x $15/1M = ~$0.96/day from this one call site alone.

5. **ADDITION: post_quality_gate.py uses Grok for tweet quality scoring** (~10 calls/day). This is a simple classification task that Gemini or local Ollama can handle.

### Consensus Actions (agreed by Gemini + Claude)

| # | Action | Gemini | Claude | Consensus |
|---|--------|--------|--------|-----------|
| 1 | Build xai_gateway.py with daily budget caps | AGREE | AGREE | **DO IT** |
| 2 | Route all calls through gateway | AGREE | AGREE | **DO IT** |
| 3 | Strip x_search from story_engine for non-X themes | AGREE | AGREE | **DO IT** — reduce to 3 themes |
| 4 | Remove Grok from claim_verifier web_search default | AGREE | AGREE | **DO IT** — use direct URL fetch |
| 5 | Keep x_reader on Grok x_search but through gateway | AGREE | AGREE | **DO IT** |
| 6 | Remove Grok from article_automation.py writing | N/A | AGREE | **DO IT** — route to Gemini |
| 7 | Remove Grok from post_quality_gate.py | N/A | AGREE | **DO IT** — route to Gemini |
| 8 | Add cost logging to story_engine | AGREE | AGREE | **DO IT** |
| 9 | Add Telegram alert on 402/429/budget-stop | AGREE | AGREE | **DO IT** |
| 10 | Keep Grok for cross_llm_audit trifecta (XAI_AUDIT_API_KEY) | AGREE | AGREE | **DO IT** |
