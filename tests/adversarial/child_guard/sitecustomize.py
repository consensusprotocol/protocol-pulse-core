"""The adversarial suite's network guard for its PYTHON CHILD PROCESSES (integrator audit cycle 2, P0: a child
interpreter does not inherit the parent's socket patches). conftest.py puts this directory first on the PYTHONPATH of
every Python child the suite starts, so the interpreter imports this module at startup and the child refuses the
network like its parent: no AF_INET / AF_INET6 connect, connect_ex, sendto or sendmsg, no name lookup forward or
reverse (getaddrinfo, gethostbyname[_ex], gethostbyaddr, getnameinfo: the suite's one list, netguard_names.py, which
conftest.py and the exam runner use too). The one way around it is the documented opt-in
for a model-backed gate sitting the moments exam: PP_MOMENTS_ALLOW_NETWORK=1 in the child's environment
(test_moments_gates.py). Not a test module.
What it cannot reach (integrator batch 78, glm): it patches the socket module's functions when site imports it, after
site has processed the .pth files. Code run by a .pth file before that, which bound a socket function by name (`from
socket import getaddrinfo`), would keep the original. Checked 2026-11-14 on this interpreter: no .pth file binds a
socket function by name (only coloredlogs.pth can import socket, when COLOREDLOGS_AUTO_INSTALL is set, and coloredlogs
uses `socket.<name>` attribute access, which the patches reach). conftest.py refuses to start a Python child with
-I / -S / -E, the flags that skip this module."""
import os
import socket

if os.environ.get("PP_MOMENTS_ALLOW_NETWORK") != "1":
    class ChildNetworkBlocked(BaseException):
        """A BaseException, as in the parent: an `except Exception` in the child cannot swallow it."""

    def _blocked(what):
        raise ChildNetworkBlocked(f"tests/adversarial child: network is disabled in this suite ({what})")

    _INET = (socket.AF_INET, socket.AF_INET6)

    def _inet(name):
        real = getattr(socket.socket, name)

        def guarded(self, *a, **k):
            if self.family in _INET:
                _blocked(name)
            return real(self, *a, **k)
        guarded.__name__ = f"_child_no_{name}"
        return guarded

    def _lookup(name):
        def guarded(*a, **k):
            _blocked(name)
        guarded.__name__ = f"_child_no_{name}"
        return guarded

    from netguard_names import INET_METHODS, LOOKUPS     # the suite's one list (this directory, first on PYTHONPATH)

    for _n in INET_METHODS:
        setattr(socket.socket, _n, _inet(_n))
    for _n in LOOKUPS:
        setattr(socket, _n, _lookup(_n))
