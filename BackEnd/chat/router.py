from __future__ import annotations

from uuid import uuid4

from fastapi import APIRouter, HTTPException

from .mermaid_exporter import workflow_to_mermaid
from .schemas import (
    ChatMessageRequest,
    ChatMessageResponse,
    ChatSession,
    StartChatRequest,
    StartChatResponse,
)
from .session_store import get_session_store
from .workflow_api_schemas import WorkflowGetResponse
from .workflow_registry import get_workflow
from .workflow_runner import WorkflowRunner

router = APIRouter()


@router.get("/workflows/{workflow_id}", response_model=WorkflowGetResponse)
async def get_workflow_definition(workflow_id: str) -> WorkflowGetResponse:
    wf = get_workflow(workflow_id)
    return WorkflowGetResponse(
        workflow_id=wf.workflow_id,
        version=wf.version,
        raw=wf.raw,
        mermaid=workflow_to_mermaid(wf),
    )


@router.post("/start", response_model=StartChatResponse)
async def start_chat(request: StartChatRequest) -> StartChatResponse:
    store = get_session_store()

    session_id = f"sess_{uuid4().hex}"  # stable external id
    session = ChatSession(
        session_id=session_id,
        user_id=request.user_id,
        workflow_id=request.workflow_id,
        candidate_ids=request.candidate_ids,
        state="WAIT_USER",
        slots={},
        messages=[],
    )

    wf = get_workflow(session.workflow_id)
    runner = WorkflowRunner(wf)
    result = await runner.run_start(session)

    # Persist greeting into session history
    if result.assistant_message:
        session.add_message("assistant", result.assistant_message)

    store.create(session)

    return StartChatResponse(
        session_id=session_id,
        assistant_message=result.assistant_message or "",
        state=session.state,
    )


@router.post("/message", response_model=ChatMessageResponse)
async def chat_message(request: ChatMessageRequest) -> ChatMessageResponse:
    store = get_session_store()
    session = store.get(request.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="session not found")

    session.add_message("user", request.message)

    wf = get_workflow(session.workflow_id)
    runner = WorkflowRunner(wf)
    result = await runner.run_message(session, user_message=request.message)

    if result.assistant_message:
        session.add_message("assistant", result.assistant_message)

    store.save(session)

    return ChatMessageResponse(
        assistant_message=result.assistant_message or "",
        state=session.state,
        intent=str(session.slots.get("intent") or "") or None,
        debug=result.debug,
    )
