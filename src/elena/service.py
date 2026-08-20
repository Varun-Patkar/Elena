from uuid import UUID

from elena.contracts import Conversation, Message, Role, TaskState, TurnResponse
from elena.providers import ChatProvider
from elena.storage import ConversationStore


class ConversationNotFoundError(LookupError):
    pass


class ConversationService:
    def __init__(self, store: ConversationStore, provider: ChatProvider) -> None:
        self.store = store
        self.provider = provider

    def create_conversation(self, title: str) -> Conversation:
        return self.store.create_conversation(
            Conversation(title=title, provider=self.provider.name)
        )

    def get_conversation(self, conversation_id: UUID) -> Conversation:
        conversation = self.store.get_conversation(conversation_id)
        if conversation is None:
            raise ConversationNotFoundError(str(conversation_id))
        return conversation

    async def send_message(self, conversation_id: UUID, content: str) -> TurnResponse:
        conversation = self.get_conversation(conversation_id)
        user_message = Message(
            conversation_id=conversation_id,
            role=Role.USER,
            content=content,
        )
        self.store.add_message(user_message)
        self.store.set_state(conversation_id, TaskState.THINKING)

        try:
            current = self.get_conversation(conversation_id)
            chunks = [chunk async for chunk in self.provider.stream(current.messages)]
            reply = Message(
                conversation_id=conversation_id,
                role=Role.ASSISTANT,
                content="".join(chunks).strip(),
                spoken=True,
            )
            self.store.add_message(reply)
            self.store.set_state(conversation_id, TaskState.COMPLETED)
        except Exception:
            self.store.set_state(conversation_id, TaskState.BLOCKED_ACTIONABLE)
            raise

        return TurnResponse(
            conversation=self.get_conversation(conversation_id), reply=reply
        )
