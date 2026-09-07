#!/usr/bin/env python3
"""Run seed.py (T028 alias)."""

import subprocess
import sys
from pathlib import Path

if __name__ == "__main__":
    seed = Path(__file__).with_name("seed.py")
    raise SystemExit(subprocess.call([sys.executable, str(seed)]))
