"""
Quick GPU sanity check for the dual 4090 server.

Run from project root with the virtualenv active:
    source .venv/bin/activate
    python gpu_test.py
"""

import subprocess
import sys

try:
    import torch
except ImportError:
    print("torch is not installed in this environment. Activate the venv and run setup_server.sh first.")
    sys.exit(1)


def main() -> None:
    print("=== GPU Test ===")
    print(f"Python: {sys.version.split()[0]}")
    print(f"PyTorch version: {torch.__version__}")

    if not torch.cuda.is_available():
        print("CUDA is NOT available to PyTorch (torch.cuda.is_available() == False).")
    else:
        count = torch.cuda.device_count()
        print(f"CUDA is available. Detected {count} GPU(s).")
        for idx in range(count):
            name = torch.cuda.get_device_name(idx)
            print(f"  [{idx}] {name}")

    print("\n=== nvidia-smi ===")
    try:
        subprocess.run(["nvidia-smi"], check=False)
    except FileNotFoundError:
        print("nvidia-smi not found on PATH. Install NVIDIA drivers / CUDA toolkit.")


if __name__ == "__main__":
    main()

