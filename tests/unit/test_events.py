"""Unit tests for the event system."""
import json
import pytest
from datetime import datetime
from genworlds.events.abstracts.event import AbstractEvent


class ConcreteEvent(AbstractEvent):
    event_type: str = "test_event"
    description: str = "A test event."
    sender_id: str
    payload: str = ""


class TestAbstractEvent:
    def test_required_fields(self):
        ev = ConcreteEvent(sender_id="agent-1")
        assert ev.event_type == "test_event"
        assert ev.sender_id == "agent-1"
        assert ev.target_id is None

    def test_created_at_defaults_to_now(self):
        before = datetime.now()
        ev = ConcreteEvent(sender_id="agent-1")
        after = datetime.now()
        assert before <= ev.created_at <= after

    def test_serialise_round_trip(self):
        ev = ConcreteEvent(sender_id="a", target_id="b", payload="hello")
        raw = ev.model_dump_json()
        reloaded = ConcreteEvent.model_validate_json(raw)
        assert reloaded.sender_id == ev.sender_id
        assert reloaded.target_id == ev.target_id
        assert reloaded.payload == ev.payload

    def test_model_validate_from_dict(self):
        data = {
            "event_type": "test_event",
            "description": "desc",
            "sender_id": "x",
            "created_at": datetime.now().isoformat(),
        }
        ev = ConcreteEvent.model_validate(data)
        assert ev.sender_id == "x"
