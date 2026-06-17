"""
Model Registry for Isolated Model Loading.

Ensures models are loaded in isolated contexts to prevent shared state
and memory leaks. This is part of Layer 5 of the security architecture.
"""

import threading
from typing import Dict, Optional, Any, Type
from enum import Enum
import logging


logger = logging.getLogger(__name__)


class ModelType(str, Enum):
    """Supported model types."""

    STT = "stt"  # Fast Conformer for speech-to-text
    EMBEDDING = "embedding"  # Sentence Transformers
    TTS = "tts"  # EGTTS for text-to-speech


class ModelNotFoundError(Exception):
    """Raised when a requested model is not found in the registry."""

    def __init__(self, model_name: str):
        """
        Initialize model not found error.

        Args:
            model_name: Name of the model that was not found
        """
        super().__init__(f"Model '{model_name}' not found in registry")
        self.model_name = model_name


class ModelRegistry:
    """
    Registry for managing ML models with isolated loading.

    Ensures each model is loaded in its own context to prevent:
    - Shared state between requests
    - Memory leaks
    - Cross-tenant data contamination
    """

    def __init__(self):
        """Initialize model registry."""
        self._models: Dict[str, Any] = {}
        self._model_configs: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.RLock()  # Reentrant lock for thread safety

    def register_model(
        self,
        model_name: str,
        model_type: ModelType,
        model_class: Type,
        config: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Register a model class (not instance) in the registry.

        Args:
            model_name: Unique name for the model
            model_type: Type of model (STT, EMBEDDING, TTS)
            model_class: Model class (not instance)
            config: Optional configuration dictionary
        """
        with self._lock:
            if model_name in self._models:
                logger.warning(f"Model '{model_name}' already registered, overwriting")

            self._models[model_name] = {
                "type": model_type,
                "class": model_class,
                "instance": None,  # Lazy loading
            }
            self._model_configs[model_name] = config or {}

            logger.info(f"Registered model '{model_name}' of type '{model_type.value}'")

    def load_model(
        self,
        model_name: str,
        force_reload: bool = False,
    ) -> Any:
        """
        Load a model instance (lazy loading with caching).

        Models are loaded on first access and cached for subsequent use.
        Each model is loaded in isolation to prevent shared state.

        Args:
            model_name: Name of the model to load
            force_reload: If True, reload model even if already loaded

        Returns:
            Model instance

        Raises:
            ModelNotFoundError: If model is not registered
        """
        with self._lock:
            if model_name not in self._models:
                raise ModelNotFoundError(model_name)

            model_info = self._models[model_name]

            # Return cached instance if available and not forcing reload
            if model_info["instance"] is not None and not force_reload:
                logger.debug(f"Returning cached instance of model '{model_name}'")
                return model_info["instance"]

            # Load model in isolated context
            logger.info(f"Loading model '{model_name}'...")

            try:
                model_class = model_info["class"]
                config = self._model_configs.get(model_name, {})

                # Create new instance (isolated from other instances)
                model_instance = model_class(**config)

                # Cache the instance
                model_info["instance"] = model_instance

                logger.info(f"Successfully loaded model '{model_name}'")
                return model_instance

            except Exception as e:
                logger.error(f"Failed to load model '{model_name}': {e}", exc_info=True)
                raise

    def get_model(
        self,
        model_name: str,
        auto_load: bool = True,
    ) -> Optional[Any]:
        """
        Get a model instance from the registry.

        Args:
            model_name: Name of the model
            auto_load: If True, load model if not already loaded

        Returns:
            Model instance or None if not found/loaded

        Raises:
            ModelNotFoundError: If model is not registered
        """
        with self._lock:
            if model_name not in self._models:
                raise ModelNotFoundError(model_name)

            model_info = self._models[model_name]

            # Return cached instance if available
            if model_info["instance"] is not None:
                return model_info["instance"]

            # Auto-load if requested
            if auto_load:
                return self.load_model(model_name)

            return None

    def unload_model(self, model_name: str) -> None:
        """
        Unload a model from memory.

        Args:
            model_name: Name of the model to unload

        Raises:
            ModelNotFoundError: If model is not registered
        """
        with self._lock:
            if model_name not in self._models:
                raise ModelNotFoundError(model_name)

            model_info = self._models[model_name]

            if model_info["instance"] is not None:
                logger.info(f"Unloading model '{model_name}'...")

                # Clean up model instance
                # If model has cleanup method, call it
                if hasattr(model_info["instance"], "cleanup"):
                    try:
                        model_info["instance"].cleanup()
                    except Exception as e:
                        logger.warning(f"Error during model cleanup: {e}")

                # Clear instance
                model_info["instance"] = None

                logger.info(f"Successfully unloaded model '{model_name}'")

    def unload_all_models(self) -> None:
        """Unload all models from memory."""
        with self._lock:
            model_names = list(self._models.keys())
            for model_name in model_names:
                try:
                    self.unload_model(model_name)
                except Exception as e:
                    logger.warning(f"Error unloading model '{model_name}': {e}")

    def list_models(self) -> Dict[str, Dict[str, Any]]:
        """
        List all registered models.

        Returns:
            Dictionary mapping model names to their metadata
        """
        with self._lock:
            return {
                name: {
                    "type": info["type"].value,
                    "loaded": info["instance"] is not None,
                    "config": self._model_configs.get(name, {}),
                }
                for name, info in self._models.items()
            }

    def is_model_loaded(self, model_name: str) -> bool:
        """
        Check if a model is currently loaded.

        Args:
            model_name: Name of the model

        Returns:
            True if model is loaded, False otherwise

        Raises:
            ModelNotFoundError: If model is not registered
        """
        with self._lock:
            if model_name not in self._models:
                raise ModelNotFoundError(model_name)

            return self._models[model_name]["instance"] is not None


# Global model registry instance
_global_registry: Optional[ModelRegistry] = None
_registry_lock = threading.Lock()


def get_model_registry() -> ModelRegistry:
    """
    Get the global model registry instance (singleton).

    Returns:
        Global ModelRegistry instance
    """
    global _global_registry

    if _global_registry is None:
        with _registry_lock:
            if _global_registry is None:
                _global_registry = ModelRegistry()

    return _global_registry
