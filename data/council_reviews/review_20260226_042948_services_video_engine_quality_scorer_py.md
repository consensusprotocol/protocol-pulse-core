# Council Code Review — services/video_engine/quality_scorer.py

**Date**: 2026-02-26T04:27:59.503613
**Stage**: post
**Feature**: Video quality scoring (multi-LLM judging), A/B testing with statistical significance, volatility-aware smart scheduler

## Scores

- **Consensus**: 5.7 / 10
- **Local Analysis**: 6.8 / 10
  - architecture: 7/10
  - error_handling: 6/10
  - edge_cases: 7/10
  - security: 7/10
  - performance: 7/10
  - maintainability: 7/10

## Verdict: REWRITE


## Warnings

- 6 broad 'except Exception' — consider narrower types

## LLM Reviews

### OPENAI

### Code Review for `services/video_engine/quality_scorer.py`

#### 1. Architecture
**Score: 7/10**

- **Issues:**
  - The code has a clear structure with a single class `QualityScorer` that encapsulates the functionality. However, the methods `_judge_claude`, `_judge_grok`, and `_judge_openai` are very similar and could be refactored to reduce redundancy (lines 142-212).
  - The use of hardcoded model names and API keys in the judge methods reduces flexibility and could be improved by externalizing these configurations (lines 150, 179, 208).
  - The heuristic scoring logic is embedded within the class, which could be separated into its own module or class for better separation of concerns (lines 267-324).

- **Improvements:**
  - Refactor the judge methods to use a common method with parameters for the model and API details.
  - Externalize configuration details such as model names and API keys to a configuration file or environment variables.
  - Consider creating a separate module or class for heuristic scoring to improve modularity.

#### 2. Error Handling
**Score: 6/10**

- **Issues:**
  - The code uses broad exception handling (`except Exception as e`) which can mask specific errors and make debugging difficult (lines 159, 188, 217).
  - There is no retry mechanism for API calls, which could lead to failures in transient network issues (lines 150-212).

- **Improvements:**
  - Use specific exception types for handling known errors (e.g., network errors, JSON parsing errors).
  - Implement a retry mechanism with exponential backoff for API calls to handle transient errors more gracefully.

#### 3. Edge Cases
**Score: 5/10**

- **Issues:**
  - The code does not handle empty or malformed inputs robustly. For example, if `title` or `content` is empty, the scoring logic might not behave as expected (lines 101-105).
  - There is no handling for concurrent access to the `QUALITY_DB_PATH`, which could lead to race conditions (line 15).

- **Improvements:**
  - Add input validation to ensure `title`, `content`, and `sources` are not empty or malformed before processing.
  - Implement file locking or use a database with transaction support to handle concurrent access to `QUALITY_DB_PATH`.

#### 4. Security
**Score: 4/10**

- **Issues:**
  - API keys are fetched directly from environment variables without validation or masking (lines 150, 179, 208).
  - There is no input sanitization for `title`, `content`, and `sources`, which could lead to injection attacks if these inputs are not controlled (lines 101-105).

- **Improvements:**
  - Validate and mask API keys when logging or displaying them.
  - Implement input sanitization to prevent injection attacks, especially if inputs are used in dynamic contexts.

#### 5. Performance
**Score: 6/10**

- **Issues:**
  - The code does not implement any caching strategy for repeated evaluations of the same content, which could improve performance (lines 101-105).
  - The heuristic scoring logic could be optimized for large content inputs (lines 267-324).

- **Improvements:**
  - Implement caching for repeated content evaluations to reduce redundant processing.
  - Optimize the heuristic scoring logic to handle large inputs more efficiently, possibly by using more efficient data structures or algorithms.

#### 6. Maintainability
**Score: 7/10**

- **Issues:**
  - The code is generally readable, but the use of magic numbers for scoring thresholds and weights reduces clarity (lines 19-35).
  - The logging messages could be more descriptive to aid in debugging and monitoring (lines 159, 188, 217).

- **Improvements:**
  - Replace magic numbers with named constants or configuration settings to improve readability.
  - Enhance logging messages with more context to aid in debugging and understanding system behavior.

