from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ResearchConfig(BaseModel):
    """Configuration loaded from RunnableConfig.configurable."""

    model_config = ConfigDict(extra="ignore")

    model: str = "gpt-5.2-2025-12-11"
    temperature: float = 1
    max_searches: int = 5

    @classmethod
    def from_runnable_config(cls, config: dict[str, Any] | None) -> "ResearchConfig":
        if not config:
            return cls()
        configurable = config.get("configurable", {})
        if not isinstance(configurable, dict) or not configurable:
            return cls()
        return cls.model_validate(configurable)


class ClarificationDecision(BaseModel):
    needs_clarification: bool = Field(
        description="Whether a clarification question is required before research starts."
    )
    question: str | None = Field(
        default=None,
        description="The question to ask the user if clarification is required.",
    )


class ResearchTask(BaseModel):
    query: str = Field(description="The research query to investigate.")


class ResearchReport(BaseModel):
    content: str = Field(description="The research report content.")
