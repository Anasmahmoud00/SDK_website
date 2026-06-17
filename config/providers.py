"""
Providers Configuration Loader.

Loads and manages provider configurations from providers.yml.
Supports environment variable substitution and runtime toggling.
"""

import os
import yaml
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from enum import Enum


class ProviderType(str, Enum):
    """Types of providers."""
    LLM = "llm"
    STT = "stt"
    TTS = "tts"
    REALTIME = "realtime"
    EMBEDDINGS = "embeddings"
    WEB = "web"


@dataclass
class ProviderInfo:
    """Information about a single provider."""
    name: str
    type: ProviderType
    enabled: bool
    primary: bool
    config: Dict[str, Any]
    
    @property
    def api_key(self) -> Optional[str]:
        """Get API key from environment (stripped of whitespace/BOM)."""
        key_env = self.config.get("api_key_env")
        if key_env:
            raw = os.getenv(key_env) or ""
            raw = raw.strip().strip("\ufeff")
            return raw or None
        return None
    
    @property
    def is_available(self) -> bool:
        """Check if provider is available (enabled + has credentials)."""
        if not self.enabled:
            return False
        
        # Check if API key is required and present
        key_env = self.config.get("api_key_env")
        if key_env:
            return bool(os.getenv(key_env))
        
        return True