### Summary

- **Overall Score**: 5.8/10
- **Production Ready**: WITH_FIXES
- **Critical Issues**:
  - Broad exception handling without specific error types.
  - Lack of input validation and sanitization.
  - No retry mechanism for API calls.

- **Recommended Improvements**:
  1. Refactor judge methods to reduce redundancy and improve configurability.
  2. Implement specific exception handling and retry mechanisms for API calls.
  3. Add input validation and sanitization to prevent injection attacks.
  4. Introduce caching for performance optimization.
  5. Use named constants for configuration settings to improve readability.

Addressing these issues will enhance the robustness, security, and performance of the system, making it more suitable for production deployment.

### GROK

Below is a detailed review of the provided code for Protocol Pulse's `quality_scorer.py`. I have evaluated the code across the specified dimensions with a rigorous focus on production readiness, industry standards, and potential risks. Each dimension is scored from 1 to 10, with specific issues and actionable improvements listed. The review prioritizes correctness, scalability, and robustness for a high-performance Bitcoin intelligence platform running on dual RTX 4090s.

---

### 1. Architecture
**Score: 7/10**

**Issues:**
- **Separation of Concerns (General):** The `QualityScorer` class handles multiple responsibilities: scoring logic, LLM integration, heuristic scoring, logging, and decision-making. This violates the Single Responsibility Principle, making the class harder to extend or modify.
- **Extensibility (Line 203-238, 240-275, 277-312):** Hardcoded LLM integrations (`_judge_claude`, `_judge_grok`, `_judge_openai`) limit extensibility. Adding a new LLM requires modifying the class directly rather than using a plugin or registry pattern.
- **Configuration Management (Line 45-51, 53-59):** Hardcoded thresholds (`PUBLISH_THRESHOLD`, etc.) and dimension weights (`DIMENSION_WEIGHTS`) are not configurable via environment variables or a config file, reducing flexibility for tuning in production.
- **Data Persistence (Line 41):** The `QUALITY_DB_PATH` is hardcoded and assumes a specific file structure, which may not be portable across environments.

**Improvements:**
- Split `QualityScorer` into smaller components (e.g., `JudgeManager` for LLM interactions, `ScoreAggregator` for merging results, `DecisionEngine` for publish/block logic).
- Implement a plugin system or registry for LLM judges to allow dynamic addition of new models without code changes.
- Move thresholds and weights to a configuration file or environment variables with proper validation (e.g., ensure weights sum to 1.0).
- Abstract the data persistence layer to support different storage backends (e.g., JSON file, database) via a configurable interface.

---

### 2. Error Handling
**Score: 6/10**

**Issues:**
- **Generic Exception Catching (Line 188, 224, 260):** Broad `Exception` catching in LLM judge methods (`_judge_claude`, `_judge_grok`, `_judge_openai`) risks masking critical errors (e.g., network failures vs. API quota issues). Logs are written, but no recovery or retry logic is implemented.
- **Silent Failures (Line 190, 226, 262):** If an API key is missing, the method silently returns `None` without logging a specific error, making debugging harder.
- **Incomplete Fallback (Line 167-172):** The heuristic fallback is triggered only if all LLMs fail, but there’s no mechanism to retry failed LLMs or prioritize certain models over others.
- **JSON Parsing Risks (Line 279-289):** JSON parsing errors in `_parse_judge_response` are logged but not handled with a fallback beyond returning `None`, which could lead to incomplete scoring if one judge fails.

**Improvements:**
- Catch specific exceptions (e.g., `anthropic.RateLimitError`, `openai.AuthenticationError`) and implement tailored recovery (e.g., retry on rate limits, fail fast on auth issues).
- Log explicit errors for missing API keys and treat this as a configuration error requiring immediate attention.
- Add retry logic for transient LLM failures (e.g., network issues) with exponential backoff.
- Enhance fallback logic to handle partial judge failures (e.g., proceed with available scores if at least one judge succeeds).

---

### 3. Edge Cases
**Score: 5/10**

