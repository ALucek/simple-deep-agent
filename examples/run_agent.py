"""
Simplified CLI interface example for running the simple deep research agent.
"""

import asyncio
import os
import sys
import uuid

from langchain_core.messages import AIMessage, HumanMessage
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from src.graphs.main_graph import builder


def _extract_interrupt(event: dict) -> str | None:
    interrupts = event.get("__interrupt__")
    if not interrupts:
        return None
    if isinstance(interrupts, (list, tuple)):
        interrupt_obj = interrupts[0] if interrupts else None
    else:
        interrupt_obj = interrupts
    if interrupt_obj is None:
        return None
    return getattr(interrupt_obj, "value", interrupt_obj)


async def run() -> None:
    graph = builder.compile(checkpointer=InMemorySaver())
    thread_id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": thread_id}}

    user_input = input("User: ").strip()
    if not user_input:
        print("No input provided.")
        return

    next_input: dict | Command = {
        "messages": [HumanMessage(content=user_input)]
    }

    while True:
        interrupt_question = None
        last_ai_message = None

        async for event in graph.astream(next_input, config, stream_mode="updates"):
            interrupt_question = _extract_interrupt(event) or interrupt_question
            for payload in event.values():
                if isinstance(payload, dict) and "messages" in payload:
                    message = payload["messages"][-1]
                    if isinstance(message, AIMessage):
                        last_ai_message = message

        if last_ai_message:
            print(f"\nAssistant: {last_ai_message.content}\n")

        if not interrupt_question:
            break

        answer = input(f"{interrupt_question}\n> ").strip()
        next_input = Command(resume=answer)


if __name__ == "__main__":
    asyncio.run(run())
