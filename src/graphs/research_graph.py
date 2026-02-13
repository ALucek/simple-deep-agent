from __future__ import annotations

from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import ToolNode

from src.models import ResearchConfig
from src.prompts.research_agent_prompt import RESEARCH_AGENT_SYSTEM_PROMPT
from src.state import ResearchState
from src.tools.web_search import internet_search
from src.utils import build_chat_model, last_ai_message, prepend_system_message


def research_agent_node(state: ResearchState, config: RunnableConfig) -> dict:
    cfg = ResearchConfig.from_runnable_config(config)
    model = build_chat_model(cfg).bind_tools([internet_search])
    messages = prepend_system_message(
        state["messages"], RESEARCH_AGENT_SYSTEM_PROMPT
    )
    response = model.invoke(messages, config=config)
    return {"messages": [response]}


def route_research(state: ResearchState) -> str:
    last_message = last_ai_message(state["messages"])
    if isinstance(last_message, AIMessage) and last_message.tool_calls:
        return "tools"
    return "end"


def build_research_graph():
    builder = StateGraph(ResearchState)
    builder.add_node("research_agent", research_agent_node)
    builder.add_node("research_tools", ToolNode([internet_search]))
    builder.add_edge(START, "research_agent")
    builder.add_conditional_edges(
        "research_agent",
        route_research,
        {"tools": "research_tools", "end": END},
    )
    builder.add_edge("research_tools", "research_agent")
    return builder.compile()


graph = build_research_graph()
