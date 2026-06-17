"""Shared HTTP helpers for API routes.

Used by API routes for consistent structured error responses (code + message in
detail) that work with the global error handler.
"""

from __future__ import annotations

from typing import Optional

from fastapi import HTTPException


def http_error(
    status: int,
    code: str,
    message: str,
    *,
    headers: Optional[dict[str, str]] = None,
) -> HTTPException:
    """Return an HTTPException with detail dict for consistent API error format."""
    return HTTPException(
        status_code=status,
        detail={"code": code, "message": message},
        headers=headers or {},
    )
