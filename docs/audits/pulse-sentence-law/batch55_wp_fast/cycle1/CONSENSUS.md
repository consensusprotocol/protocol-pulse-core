# Batch 55 cycle 1: consensus and what was done

- C1 [high], an exception escaping _fetch would surface at f.result(), crash the cycle and lose the ready jobs: implemented. f.result() is caught per future, and every row of that video gets a failure row ("fetch: <type>: <message>"). The cycle goes on. Test: test_a_fetch_that_dies_writes_failure_rows_and_the_cycle_goes_on.
- C2 [medium], the decode_batch test did not prove one load per batch: rewritten to assert the ORDER. No reference call comes before the last verbatim call, so the GPU changes model once per batch. ts._whisper and ts._reference return the resident model, because gpu0.whisper goes through swap_to, which loads only a model that is not resident.
- glm, cross-examination, which time each field covers: documented in the code. gpu_s is the time HOLDING the lease and contains foreign_wait_s; lease_wait_s is waiting for another caller's lease; fetch_s is summed over the fetch threads.
- qwen F1 (critical, 0 votes), "a record is written for a failed decode": no. _one raises before make_record, and the except path writes only the failure row (test m003).
- qwen F2 (0 votes), a race on report: every mutation runs on the main thread; the fetch threads return their own values.
- qwen F3 (0 votes), "_whisper per window reloads": no, see C2.
