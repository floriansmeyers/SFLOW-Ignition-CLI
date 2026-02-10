"""Common response models."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class ErrorResponse(BaseModel):
    """Standard error response from the gateway."""

    status: int
    message: str
    details: str | None = None


class PaginatedResponse(BaseModel):
    """Paginated API response wrapper."""

    items: list[Any]
    total: int | None = None
    offset: int = 0
    limit: int | None = None
