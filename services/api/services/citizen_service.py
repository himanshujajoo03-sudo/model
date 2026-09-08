"""Citizen report business service."""

from .kafka_service import publish_citizen_event


def submit_report(event: dict) -> None:
    """Publish a fully normalized citizen event to citizen.raw; no DB write."""
    publish_citizen_event(event)
