"""Retired — Rule admin routes removed from MVP API surface."""

from fastapi import APIRouter

router = APIRouter(prefix="/_retired/rules", include_in_schema=False)
