from __future__ import annotations

from functools import lru_cache

from langchain_core.messages import HumanMessage
from langchain_core.tools import StructuredTool

from src.graphs.research_graph import build_research_graph
from src.models import ResearchReport, ResearchTask


@lru_cache(maxsize=1)
def _compiled_research_graph():
    return build_research_graph()


def _run_research_agent(
    question: str,
    focus: str | None = None,
    constraints: list[str] | None = None,
) -> dict:
    task = ResearchTask(
        question=question, focus=focus, constraints=constraints or []
    )
    graph = _compiled_research_graph()
    result = graph.invoke({"messages": [HumanMessage(content=task.to_prompt())]})
    last_message = result["messages"][-1]
    content = getattr(last_message, "content", "") or ""
    report = ResearchReport(content=content, sources=[])
    return report.model_dump()


@lru_cache(maxsize=1)
def build_research_tool() -> StructuredTool:
    return StructuredTool.from_function(
        func=_run_research_agent,
        name="run_research_agent",
        description=(
            "Run a focused research sub-agent and return a structured report."
        ),
        args_schema=ResearchTask,
    )
