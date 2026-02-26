from langchain_core.messages import AIMessage, SystemMessage, ToolMessage
from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import ToolNode

from src.models import ResearchConfig
from src.prompts.deepagent_prompt import get_orchestrator_system_prompt
from src.state import OrchestratorState
from src.tools.research_agent_tool import build_research_tool
from src.tools.todo_list import build_todo_tool
from src.utils import build_chat_model


research_tool = build_research_tool()
todo_tool = build_todo_tool()


MIXED_TOOL_WARNING = (
    "Error: You called both run_research_agent and set_todos in the same turn. "
    "These must be called in separate turns. Please retry with only one tool type."
)


async def orchestrator_node(state: OrchestratorState, config: RunnableConfig) -> dict:
    cfg = ResearchConfig.from_runnable_config(config)
    model = build_chat_model(cfg, role="orchestrator").bind_tools(
        [research_tool, todo_tool]
    )
    messages = [
        SystemMessage(content=get_orchestrator_system_prompt()),
        *state["messages"],
    ]
    response = await model.ainvoke(messages, config=config)

    if response.tool_calls:
        tool_names = {call.get("name") for call in response.tool_calls}
        if len(tool_names) > 1:
            return {
                "messages": [
                    response,
                    *[
                        ToolMessage(
                            content=MIXED_TOOL_WARNING,
                            name=call.get("name", ""),
                            tool_call_id=call.get("id", ""),
                        )
                        for call in response.tool_calls
                    ],
                ]
            }

    return {"messages": [response]}


def route_orchestrator(state: OrchestratorState) -> str:
    last_message = state["messages"][-1]
    if isinstance(last_message, ToolMessage):
        if last_message.content == MIXED_TOOL_WARNING:
            return "orchestrator"
        return "end"
    if not isinstance(last_message, AIMessage) or not last_message.tool_calls:
        return "end"
    tool_names = {call.get("name") for call in last_message.tool_calls}
    if tool_names == {"run_research_agent"}:
        return "research_agent"
    if tool_names == {"set_todos"}:
        return "todo_list"
    return "end"


builder = StateGraph(OrchestratorState)
builder.add_node("orchestrator", orchestrator_node)
builder.add_node("research_agent", ToolNode([research_tool]))
builder.add_node("todo_list", ToolNode([todo_tool]))

builder.add_edge(START, "orchestrator")
builder.add_conditional_edges(
    "orchestrator",
    route_orchestrator,
    {
            "orchestrator": "orchestrator",
        "research_agent": "research_agent",
        "todo_list": "todo_list",
        "end": END,
    },
)
builder.add_edge("research_agent", "orchestrator")
builder.add_edge("todo_list", "orchestrator")

orchestrator_graph = builder.compile().with_config(recursion_limit=1000)
