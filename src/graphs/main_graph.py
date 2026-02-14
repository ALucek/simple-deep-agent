from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import ToolNode
from langgraph.types import interrupt

from src.models import ClarificationDecision, ResearchConfig
from src.prompts.clarify_prompt import CLARIFY_SYSTEM_PROMPT
from src.prompts.deepagent_prompt import ORCHESTRATOR_SYSTEM_PROMPT
from src.state import GraphState
from src.tools.research_agent_tool import build_research_tool
from src.tools.todo_list import build_todo_tool
from src.utils import build_chat_model


async def decide_clarification_node(
    state: GraphState, config: RunnableConfig
) -> dict:
    cfg = ResearchConfig.from_runnable_config(config)
    model = build_chat_model(
        cfg,
        model=cfg.clarifier_model,
        temperature=cfg.clarifier_temperature,
    ).with_structured_output(ClarificationDecision)
    messages = [SystemMessage(content=CLARIFY_SYSTEM_PROMPT), *state["messages"]]
    decision = await model.ainvoke(messages, config=config)
    question = decision.question if decision.needs_clarification else None
    return {"clarification_question": question}


async def clarification_interrupt_node(state: GraphState) -> dict:
    question = state.get("clarification_question")
    if not question:
        return {}
    answer = interrupt({"question": question})
    return {
        "messages": [
            AIMessage(content=question),
            HumanMessage(content=str(answer)),
        ],
        "clarification_question": None,
    }


def route_after_clarification(state: GraphState) -> str:
    if state.get("clarification_question"):
        return "clarification_interrupt"
    return "orchestrator"


async def orchestrator_node(state: GraphState, config: RunnableConfig) -> dict:
    cfg = ResearchConfig.from_runnable_config(config)
    research_tool = build_research_tool()
    todo_tool = build_todo_tool()
    model = build_chat_model(
        cfg,
        model=cfg.orchestrator_model,
        temperature=cfg.orchestrator_temperature,
    ).bind_tools([research_tool, todo_tool])
    messages = [
        SystemMessage(content=ORCHESTRATOR_SYSTEM_PROMPT),
        *state["messages"],
    ]
    response = await model.ainvoke(messages, config=config)
    return {"messages": [response]}


def route_orchestrator(state: GraphState) -> str:
    last_message = state["messages"][-1]
    if not isinstance(last_message, AIMessage) or not last_message.tool_calls:
        return "end"
    tool_names = {call.get("name") for call in last_message.tool_calls}
    if tool_names == {"run_research_agent"}:
        return "research_agent"
    if tool_names == {"set_todos"} and len(last_message.tool_calls) == 1:
        return "todo_list"
    return "end"


research_tool = build_research_tool()
todo_tool = build_todo_tool()

builder = StateGraph(GraphState)
builder.add_node("decide_clarification", decide_clarification_node)
builder.add_node("clarification_interrupt", clarification_interrupt_node)
builder.add_node("orchestrator", orchestrator_node)
builder.add_node("research_agent", ToolNode([research_tool]))
builder.add_node("todo_list", ToolNode([todo_tool]))

builder.add_edge(START, "decide_clarification")
builder.add_conditional_edges(
    "decide_clarification",
    route_after_clarification,
    {
        "clarification_interrupt": "clarification_interrupt",
        "orchestrator": "orchestrator",
    },
)
builder.add_edge("clarification_interrupt", "decide_clarification")
builder.add_conditional_edges(
    "orchestrator",
    route_orchestrator,
    {
        "research_agent": "research_agent",
        "todo_list": "todo_list",
        "end": END,
    },
)
builder.add_edge("research_agent", "orchestrator")
builder.add_edge("todo_list", "orchestrator")

main_graph = builder.compile()
