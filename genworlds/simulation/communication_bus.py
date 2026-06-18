from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Protocol, runtime_checkable
from genworlds.events.abstracts.event import AbstractEvent


@runtime_checkable
class CommunicationBus(Protocol):
    """Minimal interface for sending events to the simulation bus."""

    def send_event(self, event: AbstractEvent) -> None: ...

    def launch_websocket_thread(self) -> None: ...
