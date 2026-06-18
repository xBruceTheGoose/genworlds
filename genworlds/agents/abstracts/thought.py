from abc import ABC, abstractmethod
from typing import Any


class AbstractThought(ABC):
    @abstractmethod
    def run(self, *args: Any, **kwargs: Any) -> Any:
        """Run the thought and produce a response."""
