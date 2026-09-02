"""Service entrypoint — routes by SERVICE_ROLE to HTTP or worker runtime."""

from __future__ import annotations

import logging
import sys

import uvicorn

from argus.apps.http import create_admin_app, create_ingest_app, create_ws_app
from argus.config import settings
from argus.core.logging import RequestContextMiddleware, configure_logging

logger = logging.getLogger(__name__)

HTTP_ROLES = frozenset({"api-admin", "api-ingest", "ws-gateway"})
WORKER_ROLES = frozenset(
    {"worker-vlm", "worker-aggregator", "worker-notify", "worker-scheduler"}
)


def _configure_logging() -> None:
    configure_logging()


def _attach_middleware(app) -> None:
    app.add_middleware(RequestContextMiddleware)


def _run_http_service() -> None:
    role = settings.service_role
    if role == "api-admin":
        app = create_admin_app()
    elif role == "api-ingest":
        app = create_ingest_app()
    elif role == "ws-gateway":
        app = create_ws_app()
    else:
        raise ValueError(f"Unsupported HTTP role: {role}")

    _attach_middleware(app)
    port = settings.resolved_api_port()
    logger.info("Starting %s on %s:%s", role, settings.api_host, port)
    uvicorn.run(app, host=settings.api_host, port=port, log_level=settings.log_level.lower())


def _run_worker_service() -> None:
    from argus.workers.runtime import run_worker_for_role

    role = settings.service_role
    logger.info("Starting Celery runtime for %s", role)
    run_worker_for_role(role)


def main() -> None:
    _configure_logging()
    role = settings.service_role
    logger.info("ARGUS backend starting with SERVICE_ROLE=%s", role)

    if role in HTTP_ROLES:
        _run_http_service()
    elif role in WORKER_ROLES:
        _run_worker_service()
    else:
        logger.error("Unknown SERVICE_ROLE: %s", role)
        sys.exit(1)


if __name__ == "__main__":
    main()
