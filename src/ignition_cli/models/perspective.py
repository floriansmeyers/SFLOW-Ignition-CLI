"""Pydantic models for Perspective view structures."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ComponentMeta(BaseModel):
    """Component metadata (name, flags)."""

    name: str
    hasDelegate: bool = False


class ViewProps(BaseModel):
    """Top-level view properties."""

    defaultSize: dict[str, int] = Field(
        default_factory=lambda: {"width": 800, "height": 600},
    )


class PerspectiveComponent(BaseModel):
    """A single Perspective component node."""

    type: str
    version: int = 0
    props: dict[str, Any] = Field(default_factory=dict)
    meta: ComponentMeta
    position: dict[str, Any] = Field(default_factory=dict)
    custom: dict[str, Any] = Field(default_factory=dict)
    propConfig: dict[str, Any] = Field(default_factory=dict)
    children: list[PerspectiveComponent] = Field(default_factory=list)
    events: dict[str, Any] = Field(default_factory=dict)


class PerspectiveView(BaseModel):
    """A complete Perspective view definition (view.json)."""

    root: PerspectiveComponent
    custom: dict[str, Any] = Field(default_factory=dict)
    params: dict[str, Any] = Field(default_factory=dict)
    props: ViewProps = Field(default_factory=ViewProps)
    propConfig: dict[str, Any] = Field(default_factory=dict)


class ResourceMeta(BaseModel):
    """Resource metadata (resource.json) for a Perspective resource."""

    scope: str = "G"
    version: int = 1
    restricted: bool = False
    overridable: bool = True
    files: list[str] = Field(default_factory=list)
    attributes: dict[str, Any] = Field(default_factory=dict)


class StyleClass(BaseModel):
    """A Perspective style class definition (style.json)."""

    base: dict[str, Any] = Field(default_factory=dict)


class PageConfig(BaseModel):
    """Perspective page configuration (config.json)."""

    pages: dict[str, Any] = Field(default_factory=dict)
