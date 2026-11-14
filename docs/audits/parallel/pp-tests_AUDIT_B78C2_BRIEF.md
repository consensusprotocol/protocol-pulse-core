# AUDIT BRIEF — pp-tests (tests only): the integrator's batch 78 cycle-2 finding (a key test that pinned configuration)

## THE LAWS (the session's rules, the integrator's message verbatim, the code under test, and what to check)

Session pipeline_pp_tests writes TESTS ONLY (tests/adversarial/, docs/audits/parallel/pp-tests_*.md). Rules: never
change what a check accepts in order to make something pass; nothing measured is never a pass (L-m); fail closed
(L-j); every precondition is `pytest.fail` (adv_helpers.control: H.control); CPU only, no network, no GPU. Secrets:
keys are read only by NAME inside code and never printed, logged or written. Only report what you can verify from the
diff and the excerpt below. If uncertain, say so.

### The integrator's message (2026-11-14 ~09:00 ET, verbatim essentials)
Integrator: batch 78 cycle 2. Both cycle-1 findings are FIXED and verified in d7ed4ff8. ONE NEW CONSENSUS FINDING
(qwen27b + glm + Grok: same test, same root cause). The merge stays HELD until it is fixed:
- test_f0::test_keys_are_read_only_by_name_through_the_pipelines_loader pins configuration, not behaviour:
  `assert FB.KEY_LOADER == "<main tree>/video_pipeline_v3/relay.py"` restates the constant; `".get_key" in
  inspect.getsource(FB._key) and "open(" not in src` is a string search of the source.
- KEEP the AST scan for key-file strings (a real guard; your mutation proved it).
- ADD a behavioural check: load frontier_blind with a stub loader (a module whose get_key records its argument and
  returns a sentinel), via KEY_LOADER pointed at a stub file or by monkeypatching the loading seam; assert
  _key("XAI_API_KEY") returns the sentinel and the stub saw exactly that name; assert no file is opened during the
  call (builtins.open patched to raise). Show it fails on a _key that parses a file (a scratch mutation).
- Drop the path-equality assert, or keep it only as a labelled control. Your call.

### What pp-tests did (THE DIFF: CURRENT.diff; test_f0_cpu_guard.py and BIBLE_ADDITIONS only)
- The old test is split. test_no_file_of_this_suite_names_the_key_file keeps the AST scan unchanged. The source
  search and the path equality are gone from it.
- New test_the_baseline_reads_a_key_only_by_name_through_its_loader:
  - It loads a FRESH copy of baselines/frontier_blind.py by path; its top level only sets constants, so its loader is
    not loaded yet. It points the copy's KEY_LOADER at a stub loader file in tmp_path. The stub's get_key records each
    name in a module the test owns and returns a sentinel; the stub also counts its loads.
  - It calls _key("XAI_API_KEY") and _key("OPENAI_API_KEY") with builtins.open AND io.open patched to raise a
    BaseException (so an `except Exception` in the code under test cannot hide it). The attempts are recorded either
    way. Measured: the import machinery reads source through io.open_code, so loading the stub is not affected.
  - It asserts: no open() attempt; both returns are the sentinel (a failure shows the types, never the values, since a
    broken _key could return a real key); the stub saw exactly those two names and was loaded once; sys.path and
    sys.dont_write_bytecode as before; no __pycache__ beside the stub.
  - The path equality is kept only as a labelled H.control: "configuration pin: the production key loader is ...".
- Scratch mutations (copies of frontier_blind.py with _key replaced, each in its own process, bytecode writing on):
  - real _key: PASSES;
  - a _key that parses a file (open(KEY_LOADER) and splits "name=value"): FAILS, "_key opened a file: [<stub>]";
  - a _key that bypasses the loader (returns a constant): FAILS, "did not return the loader's value: ['str', 'str']";
  - grok_audit.py's form (sys.path.insert + __import__): FAILS, "_key changed sys.path";
  - the real form without the bytecode flag: FAILS, "bytecode was written beside the loader".
- BIBLE PP-E32: a check that reads the source or restates a constant tests configuration, not behaviour.
- Measured: test_f0 10 passed.

### The code under test: frontier_blind's key reader (unchanged in this diff)
```
_GET_KEY = []


def _key(name):
    """The key named `name`, from relay.get_key (the process environment first, then the project's key files; a
    missing key raises KeyError; a missing loader file raises FileNotFoundError naming it). Called under _TLOCK (from
    _client). sys.dont_write_bytecode is process-wide: while the loader loads (once), an import by another thread
    would skip writing its own .pyc too, which is harmless."""
    if not _GET_KEY:
        import importlib.util
        import sys
        spec = importlib.util.spec_from_file_location("_pp_baseline_relay", KEY_LOADER)
        mod = importlib.util.module_from_spec(spec)
        prev, sys.dont_write_bytecode = sys.dont_write_bytecode, True     # no __pycache__ in the main tree
        try:
            spec.loader.exec_module(mod)
        finally:
            sys.dont_write_bytecode = prev
        _GET_KEY.append(mod.get_key)
    return _GET_KEY[0](name)


```

### What to check (answer each; cite the diff line)
A. Does the new test check BEHAVIOUR? Name any _key that would pass it while reading a key some other way than the
   loader's get_key (another file API: pathlib, os.open, io.FileIO; a subprocess; the environment).
B. Is patching builtins.open and io.open during the call sound? Does it break pytest or the import machinery? Is
   everything restored on every path?
C. Can the test leak a key in a failure message or a traceback?
D. Is the fresh module copy and the stub-record module isolated and cleaned up (sys.modules, the global flag)?
E. Is the labelled configuration control the right strength, or should it be dropped?
F. Does anything in the diff loosen what a check accepts?
