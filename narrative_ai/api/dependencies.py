"""FastAPI dependency factories for repositories, engines, and app services.

Single source of truth for all injectable dependencies; no route-level
engine or service creation. Lazy singletons for engines; 503 when unavailable.
"""

from __future__ import annotations

import logging
import uuid
from typing import TYPE_CHECKING, Any, AsyncGenerator, Optional

if TYPE_CHECKING:
    from narrative_ai.application.services.entry_service import EntryService
    from narrative_ai.application.services.user_service import UserService

from fastapi import Depends, Header

from narrative_ai.api.http_helpers import http_error

try:
    from narrative_ai.api.middleware.auth import get_current_user  # noqa: F401 -- re-export
except Exception:

    async def get_current_user():  # type: ignore[override]
        raise RuntimeError("Auth dependencies are not available")


from narrative_ai.application.services.ingestion_service import IngestionAppService
from narrative_ai.application.services.llm_service import LLMAppService
from narrative_ai.application.services.rag_service import RAGAppService
from narrative_ai.application.services.stt_service import STTAppService
from narrative_ai.application.services.tts_service import TTSAppService
from narrative_ai.application.services.vlm_service import VLMAppService
from narrative_ai.engines.llm import ConversationManager
from narrative_ai.infrastructure.cache.user_profile_cache import get_user_profile_cache

try:
    from sqlalchemy.ext.asyncio import AsyncSession
    from narrative_ai.infrastructure.database.repositories.analytics_event_repository_impl import (
        PostgresAnalyticsEventRepository,
    )
    from narrative_ai.infrastructure.database.repositories.audio_repository_impl import PostgresAudioRepository
    from narrative_ai.infrastructure.database.repositories.conversation_repository_impl import (
        PostgresConversationRepository,
    )
    from narrative_ai.infrastructure.database.repositories.entry_media_repository_impl import (
        PostgresEntryMediaRepository,
    )
    from narrative_ai.infrastructure.database.repositories.entry_repository_impl import PostgresEntryRepository
    from narrative_ai.infrastructure.database.repositories.search_repository_impl import PgvectorSearchRepository
    from narrative_ai.infrastructure.database.repositories.user_repository_impl import PostgresUserRepository
    from narrative_ai.infrastructure.database.session import get_db as _get_db_session

    _DB_DEPS_AVAILABLE = True
except Exception:
    AsyncSession = Any  # type: ignore[assignment]
    PostgresAnalyticsEventRepository = Any  # type: ignore[assignment]
    PostgresAudioRepository = Any  # type: ignore[assignment]
    PostgresConversationRepository = Any  # type: ignore[assignment]
    PostgresEntryMediaRepository = Any  # type: ignore[assignment]
    PostgresEntryRepository = Any  # type: ignore[assignment]
    PgvectorSearchRepository = Any  # type: ignore[assignment]
    PostgresUserRepository = Any  # type: ignore[assignment]
    _get_db_session = None
    _DB_DEPS_AVAILABLE = False

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Lazy singletons for engine instances
# ---------------------------------------------------------------------------

_stt_engine_instance = None
_tts_engine_instance = None
_llm_engine_instance = None
_rag_engine_instance = None
_vlm_engine_instance = None
_ingestion_engine_instance = None
_web_engine_instance = None
_conversation_manager_instance = None

# ---------------------------------------------------------------------------
# Lazy singletons for app services
# ---------------------------------------------------------------------------

_stt_service_instance: Optional[STTAppService] = None
_tts_service_instance: Optional[TTSAppService] = None
_llm_service_instance: Optional[LLMAppService] = None
_rag_service_instance: Optional[RAGAppService] = None
_vlm_service_instance: Optional[VLMAppService] = None
_ingestion_service_instance: Optional[IngestionAppService] = None


# ---------------------------------------------------------------------------
# Database session
# ---------------------------------------------------------------------------


