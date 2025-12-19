from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Dict
from common.logging import get_logger

log = get_logger("domain_events")

@dataclass
class DomainEvent:
    name: str
    payload: dict

class EventPublisher:
    """Заготовка для будущего брокера сообщений.
    Сейчас просто пишет событие в лог, сохраняя request_id/trace в контексте."
    """
    def publish(self, event: DomainEvent) -> None:
        log.info(f"event={event.name} payload={event.payload}")

publisher = EventPublisher()
