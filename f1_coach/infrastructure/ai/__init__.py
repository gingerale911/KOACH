"""AI adapter — Gemini, the single model used by the app."""

from f1_coach.infrastructure.ai.adapter_factory import create_ai_adapter
from f1_coach.infrastructure.ai.gemini_adapter import GeminiAdapter

__all__ = ["create_ai_adapter", "GeminiAdapter"]