def _require_db() -> None:
    """Raise RuntimeError if database dependencies are not available. Used by get_db and repo factories."""
    if not _DB_DEPS_AVAILABLE or _get_db_session is None:
        raise RuntimeError("Database dependencies are not available")


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Yield an async database session."""
    _require_db()
    async for session in _get_db_session():
        yield session


# ---------------------------------------------------------------------------
# Header helpers
# ---------------------------------------------------------------------------


def get_user_tenant(
    current_user: dict = Depends(get_current_user),
    x_tenant_id: Optional[str] = Header(None, alias="X-Tenant-ID"),
) -> tuple[str, Optional[str]]:
    """Resolve authenticated user and optional tenant IDs.

    Security notes:
    - User identity is sourced from validated JWT claims only.
    - ``X-User-ID`` is intentionally not trusted to prevent spoofing.
    - ``X-Tenant-ID`` is optional but must be a valid UUID when provided.
    """
    raw_user_id = current_user.get("user_id")
    try:
        user_id = str(uuid.UUID(str(raw_user_id)))
    except (ValueError, TypeError):
        raise http_error(401, "INVALID_TOKEN", "Invalid token")

    tenant_id: Optional[str] = None
    if x_tenant_id:
        try:
            tenant_id = str(uuid.UUID(x_tenant_id))
        except (ValueError, TypeError):
            raise http_error(400, "INVALID_TENANT_ID", "Invalid X-Tenant-ID")

    return user_id, tenant_id


# ---------------------------------------------------------------------------
# Repository factories
# ---------------------------------------------------------------------------


async def get_user_repo(
    db: AsyncSession = Depends(get_db),
) -> PostgresUserRepository:
    _require_db()
    return PostgresUserRepository(db)


async def get_entry_repo(
    db: AsyncSession = Depends(get_db),
) -> PostgresEntryRepository:
    _require_db()
    return PostgresEntryRepository(db)


async def get_entry_media_repo(
    db: AsyncSession = Depends(get_db),
) -> PostgresEntryMediaRepository:
    _require_db()
    return PostgresEntryMediaRepository(db)


async def get_conversation_repo(
    db: AsyncSession = Depends(get_db),
) -> PostgresConversationRepository:
    _require_db()
    return PostgresConversationRepository(db)


async def get_search_repo(
    db: AsyncSession = Depends(get_db),
) -> PgvectorSearchRepository:
    _require_db()
    return PgvectorSearchRepository(db)


async def get_audio_repo(
    db: AsyncSession = Depends(get_db),
) -> PostgresAudioRepository:
    _require_db()
    return PostgresAudioRepository(db)


async def get_analytics_event_repo(
    db: AsyncSession = Depends(get_db),
) -> PostgresAnalyticsEventRepository:
    _require_db()
    return PostgresAnalyticsEventRepository(db)


# ---------------------------------------------------------------------------
# Engine factories (lazy singleton)
# ---------------------------------------------------------------------------


async def get_stt_engine():
    global _stt_engine_instance
    if _stt_engine_instance is not None:
        return _stt_engine_instance
    try:
        from narrative_ai.engines.stt import create_stt_engine_from_providers

        _stt_engine_instance = await create_stt_engine_from_providers(auto_initialize=True)
        return _stt_engine_instance
    except Exception as exc:
        logger.warning("Could not create STT engine: %s", exc)
        return None


async def get_tts_engine():
    global _tts_engine_instance
    if _tts_engine_instance is not None:
        return _tts_engine_instance
    try:
        from narrative_ai.engines.tts import create_tts_engine_from_providers

        _tts_engine_instance = await create_tts_engine_from_providers(auto_initialize=True)
        return _tts_engine_instance
    except Exception as exc:
        logger.warning("Could not create TTS engine: %s", exc)
        return None


async def get_llm_engine():
    global _llm_engine_instance
    if _llm_engine_instance is not None:
        return _llm_engine_instance
    try:
        from narrative_ai.engines.llm import LLMEngine

        engine = LLMEngine()
        await engine.initialize()
        _llm_engine_instance = engine
        return _llm_engine_instance
    except Exception as exc:
        logger.warning("Could not create LLM engine: %s", exc)
        return None


async def get_rag_engine():
    global _rag_engine_instance
    if _rag_engine_instance is not None:
        return _rag_engine_instance
    try:
        from narrative_ai.engines.rag import MemoryManager

        _rag_engine_instance = MemoryManager()
        return _rag_engine_instance
    except Exception as exc:
        logger.warning("Could not create RAG engine: %s", exc)
        return None


async def get_vlm_engine():
    global _vlm_engine_instance
    if _vlm_engine_instance is not None:
        return _vlm_engine_instance
    try:
        from narrative_ai.engines.vlm import VLMProcessor

        _vlm_engine_instance = VLMProcessor()
        return _vlm_engine_instance
    except Exception as exc:
        logger.warning("Could not create VLM engine: %s", exc)
        return None


async def get_ingestion_engine():
    global _ingestion_engine_instance
    if _ingestion_engine_instance is not None:
        return _ingestion_engine_instance
    try:
        from narrative_ai.engines.input_processor import IngestionPipeline

        _ingestion_engine_instance = IngestionPipeline()
        return _ingestion_engine_instance
    except Exception as exc:
        logger.warning("Could not create Ingestion engine: %s", exc)
        return None


async def get_web_engine():
    global _web_engine_instance
    if _web_engine_instance is not None:
        return _web_engine_instance
    try:
        from narrative_ai.engines.web_intel import WebIntelEngine

        _web_engine_instance = WebIntelEngine.from_providers_config()
        return _web_engine_instance
    except Exception as exc:
        logger.warning("Could not create Web Intelligence engine: %s", exc)
        return None


async def get_conversation_manager() -> ConversationManager:
    global _conversation_manager_instance
    if _conversation_manager_instance is None:
        _conversation_manager_instance = ConversationManager()
    return _conversation_manager_instance


# ---------------------------------------------------------------------------
# Application service factories (lazy singleton)
# ---------------------------------------------------------------------------


async def get_stt_service() -> STTAppService:
    global _stt_service_instance
    if _stt_service_instance is not None:
        return _stt_service_instance
    engine = await get_stt_engine()
    if engine is None:
        raise http_error(503, "STT_UNAVAILABLE", "STT service temporarily unavailable")
    _stt_service_instance = STTAppService(engine)
    return _stt_service_instance


async def get_tts_service() -> TTSAppService:
    global _tts_service_instance
    if _tts_service_instance is not None:
        return _tts_service_instance
    engine = await get_tts_engine()
    if engine is None:
        raise http_error(503, "TTS_UNAVAILABLE", "TTS service temporarily unavailable")
    _tts_service_instance = TTSAppService(engine)
    return _tts_service_instance


async def get_llm_service() -> LLMAppService:
    global _llm_service_instance
    if _llm_service_instance is not None:
        return _llm_service_instance
    engine = await get_llm_engine()
    if engine is None:
        raise http_error(503, "LLM_UNAVAILABLE", "LLM service temporarily unavailable")
    conv = await get_conversation_manager()
    _llm_service_instance = LLMAppService(engine, conversation_manager=conv)
    return _llm_service_instance


async def get_rag_service() -> RAGAppService:
    global _rag_service_instance
    if _rag_service_instance is not None:
        return _rag_service_instance
    engine = await get_rag_engine()
    if engine is None:
        raise http_error(503, "RAG_UNAVAILABLE", "RAG service temporarily unavailable")
    _rag_service_instance = RAGAppService(engine)
    return _rag_service_instance


async def get_vlm_service() -> VLMAppService:
    global _vlm_service_instance
    if _vlm_service_instance is not None:
        return _vlm_service_instance
    engine = await get_vlm_engine()
    if engine is None:
        raise http_error(503, "VLM_UNAVAILABLE", "VLM service temporarily unavailable")
    _vlm_service_instance = VLMAppService(engine, max_concurrency=2)
    return _vlm_service_instance


async def get_ingestion_service() -> IngestionAppService:
    global _ingestion_service_instance
    if _ingestion_service_instance is not None:
        return _ingestion_service_instance
    engine = await get_ingestion_engine()
    if engine is None:
        raise http_error(503, "INGESTION_UNAVAILABLE", "Ingestion service temporarily unavailable")
    _ingestion_service_instance = IngestionAppService(engine, max_concurrency=3)
    return _ingestion_service_instance


async def get_entry_processor():
    llm = await get_llm_engine()
    if llm is None:
        return None
    from narrative_ai.api.services.entry_processor import EntryProcessor

    return EntryProcessor(llm)


# ---------------------------------------------------------------------------
# Entry & User application services (diary + auth)
# ---------------------------------------------------------------------------


async def get_entry_service(
    entry_repo: PostgresEntryRepository = Depends(get_entry_repo),
    user_repo: PostgresUserRepository = Depends(get_user_repo),
) -> "EntryService":
    """Return the EntryService for diary entry use cases."""
    from narrative_ai.application.services.entry_service import EntryService
    from narrative_ai.application.services.user_profile_service import UserProfileService

    processor = await get_entry_processor()
    stt = await get_stt_engine()
    rag = await get_rag_engine()
    profile_cache = get_user_profile_cache()
    profile_service = UserProfileService(entry_repo, profile_cache, user_repo=user_repo)
    return EntryService(
        entry_repo,
        entry_processor=processor,
        stt_engine=stt,
        profile_service=profile_service,
        rag_engine=rag,
    )


async def get_user_service(
    user_repo: PostgresUserRepository = Depends(get_user_repo),
) -> "UserService":
    """Return the UserService for auth and user profile use cases.

    UserService.authenticate is timing-safe and does not leak email existence."""
    from narrative_ai.application.services.user_service import UserService
    from narrative_ai.infrastructure.security.password_hasher import (
        hash_password,
        verify_password,
    )

    return UserService(
        user_repo,
        hash_password=hash_password,
        verify_password=verify_password,
    )


# ---------------------------------------------------------------------------
# Shutdown helpers
# ---------------------------------------------------------------------------


async def shutdown_engine_singletons() -> None:
    """Gracefully release shared engine references."""
    global _stt_engine_instance
    global _tts_engine_instance
    global _llm_engine_instance
    global _rag_engine_instance
    global _vlm_engine_instance
    global _ingestion_engine_instance
    global _web_engine_instance
    global _conversation_manager_instance
    global _stt_service_instance
    global _tts_service_instance
    global _llm_service_instance
    global _rag_service_instance
    global _vlm_service_instance
    global _ingestion_service_instance

    for name, engine in (
        ("STT", _stt_engine_instance),
        ("TTS", _tts_engine_instance),
        ("LLM", _llm_engine_instance),
    ):
        if engine is not None and hasattr(engine, "shutdown"):
            try:
                await engine.shutdown()
                logger.info("%s engine shut down via dependency cleanup.", name)
            except Exception as exc:
                logger.warning("Failed shutting down %s engine: %s", name, exc)

    _stt_engine_instance = None
    _tts_engine_instance = None
    _llm_engine_instance = None
    _rag_engine_instance = None
    _vlm_engine_instance = None
    _ingestion_engine_instance = None
    _web_engine_instance = None
    _conversation_manager_instance = None

    _stt_service_instance = None
    _tts_service_instance = None
    _llm_service_instance = None
    _rag_service_instance = None
    _vlm_service_instance = None
    _ingestion_service_instance = None
