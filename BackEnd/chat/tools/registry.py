from __future__ import annotations

from typing import Any, Dict

from .talent_search_tool import TalentSearchTool


class ToolRegistryError(ValueError):
    pass


class ToolRegistry:
    def __init__(self):
        self._tools = {
            "talent_search": TalentSearchTool(),
        }

    def run(self, tool_name: str, tool_input: Dict[str, Any]) -> Dict[str, Any]:
        if tool_name not in self._tools:
            raise ToolRegistryError(f"unknown tool: {tool_name}")

        tool = self._tools[tool_name]
        if tool_name == "talent_search":
            return tool.search(parsed_query=tool_input)

        raise ToolRegistryError(f"tool not runnable: {tool_name}")
