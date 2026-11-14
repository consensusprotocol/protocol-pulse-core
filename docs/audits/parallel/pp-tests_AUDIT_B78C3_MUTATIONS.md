# pp-tests — scratch mutations of frontier_blind._key against test_f0's behavioural key test (batch 78 cycles 2-3)

Evidence for test_f0::test_the_baseline_reads_a_key_only_by_name_through_its_loader. Recorded 2026-11-14, kept in the
repo on the integrator panel's request (batch 78 cycle 3, glm P1: the mutation evidence was not in the diff).

How it was run:
- Each mutation is a copy of tests/adversarial/baselines/frontier_blind.py with `_key` replaced. The copies were in
  the session's scratchpad, never in the worktree.
- Each was loaded by test_f0's own `_load_frontier_blind(path)` and checked by its own `_check_key_behaviour`. The
  test's assertions are therefore exactly the ones the wall runs.
- Each ran in its own process, under the suite's guards (conftest imported, as in pytest).
- Every mutation ran twice: with bytecode writing on, and under `python3 -B`.
- The side reads read the STUB loader file in a temporary directory. No key file was read by any mutation.
- The last block re-runs the three side reads against the PREVIOUS version of the test (a55e4dcf), loaded the same
  way. They pass there: that is the gap cycle 3 found.

## The `_key` of each mutation

### M0_real
```python
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

### M1_parses_a_file
```python
def _key(name):
    with open(KEY_LOADER) as f:
        for line in f:
            k, _, v = line.partition("=")
            if k.strip() == name:
                return v.strip()
    raise KeyError(name)
```

### M2_bypasses_the_loader
```python
def _key(name):
    return "not-from-the-loader"
```

### M3_sys_path_form
```python
def _key(name):
    if not _GET_KEY:
        import sys
        sys.path.insert(0, os.path.dirname(KEY_LOADER))
        mod = __import__(os.path.splitext(os.path.basename(KEY_LOADER))[0])
        _GET_KEY.append(mod.get_key)
    return _GET_KEY[0](name)
```

### M4_bytecode_flag_left_alone
```python
def _key(name):
    if not _GET_KEY:
        import importlib.util
        spec = importlib.util.spec_from_file_location("_pp_baseline_relay", KEY_LOADER)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        _GET_KEY.append(mod.get_key)
    return _GET_KEY[0](name)
```

### M5_parses_through_os_open
```python
def _key(name):
    fd = os.open(KEY_LOADER, os.O_RDONLY)
    try:
        data = os.read(fd, 1 << 16).decode()
    finally:
        os.close(fd)
    for line in data.splitlines():
        k, _, v = line.partition("=")
        if k.strip() == name:
            return v.strip()
    raise KeyError(name)
```

### M6_side_read_via_python_child
```python
def _key(name):
    """The key named `name`, from relay.get_key (the process environment first, then the project's key files; a
    missing key raises KeyError; a missing loader file raises FileNotFoundError naming it). Called under _TLOCK (from
    _client). sys.dont_write_bytecode is process-wide: while the loader loads (once), an import by another thread
    would skip writing its own .pyc too, which is harmless."""
    import subprocess as _sp, sys as _sys          # a SIDE read of the loader file through a child, result discarded
    _sp.run([_sys.executable, "-c", "import sys; open(sys.argv[1]).read()", KEY_LOADER])     # no pipes
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

### M7_side_read_via_os_system
```python
def _key(name):
    """The key named `name`, from relay.get_key (the process environment first, then the project's key files; a
    missing key raises KeyError; a missing loader file raises FileNotFoundError naming it). Called under _TLOCK (from
    _client). sys.dont_write_bytecode is process-wide: while the loader loads (once), an import by another thread
    would skip writing its own .pyc too, which is harmless."""
    os.system(f"cat {KEY_LOADER} > /dev/null")      # a SIDE read through a shell, result discarded
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

### M8_side_read_via_posix_spawn
```python
def _key(name):
    """The key named `name`, from relay.get_key (the process environment first, then the project's key files; a
    missing key raises KeyError; a missing loader file raises FileNotFoundError naming it). Called under _TLOCK (from
    _client). sys.dont_write_bytecode is process-wide: while the loader loads (once), an import by another thread
    would skip writing its own .pyc too, which is harmless."""
    _pid = os.posix_spawn("/bin/cat", ["cat", KEY_LOADER], {})   # a SIDE read, a spawned process, result discarded
    os.waitpid(_pid, 0)
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

## Results (verbatim; temporary directories shown as <tmp>; long lines cut at 170 characters; re-run after
the cycle-2 edits: the starter list's self-check and the corrected boundary comment)
```
### python3  (bytecode on)
M0_real.py -> PASSES
M1_parses_a_file.py -> FAILS: _key opened a file or started a process: ["builtins.open('<tmp>/relay_stub.py')", "builtins.open('/
M2_bypasses_the_loader.py -> FAILS: _key did not return the loader's value: ['str', 'str']
M3_sys_path_form.py -> FAILS: _key changed sys.path
M4_bytecode_flag_left_alone.py -> FAILS: bytecode was written beside the loader
M5_parses_through_os_open.py -> FAILS: _key opened a file or started a process: ["os.open('<tmp>/relay_stub.py')", "os.open('/tmp/tmpqcpf6
M6_side_read_via_python_child.py -> FAILS: _key opened a file or started a process: ["subprocess.Popen(['/usr/bin/python3', '-c', 'import sys; open(sys.a
M7_side_read_via_os_system.py -> FAILS: _key opened a file or started a process: ["os.system('cat <tmp>/relay_stub.py > /dev/null')", "os.s
M8_side_read_via_posix_spawn.py -> FAILS: _key opened a file or started a process: ["os.posix_spawn('/bin/cat')", "os.posix_spawn('/bin/cat')"]
### python3 -B (bytecode suppressed by -B)
M0_real.py -> PASSES
M1_parses_a_file.py -> FAILS: _key opened a file or started a process: ["builtins.open('<tmp>/relay_stub.py')", "builtins.open('/
M2_bypasses_the_loader.py -> FAILS: _key did not return the loader's value: ['str', 'str']
M3_sys_path_form.py -> FAILS: _key changed sys.path
M4_bytecode_flag_left_alone.py -> FAILS: bytecode was written beside the loader
M5_parses_through_os_open.py -> FAILS: _key opened a file or started a process: ["os.open('<tmp>/relay_stub.py')", "os.open('/tmp/tmpiopjc
M6_side_read_via_python_child.py -> FAILS: _key opened a file or started a process: ["subprocess.Popen(['/usr/bin/python3', '-c', 'import sys; open(sys.a
M7_side_read_via_os_system.py -> FAILS: _key opened a file or started a process: ["os.system('cat <tmp>/relay_stub.py > /dev/null')", "os.s
M8_side_read_via_posix_spawn.py -> FAILS: _key opened a file or started a process: ["os.posix_spawn('/bin/cat')", "os.posix_spawn('/bin/cat')"]
### the three side reads against the PREVIOUS test (a55e4dcf)
M6_side_read_via_python_child.py -> PASSES the previous test
M7_side_read_via_os_system.py -> PASSES the previous test
M8_side_read_via_posix_spawn.py -> PASSES the previous test
```
