"""Unit tests for world actions (no mutation, correct dispatch)."""
import pytest
from unittest.mock import MagicMock
from genworlds.worlds.concrete.base.actions import (
    WorldSendsAvailableActionSchemas,
    WorldSendsAvailableEntities,
    AgentWantsUpdatedStateEvent,
)
from genworlds.worlds.abstracts.world_entity import AbstractWorldEntity, EntityTypeEnum


def _make_entity(entity_id, entity_type):
    return MagicMock(
        spec=AbstractWorldEntity,
        entity_type=entity_type,
        id=entity_id,
    )


def _make_world(entities: dict, action_schemas: dict):
    world = MagicMock()
    world.id = "world-1"
    world.name = "Test World"
    world.description = "A test world."
    world.entities = entities
    world.action_schemas = action_schemas
    world.update_entities = MagicMock()
    world.update_action_schemas = MagicMock()
    world.send_event = MagicMock()
    return world


class TestWorldSendsAvailableActionSchemas:
    def test_does_not_mutate_canonical_schemas(self):
        schemas = {
            "world-1:WorldAction": "desc|event_type|{}",
            "agent-1:AgentAction": "desc|event_type|{}",
            "agent-2:AgentAction": "desc|event_type|{}",
        }
        entities = {
            "world-1": _make_entity("world-1", "WORLD"),
            "agent-1": _make_entity("agent-1", "AGENT"),
            "agent-2": _make_entity("agent-2", "AGENT"),
        }
        world = _make_world(entities, schemas)
        action = WorldSendsAvailableActionSchemas(host_object=world)
        event = AgentWantsUpdatedStateEvent(sender_id="agent-1", target_id="world-1")
        action(event)

        # Canonical dict must be untouched
        assert set(world.action_schemas.keys()) == set(schemas.keys())

    def test_filtered_copy_sent_to_requester(self):
        schemas = {
            "world-1:WorldAction": "desc|event_type|{}",
            "agent-1:AgentAction": "desc|event_type|{}",
            "agent-2:AgentAction": "desc|event_type|{}",
        }
        entities = {
            "world-1": _make_entity("world-1", "WORLD"),
            "agent-1": _make_entity("agent-1", "AGENT"),
            "agent-2": _make_entity("agent-2", "AGENT"),
        }
        world = _make_world(entities, schemas)
        action = WorldSendsAvailableActionSchemas(host_object=world)
        event = AgentWantsUpdatedStateEvent(sender_id="agent-1", target_id="world-1")
        action(event)

        sent_event = world.send_event.call_args[0][0]
        # World-level and other-agent actions should be filtered out
        assert "world-1:WorldAction" not in sent_event.available_action_schemas
        assert "agent-2:AgentAction" not in sent_event.available_action_schemas
        assert "agent-1:AgentAction" in sent_event.available_action_schemas
