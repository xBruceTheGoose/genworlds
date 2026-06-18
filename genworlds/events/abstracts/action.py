from __future__ import annotations
from abc import ABC, abstractmethod
import json
from typing import Any, Type, TypeVar, Generic, Tuple

from genworlds.events.abstracts.event import AbstractEvent

T = TypeVar("T", bound=AbstractEvent)


class AbstractAction(ABC, Generic[T]):
    trigger_event_class: Type[T]
    description: str

    def __init__(self, host_object: "AbstractObject"):
        self.host_object = host_object

    @property
    def action_schema(self) -> Tuple[str, str]:
        return (
            f"{self.host_object.id}:{self.__class__.__name__}",
            f"{self.description}|{self.trigger_event_class.model_fields['event_type'].default}|"
            + json.dumps(self.trigger_event_class.model_json_schema()),
        )

    @abstractmethod
    def __call__(self, event: T, *args: Any, **kwargs: Any) -> Any:
        pass
