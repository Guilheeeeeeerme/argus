"""Strict guardrail registry loader. Fails closed on any violation."""

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

_PROMPT_KEYS = ("id", "kind", "purpose", "template")
_POLICY_KEYS = ("id", "severity", "action", "patterns")
_FINAL_ACTION = "block"


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
class GuardrailRegistry:
    prompts: tuple[PromptSpec, ...]
    policies: tuple[PolicySpec, ...]

    def get_prompt(self, prompt_id: str) -> str:
        for prompt in self.prompts:
            if prompt.id == prompt_id:
                return prompt.template
        raise RegistryError(f"Prompt not found in registry: {prompt_id}")


def registry_candidate_paths() -> list[Path]:
    return [
        Path(__file__).resolve().parent / REGISTRY_FILENAME,
        Path.cwd() / REGISTRY_FILENAME,
        Path.cwd() / "guardrails" / REGISTRY_FILENAME,
    ]


def _load_yaml(path: Path) -> dict[str, Any]:
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise RegistryError(f"Invalid YAML in guardrail registry {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise RegistryError(f"Guardrail registry {path} must be a mapping")
    return data


def _validate(data: dict[str, Any], path: Path) -> GuardrailRegistry:
    if data.get("version") != REGISTRY_VERSION:
        raise RegistryError(
            f"Guardrail registry {path} must declare version: {REGISTRY_VERSION}"
        )

    prompts = _validate_prompts(data.get("prompts"), path)
    policies = _validate_policies(data.get("policies"), path)
    return GuardrailRegistry(prompts=prompts, policies=policies)


def _validate_prompts(value: Any, path: Path) -> tuple[PromptSpec, ...]:
    if not isinstance(value, list) or not value:
        raise RegistryError(f"Guardrail registry {path} requires a non-empty prompts list")
    seen: set[str] = set()
    prompts: list[PromptSpec] = []
    for index, entry in enumerate(value):
        if not isinstance(entry, dict):
            raise RegistryError(f"Prompt entry {index} in {path} must be a mapping")
        _require_keys(entry, _PROMPT_KEYS, f"prompt entry {index}", path)
        prompt_id = entry["id"]
        if not isinstance(prompt_id, str) or not prompt_id.strip():
            raise RegistryError(f"Prompt entry {index} in {path} has an invalid id")
        if prompt_id in seen:
            raise RegistryError(f"Duplicate prompt id {prompt_id!r} in {path}")
        seen.add(prompt_id)
        for key in ("kind", "purpose", "template"):
            if not isinstance(entry[key], str) or not entry[key].strip():
                raise RegistryError(f"Prompt {prompt_id!r} field {key!r} must be a non-empty string")
        prompts.append(
            PromptSpec(
                id=prompt_id,
                kind=entry["kind"],
                purpose=entry["purpose"],
                template=entry["template"],
            )
        )
    return tuple(prompts)


def _validate_policies(value: Any, path: Path) -> tuple[PolicySpec, ...]:
    if not isinstance(value, list) or not value:
        raise RegistryError(f"Guardrail registry {path} requires a non-empty policies list")
    seen: set[str] = set()
    policies: list[PolicySpec] = []
    for index, entry in enumerate(value):
        if not isinstance(entry, dict):
            raise RegistryError(f"Policy entry {index} in {path} must be a mapping")
        _require_keys(entry, _POLICY_KEYS, f"policy entry {index}", path)
        policy_id = entry["id"]
        if not isinstance(policy_id, str) or not policy_id.strip():
            raise RegistryError(f"Policy entry {index} in {path} has an invalid id")
        if policy_id in seen:
            raise RegistryError(f"Duplicate policy id {policy_id!r} in {path}")
        seen.add(policy_id)
        for key in ("severity", "action"):
            if not isinstance(entry[key], str) or not entry[key].strip():
                raise RegistryError(f"Policy {policy_id!r} field {key!r} must be a non-empty string")
        if entry["action"] != _FINAL_ACTION:
            raise RegistryError(f"Policy {policy_id!r} action must be {_FINAL_ACTION!r}")
        patterns = entry["patterns"]
        if not isinstance(patterns, list) or not patterns:
            raise RegistryError(f"Policy {policy_id!r} requires a non-empty patterns list")
        compiled: list[re.Pattern[str]] = []
        for pattern in patterns:
            if not isinstance(pattern, str) or not pattern.strip():
                raise RegistryError(f"Policy {policy_id!r} patterns must be non-empty strings")
            try:
                compiled.append(re.compile(pattern))
            except re.error as exc:
                raise RegistryError(
                    f"Policy {policy_id!r} has an invalid regex {pattern!r}: {exc}"
                ) from exc
        policies.append(
            PolicySpec(
                id=policy_id,
                severity=entry["severity"],
                action=entry["action"],
                patterns=tuple(compiled),
            )
        )
    return tuple(policies)


def _require_keys(entry: dict[str, Any], keys: tuple[str, ...], label: str, path: Path) -> None:
    for key in keys:
        if key not in entry:
            raise RegistryError(f"{label.capitalize()} in {path} is missing required key {key!r}")


def load_registry(path: Path | None = None) -> GuardrailRegistry:
    candidates = [path] if path is not None else registry_candidate_paths()
    for candidate in candidates:
        if candidate.is_file():
            return _validate(_load_yaml(candidate), candidate)
    tried = ", ".join(str(c) for c in candidates)
    raise RegistryError(f"Guardrail registry file not found (tried: {tried})")


@lru_cache(maxsize=1)
def get_registry() -> GuardrailRegistry:
    registry = load_registry()
    logger.debug(
        "Guardrail registry loaded: %d prompts, %d policies",
        len(registry.prompts),
        len(registry.policies),
    )
    return registry


_PLACEHOLDER = re.compile(r"\{\{\s*([a-zA-Z0-9_]+)\s*\}\}")


def render_prompt(prompt_id: str, values: dict[str, str] | None = None) -> str:
    """Substitute placeholders in a single pass.

    Sequential per-key replacement would let an earlier value inject a literal
    ``{{other_key}}`` that a later iteration then expands, so a DB-sourced
    prompt fragment could reach into another slot (LLM01).
    """
    template = get_registry().get_prompt(prompt_id)
    supplied = values or {}

    def substitute(match: re.Match[str]) -> str:
        name = match.group(1)
        return supplied.get(name, match.group(0))

    return _PLACEHOLDER.sub(substitute, template)
