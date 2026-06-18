import logging
from typing import List

from genworlds.objects.abstracts.object import AbstractObject
from genworlds.events.abstracts.action import AbstractAction
from use_cases.roundtable.objects.job import Job
from use_cases.roundtable.events import (
    AgentReadsBlackboardEvent,
    AgentDeletesJobFromBlackboardEvent,
    AgentAddsJobToBlackboardEvent,
    BlackboardSendsContentEvent,
    UserAddsJobToBlackboardEvent,
)

logger = logging.getLogger(__name__)


class ReadBlackboard(AbstractAction):
    trigger_event_class = AgentReadsBlackboardEvent
    description = "Read the content of the blackboard."

    def __init__(self, host_object: AbstractObject):
        super().__init__(host_object=host_object)

    def __call__(self, event: AgentReadsBlackboardEvent):
        logger.info("Agent %s reads blackboard %s.", event.sender_id, self.host_object.id)
        self.host_object.send_event(
            BlackboardSendsContentEvent(
                sender_id=self.host_object.id,
                target_id=event.sender_id,
                blackboard_content=list(self.host_object.content),
            )
        )


class AddJob(AbstractAction):
    trigger_event_class = AgentAddsJobToBlackboardEvent
    description = "Add a job to the blackboard."

    def __init__(self, host_object: AbstractObject):
        super().__init__(host_object=host_object)

    def __call__(self, event: AgentAddsJobToBlackboardEvent):
        self.host_object.content.append(event.new_job)


class AddJobFromUser(AbstractAction):
    trigger_event_class = UserAddsJobToBlackboardEvent
    description = "User adds a job to the blackboard."

    def __init__(self, host_object: AbstractObject):
        super().__init__(host_object=host_object)

    def __call__(self, event: UserAddsJobToBlackboardEvent):
        self.host_object.content.append(event.new_job)


class DeleteJob(AbstractAction):
    trigger_event_class = AgentDeletesJobFromBlackboardEvent
    description = "Delete a job from the blackboard."

    def __init__(self, host_object: AbstractObject):
        super().__init__(host_object=host_object)

    def __call__(self, event: AgentDeletesJobFromBlackboardEvent):
        self.host_object.content = [
            job for job in self.host_object.content if job.id != event.job_id
        ]


class Blackboard(AbstractObject):
    def __init__(self, name: str, description: str, id: str = None):
        self.content: List[Job] = []
        actions = [
            ReadBlackboard(host_object=self),
            AddJob(host_object=self),
            AddJobFromUser(host_object=self),
            DeleteJob(host_object=self),
        ]
        super().__init__(name=name, description=description, id=id, actions=actions)
