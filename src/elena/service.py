from uuid import UUID

from elena.contracts import Conversation, Message, Role, TaskState, TurnResponse
from elena.providers import ProviderRegistry
from elena.storage import ConversationStore


class ConversationNotFoundError(LookupError):
    pass


class ConversationService:
    def __init__(self, store: ConversationStore, providers: ProviderRegistry) -> None:
        self.store = store
        self.providers = providers

    def create_conversation(self, title: str, provider: str) -> Conversation:
        self.providers.resolve(provider)
        return self.store.create_conversation(
            Conversation(title=title, provider=provider)
        )

    def get_conversation(self, conversation_id: UUID) -> Conversation:
        conversation = self.store.get_conversation(conversation_id)
        if conversation is None:
            raise ConversationNotFoundError(str(conversation_id))
        return conversation

    async def send_message(self, conversation_id: UUID, content: str) -> TurnResponse:
        self.get_conversation(conversation_id)
        user_message = Message(
            conversation_id=conversation_id,
            role=Role.USER,
            content=content,
        )
        self.store.add_message(user_message)
        self.store.set_state(conversation_id, TaskState.THINKING)

        try:
            current = self.get_conversation(conversation_id)
            provider = self.providers.resolve(current.provider)
            chunks = [chunk async for chunk in provider.stream(current.messages)]
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
