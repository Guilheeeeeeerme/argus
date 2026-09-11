"""Retired — RuleSet admin routes removed from MVP API surface."""

from fastapi import APIRouter

router = APIRouter(prefix="/_retired/rule-sets", include_in_schema=False)
