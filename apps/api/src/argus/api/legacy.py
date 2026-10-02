"""410 Gone for the pre-rename URL space (/v1/companies/*, /v1/admin/companies/*).

Clients ship in the same release as the rename; this router only turns a
confusing 404 into an explicit signal for stale deployments or integrations.
Remove in the release after the rename.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

router = APIRouter(tags=["legacy"], include_in_schema=False)

_DETAIL = "Renamed: use /v1/accounts/… (companies → accounts, establishments → units)"


def _gone() -> None:
    raise HTTPException(status_code=status.HTTP_410_GONE, detail=_DETAIL)


@router.api_route("/v1/companies/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
async def companies_gone(path: str) -> None:
    _gone()


@router.api_route("/v1/admin/companies/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
async def admin_companies_gone(path: str) -> None:
    _gone()


@router.api_route("/v1/admin/companies", methods=["GET", "POST"])
async def admin_companies_root_gone() -> None:
    _gone()


@router.get("/v1/auth/companies")
async def auth_companies_gone() -> None:
    _gone()
