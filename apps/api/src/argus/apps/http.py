"""FastAPI application factory for HTTP deployables."""

from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from argus.config import ServiceRole, Settings, settings
from argus.core.auth import AuthContext, get_auth_context
from argus.core.exceptions import register_exception_handlers
from argus.services.database import check_database_connection

RATE_LIMIT_EXEMPT_PATHS = frozenset(
    {"/health", "/health/db", "/docs", "/redoc", "/openapi.json"}
)


def _remote_address(request) -> str:
    client = request.client
    return client.host if client and client.host else "127.0.0.1"


def build_limiter(s: Settings) -> Limiter:
    return Limiter(
        key_func=_remote_address,
        default_limits=[f"{s.rate_limit_per_minute}/minute"],
        storage_uri=s.redis_url or "memory://",
        in_memory_fallback_enabled=True,
        key_style="url",
    )


class RateLimitExemptingMiddleware(SlowAPIMiddleware):
    async def dispatch(self, request, call_next):
        if request.url.path in RATE_LIMIT_EXEMPT_PATHS:
            return await call_next(request)
        return await super().dispatch(request, call_next)


def install_rate_limiting(app: FastAPI) -> None:
    limiter = build_limiter(settings)
    app.state.limiter = limiter
    app.add_middleware(RateLimitExemptingMiddleware)
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


def create_http_app(
    service_role: ServiceRole,
    title: str,
    lifespan=None,
) -> FastAPI:
    app = FastAPI(title=title, version="0.1.0", lifespan=lifespan)
    register_exception_handlers(app)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[o.strip() for o in settings.cors_origins.split(",") if o.strip()],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

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
            "company_id": str(auth.company_id) if auth.company_id else None,
            "role": auth.role.value,
        }

    return app


def create_admin_app() -> FastAPI:
    import asyncio
    from contextlib import asynccontextmanager

    from argus.api.admin.router import router as admin_router
    from argus.api.triage.router import router as triage_router
    from argus.ws.handlers import router as ws_router
    from argus.ws.pubsub import run_pubsub_listener

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        task = asyncio.create_task(run_pubsub_listener())
        yield
        task.cancel()

    app = create_http_app("api-admin", "ARGUS Admin & Triage API", lifespan=lifespan)
    install_rate_limiting(app)
    from argus.api.dev import router as dev_router
    from argus.api.auth import router as auth_router
    from argus.api.internal import router as internal_router

    app.include_router(dev_router)
    app.include_router(auth_router)
    app.include_router(internal_router)
    app.include_router(admin_router)
    app.include_router(triage_router)
    app.include_router(ws_router)
    return app


def create_ingest_app() -> FastAPI:
    from argus.api.ingest.router import router as ingest_router

    app = create_http_app("api-ingest", "ARGUS Ingest API")
    app.include_router(ingest_router)
    return app


def create_ws_app() -> FastAPI:
    import asyncio

    from argus.ws.handlers import router as ws_router
    from argus.ws.pubsub import run_pubsub_listener

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        task = asyncio.create_task(run_pubsub_listener())
        yield
        task.cancel()

    app = FastAPI(
        title="ARGUS WebSocket Gateway",
        version="0.1.0",
        lifespan=lifespan,
    )
    register_exception_handlers(app)

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok", "service": "ws-gateway", "role": settings.service_role}

    app.include_router(ws_router)
    return app
