import os
from typing import Any, ClassVar

from pydantic import BaseModel, ConfigDict, Field

DEFAULT_CHAT_KWARGS: dict[str, Any] = {
    "model": os.getenv("DEFAULT_MODEL", "deepseek/deepseek-v4-flash"),
}
DEFAULT_MAX_SEARCHES = int(os.getenv("MAX_SEARCHES", "5"))


class RoleConfig(BaseModel):
    """Per-role overrides for model settings."""

    model_config = ConfigDict(extra="allow")
    model: str | None = Field(default=None, description="Model override for this role.")


class AgentConfig(BaseModel):
    """Configuration loaded from RunnableConfig.configurable."""

    model_config = ConfigDict(extra="ignore")

    agent: RoleConfig = Field(default_factory=RoleConfig, description="Overrides for the top-level agent.")
    subagent: RoleConfig = Field(default_factory=RoleConfig, description="Overrides for the subagent.")
    max_searches: int = Field(
        default=DEFAULT_MAX_SEARCHES,
        description="Hard limit on the number of web searches per subagent run.",
    )

    ROLES: ClassVar[set[str]] = {"agent", "subagent"}

    def chat_kwargs(self, role: str) -> dict[str, Any]:
        if role not in self.ROLES:
            raise ValueError(f"Unknown role {role!r}, expected one of {self.ROLES}")
        return {**DEFAULT_CHAT_KWARGS, **getattr(self, role).model_dump(exclude_none=True)}

    @classmethod
    def from_runnable_config(cls, config: dict[str, Any] | None) -> "AgentConfig":
        configurable = (config or {}).get("configurable")
        if not isinstance(configurable, dict) or not configurable:
            return cls()
        return cls.model_validate(configurable)
