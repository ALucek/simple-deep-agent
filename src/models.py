from typing import Any, ClassVar

from pydantic import BaseModel, ConfigDict, Field


class DefaultRoleConfig(BaseModel):
    """Default model settings."""

    model_config = ConfigDict(extra="allow")

    model: str = Field(
        default="gpt-5.2-2025-12-11",
        min_length=1,
        description="Default model for all roles.",
    )
    temperature: float = Field(
        default=1,
        description="Default temperature for all roles.",
    )


class RoleConfig(BaseModel):
    """Per-role overrides for model settings."""

    model_config = ConfigDict(extra="allow")

    model: str | None = Field(
        default=None,
        description="Optional model override for this role.",
    )
    temperature: float | None = Field(
        default=None,
        description="Optional temperature override for this role.",
    )


class ResearchConfig(BaseModel):
    """Configuration loaded from RunnableConfig.configurable."""

    model_config = ConfigDict(extra="ignore")

    default: DefaultRoleConfig = Field(
        default_factory=DefaultRoleConfig,
        description="Default model settings for all roles.",
    )
    orchestrator: RoleConfig = Field(
        default_factory=RoleConfig,
        description="Overrides for the orchestration agent.",
    )
    clarifier: RoleConfig = Field(
        default_factory=RoleConfig,
        description="Overrides for the clarifying agent.",
    )
    researcher: RoleConfig = Field(
        default_factory=RoleConfig,
        description="Overrides for the research sub-agent.",
    )
    max_searches: int = Field(
        default=30,
        description="Hard limit on the number of web searches per research run.",
    )

    ROLES: ClassVar[set[str]] = {"orchestrator", "clarifier", "researcher"}

    def chat_kwargs(self, role: str | None = None) -> dict[str, Any]:
        kwargs = self.default.model_dump(exclude_none=True)
        if role:
            if role not in self.ROLES:
                raise ValueError(f"Unknown role {role!r}, expected one of {self.ROLES}")
            kwargs.update(getattr(self, role).model_dump(exclude_none=True))
        return kwargs

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
