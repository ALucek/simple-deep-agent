from __future__ import annotations

from typing import Literal

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

TODO_LIST_TOOL_DESCRIPTION = """Track and manage your research plan as a structured todo list. Each call overwrites the entire list, so always include all items with their current status.
Usage guidelines:
1. Always Send Full State - This tool replaces the todo list on every call. Include all items (completed, in progress, and outstanding) each time, not just changes.
2. Update Frequently - Call this tool after completing a step or before starting a new one to keep the plan accurate and up to date.
3. Keep Items Granular - Each todo should represent a single, actionable step (e.g. one research query or one section to write), not a broad phase.
"""

class TodoItem(BaseModel):
    description: str = Field(description="Short description of the todo.")
    progress: Literal["completed", "in progress", "outstanding"] = Field(
        description="Progress status for the todo item."
    )


class TodoList(BaseModel):
    todos: list[TodoItem] = Field(
        description="List of todo items with descriptions and progress."
    )


def _set_todos(todos: list[TodoItem]) -> str:
    return TodoList(todos=todos).model_dump_json()


def build_todo_tool() -> StructuredTool:
    return StructuredTool.from_function(
        func=_set_todos,
        name="set_todos",
        description=TODO_LIST_TOOL_DESCRIPTION,
        args_schema=TodoList,
    )
