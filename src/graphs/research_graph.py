from __future__ import annotations

from langchain_core.messages import AIMessage, SystemMessage, ToolMessage
from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, START, StateGraph

from src.models import ResearchConfig
from src.prompts.research_agent_prompt import RESEARCH_AGENT_SYSTEM_PROMPT
from src.state import ResearchState
from src.tools.web_search import build_web_search_tool
from src.utils import build_chat_model


def research_agent_node(state: ResearchState, config: RunnableConfig) -> dict:
    cfg = ResearchConfig.from_runnable_config(config)
    web_search_tool = build_web_search_tool()
    model = build_chat_model(
        cfg,
        model=cfg.researcher_model,
        temperature=cfg.researcher_temperature,
    ).bind_tools([web_search_tool])
    messages = [
        SystemMessage(content=RESEARCH_AGENT_SYSTEM_PROMPT),
        *state["messages"],
    ]
    response = model.invoke(messages, config=config)
    return {"messages": [response]}


def route_research(state: ResearchState) -> str:
    last_message = state["messages"][-1]
    if isinstance(last_message, AIMessage) and last_message.tool_calls:
        return "tools"
    return "end"


def web_search_node(state: ResearchState, config: RunnableConfig) -> dict:
    cfg = ResearchConfig.from_runnable_config(config)
    last_message = state["messages"][-1]
    tool_calls = last_message.tool_calls or []

    used = state.get("search_count", 0)
    remaining = max(cfg.max_searches - used, 0)
    execute_calls = tool_calls[:remaining]
    skipped_calls = tool_calls[remaining:]

    web_search_tool = build_web_search_tool()
    tool_messages: list[ToolMessage] = []
    for call in execute_calls:
        result = web_search_tool.invoke(call.get("args", {}))
        tool_messages.append(
            ToolMessage(
                content=result,
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


def build_research_graph():
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
    return builder.compile()


research_graph = build_research_graph()
