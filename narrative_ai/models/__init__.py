"""
Model Registry Module.

Provides isolated model loading to prevent shared state between
different model instances. This is part of Layer 5 of the security architecture.
"""

from narrative_ai.models.registry import ModelRegistry, ModelNotFoundError

__all__ = ["ModelRegistry", "ModelNotFoundError"]
