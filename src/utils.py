from __future__ import annotations


from langchain_openai import ChatOpenAI

from src.models import ResearchConfig


def build_chat_model(config: ResearchConfig) -> ChatOpenAI:
    return ChatOpenAI(model=config.model, temperature=config.temperature)


