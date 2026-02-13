from __future__ import annotations

from typing import Literal

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field


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
        description=(
            "Record a list of todos with progress status. "
            "Progress must be one of: completed, in progress, outstanding."
        ),
        args_schema=TodoList,
    )
