"""FastAPI security dependencies and request auth wiring."""

from argus.core.auth import (
    AuthContext,
    get_auth_context,
    get_authenticated_db,
    require_role,
    set_tenant_context,
)

__all__ = [
    "AuthContext",
    "get_auth_context",
    "get_authenticated_db",
    "require_role",
    "set_tenant_context",
]
