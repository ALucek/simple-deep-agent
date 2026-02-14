from __future__ import annotations

from langchain_core.messages import HumanMessage
from langchain_core.tools import StructuredTool

from src.models import ResearchReport, ResearchTask
from src.graphs.research_graph import build_research_graph

RESEARCH_AGENT_TOOL_DESCRIPTION = """Run a focused research sub-agent that will perform comprehensive web searches and return a structured report. 
Usage guidelines:
1. Specify Intent - The research agent is another LLM based agent that can be given further instructions or clarification to perform the research task.
2. Be Specific - Research agents excel at individual topic deep dives. Avoid broad, multi-topic queries. Call this tool multiple times for different topics.
"""

async def _run_research_agent(query: str) -> dict:
    task = ResearchTask(query=query)
    graph = build_research_graph()
    result = await graph.ainvoke({"messages": [HumanMessage(content=task.query)]})
    last_message = result["messages"][-1]
    content = getattr(last_message, "content", "") or ""
    report = ResearchReport(content=content)
    return report.model_dump()


def build_research_tool() -> StructuredTool:
    return StructuredTool.from_function(
        coroutine=_run_research_agent,
        name="run_research_agent",
        description=RESEARCH_AGENT_TOOL_DESCRIPTION,
        args_schema=ResearchTask,
    )
