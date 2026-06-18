from genworlds.objects.abstracts.object import AbstractObject
from genworlds.events.abstracts.event import AbstractEvent
from genworlds.events.abstracts.action import AbstractAction


class AgentWantsUpdatedStateEvent(AbstractEvent):
    event_type: str = "agent_wants_updated_state"
    description: str = "Agent wants to update its state."
    sender_id: str
    target_id: str


class WorldSendsAvailableEntitiesEvent(AbstractEvent):
    event_type: str = "world_sends_available_entities_event"
    description: str = "Send available entities."
    sender_id: str
    available_entities: dict
    target_id: str


class WorldSendsAvailableEntities(AbstractAction):
    trigger_event_class = AgentWantsUpdatedStateEvent
    description = "Send available entities."

    def __init__(self, host_object: AbstractObject):
        super().__init__(host_object=host_object)

    def __call__(self, event: AgentWantsUpdatedStateEvent):
        self.host_object.update_entities()
        event = WorldSendsAvailableEntitiesEvent(
            sender_id=self.host_object.id,
            available_entities=dict(self.host_object.entities),
            target_id=event.sender_id,
        )
        self.host_object.send_event(event)


class WorldSendsAvailableActionSchemasEvent(AbstractEvent):
    event_type: str = "world_sends_available_action_schemas_event"
    description: str = "The world sends the possible action schemas to all the agents."
    sender_id: str
    world_name: str
    world_description: str
    available_action_schemas: dict
    target_id: str


class WorldSendsAvailableActionSchemas(AbstractAction):
    trigger_event_class = AgentWantsUpdatedStateEvent
    description = "The world sends the possible action schemas to all the agents."

    def __init__(self, host_object: AbstractObject):
        super().__init__(host_object=host_object)

    def __call__(self, event: AgentWantsUpdatedStateEvent):
        self.host_object.update_action_schemas()
        self.host_object.update_entities()

        # Build a filtered copy — never mutate the world's canonical dict
        all_action_schemas: dict = dict(self.host_object.action_schemas)
        all_entities: dict = dict(self.host_object.entities)

        filtered = {
            schema_key: schema_val
            for schema_key, schema_val in all_action_schemas.items()
            if not (
                schema_key.split(":")[0] in all_entities
                and all_entities[schema_key.split(":")[0]].entity_type == "AGENT"
                and schema_key.split(":")[0] != event.sender_id
            )
            and not (
                schema_key.split(":")[0] in all_entities
                and all_entities[schema_key.split(":")[0]].entity_type == "WORLD"
            )
            and schema_key != f"{event.sender_id}:AgentListensEvents"
        }

        response_event = WorldSendsAvailableActionSchemasEvent(
            sender_id=self.host_object.id,
            world_name=self.host_object.name,
            world_description=self.host_object.description,
            available_action_schemas=filtered,
            target_id=event.sender_id,
        )
        self.host_object.send_event(response_event)


class UserSpeaksWithAgentEvent(AbstractEvent):
    event_type: str = "user_speaks_with_agent_event"
    description: str = "The user speaks with an agent."
    sender_id: str
    message: str
