"""
Narrative AI SDK - Central entry point for all AI engines.

The public surface is intentionally tiny::

    import narrative_ai as nai

    # minimal usage (uses providers.yml / env defaults)
    answer = await nai.llm.generate("Hello world")

    # bring-your-own model + provider + key (no config files to edit)
    nai.llm.configure(provider="openai", model="gpt-4o", api_key="sk-...")
    answer = await nai.llm.generate("Hello world")

Engines are resolved lazily (PEP 562 ``__getattr__``) so that simply doing
``import narrative_ai`` is cheap and does NOT require every optional, heavy
dependency (torch, httpx, openai, livekit, ...) to be installed. Each engine's
extra dependencies are only imported the first time you access that engine, and
a missing optional dependency raises a clear, actionable ``ImportError`` telling
you exactly which extra to install (e.g. ``pip install narrative-ai-framework[llm]``)
instead of breaking ``import narrative_ai`` entirely.
"""

from __future__ import annotations

import importlib
from types import ModuleType

__version__ = "0.4.0"

# Engine name -> (dotted module path, pip extras group that provides its deps)
_ENGINES: dict[str, tuple[str, str]] = {
    "llm": ("narrative_ai.engines.llm.api", "llm"),
    "ocr": ("narrative_ai.engines.ocr.api", "ocr"),
    "stt": ("narrative_ai.engines.stt.api", "stt"),
    "tts": ("narrative_ai.engines.tts.api", "tts"),
    "rag": ("narrative_ai.engines.rag.api", "rag"),
    "vlm": ("narrative_ai.engines.vlm.api", "vlm"),
    "input_processor": ("narrative_ai.engines.input_processor.api", "ocr"),
    "web_intel": ("narrative_ai.engines.web_intel.api", "web"),
    "voice_mode": ("narrative_ai.engines.voice_mode.api", "voice"),
}

__all__ = ["__version__", *_ENGINES.keys()]


def _load_engine(name: str) -> ModuleType:
    """Import an engine's ``api`` module, raising a friendly error on missing deps."""
    module_path, extra = _ENGINES[name]
    try:
        return importlib.import_module(module_path)
    except ImportError as exc:
        missing = getattr(exc, "name", None) or str(exc)
        raise ImportError(
            f"The '{name}' engine requires optional dependencies that are not "
            f"installed (missing module: '{missing}').\n"
            f"Install them with:  pip install narrative-ai-framework[{extra}]\n"
            f"Or install everything with:  pip install narrative-ai-framework[all]"
        ) from exc


def __getattr__(name: str) -> ModuleType:
    """Lazily resolve ``narrative_ai.<engine>`` on first access (PEP 562)."""
    if name in _ENGINES:
        module = _load_engine(name)
        # Cache on the package so subsequent lookups skip __getattr__ entirely.
        globals()[name] = module
        return module
    raise AttributeError(f"module 'narrative_ai' has no attribute '{name}'")


def __dir__() -> list[str]:
    return sorted(set(__all__) | set(globals().keys()))
