from typing import Annotated, TypedDict

from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages


class AgentState(TypedDict):
    """State for the top-level agent graph."""

    messages: Annotated[list[AnyMessage], add_messages]


class SubagentState(TypedDict):
    """State for the subagent graph."""

    messages: Annotated[list[AnyMessage], add_messages]
    search_count: int
