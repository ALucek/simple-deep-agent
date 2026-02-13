from __future__ import annotations

from langchain_core.messages import AIMessage, SystemMessage
from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import ToolNode

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


def build_research_graph():
    builder = StateGraph(ResearchState)
    web_search_tool = build_web_search_tool()
    builder.add_node("research_agent", research_agent_node)
    builder.add_node("web_search", ToolNode([web_search_tool]))
    builder.add_edge(START, "research_agent")
    builder.add_conditional_edges(
        "research_agent",
        route_research,
        {"tools": "web_search", "end": END},
    )
    builder.add_edge("web_search", "research_agent")
    return builder.compile()


graph = build_research_graph()
