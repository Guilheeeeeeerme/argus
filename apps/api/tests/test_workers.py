"""WS event helper contracts for MVP detection/triage publish shapes."""

from argus.services.ws_events import (
    EVENT_DETECTION_CREATED,
    EVENT_TRIAGE_UPDATED,
)


def test_ws_event_type_constants() -> None:
    assert EVENT_DETECTION_CREATED == "detection.created"
    assert EVENT_TRIAGE_UPDATED == "triage.updated"
