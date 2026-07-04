import asyncio

from langchain_core.messages import AIMessage, ToolMessage
from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, START, StateGraph

from src.config import AgentConfig
from src.prompts.subagent_prompt import get_subagent_system_prompt
from src.state import SubagentState
from src.tools.web_search import build_tavily_tool, process_search_results
from src.utils import build_chat_model, build_messages

web_search_tool = build_tavily_tool()


async def subagent_node(state: SubagentState, config: RunnableConfig) -> dict:
    cfg = AgentConfig.from_runnable_config(config)
    model = build_chat_model(cfg, role="subagent").bind_tools([web_search_tool])
    messages = build_messages(get_subagent_system_prompt(), state["messages"])
    response = await model.ainvoke(messages, config=config)
    return {"messages": [response]}


def route_subagent(state: SubagentState) -> str:
    last_message = state["messages"][-1]
    if isinstance(last_message, AIMessage) and last_message.tool_calls:
        return "tools"
    return "end"


async def web_search_node(state: SubagentState, config: RunnableConfig) -> dict:
    cfg = AgentConfig.from_runnable_config(config)
    last_message = state["messages"][-1]
    tool_calls = last_message.tool_calls or []

    used = state.get("search_count", 0)
    remaining = max(cfg.max_searches - used, 0)
    execute_calls = tool_calls[:remaining]
    skipped_calls = tool_calls[remaining:]

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
            content = process_search_results(result)
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


builder = StateGraph(SubagentState)
builder.add_node("subagent", subagent_node)
builder.add_node("web_search", web_search_node)
builder.add_edge(START, "subagent")
builder.add_conditional_edges(
    "subagent",
    route_subagent,
    {"tools": "web_search", "end": END},
)
builder.add_edge("web_search", "subagent")

subagent = builder.compile().with_config(recursion_limit=100)
