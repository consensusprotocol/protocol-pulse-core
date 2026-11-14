# Batch 64 cycle 2: one consensus finding, fixed
glm F1 [medium], agreed by qwen27b and glm (the write-up wanders; its evidence and fix are clear): serve_once caught only
gpu0.LeaseBusy around the decodes. decode() re-raises gpu0.Gpu0Stop (a BaseException: GpuOOM, Gpu0Foreign,
Gpu0NotFree, Gpu0Unreadable), so a transient GPU0 condition ended the serving process. Nothing wrong was answered (the
request stayed pending), but the service stopped. VALID.
FIX: serve_once catches gpu0.Gpu0Stop (LeaseBusy is one) and logs it. Requests already decoded in the batch are answered
after the lease; the rest stay pending and are asked again on the next pass (the serve loop sleeps when nothing was
answered). decode() still re-raises it, so a GPU0 stop ends the batch. New test:
test_a_gpu0_stop_leaves_the_rest_pending_and_the_service_running (an out-of-memory error on a new window's decode: no
crash, the request pending, no entry invented, answered on the next pass). test_lock_precheck: 14 passed.
Raised but not agreed, checked, no change:
- qwen27b F1 [critical] "no lease when every request is cached; the paid recogniser without the lease": a cached
  request copies its entry and calls neither the GPU nor the recogniser. The recogniser never needs the lease: it is a
  network call, and the contract runs it after the lease on purpose.
- qwen27b (low) "lock_precheck.py is not in DECODER_SHA": by design. The sha names the code that makes the decode and
  the lock (the render's own). lock_precheck.py only routes requests, and a change to it does not change what the
  render locks.
