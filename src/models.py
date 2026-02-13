from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ResearchConfig(BaseModel):
    """Configuration loaded from RunnableConfig.configurable."""

    model_config = ConfigDict(extra="ignore")

    model: str = Field(
        default="gpt-5.2-2025-12-11",
        description="Default model for all roles if role overrides not set.",
    )
    temperature: float = Field(
        default=1,
        description="Default temperature for all roles if role overrides not set.",
    )
    orchestrator_model: str | None = Field(
        default=None,
        description="Optional model override for the orchestration agent.",
    )
    orchestrator_temperature: float | None = Field(
        default=None,
        description="Optional temperature override for the orchestration agent.",
    )
    clarifier_model: str | None = Field(
        default=None,
        description="Optional model override for the clarifying agent.",
    )
    clarifier_temperature: float | None = Field(
        default=None,
        description="Optional temperature override for the clarifying agent.",
    )
    researcher_model: str | None = Field(
        default=None,
        description="Optional model override for the research sub-agent.",
    )
    researcher_temperature: float | None = Field(
        default=None,
        description="Optional temperature override for the research sub-agent.",
    )
    max_searches: int = Field(
        default=30,
        description="Hard limit on the number of web searches per research run.",
    )

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