**Issues:**
- **Input Validation (Line 139-140):** No validation for empty or malformed inputs (`title`, `content`, `sources`). An empty `content` string could still be passed to LLMs, wasting resources or causing errors.
- **Content Truncation (Line 208, 244, 280):** Hardcoded truncation of `content` to 5000 characters in LLM prompts may cut off critical context, skewing scores for longer articles.
- **Sources Handling (Line 141):** Truncation of `sources` to 10 items without logging or warning could miss important references in scoring.
- **Concurrent Access (Line 41, 160-161):** The `QUALITY_DB_PATH` file-based logging in `_log_score` (not fully shown but implied) risks race conditions in a multi-threaded or distributed environment.

**Improvements:**
- Add input validation for `title` and `content` (e.g., minimum length, non-whitespace checks) and raise appropriate exceptions.
- Implement configurable content truncation with a warning log if content is cut off, or use summarization for long content before passing to LLMs.
- Log a warning if `sources` are truncated and consider passing all sources or a summary to judges.
- Use a thread-safe or distributed logging mechanism (e.g., database, queue-based logging) instead of direct file writes for score logging.

---

### 4. Security
**Score: 5/10**

**Issues:**
- **API Key Exposure (Line 202, 238, 274):** API keys are read directly from environment variables without additional safeguards (e.g., vault integration). If logs are misconfigured, keys could be exposed.
- **Prompt Injection Risk (Line 206-210, 242-246, 278-282):** User-provided `title` and `content` are directly formatted into LLM prompts without sanitization, risking prompt injection attacks.
- **Lack of Rate Limiting (Line 203-238, 240-275, 277-312):** No rate limiting or quota checks for LLM API calls, which could lead to abuse or unexpected costs in production.

**Improvements:**
- Use a secure secrets management system (e.g., HashiCorp Vault, AWS Secrets Manager) for API keys instead of environment variables.
- Sanitize `title` and `content` inputs to prevent prompt injection (e.g., escape special characters, limit input size, or use structured input formats for LLMs).
- Implement rate limiting and quota tracking for LLM API calls, with configurable limits per judge to prevent cost overruns.

---

### 5. Performance
**Score: 6/10**

**Issues:**
- **Sequential LLM Calls (Line 178-186):** LLM judges are called sequentially rather than in parallel, increasing latency for multi-LLM scoring.
- **No Caching (General):** No caching mechanism for repeated scoring of identical content or for LLM responses, which could reduce redundant API calls and costs.
- **Resource Intensity (Line 203-238, 240-275, 277-312):** Running multiple LLMs per article without batching or prioritization could overwhelm system resources or API quotas, especially on high-throughput workloads.
- **Heuristic Scoring Overhead (Line 291-336):** Heuristic scoring logic, while lightweight, recalculates metrics like word count and regex matches every time, without memoization.

**Improvements:**
- Use asynchronous or parallel processing (e.g., `asyncio`, `concurrent.futures`) to call LLM judges concurrently, reducing overall latency.
- Implement a caching layer (e.g., Redis) for scoring results based on content hash to avoid redundant API calls for unchanged content.
- Add configurable batching or prioritization for LLM calls (e.g., limit to 2 judges if under high load) to optimize resource usage.
- Memoize heuristic scoring calculations or precompute static metrics (e.g., word count) when content is first processed.

---

### 6. Maintainability
**Score: 7/10**

**Issues:**
- **Incomplete Documentation (Line 1-34, 121-137):** While there’s a module docstring and some method docs, critical details (e.g., expected LLM response format, heuristic logic assumptions) are undocumented.
- **Hardcoded Values (Line 209, 245, 281):** Magic numbers (e.g., `max_tokens=1000`, `temperature=0.3`, content truncation at 5000) lack explanation or configuration options.
- **Testability (General):** No clear separation of logic for unit testing (e.g., mocking LLM calls is difficult due to direct API client instantiation in methods).
- **Code Duplication (Line 203-238, 240-275, 277-312):** LLM judge methods have near-identical structure, violating DRY principles and increasing maintenance burden.

