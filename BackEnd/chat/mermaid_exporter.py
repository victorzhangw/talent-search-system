from __future__ import annotations

from typing import Any, Dict, Set

from .workflow_loader import LoadedWorkflow


def _label(node_id: str, node: Dict[str, Any]) -> str:
    ntype = node.get("type", "")
    if ntype == "template":
        return f"{node_id}\\n(template)"
    if ntype == "state_init":
        return f"{node_id}\\n(state_init)"
    if ntype == "wait_user":
        return f"{node_id}\\n(wait_user)"
    if ntype == "end":
        return f"{node_id}\\n(end)"
    if ntype == "tool":
        return f"{node_id}\\n(tool)"
    if ntype == "llm":
        return f"{node_id}\\n(llm)"
    return f"{node_id}\\n({ntype})"


def workflow_to_mermaid(workflow: LoadedWorkflow) -> str:
    nodes = workflow.nodes

    lines = ["flowchart TD"]
    lines.append(f"  entry_start([{workflow.entry_start}])")
    lines.append(f"  entry_message([{workflow.entry_message}])")

    # Declare nodes
    for node_id, node in nodes.items():
        label = _label(node_id, node)
        lines.append(f"  {node_id}[{label}]")

    # Entry edges
    lines.append(f"  entry_start --> {workflow.entry_start}")
    lines.append(f"  entry_message --> {workflow.entry_message}")

    # Edges
    for node_id, node in nodes.items():
        nxt = node.get("next")
        if isinstance(nxt, str) and nxt:
            lines.append(f"  {node_id} --> {nxt}")
        elif isinstance(nxt, dict):
            for k, v in nxt.items():
                if isinstance(v, str) and v:
                    lines.append(f"  {node_id} -- {k} --> {v}")

    return "\n".join(lines) + "\n"
