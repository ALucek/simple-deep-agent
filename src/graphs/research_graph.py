import asyncio

from langchain_core.messages import AIMessage, SystemMessage, ToolMessage
from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, START, StateGraph

from src.models import ResearchConfig
from src.prompts.research_agent_prompt import get_research_agent_system_prompt
from src.state import ResearchState
from src.tools.web_search import (
    build_tavily_tool,
    filter_results,
    format_results_markdown,
)
from src.utils import build_chat_model


async def research_agent_node(state: ResearchState, config: RunnableConfig) -> dict:
    cfg = ResearchConfig.from_runnable_config(config)
    web_search_tool = build_tavily_tool()
    model = build_chat_model(
        cfg,
        model=cfg.researcher_model,
        temperature=cfg.researcher_temperature,
    ).bind_tools([web_search_tool])
    messages = [
        SystemMessage(content=get_research_agent_system_prompt()),
        *state["messages"],
    ]
    response = await model.ainvoke(messages, config=config)
    return {"messages": [response]}


def route_research(state: ResearchState) -> str:
    last_message = state["messages"][-1]
    if isinstance(last_message, AIMessage) and last_message.tool_calls:
        return "tools"
    return "end"


async def web_search_node(state: ResearchState, config: RunnableConfig) -> dict:
    cfg = ResearchConfig.from_runnable_config(config)
    last_message = state["messages"][-1]
    tool_calls = last_message.tool_calls or []

    used = state.get("search_count", 0)
    remaining = max(cfg.max_searches - used, 0)
    execute_calls = tool_calls[:remaining]
    skipped_calls = tool_calls[remaining:]

    web_search_tool = build_tavily_tool()
    tasks = [
        web_search_tool.ainvoke(call.get("args", {}))
        for call in execute_calls
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    tool_messages: list[ToolMessage] = []
    for call, result in zip(execute_calls, results):
        if isinstance(result, Exception):
            content = f"Error running search: {result}"
        elif isinstance(result, dict):
            content = format_results_markdown(filter_results(result))
        else:
            content = str(result)
        tool_messages.append(
            ToolMessage(
                content=content,
                name=call.get("name", "internet_search"),
                tool_call_id=call.get("id", ""),
            )
        )

    if skipped_calls:
        for call in skipped_calls:
            tool_messages.append(
                ToolMessage(
                    content=(
                        "Search limit reached. No further web searches were executed."
                    ),
                    name=call.get("name", "internet_search"),
                    tool_call_id=call.get("id", ""),
                )
            )

    return {
        "messages": tool_messages,
        "search_count": used + len(execute_calls),
    }


builder = StateGraph(ResearchState)
builder.add_node("research_agent", research_agent_node)
builder.add_node("web_search", web_search_node)
builder.add_edge(START, "research_agent")
builder.add_conditional_edges(
    "research_agent",
    route_research,
    {"tools": "web_search", "end": END},
)
builder.add_edge("web_search", "research_agent")

research_graph = builder.compile().with_config(recursion_limit=1000)
