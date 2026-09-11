"""Retired — Decision triage routes replaced by triage_cases."""

from fastapi import APIRouter

router = APIRouter(prefix="/_retired/decisions", include_in_schema=False)
