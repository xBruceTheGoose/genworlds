from typing import List, Optional
from genworlds.events.abstracts.event import AbstractEvent
from use_cases.roundtable.objects.job import Job


class AgentReadsBlackboardEvent(AbstractEvent):
    event_type: str = "agent_reads_blackboard"
    description: str = "An agent reads the blackboard."
    sender_id: str


class BlackboardSendsContentEvent(AbstractEvent):
    event_type: str = "blackboard_sends_content"
    description: str = "The blackboard sends its content."
    sender_id: str
    blackboard_content: List[Job] = []


class AgentAddsJobToBlackboardEvent(AbstractEvent):
    event_type: str = "agent_adds_job_to_blackboard"
    description: str = "Agent adds a job to the blackboard."
    new_job: Job
    sender_id: str


class UserAddsJobToBlackboardEvent(AbstractEvent):
    event_type: str = "user_adds_job_to_blackboard"
    description: str = "User adds a job to the blackboard."
    new_job: Job
    sender_id: str


class AgentDeletesJobFromBlackboardEvent(AbstractEvent):
    event_type: str = "agent_deletes_job_from_blackboard"
    description: str = "An agent deletes a job from the blackboard."
    job_id: str
    sender_id: str
