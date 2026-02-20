from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt

from src.models import ClarificationDecision, ResearchConfig
from src.prompts.clarify_prompt import CLARIFY_SYSTEM_PROMPT
from src.state import MainState
from src.utils import build_chat_model
from src.graphs.orchestrator_graph import orchestrator_graph


async def decide_clarification_node(
    state: MainState, config: RunnableConfig
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


async def clarification_interrupt_node(state: MainState) -> dict:
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


def route_after_clarification(state: MainState) -> str:
    if state.get("clarification_question"):
        return "clarification_interrupt"
    return "orchestrator"


builder = StateGraph(MainState)
builder.add_node("decide_clarification", decide_clarification_node)
builder.add_node("clarification_interrupt", clarification_interrupt_node)
builder.add_node("orchestrator", orchestrator_graph)

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
builder.add_edge("orchestrator", END)

main_graph = builder.compile().with_config(recursion_limit=1000)
