"""Structured HTTP error responses for FastAPI apps."""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException


def _error_body(
    *,
    status_code: int,
    code: str,
    message: str,
    details: Any = None,
) -> dict[str, Any]:
    body: dict[str, Any] = {
        "error": {
            "code": code,
            "message": message,
            "status": status_code,
        }
    }
    if details is not None:
        body["error"]["details"] = details
    return body


async def http_exception_handler(
    request: Request,
    exc: StarletteHTTPException,
) -> JSONResponse:
    code_map = {
        401: "unauthorized",
        403: "forbidden",
        409: "conflict",
        422: "unprocessable_entity",
    }
    code = code_map.get(exc.status_code, "http_error")
    detail = exc.detail
    if isinstance(detail, dict):
        message = detail.get("message", str(detail))
        details = detail.get("details")
    else:
        message = str(detail)
        details = None
    return JSONResponse(
        status_code=exc.status_code,
        content=_error_body(
            status_code=exc.status_code,
            code=code,
            message=message,
            details=details,
        ),
    )


async def validation_exception_handler(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=_error_body(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            code="validation_error",
            message="Request validation failed",
            details=exc.errors(),
        ),
    )


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
