from __future__ import annotations

from functools import lru_cache

from .workflow_loader import LoadedWorkflow, load_workflow


@lru_cache(maxsize=32)
def get_workflow(workflow_id: str) -> LoadedWorkflow:
    return load_workflow(workflow_id)
