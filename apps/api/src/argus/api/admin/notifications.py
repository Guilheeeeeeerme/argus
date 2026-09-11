"""Retired — notification admin routes removed from MVP API surface."""

from fastapi import APIRouter

router = APIRouter(prefix="/_retired/notifications", include_in_schema=False)
