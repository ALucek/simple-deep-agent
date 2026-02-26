
from typing import Any

from langchain_openai import ChatOpenAI

from src.models import ResearchConfig


def build_chat_model(
    config: ResearchConfig,
    *,
    role: str | None = None,
    **overrides: Any,
) -> ChatOpenAI:
    kwargs = config.chat_kwargs(role=role)
    if overrides:
        kwargs.update(overrides)
    return ChatOpenAI(**kwargs)


