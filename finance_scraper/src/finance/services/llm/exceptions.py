# ================================================== #
# MODULE: exceptions
# ================================================== #

from collections.abc import Sequence


class LLMException(Exception):
    """Global exception for the LLM service."""
    pass


class LLMProviderError(LLMException, RuntimeError):
    """Raised when a provider cannot complete an LLM request."""

    def __init__(self, provider: str, message: str) -> None:
        self.provider: str = provider
        self.message: str = message
        super().__init__(f'{provider}: {message}')


class LLMUnavailableError(LLMException, RuntimeError):
    """Raised when every configured provider fails."""

    def __init__(self, errors: Sequence[str]) -> None:
        self.errors: tuple[str, ...] = tuple(errors)
        details: str = '; '.join(self.errors) or 'no provider is configured'
        super().__init__(f'No LLM provider could generate a response: {details}')


class InvalidProviderPriorityError(LLMException, ValueError):
    """Raised when no LLM provider priority is configured."""

    def __init__(self, providers: Sequence[str] = ()) -> None:
        self.providers: tuple[str, ...] = tuple(providers)
        super().__init__('provider_priority must contain at least one provider')


class InvalidPromptError(LLMException, ValueError):
    """Raised when an LLM prompt is empty or invalid."""

    def __init__(self, prompt_name: str) -> None:
        self.prompt_name: str = prompt_name
        super().__init__(f'{prompt_name} must be a non-empty string')


class LLMInitializationError(LLMException, RuntimeError):
    """Raised when the LLM service cannot be initialized."""

    def __init__(
        self,
        message: str = 'LLM service could not be initialized',
    ) -> None:
        self.message: str = message
        super().__init__(message)


class InvalidExplanationError(LLMException, ValueError):
    """Raised when an LLM explanation has an invalid structure."""

    def __init__(self, message: str) -> None:
        self.message: str = message
        super().__init__(message)


class EmptyExplanationError(LLMException, RuntimeError):
    """Raised when an LLM returns no explanation."""

    def __init__(self) -> None:
        super().__init__('LLM returned an empty explanation')

class OllamaNotInstalledError(LLMException, RuntimeError):
    """Raised when the Ollama provider is the only remaining provider and is not installed."""

    def __init__(self) -> None:
        super().__init__('Ollama provider is not installed or was not found on the system')
