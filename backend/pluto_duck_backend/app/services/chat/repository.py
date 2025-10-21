from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional

import duckdb

from pluto_duck_backend.app.core.config import get_settings


DDL_STATEMENTS = [
    """
    CREATE TABLE IF NOT EXISTS agent_conversations (
        id UUID PRIMARY KEY,
        title VARCHAR,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        status VARCHAR DEFAULT 'active',
        last_message_preview VARCHAR,
        run_id UUID,
        metadata JSON
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS agent_messages (
        id UUID PRIMARY KEY,
        conversation_id UUID REFERENCES agent_conversations(id),
        role VARCHAR NOT NULL,
        content JSON NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        seq INTEGER,
        UNIQUE(conversation_id, seq)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS agent_events (
        id UUID PRIMARY KEY,
        conversation_id UUID REFERENCES agent_conversations(id),
        type VARCHAR NOT NULL,
        subtype VARCHAR,
        payload JSON,
        metadata JSON,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        source VARCHAR DEFAULT 'backend'
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS user_settings (
        key VARCHAR PRIMARY KEY,
        value JSON,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_messages_conversation ON agent_messages(conversation_id, seq)
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_events_conversation ON agent_events(conversation_id, timestamp)
    """,
]

DEFAULT_SETTINGS: Dict[str, Any] = {
    "data_sources": None,
    "dbt_project": None,
    "ui_preferences": {"theme": "dark"},
    "llm_provider": None,
}


@dataclass
class ConversationSummary:
    id: str
    title: Optional[str]
    status: str
    created_at: datetime
    updated_at: datetime
    last_message_preview: Optional[str]
    run_id: Optional[str]