**Improvements:**
- Add detailed docstrings for all methods, especially for heuristic scoring logic and expected LLM response parsing.
- Extract hardcoded values (e.g., `max_tokens`, content limits) into a configuration or constants module with explanatory comments.
- Refactor LLM integrations into a generic `Judge` interface or base class to reduce duplication and improve testability (e.g., mock API clients).
- Add type hints for complex data structures (e.g., judge response format) to improve code clarity and IDE support.

---

### Overall Assessment
**Overall Score: 6.0/10** (average of all dimensions)

**Production Ready: WITH_FIXES**
- The code demonstrates a solid foundation for multi-LLM content scoring with a clear decision-making framework. However, significant issues in security, edge case handling, and performance prevent it from being production-ready without fixes. It falls short of industry standards for high-performance platforms due to lack of parallelism, robust error handling, and security measures.

**Critical Issues (Blockers):**
1. **Security Risks:** Prompt injection vulnerability (Line 206-210, etc.) and insecure API key handling (Line 202, etc.) must be addressed to prevent exploitation.
2. **Edge Case Failures:** Lack of input validation (Line 139-140) risks crashes or incorrect scoring for malformed or empty inputs.
3. **Concurrent Access Risk:** File-based logging (Line 41, implied in `_log_score`) could fail under concurrent access, leading to data loss or corruption.

**Recommended Improvements (Prioritized):**
1. **Security Fixes:** Implement prompt sanitization and secure secrets management (e.g., Vault) to address critical vulnerabilities.
2. **Input Validation:** Add robust checks for `title`, `content`, and `sources` to handle edge cases gracefully.
3. **Parallel Processing:** Refactor LLM calls to run concurrently using `asyncio` or similar to improve performance.
4. **Error Handling:** Catch specific exceptions and implement retry logic for transient LLM failures.
5. **Architecture Refactoring:** Split `QualityScorer` into smaller components and introduce a plugin system for LLM judges to improve extensibility.
6. **Configuration Management:** Move hardcoded thresholds, weights, and magic numbers to a config file or environment variables.
7. **Caching:** Add a caching layer for scoring results to reduce redundant API calls and improve efficiency.
8. **Documentation:** Enhance docstrings and comments for critical logic (e.g., heuristics, parsing) to aid maintainability.

---

This code can reach production readiness with the above fixes, particularly addressing security and edge case issues. Once resolved, it has the potential to exceed industry standards with its multi-LLM approach and detailed scoring dimensions, especially for a niche Bitcoin intelligence platform. However, in its current state, deployment risks operational failures and security breaches.

### CLAUDE

# FINAL PRODUCTION REVIEW: Video Quality Scoring System

## Code Status: **INCOMPLETE** - Missing critical components for A/B testing and volatility-aware scheduling

---

## Dimension Scores

### 1. **Architecture** — Score: 4/10

**Issues:**
- **Line 1**: Misleading module name — `video_engine/quality_scorer.py` suggests video processing but handles article content
- **Missing Components**: No A/B testing framework or volatility-aware scheduler as specified
- **No Interfaces**: Lacks abstract base classes for judges, making extension difficult
- **Tight Coupling**: Direct API calls in judge methods violate dependency injection principles
- **No Configuration Management**: Hardcoded constants should be externalized

**Improvements:**
- Rename to `content_engine/quality_scorer.py`
- Extract judge interface: `class ContentJudge(ABC)`
- Implement dependency injection for API clients
- Add configuration layer for thresholds and weights

### 2. **Error Handling** — Score: 3/10

**Issues:**
- **Lines 147, 172, 197**: Generic `Exception` catching masks specific errors
- **Line 225**: `json.JSONDecodeError` handling doesn't distinguish between malformed JSON vs missing JSON
- **No Retry Logic**: API failures should have exponential backoff
- **Silent Failures**: Missing judges don't trigger alerts
- **No Circuit Breaker**: Repeated API failures could cause cascading issues

**Critical Fixes:**
```python
# Replace generic exception handling
except (anthropic.APIError, anthropic.RateLimitError) as e:
    logger.error(f"Claude API error: {e}", extra={"retry": True})
    raise QualityScoreError(f"Judge unavailable: {e}")

# Add retry decorator
@retry(stop=stop_after_attempt(3), wait=wait_exponential())
def _judge_claude(self, ...):
```

