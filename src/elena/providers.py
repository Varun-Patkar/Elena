from collections.abc import AsyncIterator, Sequence
from typing import Protocol

from elena.contracts import Message, Role


class ChatProvider(Protocol):
    name: str

    async def stream(self, messages: Sequence[Message]) -> AsyncIterator[str]: ...


class FakeProvider:
    """Deterministic provider used for local development and CI."""

    name = "fake"

    async def stream(self, messages: Sequence[Message]) -> AsyncIterator[str]:
        latest = next(
            message for message in reversed(messages) if message.role == Role.USER
        )
        response = (
            "Certainly. I have recorded your request: "
            f'"{latest.content.strip()}" '
            "The development provider is active, so no external model was contacted."
        )
        for word in response.split():
            yield f"{word} "
