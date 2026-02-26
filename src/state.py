from typing import Annotated, TypedDict

from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages


class MainState(TypedDict):
    """State for the top-level graph (clarification + handoff)."""

    messages: Annotated[list[AnyMessage], add_messages]
    clarification_question: str | None


class OrchestratorState(TypedDict):
    """State for the orchestrator subgraph."""

    messages: Annotated[list[AnyMessage], add_messages]


class ResearchState(TypedDict):
    """State for the research subgraph."""

    messages: Annotated[list[AnyMessage], add_messages]
    search_count: int
