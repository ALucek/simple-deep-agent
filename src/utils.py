from __future__ import annotations

from typing import Iterable

from langchain_core.messages import AIMessage, AnyMessage, SystemMessage
from langchain_openai import ChatOpenAI

from src.models import ResearchConfig


def build_chat_model(config: ResearchConfig) -> ChatOpenAI:
    return ChatOpenAI(model=config.model, temperature=config.temperature)


def prepend_system_message(
    messages: Iterable[AnyMessage], system_prompt: str
) -> list[AnyMessage]:
    message_list = list(messages)
    if message_list:
        first = message_list[0]
        if isinstance(first, SystemMessage) and first.content == system_prompt:
            return message_list
    return [SystemMessage(content=system_prompt), *message_list]


def last_ai_message(messages: Iterable[AnyMessage]) -> AIMessage | None:
    for message in reversed(list(messages)):
        if isinstance(message, AIMessage):
            return message
    return None
