from langchain_core.messages import HumanMessage
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import StructuredTool

from src.graphs.research_graph import research_graph
from src.models import ResearchTask

RESEARCH_AGENT_TOOL_DESCRIPTION = """Run a focused research sub-agent that will perform comprehensive web searches and return a structured report. 
Usage guidelines:
1. Specify Intent - The research agent is another LLM based agent that can be given further instructions or clarification to perform the research task.
2. Be Specific - Research agents excel at individual topic deep dives. Avoid broad, multi-topic queries. Call this tool multiple times for different topics.
"""


async def _run_research_agent(query: str, config: RunnableConfig) -> dict:
    result = await research_graph.ainvoke(
        {"messages": [HumanMessage(content=query)]},
        config=config,
    )
    last_message = result["messages"][-1]
    content = getattr(last_message, "content", "") or ""
    return {"content": content}


def build_research_tool() -> StructuredTool:
    return StructuredTool.from_function(
        coroutine=_run_research_agent,
        name="run_research_agent",
        description=RESEARCH_AGENT_TOOL_DESCRIPTION,
        args_schema=ResearchTask,
    )