class ProvidersConfig:
    """
    Providers Configuration Manager.
    
    Loads configuration from providers.yml and provides easy access
    to provider settings with environment variable substitution.
    
    Example:
        config = ProvidersConfig()
        
        # Get primary LLM provider
        llm = config.get_primary_provider(ProviderType.LLM)
        print(f"Using LLM: {llm.name}")
        
        # Get all enabled STT providers
        stt_providers = config.get_enabled_providers(ProviderType.STT)
        
        # Toggle a provider
        config.set_enabled("openai", ProviderType.LLM, False)
    """
    
    DEFAULT_CONFIG_PATH = Path(__file__).parent / "providers.yml"
    
    def __init__(self, config_path: Optional[Path] = None):
        """
        Initialize providers configuration.
        
        Args:
            config_path: Path to providers.yml (uses default if not provided)
        """
        self.config_path = config_path or self.DEFAULT_CONFIG_PATH
        self._config: Dict[str, Any] = {}
        self._providers: Dict[str, Dict[str, ProviderInfo]] = {}
        
        self._load_config()
    
    def _load_config(self) -> None:
        """Load configuration from YAML file."""
        if not self.config_path.exists():
            raise FileNotFoundError(f"Providers config not found: {self.config_path}")
        
        with open(self.config_path, 'r', encoding='utf-8') as f:
            self._config = yaml.safe_load(f)
        
        # Parse providers
        self._parse_providers()
    
    def _parse_providers(self) -> None:
        """Parse provider configurations into ProviderInfo objects."""
        self._providers = {}
        non_provider_keys = {
            "enabled",
            "mode",
            "primary_provider",
            "fallback_order",
            "min_confidence",
            "vad",
            "emotion_detection",
            "default_provider",
            "default_dimension",
            "timeout_ms",
            "max_results",
            "freshness_ttl",
            "deny_domains",
        }
        
        for provider_type in ProviderType:
            type_key = provider_type.value
            if type_key not in self._config:
                continue
            
            type_config = self._config[type_key]
            self._providers[type_key] = {}
            
            for name, config in type_config.items():
                # Skip non-provider keys
                if name in non_provider_keys:
                    continue
                
                if isinstance(config, dict):
                    self._providers[type_key][name] = ProviderInfo(
                        name=name,
                        type=provider_type,
                        enabled=config.get('enabled', False),
                        primary=config.get('primary', False),
                        config=config,
                    )
    
    def reload(self) -> None:
        """Reload configuration from file."""
        self._load_config()
    
    # =========================================================================
    # Provider Access Methods
    # =========================================================================
    
    def get_provider(self, name: str, provider_type: ProviderType) -> Optional[ProviderInfo]:
        """
        Get a specific provider.
        
        Args:
            name: Provider name (e.g., "openai", "elevenlabs")
            provider_type: Type of provider
        
        Returns:
            ProviderInfo or None if not found
        """
        type_providers = self._providers.get(provider_type.value, {})
        return type_providers.get(name)
    
    def get_all_providers(self, provider_type: ProviderType) -> List[ProviderInfo]:
        """
        Get all providers of a type.
        
        Args:
            provider_type: Type of provider
        
        Returns:
            List of ProviderInfo objects
        """
        type_providers = self._providers.get(provider_type.value, {})
        return list(type_providers.values())
    
    def get_enabled_providers(self, provider_type: ProviderType) -> List[ProviderInfo]:
        """
        Get all enabled providers of a type.
        
        Args:
            provider_type: Type of provider
        
        Returns:
            List of enabled ProviderInfo objects
        """
        return [p for p in self.get_all_providers(provider_type) if p.enabled]
    
    def get_available_providers(self, provider_type: ProviderType) -> List[ProviderInfo]:
        """
        Get all available providers (enabled + has credentials).
        
        Args:
            provider_type: Type of provider
        
        Returns:
            List of available ProviderInfo objects
        """
        return [p for p in self.get_all_providers(provider_type) if p.is_available]
    
    def get_primary_provider(self, provider_type: ProviderType) -> Optional[ProviderInfo]:
        """
        Get the primary provider for a type.
        
        Args:
            provider_type: Type of provider
        
        Returns:
            Primary ProviderInfo or None
        """
        for provider in self.get_all_providers(provider_type):
            if provider.primary and provider.enabled:
                return provider
        
        # Fallback to first enabled
        enabled = self.get_enabled_providers(provider_type)
        return enabled[0] if enabled else None
    
    def get_fallback_order(self, provider_type: ProviderType) -> List[str]:
        """
        Get fallback order for a provider type.
        
        Args:
            provider_type: Type of provider
        
        Returns:
            List of provider names in fallback order
        """
        type_config = self._config.get(provider_type.value, {})
        return type_config.get('fallback_order', [])
    
    def get_providers_in_order(self, provider_type: ProviderType) -> List[ProviderInfo]:
        """
        Get enabled providers in fallback order.
        
        Args:
            provider_type: Type of provider
        
        Returns:
            List of ProviderInfo in order
        """
        fallback_order = self.get_fallback_order(provider_type)
        enabled = {p.name: p for p in self.get_enabled_providers(provider_type)}
        
        result = []
        
        # Add in fallback order
        for name in fallback_order:
            if name in enabled:
                result.append(enabled.pop(name))
        
        # Add any remaining
        result.extend(enabled.values())
        
        return result
    
    # =========================================================================
    # Provider Configuration Methods
    # =========================================================================
    
    def set_enabled(self, name: str, provider_type: ProviderType, enabled: bool) -> None:
        """
        Enable or disable a provider at runtime.
        
        Note: This doesn't persist to file.
        
        Args:
            name: Provider name
            provider_type: Type of provider
            enabled: Whether to enable
        """
        provider = self.get_provider(name, provider_type)
        if provider:
            provider.enabled = enabled
    
    def set_primary(self, name: str, provider_type: ProviderType) -> None:
        """
        Set a provider as primary.
        
        Note: This doesn't persist to file.
        
        Args:
            name: Provider name
            provider_type: Type of provider
        """
        # Clear existing primary
        for provider in self.get_all_providers(provider_type):
            provider.primary = False
        
        # Set new primary
        provider = self.get_provider(name, provider_type)
        if provider:
            provider.primary = True
    
    def get_config(self, name: str, provider_type: ProviderType, key: str, default: Any = None) -> Any:
        """
        Get a specific configuration value for a provider.
        
        Args:
            name: Provider name
            provider_type: Type of provider
            key: Configuration key (supports dot notation: "models.default")
            default: Default value if not found
        
        Returns:
            Configuration value
        """
        provider = self.get_provider(name, provider_type)
        if not provider:
            return default
        
        # Support dot notation
        config = provider.config
        for k in key.split('.'):
            if isinstance(config, dict) and k in config:
                config = config[k]
            else:
                return default
        
        return config
    
    # =========================================================================
    # Global Settings
    # =========================================================================
    
    @property
    def global_config(self) -> Dict[str, Any]:
        """Get global configuration."""
        return self._config.get('global', {})
    
    @property
    def default_timeout(self) -> int:
        """Get default timeout."""
        return self.global_config.get('default_timeout', 30)
    
    @property
    def retry_config(self) -> Dict[str, Any]:
        """Get retry configuration."""
        return self.global_config.get('retry', {
            'max_attempts': 3,
            'backoff_multiplier': 2.0,
            'initial_delay': 1.0,
        })
    
    @property
    def monitoring_config(self) -> Dict[str, Any]:
        """Get monitoring configuration."""
        return self._config.get('monitoring', {})
    
    # =========================================================================
    # Utility Methods
    # =========================================================================
    
    def get_api_key(self, name: str, provider_type: ProviderType) -> Optional[str]:
        """
        Get API key for a provider.
        
        Args:
            name: Provider name
            provider_type: Type of provider
        
        Returns:
            API key from environment or None
        """
        provider = self.get_provider(name, provider_type)
        return provider.api_key if provider else None
    
    def to_dict(self) -> Dict[str, Any]:
        """Export current configuration as dictionary."""
        return self._config.copy()
    
    def __repr__(self) -> str:
        provider_counts = {
            ptype.value: len(self.get_enabled_providers(ptype))
            for ptype in ProviderType
        }
        return f"ProvidersConfig({provider_counts})"


