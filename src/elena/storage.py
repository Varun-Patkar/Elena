import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from uuid import UUID

from elena.contracts import Conversation, Message, Role, TaskState, utc_now


class ConversationStore:
    def __init__(self, database_path: Path) -> None:
        self.database_path = database_path
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA journal_mode = WAL")
        try:
            yield connection
            connection.commit()
        finally:
            connection.close()

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.executescript("""
                CREATE TABLE IF NOT EXISTS conversations (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    provider TEXT NOT NULL,
                    state TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS messages (
                    id TEXT PRIMARY KEY,
                    conversation_id TEXT NOT NULL REFERENCES conversations(id),
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    spoken INTEGER NOT NULL DEFAULT 0
                );
                CREATE INDEX IF NOT EXISTS idx_messages_conversation_created
                ON messages(conversation_id, created_at);
                """)

    def create_conversation(self, conversation: Conversation) -> Conversation:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO conversations (id, title, provider, state, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    str(conversation.id),
                    conversation.title,
                    conversation.provider,
                    conversation.state,
                    conversation.created_at.isoformat(),
                    conversation.updated_at.isoformat(),
                ),
            )
        return conversation

    def add_message(self, message: Message) -> Message:
        now = utc_now()
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO messages (id, conversation_id, role, content, created_at, spoken)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    str(message.id),
                    str(message.conversation_id),
                    message.role,
                    message.content,
                    message.created_at.isoformat(),
                    int(message.spoken),
                ),
            )
            connection.execute(
                "UPDATE conversations SET updated_at = ? WHERE id = ?",
                (now.isoformat(), str(message.conversation_id)),
            )
        return message

    def set_state(self, conversation_id: UUID, state: TaskState) -> None:
        with self._connect() as connection:
            connection.execute(
                "UPDATE conversations SET state = ?, updated_at = ? WHERE id = ?",
                (state, utc_now().isoformat(), str(conversation_id)),
            )

    def get_conversation(self, conversation_id: UUID) -> Conversation | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM conversations WHERE id = ?", (str(conversation_id),)
            ).fetchone()
            if row is None:
                return None
            message_rows = connection.execute(
                "SELECT * FROM messages WHERE conversation_id = ? ORDER BY created_at, rowid",
                (str(conversation_id),),
            ).fetchall()

        return Conversation(
            id=UUID(row["id"]),
            title=row["title"],
            provider=row["provider"],
            state=TaskState(row["state"]),
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
            messages=[
                Message(
                    id=UUID(message_row["id"]),
                    conversation_id=UUID(message_row["conversation_id"]),
                    role=Role(message_row["role"]),
                    content=message_row["content"],
                    created_at=datetime.fromisoformat(message_row["created_at"]),
                    spoken=bool(message_row["spoken"]),
                )
                for message_row in message_rows
            ],
        )
