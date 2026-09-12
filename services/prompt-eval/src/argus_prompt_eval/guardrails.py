"""Prompt fencing / screening — OWASP-style LLM01/LLM02 mitigations.

AI Engineering pattern: Prompt fencing / screening (guardrails).
Adapted from apps/api guardrails; PromptSet vocabulary only (no Recipe/Rule).
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)

REGISTRY_VERSION = 1
REGISTRY_FILENAME = "registry.yml"
FENCE_PROMPT_ID = "context.fence"


class RegistryError(RuntimeError):
    pass


@dataclass(frozen=True)
class PromptSpec:
    id: str
    kind: str
    purpose: str
    template: str


@dataclass(frozen=True)
class PolicySpec:
    id: str
    severity: str
    action: str
    patterns: tuple[re.Pattern[str], ...]


@dataclass(frozen=True)
class PolicyHit:
    policy_id: str
    severity: str
    action: str


@dataclass(frozen=True)
class GuardrailRegistry:
    prompts: tuple[PromptSpec, ...]
    policies: tuple[PolicySpec, ...]

    def get_prompt(self, prompt_id: str) -> str:
        for prompt in self.prompts:
            if prompt.id == prompt_id:
                return prompt.template
        raise RegistryError(f"Prompt not found in registry: {prompt_id}")


def _candidate_paths() -> list[Path]:
    return [
        Path(__file__).resolve().parent / REGISTRY_FILENAME,
        Path.cwd() / REGISTRY_FILENAME,
        Path.cwd() / "guardrails" / REGISTRY_FILENAME,
    ]


def _validate(data: dict[str, Any], path: Path) -> GuardrailRegistry:
    if data.get("version") != REGISTRY_VERSION:
        raise RegistryError(
            f"Guardrail registry {path} must declare version: {REGISTRY_VERSION}"
        )
    prompts_raw = data.get("prompts")
    policies_raw = data.get("policies")
    if not isinstance(prompts_raw, list) or not prompts_raw:
        raise RegistryError(f"Guardrail registry {path} needs non-empty prompts")
    if not isinstance(policies_raw, list) or not policies_raw:
        raise RegistryError(f"Guardrail registry {path} needs non-empty policies")

    prompts: list[PromptSpec] = []
    seen: set[str] = set()
    for item in prompts_raw:
        if not isinstance(item, dict):
            raise RegistryError(f"Invalid prompt entry in {path}")
        pid = item.get("id")
        if not isinstance(pid, str) or pid in seen:
            raise RegistryError(f"Duplicate or invalid prompt id in {path}")
        seen.add(pid)
        prompts.append(
            PromptSpec(
                id=pid,
                kind=str(item.get("kind", "")),
                purpose=str(item.get("purpose", "")),
                template=str(item.get("template", "")),
            )
        )

    policies: list[PolicySpec] = []
    seen_p: set[str] = set()
    for item in policies_raw:
        if not isinstance(item, dict):
            raise RegistryError(f"Invalid policy entry in {path}")
        pid = item.get("id")
        if not isinstance(pid, str) or pid in seen_p:
            raise RegistryError(f"Duplicate or invalid policy id in {path}")
        seen_p.add(pid)
        raw_patterns = item.get("patterns") or []
        compiled: list[re.Pattern[str]] = []
        for pattern in raw_patterns:
            try:
                compiled.append(re.compile(str(pattern)))
            except re.error as exc:
                raise RegistryError(
                    f"Malformed regex in policy {pid} ({path}): {exc}"
                ) from exc
        policies.append(
            PolicySpec(
                id=pid,
                severity=str(item.get("severity", "medium")),
                action=str(item.get("action", "block")),
                patterns=tuple(compiled),
            )
        )
    return GuardrailRegistry(prompts=tuple(prompts), policies=tuple(policies))


@lru_cache
def get_registry() -> GuardrailRegistry:
    for path in _candidate_paths():
        if not path.is_file():
            continue
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise RegistryError(f"Guardrail registry {path} must be a mapping")
        logger.info("Loaded guardrail registry from %s", path)
        return _validate(data, path)
    raise RegistryError("No guardrail registry.yml found")


_PLACEHOLDER = re.compile(r"\{\{\s*([a-zA-Z0-9_]+)\s*\}\}")

# The payload must never be able to emit the fence markers itself: webhook
# context containing END_UNTRUSTED_VLM_CONTEXT would otherwise close the data
# block early and have its remaining text read as instructions (LLM01).
_FENCE_MARKERS = re.compile(r"(BEGIN|END)_UNTRUSTED_VLM_CONTEXT")

# Invisible to a human reviewer, visible to the model: Unicode tag block
# (smuggled ASCII), zero-width characters, and bidi overrides. These are the
# encoding axis of prompt injection in OWASP LLM01.
_INVISIBLE = re.compile(
    "[\u200b-\u200f\u202a-\u202e\u2060-\u2064\u2066-\u2069\ufeff"
    "\U000e0000-\U000e007f]"
)


def render_prompt(prompt_id: str, values: dict[str, str]) -> str:
    """Substitute placeholders in a single pass.

    Sequential per-key replacement would let an earlier value inject a literal
    ``{{other_key}}`` that a later iteration then expands (LLM01).
    """
    template = get_registry().get_prompt(prompt_id)

    def substitute(match: re.Match[str]) -> str:
        return values.get(match.group(1), match.group(0))

    return _PLACEHOLDER.sub(substitute, template)


def neutralize(payload: str) -> str:
    """Strip invisible characters and defang fence markers in untrusted text."""
    return _FENCE_MARKERS.sub(
        r"\1_UNTRUSTED_VLM_CONTEXT_NEUTRALIZED", _INVISIBLE.sub("", payload)
    )


def fence(payload: str) -> str:
    """Wrap untrusted payload in registry fence markers (data, not instructions)."""
    return (
        get_registry()
        .get_prompt(FENCE_PROMPT_ID)
        .replace("{{payload}}", neutralize(payload))
    )


def screen(text: str) -> list[PolicyHit]:
    """Screen text against registry policies. Never returns matched snippets."""
    if not text:
        return []
    hits: list[PolicyHit] = []
    for policy in get_registry().policies:
        for pattern in policy.patterns:
            if pattern.search(text) is None:
                continue
            hits.append(PolicyHit(policy.id, policy.severity, policy.action))
            break
    return hits


def is_blocked(text: str) -> bool:
    return any(hit.action == "block" for hit in screen(text))
