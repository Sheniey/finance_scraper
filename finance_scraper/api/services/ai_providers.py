from finance.config import (
    ANTHROPIC_API_KEY,
    DEEPSEEK_API_KEY,
    LOCAL_LLM_SETTINGS,
    OPENAI_API_KEY,
)
from finance.services.llm.strategy import OllamaStrategy


def has_available_ai_provider() -> bool:
    """Return whether a cloud API key or a responding Ollama service exists."""

    if any(
        (
            OPENAI_API_KEY,
            DEEPSEEK_API_KEY,
            ANTHROPIC_API_KEY,
        ),
    ):
        return True
    return OllamaStrategy(LOCAL_LLM_SETTINGS).is_available
