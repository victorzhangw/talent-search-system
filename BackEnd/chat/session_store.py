from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, Optional

from .schemas import ChatSession


class SessionStore(ABC):
    """Abstract session store.

    Milestone 1 ships with an in-memory implementation.
    Milestone 2+ can add Redis/PostgreSQL implementations without changing API layer.
    """

    @abstractmethod
    def create(self, session: ChatSession) -> None:
        raise NotImplementedError

    @abstractmethod
    def get(self, session_id: str) -> Optional[ChatSession]:
        raise NotImplementedError

    @abstractmethod
    def save(self, session: ChatSession) -> None:
        raise NotImplementedError


class InMemorySessionStore(SessionStore):
    def __init__(self):
        self._sessions: Dict[str, ChatSession] = {}

    def create(self, session: ChatSession) -> None:
        session.created_at = datetime.utcnow()
        session.updated_at = datetime.utcnow()
        self._sessions[session.session_id] = session

    def get(self, session_id: str) -> Optional[ChatSession]:
        return self._sessions.get(session_id)

    def save(self, session: ChatSession) -> None:
        session.updated_at = datetime.utcnow()
        self._sessions[session.session_id] = session


# Process-wide singleton for Milestone 1.
# NOTE: This is intentionally scoped to the new /api/chat endpoints only.
_default_store = InMemorySessionStore()


def get_session_store() -> SessionStore:
    return _default_store