### 3. **Edge Cases** — Score: 2/10

**Issues:**
- **Line 80**: No validation for empty title/content
- **Line 109**: Division by zero possible if all weights are 0
- **Line 167**: Model name hardcoded — what if deprecated?
- **No Rate Limiting**: Could hit API limits with burst traffic
- **Concurrent Access**: No thread safety for `_scores_log`
- **Memory Leaks**: `_scores_log` grows unbounded

**Critical Fixes:**
```python
def score_article(self, title: str, content: str, **kwargs) -> Dict:
    if not title or not content:
        raise ValueError("Title and content cannot be empty")
    
    if len(content) < 50:
        logger.warning("Content too short for reliable scoring")
    
    # Add thread safety
    with self._lock:
        result = self._compute_score(...)
```

### 4. **Security** — Score: 5/10

**Issues:**
- **Lines 136, 161, 186**: API keys stored in environment variables (acceptable)
- **Line 209**: No input sanitization before sending to LLMs
- **No Rate Limiting**: Vulnerable to DoS attacks
- **Log Injection**: User content could inject malicious log entries
- **No Input Length Limits**: Could send massive payloads to APIs

**Improvements:**
```python
def _sanitize_content(self, content: str) -> str:
    """Sanitize content before API calls."""
    # Remove potential prompt injection attempts
    cleaned = re.sub(r'system:|assistant:|user:', '', content)
    return cleaned[:10000]  # Reasonable limit
```

### 5. **Performance** — Score: 4/10

**Issues:**
- **Line 137**: Sequential API calls — should be parallel
- **No Caching**: Identical content scored multiple times
- **Line 245**: Regex compilation happens on every call
- **Memory Usage**: Storing full content in logs
- **No Connection Pooling**: New HTTP connections for each request

**Critical Improvements:**
```python
import asyncio
from concurrent.futures import ThreadPoolExecutor

async def score_article_async(self, ...):
    """Parallel judge execution."""
    tasks = [
        asyncio.create_task(self._judge_claude_async(...)),
        asyncio.create_task(self._judge_grok_async(...)),
        asyncio.create_task(self._judge_openai_async(...))
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)
```

### 6. **Maintainability** — Score: 6/10

**Issues:**
- **Line 34**: Magic numbers without explanation
- **Missing Tests**: No unit tests visible
- **Inconsistent Naming**: `sources_str` vs `sources_list`
- **Long Methods**: `score_article` does too much
- **No Type Hints**: Many return types are `Optional[Dict]` — too generic

**Improvements:**
```python
from dataclasses import dataclass
from typing import TypedDict

class QualityScore(TypedDict):
    score: float
    reasoning: str

@dataclass
class ScoringResult:
    overall_score: float
    dimensions: Dict[str, QualityScore]
    decision: Literal["publish", "review", "block"]
    judges: List[str]
```

---

## **MISSING COMPONENTS** (Critical)

The code is missing two of the three required features:

### A/B Testing Framework
No implementation of statistical significance testing for content variants.

**Required Implementation:**
```python
class ABTester:
    def create_experiment(self, control: str, variants: List[str]) -> str:
        """Create A/B test with statistical power analysis."""
        
    def record_result(self, exp_id: str, variant: str, metric: float):
        """Record performance metric."""
        
    def get_significance(self, exp_id: str) -> Dict:
        """Calculate statistical significance with p-values."""
```

### Volatility-Aware Scheduler
No smart scheduling based on market conditions.

**Required Implementation:**
```python
class VolatilityScheduler:
    def get_optimal_publish_time(self, content_type: str) -> datetime:
        """Schedule based on market volatility and engagement patterns."""
        
    def should_delay_publication(self, current_volatility: float) -> bool:
        """Delay during extreme market movements."""
```

---

## Overall Assessment

### **Overall Score**: 4.0/10
### **Production Ready**: NO

