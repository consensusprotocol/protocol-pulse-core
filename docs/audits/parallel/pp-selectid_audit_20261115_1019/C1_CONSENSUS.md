# C1 CONSENSUS — pp-selectid audit 20261115_1019 (ruling 95's refused count in the driver: a name collision)

Reviewers: qwen3.8-27b (P1_OR_WORSE: 0, "[P1] None. The fix correctly resolves the name collision"). glm's ruling-99
breaker was open until 11:11 ET, so the next family reviewed: deepseek-v4.1-flash gave NO ANSWER (finish=length,
16,000 tokens of reasoning, empty content). Grok was therefore asked (ruling 107 (2)): grok-4.20-0309-reasoning. Its
text says "No P0 or P1 defects", but its closing line counts 1, because it calls its one [P2] "must be fixed before
merge". Cycle 1: $0.0245 vendor-reported.

AGREED BY ALL: the collision fix is correct. next_try is computed from the intended inputs, and nothing between it and
the build record changes what it read. No other name collides (`wp_refused` and `next_try` are each bound once in
main()). Moving ruling 95 before the guard changes no build outcome, and "a report, never the build" is kept.

1. Grok [P2] / qwen [P2] "the surviving mutation: res["next_attempt"] = {} on the router path is untested". ACCEPTED AS
   A STATED GAP, WITH A RUNTIME CHECK INSTEAD.
   - Why no test: the line is a plain copy of next_try, a value computed once (bound once, tested in inputs.json by
     test_ruling_95_counts_the_refused_from_the_inputs_alone, which kills D1 and D2). Reaching the line needs the driver
     past build_router to package.json: a fake router with breaker_events, spent, chains, backends, config,
     effective_deadline and first_bounds, plus the shadow, circuit-breaker, registry and fingerprint paths. That is
     dozens of lines of brittle fakes for one assignment.
   - The runtime check: the first real build after this lands is checked. Its package.json "next_attempt" must equal its
     inputs.json "next_attempt", with the refused counted, and its ruling-95 log line must print the refused. The result
     goes on that build's STATE line.
   - Grok's point stands as a lesson. The defect being fixed was itself a surviving "untested wiring" mutation, so this
     record names the gap and the check rather than calling it harmless.
2. Grok [P3] / qwen [P3] "the comments carry build-specific history". DONE: the source comment is now one line ("a name
   of its own: main() later binds `refused` to start_refused()'s answer"), and the test docstring states the behaviour.
   The history lives in the commit message and in this audit.
3. Grok [P3] / qwen [P3] "except Exception on the report path". NO CHANGE: it is the same guard the base had at :510
   ("a report, never the build", noqa BLE001), moved with the call. A report must never end a build.
4. qwen [P2] "the timing shift". Settled in qwen's own text: next_attempt reads rows, the word-pass index, now and the
   refused ids, and none of them changes after build_inputs.

THE CODE NOW: the same fix, with the comment and the docstring trimmed. Suites: 685 pass. Mutations: 4 of 5 killed after
a control run; D5 (the record's copy, past the router) survives as stated above.
