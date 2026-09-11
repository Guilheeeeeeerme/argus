"""Shared fixtures and seed IDs for MVP API tests.

Seed IDs match apps/api/scripts/seed_demo.py.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

os.environ.setdefault("AUTH0_USE_MOCK", "true")
os.environ.setdefault("AUTH0_DOMAIN", "dev.argus.local")

# Allow importing prompt-eval pure helpers from services/prompt-eval.
_PROMPT_EVAL_SRC = Path(__file__).resolve().parents[3] / "services" / "prompt-eval" / "src"
if _PROMPT_EVAL_SRC.is_dir() and str(_PROMPT_EVAL_SRC) not in sys.path:
    sys.path.insert(0, str(_PROMPT_EVAL_SRC))

from argus.apps.http import create_admin_app  # noqa: E402
from argus.config import get_settings  # noqa: E402
from argus.services.database import dispose_engine  # noqa: E402
from argus.services.redis import close_redis  # noqa: E402

get_settings.cache_clear()

SEED_COMPANY_ID = "11111111-1111-4111-8111-111111111111"
SEED_ESTABLISHMENT_ID = "22222222-2222-4222-8222-222222222222"
SEED_CAMERA_ID = "33333333-3333-4333-8333-333333333333"
SEED_PROMPT_SET_ID = "55555555-5555-4555-8555-555555555555"
SEED_PROMPT_ID = "77777777-7777-4777-8777-777777777777"
SEED_WEBHOOK_ID = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
SEED_ROOT_EMAIL = "root@argus.local"
SEED_PASSWORD = "Password123!"

# Backward-compatible alias used by older test names.
SEED_LOCATION_ID = SEED_ESTABLISHMENT_ID


@pytest_asyncio.fixture
async def admin_client():
    transport = ASGITransport(app=create_admin_app())
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    await close_redis()
    await dispose_engine()


@pytest.fixture
def seed_ids() -> dict[str, str]:
    return {
        "company_id": SEED_COMPANY_ID,
        "establishment_id": SEED_ESTABLISHMENT_ID,
        "camera_id": SEED_CAMERA_ID,
        "prompt_set_id": SEED_PROMPT_SET_ID,
        "prompt_id": SEED_PROMPT_ID,
        "webhook_id": SEED_WEBHOOK_ID,
    }