# =============================================================================
# Convenience Functions
# =============================================================================

_global_config: Optional[ProvidersConfig] = None


def get_providers_config() -> ProvidersConfig:
    """
    Get the global providers configuration.
    
    Returns:
        ProvidersConfig instance
    """
    global _global_config
    if _global_config is None:
        _global_config = ProvidersConfig()
    return _global_config


def get_llm_provider(name: Optional[str] = None) -> Optional[ProviderInfo]:
    """Get an LLM provider (primary if name not specified)."""
    config = get_providers_config()
    if name:
        return config.get_provider(name, ProviderType.LLM)
    return config.get_primary_provider(ProviderType.LLM)


def get_stt_provider(name: Optional[str] = None) -> Optional[ProviderInfo]:
    """Get an STT provider (primary if name not specified)."""
    config = get_providers_config()
    if name:
        return config.get_provider(name, ProviderType.STT)
    return config.get_primary_provider(ProviderType.STT)


def get_tts_provider(name: Optional[str] = None) -> Optional[ProviderInfo]:
    """Get a TTS provider (primary if name not specified)."""
    config = get_providers_config()
    if name:
        return config.get_provider(name, ProviderType.TTS)
    return config.get_primary_provider(ProviderType.TTS)


def get_web_provider(name: Optional[str] = None) -> Optional[ProviderInfo]:
    """Get a Web provider (primary if name not specified)."""
    config = get_providers_config()
    if name:
        return config.get_provider(name, ProviderType.WEB)
    return config.get_primary_provider(ProviderType.WEB)


if __name__ == "__main__":
    # Test the configuration
    config = ProvidersConfig()
    
    print("=== Providers Configuration ===\n")
    
    for ptype in ProviderType:
        print(f"\n{ptype.value.upper()} Providers:")
        print("-" * 40)
        
        for provider in config.get_all_providers(ptype):
            status = "✓" if provider.is_available else "○" if provider.enabled else "✗"
            primary = " [PRIMARY]" if provider.primary else ""
            print(f"  {status} {provider.name}{primary}")
        
        primary = config.get_primary_provider(ptype)
        if primary:
            print(f"  → Primary: {primary.name}")
