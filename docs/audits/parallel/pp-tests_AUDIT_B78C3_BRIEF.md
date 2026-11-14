# AUDIT BRIEF — pp-tests (tests only): the integrator's batch 78 cycle-3 finding (a side read through a child process)

## THE LAWS (the session's rules, the integrator's message verbatim, what was done and measured, what to check)

Session pipeline_pp_tests writes TESTS ONLY (tests/adversarial/, docs/audits/parallel/pp-tests_*.md). Rules: never
change what a check accepts in order to make something pass; nothing measured is never a pass (L-m); fail closed
(L-j); preconditions are `pytest.fail` (H.control); CPU only, no network, no GPU. Secrets are read only by NAME and
never printed. Only report what you can verify from the diff. If uncertain, say so.

### The integrator's message (2026-11-14 ~09:30 ET, verbatim essentials)
Integrator: batch 78 cycle 3 (verification of a55e4dcf). The behavioural test is good. Grok PASS, 0 findings. ONE
CONSENSUS FINDING (glm F1, agreed by qwen27b), narrow but true, and the last thing before I merge:
- The "nothing opened" guarantee covers only open / io.open / os.open.
- A _key that ALSO reads the key file through a subprocess (subprocess.run / Popen / os.system / os.posix_spawn /
  os.exec*), then discards the result and returns the loader's value, passes every assertion. The sentinel check
  catches a _key that RETURNS such a read, not a side read.
- FIX: during the two calls, also deny subprocess.Popen (subprocess.run and check_output go through it), os.system,
  os.posix_spawn / posix_spawnp and os.exec*. Raise a BaseException and record the attempts, as you do for open. Add
  one scratch mutation that side-reads via subprocess and must fail. Nothing else changes.
REFUTED by the integrator, no change: "the bytecode-flag assert breaks under -B"; "a key value can leak" (failures
print types and names only).

### What pp-tests did (THE DIFF: CURRENT.diff; test_f0_cpu_guard.py and BIBLE_ADDITIONS only)
- `_FileOpened` became `_Denied` (a BaseException): a file opened OR a process started.
- `_check_key_behaviour` denies, during the two calls, and restores in the finally:
  - files: builtins.open, io.open, os.open;
  - processes: subprocess.Popen (run / check_output / call / os.popen go through it) and every os starter present
    (system, popen, posix_spawn, posix_spawnp, fork, forkpty, the exec* family, the spawn* family; os.spawn* go
    through os.fork).
  Each records `<module>.<name>(<first arg>)` and raises _Denied. The assertion: `denied == []`, "_key opened a file
  or started a process".
- Mutations: scratch copies of frontier_blind with `_key` replaced, each in its own process, run with bytecode on AND
  under -B, under the suite's own guards (as in pytest).
  - Three SIDE-READ mutations read the loader file, discard the result and then behave exactly like the real _key:
    - M6: a Python child with no pipes. The suite's conftest allows Python children, and with pipes subprocess
      opens their fds through io.open, which was already denied; so the no-pipe form is the real gap.
    - M7: os.system("cat ... > /dev/null").
    - M8: os.posix_spawn("/bin/cat", ...).
  - Against the PREVIOUS test (a55e4dcf) all three PASSED (measured), which confirms the finding. Against the new
    test all three FAIL, naming subprocess.Popen / os.system / os.posix_spawn.
  - The real _key passes. M1-M5 still fail on their own assertions: parse with open; parse through os.open; bypass
    the loader; the sys.path form; bytecode left on. Nothing is left in sys.modules.
- The boundary is measured and documented. _io.open cannot be denied, because io.open_code calls it to read the
  stub's source: denying it broke the load. So io.FileIO, a reference to open bound before the call (tokenize.open)
  and C-level calls (ctypes) are NOT denied; such a _key is caught only if what it returns is not the loader's value.
  Only a process-wide audit hook would see those; it was not added (the integrator: "Nothing else changes").
- BIBLE PP-E32: the rule now says to deny EVERY route to the forbidden effect, and lists what is not denied.
- Measured: test_f0 10 passed.

### What to check (answer each; cite the diff line)
A. Is any Python-level route to starting a process during the calls still open (outside the documented boundary)?
B. Is patching and restoring subprocess.Popen (a class) and the os functions safe? Is everything restored on every
   path? Does the suite's own conftest guard on Popen.__init__ survive?
C. Is the documented boundary accurate and honestly stated?
D. Does anything in the diff loosen what a check accepts?
