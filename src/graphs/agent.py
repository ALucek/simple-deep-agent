from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import ToolNode

from src.config import AgentConfig
from src.prompts.agent_prompt import get_agent_system_prompt
from src.state import AgentState
from src.tools.subagent_tool import build_subagent_tool
from src.tools.todo_list import build_todo_tool
from src.utils import build_chat_model, build_messages


subagent_tool = build_subagent_tool()
todo_tool = build_todo_tool()


async def agent_node(state: AgentState, config: RunnableConfig) -> dict:
    cfg = AgentConfig.from_runnable_config(config)
    model = build_chat_model(cfg, role="agent").bind_tools(
        [subagent_tool, todo_tool]
    )
    messages = build_messages(get_agent_system_prompt(), state["messages"])
    response = await model.ainvoke(messages, config=config)
    return {"messages": [response]}


def route_agent(state: AgentState) -> str:
    last_message = state["messages"][-1]
    if not isinstance(last_message, AIMessage) or not last_message.tool_calls:
        return "end"
    tool_names = {call.get("name") for call in last_message.tool_calls}
    if "run_subagent" in tool_names:
        return "subagent"
    if "set_todos" in tool_names:
        return "todo_list"
    return "end"


builder = StateGraph(AgentState)
builder.add_node("agent", agent_node)
builder.add_node("subagent", ToolNode([subagent_tool]))
builder.add_node("todo_list", ToolNode([todo_tool]))

builder.add_edge(START, "agent")
builder.add_conditional_edges(
    "agent",
    route_agent,
    {
        "subagent": "subagent",
        "todo_list": "todo_list",
        "end": END,
    },
)
builder.add_edge("subagent", "agent")
builder.add_edge("todo_list", "agent")

agent = builder.compile().with_config(recursion_limit=100)