class ChatRepository:
    def __init__(self, warehouse_path: Path) -> None:
        self.warehouse_path = warehouse_path
        self._ensure_tables()
        self.ensure_default_settings(DEFAULT_SETTINGS)

    def _connect(self) -> duckdb.DuckDBPyConnection:
        return duckdb.connect(str(self.warehouse_path))

    def _ensure_tables(self) -> None:
        with self._connect() as con:
            for statement in DDL_STATEMENTS:
                con.execute(statement)

    def new_conversation_id(self) -> str:
        from uuid import uuid4

        return str(uuid4())

    def create_conversation(
        self,
        conversation_id: str,
        question: Optional[str],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        snippet = (question or "").strip()
        title = snippet[:80] if snippet else None
        preview = snippet[:160] if snippet else None
        now = datetime.now(UTC)
        with self._connect() as con:
            # Check if conversation already exists
            existing = con.execute(
                "SELECT id FROM agent_conversations WHERE id = ?",
                [conversation_id],
            ).fetchone()
            
            if existing:
                # Conversation already exists, skip to avoid duplicate messages
                return
            
            con.execute(
                """
                INSERT INTO agent_conversations (id, title, created_at, updated_at, status, last_message_preview, run_id, metadata)
                VALUES (?, ?, ?, ?, 'active', ?, ?, ?)
                """,
                [
                    conversation_id,
                    title,
                    now,
                    now,
                    preview,
                    conversation_id,
                    json.dumps(metadata or {}),
                ],
            )

    def append_message(
        self,
        conversation_id: str,
        role: str,
        content: Dict[str, Any],
        *,
        connection: Optional[duckdb.DuckDBPyConnection] = None,
    ) -> None:
        owns_connection = connection is None
        con = connection or self._connect()
        try:
            seq = self._next_seq(conversation_id, connection=con)
            message_id = self._generate_uuid()
            con.execute(
                """
                INSERT INTO agent_messages (id, conversation_id, role, content, created_at, seq)
                VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP, ?)
                """,
                [message_id, conversation_id, role, json.dumps(content), seq],
            )
            self._touch_conversation(
                conversation_id,
                last_message_preview=self._preview_from_content(content),
                connection=con,
            )
        finally:
            if owns_connection:
                con.close()

    def log_event(self, conversation_id: str, event: Dict[str, Any]) -> None:
        event_id = self._generate_uuid()
        payload = json.dumps(event.get("content")) if event.get("content") is not None else None
        metadata_json = json.dumps(event.get("metadata") or {})
        timestamp_value = event.get("timestamp")
        if isinstance(timestamp_value, str):
            try:
                timestamp_obj = datetime.fromisoformat(timestamp_value)
            except ValueError:
                timestamp_obj = datetime.now(UTC)
        else:
            timestamp_obj = datetime.now(UTC)
        with self._connect() as con:
            con.execute(
                """
                INSERT INTO agent_events (id, conversation_id, type, subtype, payload, metadata, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    event_id,
                    conversation_id,
                    event.get("type"),
                    event.get("subtype"),
                    payload,
                    metadata_json,
                    timestamp_obj,
                ],
            )
            self._touch_conversation(conversation_id, connection=con)

    def mark_run_completed(
        self,
        conversation_id: str,
        status: str,
        final_preview: Optional[str],
    ) -> None:
        with self._connect() as con:
            self._touch_conversation(
                conversation_id,
                status=status,
                last_message_preview=final_preview,
                connection=con,
            )

    def mark_run_started(
        self,
        conversation_id: str,
        *,
        last_message_preview: Optional[str] = None,
    ) -> None:
        with self._connect() as con:
            self._touch_conversation(
                conversation_id,
                status="active",
                last_message_preview=last_message_preview,
                connection=con,
            )

    def set_active_run(self, conversation_id: str, run_id: str) -> None:
        with self._connect() as con:
            con.execute(
                "UPDATE agent_conversations SET run_id = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                [run_id, conversation_id],
            )

    def delete_conversation(self, conversation_id: str) -> bool:
        with self._connect() as con:
            exists = con.execute(
                "SELECT 1 FROM agent_conversations WHERE id = ?",
                [conversation_id],
            ).fetchone()
            if not exists:
                return False

            con.execute(
                "DELETE FROM agent_messages WHERE conversation_id = ?",
                [conversation_id],
            )
            con.execute(
                "DELETE FROM agent_events WHERE conversation_id = ?",
                [conversation_id],
            )
            con.execute(
                "DELETE FROM agent_conversations WHERE id = ?",
                [conversation_id],
            )

        return True

    def _next_seq(
        self,
        conversation_id: str,
        *,
        connection: Optional[duckdb.DuckDBPyConnection] = None,
    ) -> int:
        owns_connection = connection is None
        con = connection or self._connect()
        try:
            seq_row = con.execute(
                "SELECT COALESCE(MAX(seq), 0) + 1 FROM agent_messages WHERE conversation_id = ?",
                [conversation_id],
            ).fetchone()
            return seq_row[0] if seq_row else 1
        finally:
            if owns_connection:
                con.close()

    def _touch_conversation(
        self,
        conversation_id: str,
        *,
        status: Optional[str] = None,
        last_message_preview: Optional[str] = None,
        connection: Optional[duckdb.DuckDBPyConnection] = None,
    ) -> None:
        owns_connection = connection is None
        con = connection or self._connect()
        try:
            if status is not None and last_message_preview is not None:
                con.execute(
                    "UPDATE agent_conversations SET status = ?, last_message_preview = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                    [status, last_message_preview, conversation_id],
                )
            elif status is not None:
                con.execute(
                    "UPDATE agent_conversations SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                    [status, conversation_id],
                )
            elif last_message_preview is not None:
                con.execute(
                    "UPDATE agent_conversations SET last_message_preview = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                    [last_message_preview, conversation_id],
                )
            else:
                con.execute(
                    "UPDATE agent_conversations SET updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                    [conversation_id],
                )
        finally:
            if owns_connection:
                con.close()

    def list_conversations(self, limit: int = 50, offset: int = 0) -> List[ConversationSummary]:
        with self._connect() as con:
            rows = con.execute(
                """
                SELECT id, title, status, created_at, updated_at, last_message_preview, run_id
                FROM agent_conversations
                ORDER BY updated_at DESC
                LIMIT ? OFFSET ?
                """,
                [limit, offset],
            ).fetchall()
        return [
            ConversationSummary(
                id=row[0],
                title=row[1],
                status=row[2],
                created_at=self._ensure_utc(row[3]),
                updated_at=self._ensure_utc(row[4]),
                last_message_preview=row[5],
                run_id=row[6],
            )
            for row in rows
        ]

    def get_conversation_summary(self, conversation_id: str) -> Optional[ConversationSummary]:
        with self._connect() as con:
            row = con.execute(
                """
                SELECT id, title, status, created_at, updated_at, last_message_preview, run_id
                FROM agent_conversations
                WHERE id = ?
                """,
                [conversation_id],
            ).fetchone()
        if not row:
            return None
        return ConversationSummary(
            id=row[0],
            title=row[1],
            status=row[2],
            created_at=self._ensure_utc(row[3]),
            updated_at=self._ensure_utc(row[4]),
            last_message_preview=row[5],
            run_id=row[6],
        )

    def get_conversation_messages(self, conversation_id: str) -> List[Dict[str, Any]]:
        with self._connect() as con:
            rows = con.execute(
                """
                SELECT id, role, content, created_at, seq
                FROM agent_messages
                WHERE conversation_id = ?
                ORDER BY seq ASC
                """,
                [conversation_id],
            ).fetchall()
        messages: List[Dict[str, Any]] = []
        for row in rows:
            content = json.loads(row[2]) if row[2] else None
            messages.append(
                {
                    "id": row[0],
                    "role": row[1],
                    "content": content,
                    "created_at": self._ensure_utc(row[3]).isoformat(),
                    "seq": row[4],
                }
            )
        return messages

    def get_conversation_events(self, conversation_id: str, limit: int = 200) -> List[Dict[str, Any]]:
        with self._connect() as con:
            rows = con.execute(
                """
                SELECT type, subtype, payload, metadata, timestamp
                FROM agent_events
                WHERE conversation_id = ?
                ORDER BY timestamp ASC
                LIMIT ?
                """,
                [conversation_id, limit],
            ).fetchall()
        events: List[Dict[str, Any]] = []
        for row in rows:
            payload = json.loads(row[2]) if row[2] else None
            metadata = json.loads(row[3]) if row[3] else None
            events.append(
                {
                    "type": row[0],
                    "subtype": row[1],
                    "content": payload,
                    "metadata": metadata,
                    "timestamp": self._ensure_utc(row[4]).isoformat() if row[4] else None,
                }
            )
        return events

    def get_settings(self) -> Dict[str, Any]:
        with self._connect() as con:
            rows = con.execute("SELECT key, value FROM user_settings").fetchall()
        result: Dict[str, Any] = {}
        for row in rows:
            result[row[0]] = json.loads(row[1]) if row[1] else None
        for key, value in DEFAULT_SETTINGS.items():
            result.setdefault(key, value)
        return result

    def update_settings(self, payload: Dict[str, Any]) -> None:
        now = datetime.now(UTC)
        with self._connect() as con:
            for key, value in payload.items():
                con.execute(
                    "INSERT OR REPLACE INTO user_settings (key, value, updated_at) VALUES (?, ?, ?)",
                    [key, json.dumps(value) if value is not None else None, now],
                )

    def ensure_default_settings(self, defaults: Optional[Dict[str, Any]] = None) -> None:
        if not defaults:
            defaults = {}
        to_seed = {}
        existing = self.get_settings()
        for key, value in defaults.items():
            if existing.get(key) is None:
                to_seed[key] = value
        if to_seed:
            self.update_settings(to_seed)

    def _generate_uuid(self) -> str:
        from uuid import uuid4

        return str(uuid4())

    def _preview_from_content(self, content: Dict[str, Any]) -> Optional[str]:
        if isinstance(content, dict):
            if "text" in content and isinstance(content["text"], str):
                return content["text"][:160]
            if "summary" in content and isinstance(content["summary"], str):
                return content["summary"][:160]
        return None

    def _ensure_utc(self, value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)


@lru_cache(maxsize=1)
def get_chat_repository() -> ChatRepository:
    settings = get_settings()
    return ChatRepository(settings.duckdb.path)
