"""Project-related data models."""

from __future__ import annotations

from pydantic import BaseModel


class ProjectSummary(BaseModel):
    """Summary of a project from the gateway."""

    name: str
    title: str | None = None
    description: str | None = None
    enabled: bool | None = None
    state: str | None = None
    last_modified: str | None = None


class ProjectResource(BaseModel):
    """A resource within a project."""

    name: str
    type: str | None = None
    path: str | None = None
    scope: str | None = None
    last_modified: str | None = None
