import json
import logging
from genworlds.objects.abstracts.object import AbstractObject
from genworlds.events.abstracts.event import AbstractEvent
from genworlds.events.abstracts.action import AbstractAction

logger = logging.getLogger(__name__)


class UserRequestsScreensToWorldEvent(AbstractEvent):
    event_type: str = "user_requests_screens_to_world"
    description: str = "The user requests the screens to the world."
    sender_id: str


class WorldSendsScreensToUserEvent(AbstractEvent):
    event_type: str = "world_sends_screens_to_user"
    description: str = "The world sends the screens to the user."
    sender_id: str
    screens_config: dict


class WorldSendsScreensToUser(AbstractAction):
    trigger_event_class = UserRequestsScreensToWorldEvent
    description = "The world sends the screens to the user."

    def __init__(self, host_object: AbstractObject):
        super().__init__(host_object=host_object)

    def __call__(self, event: UserRequestsScreensToWorldEvent):
        try:
            with open(self.host_object.screens_config_path) as f:
                screens_config = json.load(f)
        except (OSError, json.JSONDecodeError):
            logger.exception(
                "Could not load screens config from %s",
                self.host_object.screens_config_path,
            )
            return

        response = WorldSendsScreensToUserEvent(
            sender_id=self.host_object.id,
            screens_config=screens_config,
        )
        self.host_object.send_event(response)
