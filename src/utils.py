
from typing import Any

from langchain_core.messages import AnyMessage, SystemMessage, trim_messages
from langchain_openrouter import ChatOpenRouter

from src.config import AgentConfig

MAX_HISTORY_MESSAGES = 10


def build_chat_model(
    config: AgentConfig,
    *,
    role: str,
    **overrides: Any,
) -> ChatOpenRouter:
    kwargs = config.chat_kwargs(role)
    if overrides:
        kwargs.update(overrides)
    return ChatOpenRouter(**kwargs)


def build_messages(system_prompt: str, history: list[AnyMessage]) -> list[AnyMessage]:
    """Prepend the system prompt to the last MAX_HISTORY_MESSAGES of conversation history."""
    messages = [SystemMessage(content=system_prompt), *history]
    return trim_messages(
        messages,
        strategy="last",
        token_counter=len,
        max_tokens=MAX_HISTORY_MESSAGES + 1,
        start_on="human",
        include_system=True,
    )

