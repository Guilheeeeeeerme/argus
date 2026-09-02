"""FastAPI application factory for HTTP deployables."""

from fastapi import Depends, FastAPI

from argus.config import ServiceRole, settings
from argus.core.auth import AuthContext, get_auth_context
from argus.core.exceptions import register_exception_handlers
from argus.services.database import check_database_connection


def create_http_app(service_role: ServiceRole, title: str) -> FastAPI:
    app = FastAPI(title=title, version="0.1.0")
    register_exception_handlers(app)

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {
            "status": "ok",
            "service": service_role,
            "role": settings.service_role,
        }

    @app.get("/health/db")
    async def health_db() -> dict[str, bool | str]:
        ok = await check_database_connection()
        return {"database": ok}

    @app.get("/debug/auth")
    async def debug_auth(
        auth: AuthContext = Depends(get_auth_context),
    ) -> dict[str, str | None]:
        return {
            "sub": auth.sub,
            "tenant_id": str(auth.tenant_id) if auth.tenant_id else None,
            "role": auth.role.value,
        }

    return app
