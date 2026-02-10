"""Device connection data models."""

from __future__ import annotations

from pydantic import BaseModel


class DeviceConnection(BaseModel):
    """A device/driver connection on the gateway."""

    name: str
    type: str | None = None
    description: str | None = None
    enabled: bool | None = None
    state: str | None = None
    hostname: str | None = None
    port: int | None = None