### **Critical Issues** (Must Fix):
1. **Missing Core Features**: A/B testing and volatility scheduling completely absent
2. **Poor Error Recovery**: System will fail silently when APIs are down  
3. **No Concurrent Safety**: Race conditions in logging and scoring
4. **Performance Bottlenecks**: Sequential API calls will timeout under load
5. **Security Vulnerabilities**: No input validation or rate limiting

### **Recommended Improvements** (Priority Order):

1. **Implement Missing Features** (P0)
   - Build A/B testing framework with proper statistical analysis
   - Add volatility-aware scheduling with market data integration

2. **Fix Critical Bugs** (P0)
   - Add proper exception handling with specific error types
   - Implement thread safety for shared state
   - Add input validation and sanitization

3. **Performance Optimization** (P1)
   - Parallel judge execution with asyncio
   - Redis caching layer for repeated content
   - Connection pooling for API clients

4. **Production Hardening** (P1)
   - Comprehensive test suite (unit, integration, load)
   - Monitoring and alerting for judge failures
   - Configuration management with environment-specific settings

5. **Code Quality** (P2)
   - Extract judge interface and implement dependency injection
   - Add proper type hints with custom classes
   - Break down large methods and improve naming

**Verdict**: This code needs substantial work before production deployment. The missing A/B testing and volatility scheduling features alone make it unsuitable for the Bitcoin intelligence platform requirements.


## Cross-Review

## FINAL CONSENSUS REVIEW

### Adjusted Scores for Each Dimension

1. **Architecture**: 5/10
2. **Error Handling**: 4/10
3. **Edge Cases**: 4/10
4. **Security**: 4/10
5. **Performance**: 5/10
6. **Maintainability**: 6/10

### Complete List of Issues (Merged from All Reviews)

#### Architecture
- Misleading module name; should be `content_engine/quality_scorer.py`.
- Lack of separation of concerns; `QualityScorer` handles too many responsibilities.
- Hardcoded LLM integrations limit extensibility.
- Configuration details like thresholds and weights are hardcoded.
- Data persistence path is hardcoded, assuming a specific file structure.

#### Error Handling
- Broad exception handling masks specific errors.
- No retry mechanism for API calls.
- Silent failures when API keys are missing.
- JSON parsing errors are not handled robustly.

#### Edge Cases
- No validation for empty or malformed inputs.
- Content truncation may cut off critical context.
- Concurrent access to `QUALITY_DB_PATH` could lead to race conditions.
- Potential division by zero if all weights are zero.

#### Security
- API keys are not securely managed.
- No input sanitization, risking prompt injection attacks.
- No rate limiting, exposing the system to DoS attacks.
- Log injection risk due to unsanitized user content.

#### Performance
- Sequential LLM calls increase latency.
- No caching mechanism for repeated evaluations.
- Regex compilation occurs on every call.
- Lack of connection pooling for API requests.

#### Maintainability
- Magic numbers reduce code clarity.
- Incomplete documentation and missing unit tests.
- Code duplication in LLM judge methods.
- Inconsistent naming conventions.

### Prioritized Fix List

1. **Security Fixes** (P0)
   - Implement prompt sanitization and secure API key management.
   - Introduce rate limiting and input length checks.

2. **Error Handling Improvements** (P0)
   - Use specific exception types and implement retry logic.
   - Enhance logging for missing API keys and JSON parsing errors.

3. **Architecture Refactoring** (P1)
   - Split `QualityScorer` into smaller components.
   - Implement a plugin system for LLM judges.
   - Externalize configuration settings.

4. **Performance Optimization** (P1)
   - Use asynchronous processing for LLM calls.
   - Implement caching for scoring results.
   - Optimize heuristic scoring logic.

5. **Edge Case Handling** (P1)
   - Add input validation and handle concurrent access issues.
   - Ensure content truncation is logged and configurable.

6. **Maintainability Improvements** (P2)
   - Enhance documentation and add unit tests.
   - Refactor code to reduce duplication and improve naming.

### Final Verdict: FIX_THEN_SHIP

The code requires significant improvements, particularly in security, error handling, and architecture, before it can be considered production-ready. Addressing these issues will enhance the system's robustness, security, and performance, making it suitable for deployment in a high-performance Bitcoin intelligence platform.
