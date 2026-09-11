"""Negative discard — drop non-hits; no Detection / TriageCase / Redis publish.

AI Engineering pattern: Negative discard.
"""

from __future__ import annotations

import logging
from typing import Any

from argus_prompt_eval.structured_output import PromptEvalResult

logger = logging.getLogger(__name__)


def should_discard(result: PromptEvalResult) -> bool:
    """True when nothing matched above threshold."""
    if not result.any_match:
        return True
    return not any(hit.matched for hit in result.prompt_hits)


def discard_sequence(
    *,
    sequence_id: str,
    reason: str,
    frame_uris: list[str] | None = None,
    extra: dict[str, Any] | None = None,
) -> None:
    """Log discard. Frames remain TTL-bound in object storage; no DB row."""
    logger.info(
        "negative_discard sequence_id=%s reason=%s frames=%s extra=%s",
        sequence_id,
        reason,
        len(frame_uris or []),
        extra or {},
    )
