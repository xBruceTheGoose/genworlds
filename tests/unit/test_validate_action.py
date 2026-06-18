"""Unit tests for validate_action."""
import pytest
from genworlds.agents.utils.validate_action import validate_action


MOCK_SCHEMA = json.dumps({
    "title": "TestEvent",
    "type": "object",
    "properties": {
        "event_type": {"type": "string"},
        "sender_id": {"type": "string"},
        "target_id": {"anyOf": [{"type": "string"}, {"type": "null"}]},
        "created_at": {"type": "string"},
        "description": {"type": "string"},
        "payload": {"type": "string"},
    },
    "required": ["event_type", "sender_id"],
})

import json

AVAILABLE_SCHEMAS = {
    "agent-1:TestAction": f"A test action|test_event|{MOCK_SCHEMA}"
}


class TestValidateAction:
    def test_valid_own_action(self):
        result = validate_action(
            agent_id="agent-1",
            action_schema="agent-1:TestAction",
            pre_filled_event={"payload": "hello"},
            available_action_schemas=AVAILABLE_SCHEMAS,
        )
        assert isinstance(result, tuple)
        is_mine, evt = result
        assert is_mine is True
        assert evt["payload"] == "hello"

    def test_valid_other_entity_action(self):
        result = validate_action(
            agent_id="agent-1",
            action_schema="agent-1:TestAction",
            pre_filled_event={},
            available_action_schemas={"agent-1:TestAction": f"A test|test_event|{MOCK_SCHEMA}"},
        )
        is_mine, _ = result
        assert is_mine is True

    def test_unknown_schema_returns_string(self):
        result = validate_action(
            agent_id="agent-1",
            action_schema="agent-1:Nonexistent",
            pre_filled_event={},
            available_action_schemas=AVAILABLE_SCHEMAS,
        )
        assert isinstance(result, str)
        assert "Unknown action schema" in result

    def test_malformed_schema_returns_string(self):
        result = validate_action(
            agent_id="agent-1",
            action_schema="malformed-no-colon",
            pre_filled_event={},
            available_action_schemas=AVAILABLE_SCHEMAS,
        )
        assert isinstance(result, str)
