from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field


CandidateId = Union[int, str]


class StartChatRequest(BaseModel):
    user_id: Optional[str] = None
    workflow_id: str = Field(default="talent_chat_v1", description="Workflow id (reserved for later milestones)")
    candidate_ids: List[CandidateId] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class StartChatResponse(BaseModel):
    success: bool = True
    session_id: str
    assistant_message: str
    state: str = "WAIT_USER"


class ChatMessageRequest(BaseModel):
    session_id: str
    message: str


class ChatMessageResponse(BaseModel):
    success: bool = True
    assistant_message: str
    state: str = "WAIT_USER"
    intent: Optional[str] = None
    debug: Dict[str, Any] = Field(default_factory=dict)


class ChatMessage(BaseModel):
    role: str  # "user" | "assistant"
    content: str
    ts: datetime = Field(default_factory=datetime.utcnow)


class ChatSession(BaseModel):
    session_id: str
    user_id: Optional[str] = None
    workflow_id: str = "talent_chat_v1"
    candidate_ids: List[CandidateId] = Field(default_factory=list)
    state: str = "WAIT_USER"
    slots: Dict[str, Any] = Field(default_factory=dict)
    messages: List[ChatMessage] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    def add_message(self, role: str, content: str) -> None:
        self.messages.append(ChatMessage(role=role, content=content))
        self.updated_at = datetime.utcnow()
