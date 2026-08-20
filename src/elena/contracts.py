from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


def utc_now() -> datetime:
    return datetime.now(UTC)


class Role(StrEnum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class TaskState(StrEnum):
    IDLE = "idle"
    THINKING = "thinking"
    RUNNING_TOOL = "running_tool"
    WAITING_FOR_USER = "waiting_for_user"
    WAITING_FOR_APPROVAL = "waiting_for_approval"
    DELEGATED = "delegated"
    RECOVERING = "recovering"
    COMPLETED = "completed"
    BLOCKED_ACTIONABLE = "blocked_actionable"
    CANCELLED = "cancelled"


class Message(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    conversation_id: UUID
    role: Role
    content: str = Field(min_length=1)
    created_at: datetime = Field(default_factory=utc_now)
    spoken: bool = False


class Conversation(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    title: str = Field(default="New conversation", min_length=1, max_length=120)
    provider: str = "fake"
    state: TaskState = TaskState.IDLE
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
    messages: list[Message] = Field(default_factory=list)


class CreateConversationRequest(BaseModel):
    title: str = Field(default="New conversation", min_length=1, max_length=120)
    provider: str = "fake"


class SendMessageRequest(BaseModel):
    content: str = Field(min_length=1, max_length=32_000)


class TurnResponse(BaseModel):
    conversation: Conversation
    reply: Message
