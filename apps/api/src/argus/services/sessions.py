"""Opaque Redis-backed user sessions."""

from __future__ import annotations

import json
import secrets
from dataclasses import dataclass

from argus.services.redis import get_redis

SESSION_PREFIX = "argus:session:"
SESSION_TTL_SECONDS = 604800  # 7 days


@dataclass
class SessionData:
    user_id: str
    email: str
    role: str
    account_id: str | None = None
    unit_id: str | None = None

    # Deprecated aliases (one release): sessions written before the Account/Unit rename
    # live up to 7 days in Redis, and in-process callers may still use the old names.
    @property
    def company_id(self) -> str | None:
        return self.account_id

    @company_id.setter
    def company_id(self, value: str | None) -> None:
        self.account_id = value

    @property
    def establishment_id(self) -> str | None:
        return self.unit_id

    @establishment_id.setter
    def establishment_id(self, value: str | None) -> None:
        self.unit_id = value

    def to_redis(self) -> str:
        # New keys only; `from_redis` keeps reading the legacy ones.
        return json.dumps(
            {
                "user_id": self.user_id,
                "email": self.email,
                "role": self.role,
                "account_id": self.account_id,
                "unit_id": self.unit_id,
            }
        )

    @classmethod
    def from_redis(cls, raw: str) -> SessionData:
        data = json.loads(raw)
        return cls(
            user_id=data.get("user_id", ""),
            email=data.get("email", ""),
            role=data.get("role", ""),
            account_id=data.get("account_id") or data.get("company_id"),
            unit_id=data.get("unit_id") or data.get("establishment_id") or data.get("location_id"),
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
