"""Deployment mode data models."""

from __future__ import annotations

from pydantic import BaseModel


class DeploymentMode(BaseModel):
    """A gateway deployment mode (dev/staging/prod)."""

    name: str
    title: str | None = None
    description: str | None = None
    resourceCount: int | None = None
