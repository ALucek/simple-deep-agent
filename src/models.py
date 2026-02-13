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
    question: str = Field(description="The research task or question to investigate.")
    focus: str | None = Field(
        default=None, description="Optional focus or angle to prioritize."
    )
    constraints: list[str] = Field(
        default_factory=list, description="Optional constraints for the research."
    )

    def to_prompt(self) -> str:
        lines = [f"Task: {self.question}"]
        if self.focus:
            lines.append(f"Focus: {self.focus}")
        if self.constraints:
            lines.append("Constraints:")
            lines.extend(f"- {item}" for item in self.constraints)
        return "\n".join(lines)


class ResearchReport(BaseModel):
    content: str = Field(description="The research report content.")
    sources: list[str] = Field(
        default_factory=list,
        description="Optional list of sources or citation URLs.",
    )
