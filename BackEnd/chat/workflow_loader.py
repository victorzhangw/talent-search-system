from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional

import yaml


@dataclass(frozen=True)
class LoadedWorkflow:
    raw: Dict[str, Any]
    workflow_id: str
    version: int
    entry_start: str
    entry_message: str
    nodes: Dict[str, Dict[str, Any]]


class WorkflowError(ValueError):
    pass


_DEFAULT_WORKFLOWS_DIR = Path(__file__).parent / "workflows"


def load_workflow(workflow_id: str, workflows_dir: Optional[Path] = None) -> LoadedWorkflow:
    workflows_dir = workflows_dir or _DEFAULT_WORKFLOWS_DIR
    path_yaml = workflows_dir / f"{workflow_id}.yaml"
    path_yml = workflows_dir / f"{workflow_id}.yml"

    if path_yaml.exists():
        path = path_yaml
    elif path_yml.exists():
        path = path_yml
    else:
        raise WorkflowError(f"workflow not found: {workflow_id}")

    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise WorkflowError("workflow file must be a mapping")

    wid = str(raw.get("id") or workflow_id)
    version = int(raw.get("version") or 1)
    entry_start = str(raw.get("entry_start") or raw.get("entry") or "init")
    entry_message = str(raw.get("entry_message") or "on_message")

    nodes = raw.get("nodes")
    if not isinstance(nodes, dict) or not nodes:
        raise WorkflowError("workflow must define non-empty 'nodes'")

    if entry_start not in nodes:
        raise WorkflowError(f"entry_start node not found: {entry_start}")
    if entry_message not in nodes:
        raise WorkflowError(f"entry_message node not found: {entry_message}")

    return LoadedWorkflow(
        raw=raw,
        workflow_id=wid,
        version=version,
        entry_start=entry_start,
        entry_message=entry_message,
        nodes=nodes,
    )
