import logging

from genworlds.objects.abstracts.object import AbstractObject
from genworlds.events.abstracts.action import AbstractAction
from genworlds.events.abstracts.event import AbstractEvent

logger = logging.getLogger(__name__)


class AgentSpeaksIntoMicrophoneEvent(AbstractEvent):
    event_type: str = "agent_speaks_into_microphone"
    description: str = "The holder of the microphone speaks into the microphone."
    message: str
    sender_id: str


class SpeakIntoMicrophone(AbstractAction):
    trigger_event_class = AgentSpeaksIntoMicrophoneEvent
    description = "The holder of the microphone speaks into it (broadcasts to all)."

    def __init__(self, host_object: AbstractObject):
        super().__init__(host_object=host_object)

    def __call__(self, event: AgentSpeaksIntoMicrophoneEvent):
        if event.sender_id != self.host_object.holder:
            logger.warning(
                "Agent %s tried to speak but doesn't hold the microphone (holder: %s).",
                event.sender_id,
                self.host_object.holder,
            )
            return
        logger.info("Agent %s says: %s", event.sender_id, event.message)
        # Broadcast by sending with no target_id
        self.host_object.send_event(
            AgentSpeaksIntoMicrophoneEvent(
                sender_id=self.host_object.id,
                message=event.message,
            )
        )


class Microphone(AbstractObject):
    def __init__(
        self,
        name: str,
        description: str,
        holder: str,
        id: str = None,
    ):
        self.holder = holder
        actions = [SpeakIntoMicrophone(host_object=self)]
        super().__init__(name=name, description=description, id=id, actions=actions)
