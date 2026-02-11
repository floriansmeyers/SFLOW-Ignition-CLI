"""Pydantic models for CLI configuration."""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator


class GatewayProfile(BaseModel):
    """A named gateway connection profile."""

    name: str
    url: str = Field(description="Gateway base URL, e.g. https://gateway:8043")
    token: str | None = Field(
        default=None, description="API token (format: keyId:secretKey)",
    )
    username: str | None = Field(default=None, description="Basic auth username")
    password: str | None = Field(default=None, description="Basic auth password")
    verify_ssl: bool = Field(default=True, description="Verify SSL certificates")
    timeout: float = Field(
        default=30.0, gt=0, le=600, description="Request timeout in seconds",
    )

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        if not v.startswith(("http://", "https://")):
            raise ValueError("URL must start with http:// or https://")
        return v.rstrip("/")

    @property
    def auth_configured(self) -> bool:
        has_basic = (
            self.username is not None and self.password is not None
        )
        return self.token is not None or has_basic


class CLIConfig(BaseModel):
    """Root configuration model."""

    default_profile: str | None = None
    default_format: str = "table"
    profiles: dict[str, GatewayProfile] = Field(default_factory=dict)
