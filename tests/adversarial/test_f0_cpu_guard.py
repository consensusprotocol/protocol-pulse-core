"""The suite's own guard (order: no GPU at all; GPU0 is leased to the live run, GPU1 is quarantined): no CUDA device
is visible to any library, and every Whisper load a pipeline module could attempt is refused and recorded."""
import os

import pytest


def test_no_cuda_device_is_visible():
    import qa_gates  # noqa: F401  (sets CUDA_VISIBLE_DEVICES='0' at import; conftest undid it)
    assert os.environ.get("CUDA_VISIBLE_DEVICES") == ""


def test_no_network_connection_can_be_opened():
    """Telegram, the vision gateway and a model server are unreachable from this suite (a missing fake or a
    regressed send path raises instead of sending): IPv4 / IPv6, loopback included (Ollama listens on 127.0.0.1)."""
    import socket
    import urllib.request
    from adv_helpers import NetworkBlocked
    addrs = [("127.0.0.1", 11434), ("192.0.2.1", 443)]           # literal addresses: no DNS lookup
    try:                                                         # IPv6 only where the kernel has it (else socket()
        socket.socket(socket.AF_INET6).close()                   # itself fails before any connect)
        addrs.append(("::1", 11434))
    except OSError:
        pass
    for addr in addrs:
        with pytest.raises(NetworkBlocked, match="network is disabled"):
            socket.create_connection(addr, timeout=2)
    with pytest.raises(NetworkBlocked, match="network is disabled"):
        urllib.request.urlopen("http://127.0.0.1:11434/api/tags", timeout=2)
    try:                                                   # what a production `except Exception` would do
        socket.create_connection(("127.0.0.1", 9), timeout=2)
    except Exception:                                      # noqa: BLE001
        pytest.fail("the network guard was absorbed by `except Exception`")
    except NetworkBlocked:
        pass


def test_every_whisper_load_is_refused_and_recorded(whisper_attempts):
    import faster_whisper
    import word_diff
    with pytest.raises(RuntimeError, match="forbidden"):
        faster_whisper.WhisperModel("large-v3", device="cuda", compute_type="float16")
    with pytest.raises(RuntimeError, match="forbidden"):
        word_diff.Transcriber()                       # G18's default transcriber cannot start
    assert len(whisper_attempts()) == 2
