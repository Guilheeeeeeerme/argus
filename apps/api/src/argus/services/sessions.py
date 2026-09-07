"""Opaque Redis-backed user sessions."""

from __future__ import annotations

import json
import secrets
from dataclasses import asdict, dataclass

from argus.services.redis import get_redis

SESSION_PREFIX = "argus:session:"
SESSION_TTL_SECONDS = 604800  # 7 days


@dataclass
class SessionData:
    user_id: str
    email: str
    role: str
    company_id: str | None = None
    location_id: str | None = None

    def to_redis(self) -> str:
        return json.dumps(asdict(self))

    @classmethod
    def from_redis(cls, raw: str) -> SessionData:
        data = json.loads(raw)
        return cls(
            user_id=data.get("user_id", ""),
            email=data.get("email", ""),
            role=data.get("role", ""),
            company_id=data.get("company_id"),
            location_id=data.get("location_id"),
        )


def new_token() -> str:
    return f"sess_{secrets.token_urlsafe(32)}"


async def create_session(data: SessionData) -> str:
    token = new_token()
    await get_redis().set(SESSION_PREFIX + token, data.to_redis(), ex=SESSION_TTL_SECONDS)
    return token


async def get_session(token: str) -> SessionData | None:
    raw = await get_redis().get(SESSION_PREFIX + token)
    if raw is None:
        return None
    return SessionData.from_redis(raw)


async def update_session(token: str, data: SessionData) -> None:
    ttl = await get_redis().ttl(SESSION_PREFIX + token)
    if ttl < 0:
        ttl = SESSION_TTL_SECONDS
    await get_redis().set(SESSION_PREFIX + token, data.to_redis(), ex=ttl)


async def delete_session(token: str) -> None:
    await get_redis().delete(SESSION_PREFIX + token)
