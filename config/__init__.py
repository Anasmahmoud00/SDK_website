"""
Configuration module for Narrative AI Framework.

This module provides centralized configuration management for all
providers and services.
"""

from .providers import (
    ProvidersConfig,
    ProviderInfo,
    ProviderType,
    get_providers_config,
    get_llm_provider,
    get_stt_provider,
    get_tts_provider,
    get_web_provider,
)

__all__ = [
    # Classes
    "ProvidersConfig",
    "ProviderInfo",
    "ProviderType",
    
    # Functions
    "get_providers_config",
    "get_llm_provider",
    "get_stt_provider",
    "get_tts_provider",
    "get_web_provider",
]
