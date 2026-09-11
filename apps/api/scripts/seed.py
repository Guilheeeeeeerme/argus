#!/usr/bin/env python3
"""Back-compat entry: demo seed only. Platform ROOT is seed_platform / bootstrap."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

# Re-export demo seed as the historical `seed.py` target for local tools/tests.
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from seed_demo import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
