"""Gemini AI adapter.

Satisfies the AIAdapter Protocol structurally — no inheritance required.
"""

import google.generativeai as genai

from f1_coach.infrastructure.logging.logger import get_logger

logger = get_logger(__name__)

_DEFAULT_MODEL = "gemini-3.8-flash"
_FALLBACK_MODELS = ("gemini-3.8-flash", "gemini-2.5-flash")


class GeminiAdapter:
    """AIAdapter implementation backed by the Google Gemini API."""

    def __init__(self, api_key: str, model: str = _DEFAULT_MODEL) -> None:
        genai.configure(api_key=api_key)
        self._model_name = model
        self._model = genai.GenerativeModel(model)

    def generate_feedback(self, prompt: str) -> str:
        """Send the prompt to Gemini and return the generated feedback text.

        Raises:
            RuntimeError: If the Gemini API call fails.
        """
        last_error: Exception | None = None

        for model_name in (self._model_name, *[m for m in _FALLBACK_MODELS if m != self._model_name]):
            try:
                model = genai.GenerativeModel(model_name)
                response = model.generate_content(prompt)
                text = getattr(response, "text", None)
                if not text:
                    raise RuntimeError("Gemini returned an empty response.")
                return text.strip()
            except Exception as exc:  # pragma: no cover - network-dependent branch
                last_error = exc
                if "404" not in str(exc).lower() and "not available" not in str(exc).lower():
                    logger.error("Gemini API call failed: %s", exc)
                    raise RuntimeError(f"Gemini feedback generation failed: {exc}") from exc
                logger.warning("Gemini model %s unavailable, retrying with fallback model.", model_name)

        if last_error is not None:
            logger.error("Gemini API call failed for all configured model names: %s", last_error)
            raise RuntimeError(f"Gemini feedback generation failed: {last_error}") from last_error

        raise RuntimeError("Gemini feedback generation failed: no response returned.")
