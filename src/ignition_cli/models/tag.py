"""Tag-related data models."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class TagNode(BaseModel):
    """A node in the tag tree (tag or folder)."""

    name: str
    path: str | None = None
    tag_type: str | None = None
    data_type: str | None = None
    value: Any = None
    quality: str | None = None
    has_children: bool = False


class TagValue(BaseModel):
    """A tag value reading."""

    path: str
    value: Any = None
    quality: str | None = None
    timestamp: str | None = None
    data_type: str | None = None


class TagProvider(BaseModel):
    """Tag provider info."""

    name: str
    type: str | None = None
    state: str | None = None
