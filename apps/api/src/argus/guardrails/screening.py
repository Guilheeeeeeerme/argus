"""Deterministic policy screening executed before any LLM call."""

from __future__ import annotations

from dataclasses import dataclass

from argus.guardrails.registry import get_registry


@dataclass(frozen=True)
class PolicyHit:
    policy_id: str
    severity: str
    action: str


def screen(text: str) -> list[PolicyHit]:
    """Screen text against registry policies. Never returns matched snippets."""
    if not text:
        return []
    hits: list[PolicyHit] = []
    for policy in get_registry().policies:
        for pattern in policy.patterns:
            match = pattern.search(text)
            if match is None:
                continue
            hits.append(PolicyHit(policy.id, policy.severity, policy.action))
            break
    return hits


def is_blocked(text: str) -> bool:
    return any(hit.action == "block" for hit in screen(text))
