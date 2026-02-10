"""Pydantic models for CLI configuration."""

from __future__ import annotations

from pydantic import BaseModel, Field, HttpUrl


class GatewayProfile(BaseModel):
    """A named gateway connection profile."""

    name: str
    url: str = Field(description="Gateway base URL, e.g. https://gateway:8043")
    token: str | None = Field(default=None, description="API token (format: keyId:secretKey)")
    username: str | None = Field(default=None, description="Basic auth username")
    password: str | None = Field(default=None, description="Basic auth password")
    verify_ssl: bool = Field(default=True, description="Verify SSL certificates")
    timeout: float = Field(default=30.0, description="Request timeout in seconds")

    @property
    def auth_configured(self) -> bool:
        return self.token is not None or (self.username is not None and self.password is not None)


class CLIConfig(BaseModel):
    """Root configuration model."""

    default_profile: str | None = None
    default_format: str = "table"
    profiles: dict[str, GatewayProfile] = Field(default_factory=dict)
