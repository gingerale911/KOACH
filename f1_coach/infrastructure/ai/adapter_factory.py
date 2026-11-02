"""AI adapter factory.

Builds the single AIAdapter used by the app (Gemini), using the API key
read from secure storage.
"""

from f1_coach.domain.ports.ai_adapter import AIAdapter
from f1_coach.infrastructure.ai.gemini_adapter import GeminiAdapter


def create_ai_adapter(api_key: str) -> AIAdapter:
    """Instantiate the Gemini AIAdapter.

    Raises:
        ValueError: If api_key is empty.
    """
    if not api_key:
        raise ValueError("No Gemini API key configured.")
    return GeminiAdapter(api_key=api_key)
