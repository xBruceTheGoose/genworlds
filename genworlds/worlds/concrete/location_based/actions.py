from genworlds.events.abstracts.event import AbstractEvent
from genworlds.events.abstracts.action import AbstractAction
from genworlds.objects.abstracts.object import AbstractObject
from genworlds.worlds.concrete.base.actions import (
    AgentWantsUpdatedStateEvent,
    WorldSendsAvailableEntitiesEvent,
    WorldSendsAvailableActionSchemasEvent,
)


class AgentMovesToNewLocation(AbstractEvent):
    event_type: str = "agent_moves_to_new_location"
    description: str = "Agent moves to a new location in the world."
    destination_location: str
    sender_id: str


class WorldSetsAgentLocationEvent(AbstractEvent):
    event_type: str = "world_sets_agent_location"
    description: str = "The new location has been set for the agent."
    sender_id: str
    target_id: str


class WorldSetsAgentLocation(AbstractAction):
    trigger_event_class = AgentMovesToNewLocation
    description = "Move an agent to a new location in the world."

    def __init__(self, host_object: AbstractObject):
        super().__init__(host_object=host_object)

    def __call__(self, event: AgentMovesToNewLocation):
        if event.destination_location not in self.host_object.locations:
            raise ValueError(
                f"Destination location {event.destination_location} is not in world locations {self.host_object.locations}"
            )
        self.host_object.get_entity_by_id(
            event.sender_id
        ).location = event.destination_location
        response = WorldSetsAgentLocationEvent(
            sender_id=self.host_object.id,
            target_id=event.sender_id,
        )
        self.host_object.send_event(response)


class WorldSendsSameLocationEntities(AbstractAction):
    trigger_event_class = AgentWantsUpdatedStateEvent
    description = "Send entities at the same location as the requesting agent."

    def __init__(self, host_object: AbstractObject):
        super().__init__(host_object=host_object)

    def __call__(self, event: AgentWantsUpdatedStateEvent):
        self.host_object.update_entities()
        sender_entity = self.host_object.get_entity_by_id(event.sender_id)
        same_location_entities = {
            entity_id: entity
            for entity_id, entity in self.host_object.entities.items()
            if entity.location == sender_entity.location
        }
        response = WorldSendsAvailableEntitiesEvent(
            sender_id=self.host_object.id,
            target_id=event.sender_id,
            available_entities=same_location_entities,
        )
        self.host_object.send_event(response)


class WorldSendsSameLocationActionSchemas(AbstractAction):
    trigger_event_class = AgentWantsUpdatedStateEvent
    description = "Send action schemas for entities at the same location as the requesting agent."

    def __init__(self, host_object: AbstractObject):
        super().__init__(host_object=host_object)

    def __call__(self, event: AgentWantsUpdatedStateEvent):
        self.host_object.update_action_schemas()
        sender_entity = self.host_object.get_entity_by_id(event.sender_id)
        sender_location = sender_entity.location
        same_location_action_schemas = {}
        for action_schema_id, action_schema in self.host_object.action_schemas.items():
            entity_id = action_schema_id.split(":")[0]
            try:
                entity_location = self.host_object.get_entity_by_id(entity_id).location
            except KeyError:
                continue
            if entity_location == sender_location:
                same_location_action_schemas[action_schema_id] = action_schema
        response = WorldSendsAvailableActionSchemasEvent(
            sender_id=self.host_object.id,
            target_id=event.sender_id,
            world_name=self.host_object.name,
            world_description=self.host_object.description,
            available_action_schemas=same_location_action_schemas,
        )
        self.host_object.send_event(response)
