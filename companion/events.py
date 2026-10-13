from datetime import datetime, timezone
from enum import Enum
from typing import Annotated, Literal, Union
from pydantic import BaseModel, Field


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class VoiceState(str, Enum):
    idle = "idle"
    listening = "listening"
    thinking = "thinking"
    speaking = "speaking"
    interrupted = "interrupted"


class _Base(BaseModel):
    ts: str = Field(default_factory=now_iso)


class VoiceStateEvent(_Base):
    type: Literal["voice_state"] = "voice_state"
    state: VoiceState


class TranscriptEvent(_Base):
    type: Literal["transcript"] = "transcript"
    role: Literal["user", "assistant"]
    text: str
    final: bool = False


class AffectEvent(_Base):
    type: Literal["affect"] = "affect"
    sadness: float
    anxiety: float
    valence: float
    s_distress: float


class ReminderEvent(_Base):
    type: Literal["reminder"] = "reminder"
    reminder_id: int
    text: str


class ToolCallEvent(_Base):
    type: Literal["tool_call"] = "tool_call"
    call_id: str
    tool: str
    status: Literal["pending_confirmation", "running", "done", "failed"]
    summary: str


Event = Annotated[
    Union[VoiceStateEvent, TranscriptEvent, AffectEvent, ReminderEvent, ToolCallEvent],
    Field(discriminator="type"),
]