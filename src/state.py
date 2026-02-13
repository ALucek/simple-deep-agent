from __future__ import annotations

from typing import Annotated, TypedDict

from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages


class GraphState(TypedDict):
    """State for the main orchestration graph."""

    messages: Annotated[list[AnyMessage], add_messages]
    clarification_question: str | None


class ResearchState(TypedDict):
    """State for the research subgraph."""

    messages: Annotated[list[AnyMessage], add_messages]
    search_count: int
