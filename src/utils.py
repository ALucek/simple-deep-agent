
from langchain_openai import ChatOpenAI

from src.models import ResearchConfig


def build_chat_model(
    config: ResearchConfig,
    *,
    model: str | None = None,
    temperature: float | None = None,
) -> ChatOpenAI:
    return ChatOpenAI(
        model=model or config.model,
        temperature=temperature if temperature is not None else config.temperature,
    )


