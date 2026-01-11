from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Any, Dict, Optional

from .intent.router import IntentRouter
from .llm.runner import LLMRunner
from .moderation.policy_loader import load_policy
from .moderation.moderator import RuleBasedModerator
from .prompt_registry import get_prompt
from .schemas import ChatSession
from .tools.query_parser import naive_parse_query_to_engine_format
from .tools.registry import ToolRegistry
from .workflow_loader import LoadedWorkflow, WorkflowError


@dataclass
class RunResult:
    assistant_message: Optional[str]
    state: str
    last_node: str
    debug: Dict[str, Any]


class WorkflowRunner:
    """A minimal workflow runner (v0 -> Milestone 3/4).

    Supported node types:
    - state_init: sets session.state
    - template: formats a message using python str.format
    - moderation: rule-based moderation (input/output)
    - intent_router: rule-first, optional LLM fallback
    - switch: route based on a context variable
    - wait_user: stop execution and wait for next user message
    - end: stop and mark END

    Notes:
    - This runner is intentionally simple and deterministic.
    - LLM/tool nodes will be added in later milestones.
    """

    def __init__(self, workflow: LoadedWorkflow):
        self.workflow = workflow

    async def run_start(self, session: ChatSession) -> RunResult:
        return await self._run(session=session, start_node=self.workflow.entry_start, user_message=None)

    async def run_message(self, session: ChatSession, user_message: str) -> RunResult:
        return await self._run(session=session, start_node=self.workflow.entry_message, user_message=user_message)

    async def _run(self, session: ChatSession, start_node: str, user_message: Optional[str]) -> RunResult:
        nodes = self.workflow.nodes

        current = start_node
        assistant_message: Optional[str] = None
        visited = 0

        ctx: Dict[str, Any] = {
            "candidates_count": len(session.candidate_ids),
            "user_message": user_message or "",
            "assistant_message": "",
            "tool_result": {},
            "tool_json": "{}",
            "session_id": session.session_id,
            "state": session.state,
            "intent": "",
            "intent_confidence": 0.0,
            "moderation_action": "allow",
        }

        while True:
            visited += 1
            if visited > 50:
                raise WorkflowError("workflow execution exceeded max steps (50)")

            node = nodes.get(current)
            if not node:
                raise WorkflowError(f"node not found: {current}")

            ntype = node.get("type")
            if ntype == "state_init":
                to_set = node.get("set") or {}
                if isinstance(to_set, dict) and "state" in to_set:
                    session.state = str(to_set["state"])
                    ctx["state"] = session.state
                current = str(node.get("next") or "")
                if not current:
                    raise WorkflowError(f"state_init node missing next: {current}")
                continue

            if ntype == "template":
                # template can be inline or referenced from prompt registry
                prompt_ref = node.get("prompt_ref")
                if prompt_ref:
                    template = get_prompt(str(prompt_ref))
                else:
                    template = str(node.get("template") or "")

                assistant_message = template.format(**ctx)
                ctx["assistant_message"] = assistant_message
                next_node = node.get("next")
                current = str(next_node) if next_node else ""
                if not current:
                    return RunResult(
                        assistant_message=assistant_message,
                        state=session.state,
                        last_node="template",
                        debug={"workflow_id": self.workflow.workflow_id, "steps": visited},
                    )
                continue

            if ntype == "moderation":
                policy_ref = str(node.get("policy_ref") or "default_policy")
                text_key = str(node.get("input") or "user_message")
                text = str(ctx.get(text_key) or "")

                policy = load_policy(policy_ref)
                moderator = RuleBasedModerator()
                mres = moderator.moderate(text=text, policy=policy)
                ctx["moderation_action"] = mres.action

                next_map = node.get("next") or {}
                if not isinstance(next_map, dict):
                    raise WorkflowError(f"moderation node must have next mapping: {current}")

                current = str(next_map.get("blocked" if mres.blocked else "ok") or "")
                if not current:
                    raise WorkflowError(f"moderation next not configured at node: {current}")
                continue

            if ntype == "intent_router":
                text_key = str(node.get("input") or "user_message")
                text = str(ctx.get(text_key) or "")

                router = IntentRouter()
                ires = await router.route(text)

                ctx["intent"] = ires.intent
                ctx["intent_confidence"] = ires.confidence

                session.slots["intent"] = ires.intent
                session.slots["intent_confidence"] = ires.confidence
                session.slots["intent_source"] = ires.source

                current = str(node.get("next") or "")
                if not current:
                    raise WorkflowError(f"intent_router node missing next: {current}")
                continue

            if ntype == "switch":
                var = str(node.get("var") or "intent")
                value = str(ctx.get(var) or "")
                cases = node.get("cases") or {}
                if not isinstance(cases, dict):
                    raise WorkflowError(f"switch cases must be mapping: {current}")

                next_node = cases.get(value) or node.get("default_next")
                current = str(next_node or "")
                if not current:
                    raise WorkflowError(f"switch has no match and no default_next: {current}")
                continue

            if ntype == "tool":
                tool_name = str(node.get("tool_name") or "")
                if not tool_name:
                    raise WorkflowError(f"tool node missing tool_name: {current}")

                # For v1, tool_input can be a string key pointing to user_message,
                # or a mapping that includes raw_query.
                tool_input_spec = node.get("input")
                if isinstance(tool_input_spec, str):
                    parsed_query = naive_parse_query_to_engine_format(str(ctx.get(tool_input_spec) or ""))
                elif isinstance(tool_input_spec, dict):
                    raw_query_key = str(tool_input_spec.get("raw_query") or "user_message")
                    parsed_query = naive_parse_query_to_engine_format(str(ctx.get(raw_query_key) or ""))
                else:
                    parsed_query = naive_parse_query_to_engine_format(str(ctx.get("user_message") or ""))

                registry = ToolRegistry()
                try:
                    tool_result = registry.run(tool_name=tool_name, tool_input=parsed_query)
                except Exception as e:  # noqa: BLE001
                    fallback_next = node.get("fallback_next")
                    if fallback_next:
                        session.slots["tool_error"] = str(e)
                        ctx["tool_result"] = {"success": False, "error": str(e)}
                        ctx["tool_json"] = json.dumps(ctx["tool_result"], ensure_ascii=False)
                        current = str(fallback_next)
                        continue
                    raise

                ctx["tool_result"] = tool_result
                ctx["tool_json"] = json.dumps(tool_result, ensure_ascii=False)
                session.slots["last_tool"] = tool_name
                session.slots["last_tool_success"] = bool(tool_result.get("success", True))

                current = str(node.get("next") or "")
                if not current:
                    raise WorkflowError(f"tool node missing next: {current}")
                continue

            if ntype == "llm":
                model_policy = str(node.get("model_policy") or "answer_model")

                # prompts are referenced from prompt registry
                system_ref = node.get("system_ref")
                user_ref = node.get("user_ref")
                if not system_ref or not user_ref:
                    raise WorkflowError(f"llm node must have system_ref and user_ref: {current}")

                system_t = get_prompt(str(system_ref)).format(**ctx)
                user_t = get_prompt(str(user_ref)).format(**ctx)

                runner = LLMRunner()
                try:
                    llm_out = await runner.run(
                        model_policy_key=model_policy,
                        messages=[
                            {"role": "system", "content": system_t},
                            {"role": "user", "content": user_t},
                        ],
                    )
                    assistant_message = str(llm_out.get("content") or "")
                    ctx["assistant_message"] = assistant_message
                    session.slots["llm_model"] = llm_out.get("model")
                    session.slots["llm_model_policy"] = llm_out.get("model_policy")
                except Exception as e:  # noqa: BLE001
                    fallback_next = node.get("fallback_next")
                    if fallback_next:
                        session.slots["llm_error"] = str(e)
                        current = str(fallback_next)
                        continue
                    raise

                current = str(node.get("next") or "")
                if not current:
                    raise WorkflowError(f"llm node missing next: {current}")
                continue

            if ntype == "wait_user":
                return RunResult(
                    assistant_message=assistant_message,
                    state=session.state,
                    last_node=current,
                    debug={
                        "workflow_id": self.workflow.workflow_id,
                        "steps": visited,
                        "intent": ctx.get("intent"),
                        "intent_confidence": ctx.get("intent_confidence"),
                        "moderation_action": ctx.get("moderation_action"),
                    },
                )

            if ntype == "end":
                session.state = "END"
                if node.get("message_ref"):
                    assistant_message = get_prompt(str(node.get("message_ref")))
                else:
                    assistant_message = str(node.get("message") or assistant_message or "")
                return RunResult(
                    assistant_message=assistant_message,
                    state=session.state,
                    last_node=current,
                    debug={
                        "workflow_id": self.workflow.workflow_id,
                        "steps": visited,
                        "intent": ctx.get("intent"),
                        "intent_confidence": ctx.get("intent_confidence"),
                        "moderation_action": ctx.get("moderation_action"),
                    },
                )

            raise WorkflowError(f"unsupported node type: {ntype} at node {current}")
