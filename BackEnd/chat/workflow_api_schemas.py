from __future__ import annotations

from typing import Any, Dict

from pydantic import BaseModel


class WorkflowGetResponse(BaseModel):
    success: bool = True
    workflow_id: str
    version: int
    raw: Dict[str, Any]
    mermaid: str
