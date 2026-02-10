"""Generic resource data models."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class Resource(BaseModel):
    """A generic gateway resource."""

    name: str
    type: str | None = None
    config: dict[str, Any] | None = None
    state: str | None = None


class ResourceType(BaseModel):
    """A resource type discovered from OpenAPI."""

    name: str
    path: str
    methods: list[str] | None = None
    description: str | None = None
