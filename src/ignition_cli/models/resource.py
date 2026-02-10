"""Generic resource data models."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class Resource(BaseModel):
    """A generic gateway resource matching the real Ignition API response."""

    name: str
    type: str | None = None
    config: dict[str, Any] | None = None
    state: str | None = None
    files: list[str] | None = None
    data: list[str] | None = None
    signature: str | None = None
    enabled: bool | None = None
    version: int | None = None
    collection: str | None = None
    attributes: dict[str, Any] | None = None
    metrics: dict[str, Any] | None = None
    healthchecks: list[Any] | None = None


class ResourceType(BaseModel):
    """A resource type discovered from OpenAPI."""

    name: str
    path: str
    methods: list[str] | None = None
    description: str | None = None
