"""Event payloads emitted by the agent orchestrator."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional


class EventType(str, Enum):
    """High-level event categories consumed by SSE clients."""

    REASONING = "reasoning"
    TOOL = "tool"
    MESSAGE = "message"
    RUN = "run"


class EventSubType(str, Enum):
    """Fine-grained event states."""

    START = "start"
    CHUNK = "chunk"
    END = "end"
    FINAL = "final"
    ERROR = "error"


@dataclass
class AgentEvent:
    """Structured event emitted during an agent run."""

    type: EventType
    subtype: EventSubType
    content: Optional[Any] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        """Serialize event to a JSON-compatible dict."""

        return {
            "type": self.type.value,
            "subtype": self.subtype.value,
            "content": self.content,
            "metadata": self.metadata,
            "timestamp": self.timestamp.isoformat(),
        }


