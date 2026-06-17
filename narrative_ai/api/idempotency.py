"""Idempotency support for mutation endpoints.

When the client sends an Idempotency-Key header, we store the response
(keyed by user_id + key) and return the same response for duplicate
requests within the TTL window (e.g. retries or double-submit).
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Optional

from narrative_ai.infrastructure.cache import get_cache
from narrative_ai.infrastructure.cache.base_cache import BaseCache

logger = logging.getLogger(__name__)

_IDEMPOTENCY_KEY_PREFIX = "idempotency"
_IDEMPOTENCY_TTL_SECONDS = 86400  # 24 hours
_MAX_KEY_LENGTH = 128
_KEY_RE = re.compile(r"^[a-zA-Z0-9_\-]+$")


def _sanitize_idempotency_key(raw: str) -> Optional[str]:
    """Return a safe cache key part, or None if invalid."""
    if not raw or not isinstance(raw, str):
        return None
    stripped = raw.strip()
    if not stripped or len(stripped) > _MAX_KEY_LENGTH:
        return None
    if not _KEY_RE.match(stripped):
        return None
    return stripped


def _cache_key(user_id: str, idempotency_key: str) -> str:
    return f"{_IDEMPOTENCY_KEY_PREFIX}:{user_id}:{idempotency_key}"


async def get_idempotent_response(
    user_id: str,
    idempotency_key: str,
    cache: Optional[BaseCache] = None,
) -> Optional[tuple[int, dict[str, Any]]]:
    """Return cached (status_code, body_dict) if this key was already processed."""
    key = _sanitize_idempotency_key(idempotency_key)
    if not key:
        return None
    c = cache or get_cache()
    cache_key = _cache_key(user_id, key)
    try:
        raw = await c.get(cache_key)
    except Exception as exc:
        logger.debug("Idempotency cache get failed: %s", exc)
        return None
    if not raw:
        return None
    try:
        data = json.loads(raw)
        status_code = int(data.get("status_code", 201))
        body = data.get("body")
        if body is None:
            return None
        return (status_code, body)
    except (json.JSONDecodeError, TypeError, KeyError):
        return None


async def set_idempotent_response(
    user_id: str,
    idempotency_key: str,
    status_code: int,
    body: dict[str, Any],
    ttl: int = _IDEMPOTENCY_TTL_SECONDS,
    cache: Optional[BaseCache] = None,
) -> None:
    """Store response for this idempotency key so replays return the same result."""
    key = _sanitize_idempotency_key(idempotency_key)
    if not key:
        return
    c = cache or get_cache()
    cache_key = _cache_key(user_id, key)
    payload = json.dumps({"status_code": status_code, "body": body}, default=str)
    try:
        await c.set(cache_key, payload, ttl=ttl)
    except Exception as exc:
        logger.debug("Idempotency cache set failed: %s", exc)
