import os
import socket
from app import app

def find_free_port(start=5001, max_tries=5):
    """Try start, start+1, ... until we find a free port."""
    for i in range(max_tries):
        port = start + i
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(("127.0.0.1", port))
                return port
        except OSError:
            continue
    return start  # fallback, Flask will error if still in use

# Use PORT env if set, else first free port from 5001
PORT = int(os.environ.get("PORT", 0)) or find_free_port(5001)

if __name__ == "__main__":
    print(f" * Protocol Pulse on http://127.0.0.1:{PORT}")
    app.run(host="127.0.0.1", port=PORT, debug=True, use_reloader=False)
