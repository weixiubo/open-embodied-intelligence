from __future__ import annotations

from dataclasses import dataclass, field

from .logging import get_logger
from .ports import FeedbackSink

logger = get_logger("feedback")


class ConsoleFeedbackSink(FeedbackSink):
    def publish(self, message: str) -> None:
        if not message:
            return
        logger.info(message)
        print(message)


@dataclass(slots=True)
class MemoryFeedbackSink(FeedbackSink):
    messages: list[str] = field(default_factory=list)

    def publish(self, message: str) -> None:
        if message:
            self.messages.append(message)

