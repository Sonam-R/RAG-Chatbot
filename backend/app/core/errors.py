"""Shared error types and client-safe messages."""

from openai import APIConnectionError, APITimeoutError

MODEL_UNAVAILABLE_MESSAGE = (
    "The model is unavailable right now. Please try again in a moment."
)


class ModelUnavailableError(Exception):
    """Raised when Ollama / the LLM endpoint cannot be reached or times out."""

    def __init__(self, message: str = MODEL_UNAVAILABLE_MESSAGE) -> None:
        super().__init__(message)
        self.message = message


def map_openai_error(exc: BaseException) -> None:
    """Re-raise model transport failures as ModelUnavailableError."""
    if isinstance(exc, (APIConnectionError, APITimeoutError)):
        raise ModelUnavailableError() from exc
    if isinstance(exc, TimeoutError):
        raise ModelUnavailableError() from exc
    if isinstance(exc, ModelUnavailableError):
        raise exc
    name = type(exc).__name__.lower()
    if "connection" in name or "timeout" in name:
        raise ModelUnavailableError() from exc