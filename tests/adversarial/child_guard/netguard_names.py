"""The network calls EVERY guard of this suite refuses: one list for the three guards (integrator batch 78, Gemini:
the runner's own list had drifted, gethostbyaddr missing, and getnameinfo was missing from all three):
  - conftest.py in the test process (install / remove),
  - child_guard/sitecustomize.py in every Python child the suite starts,
  - moments_exam.refuse_network in the exam runner.
Each guard imports these two tuples; none keeps a list of its own. The list is shared; each guard's exception type and
restore behaviour stay its own (the type names the guard that refused). Importing this module patches nothing.
"""
INET_METHODS = ("connect", "connect_ex", "sendto", "sendmsg")      # socket.socket methods, refused for AF_INET(6)
LOOKUPS = ("getaddrinfo", "gethostbyname", "gethostbyname_ex",     # socket functions: every name lookup,
           "gethostbyaddr", "getnameinfo")                         # forward and reverse


def refused_target(name, args):
    """Where a refused INET_METHODS call was going, for the refusal's message only: connect's address, sendto's last
    argument, sendmsg's fourth; a sendmsg without one goes to the socket's connected peer (batch 78 cycle 2, glm: the
    last argument of such a call is its flags)."""
    if name in ("connect", "connect_ex"):
        return args[0] if args else "?"
    if name == "sendto":
        return args[-1] if len(args) > 1 else "?"
    return args[3] if len(args) > 3 else "its connected peer"
