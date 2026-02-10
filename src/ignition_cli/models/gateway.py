"""Gateway-related data models."""

from __future__ import annotations

from pydantic import BaseModel


class GatewayInfo(BaseModel):
    """Gateway system information."""

    name: str | None = None
    version: str | None = None
    edition: str | None = None
    state: str | None = None
    platform_os: str | None = None
    java_version: str | None = None
    uptime: int | None = None
    deploymentMode: str | None = None


class GatewayStatus(BaseModel):
    """Gateway status summary."""

    state: str
    edition: str | None = None
    version: str | None = None
    uptime_ms: int | None = None


class Module(BaseModel):
    """Installed module info."""

    name: str
    id: str | None = None
    version: str | None = None
    state: str | None = None
    license: str | None = None


class LogEntry(BaseModel):
    """Gateway log entry."""

    timestamp: str | None = None
    level: str | None = None
    logger: str | None = None
    message: str | None = None
