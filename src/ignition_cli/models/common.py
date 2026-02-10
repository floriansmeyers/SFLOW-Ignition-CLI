"""Common response models."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class ErrorResponse(BaseModel):
    """Standard error response from the gateway."""

    status: int
    message: str
    details: str | None = None


class PaginationMetadata(BaseModel):
    """Pagination metadata from the Ignition API."""

    total: int | None = None
    matching: int | None = None
    limit: int | None = None
    offset: int = 0


class PaginatedResponse(BaseModel):
    """Paginated API response wrapper matching real Ignition format.

    Format: ``{"items": [...], "metadata": {"total", "matching", "limit", "offset"}}``
    """

    items: list[Any]
    metadata: PaginationMetadata | None = None
