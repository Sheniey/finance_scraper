
from typing import Any
from abc import ABC, abstractmethod
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

import httpx
from ollama import (
    AsyncClient as OllamaClient,
    ChatResponse as OllamaResponse,
    RequestError as OllamaRequestError,
    ResponseError as OllamaResponseError,
)
from openai import APIError, AsyncOpenAI

from finance.config import (
    ANTHROPIC_API_KEY,
    DEEPSEEK_API_KEY,
    OPENAI_API_KEY,
    settings as application_settings,
)
from finance.settings import LLMModelSettings, Settings
from finance.services.llm.exceptions import (
    InvalidPromptError,
    InvalidProviderPriorityError,
    LLMInitializationError,
    LLMProviderError,
    LLMUnavailableError,
    OllamaNotInstalledError,
)


@dataclass(frozen=True)
class Response:
    message: str | None = None
    provider: str | None = None


class LLMStrategy(ABC):
    provider: str

    def __init__(self, provider_settings: LLMModelSettings) -> None:
        self.provider_settings: LLMModelSettings = provider_settings

    @property
    @abstractmethod
    def is_available(self) -> bool:
        ...

    @abstractmethod
    async def chat(
        self,
        system_prompt: str,
        user_prompt: str,
        **options: Any,
    ) -> Response:
        ...


def _messages(system_prompt: str, user_prompt: str) -> list[dict[str, str]]:
    return [
        {'role': 'system', 'content': system_prompt},
        {'role': 'user', 'content': user_prompt},
    ]


def _max_tokens(
    options: Mapping[str, Any],
    provider_settings: LLMModelSettings,
) -> int:
    configured_value: Any = options.get('max_tokens', options.get('num_predict'))
    if configured_value is None:
        return provider_settings.max_tokens
    return int(configured_value)


def _extract_openai_content(response: Any, provider: str) -> str:
    choices: Any = getattr(response, 'choices', None)
    if not choices:
        raise LLMProviderError(provider, 'the response did not include any choices')

    message: Any = getattr(choices[0], 'message', None)
    content: Any = getattr(message, 'content', None)
    if not isinstance(content, str) or not content.strip():
        raise LLMProviderError(provider, 'the response did not include text content')
    return content


class _OpenAICompatibleStrategy(LLMStrategy):
    def __init__(
        self,
        provider: str,
        provider_settings: LLMModelSettings,
        api_key: str | None,
        client: Any | None = None,
    ) -> None:
        super().__init__(provider_settings)

        self.provider: str = provider
        self.__api_key: str = (api_key or '').strip()
        self.__client: Any | None = client
        if self.__client is None and self.__api_key:
            self.__client = AsyncOpenAI(
                api_key=self.__api_key,
                base_url=self.provider_settings.base_url,
                timeout=self.provider_settings.timeout_seconds,
            )

    @property
    def is_available(self) -> bool:
        return bool(self.__api_key) or self.__client is not None

    def _request_options(self, options: Mapping[str, Any]) -> dict[str, Any]:
        request_options: dict[str, Any] = {}
        supported_options: tuple[str, ...] = (
            'frequency_penalty',
            'presence_penalty',
            'response_format',
            'seed',
            'stop',
            'temperature',
            'top_p',
        )
        for option_name in supported_options:
            if option_name in options:
                request_options[option_name] = options[option_name]

        if 'max_completion_tokens' in options:
            request_options['max_completion_tokens'] = options['max_completion_tokens']
        else:
            request_options['max_tokens'] = _max_tokens(
                options,
                self.provider_settings,
            )

        if options.get('json_mode') and 'response_format' not in request_options:
            request_options['response_format'] = {'type': 'json_object'}
        return request_options

    async def chat(
        self,
        system_prompt: str,
        user_prompt: str,
        **options: Any,
    ) -> Response:
        if not self.is_available:
            raise LLMProviderError(self.provider, 'API key is not configured')
        if self.__client is None:
            raise LLMProviderError(self.provider, 'client initialization failed')

        try:
            response: Any = await self.__client.chat.completions.create(
                model=self.provider_settings.model,
                messages=_messages(system_prompt, user_prompt),
                **self._request_options(options),
            )
        except APIError as e:
            raise LLMProviderError(self.provider, str(e)) from e
        except (AttributeError, IndexError, TypeError, ValueError) as e:
            raise LLMProviderError(
                self.provider,
                f'invalid provider response: {e}',
            ) from e

        return Response(
            message=_extract_openai_content(response, self.provider),
            provider=self.provider,
        )


class ChatGPTStrategy(_OpenAICompatibleStrategy):
    def __init__(
        self,
        provider_settings: LLMModelSettings,
        api_key: str | None = None,
        client: Any | None = None,
    ) -> None:
        super().__init__('chatgpt', provider_settings, api_key, client)


class DeepSeekStrategy(_OpenAICompatibleStrategy):
    def __init__(
        self,
        provider_settings: LLMModelSettings,
        api_key: str | None = None,
        client: Any | None = None,
    ) -> None:
        super().__init__('deepseek', provider_settings, api_key, client)


class OllamaStrategy(LLMStrategy):
    provider: str = 'ollama'

    def __init__(
        self,
        provider_settings: LLMModelSettings,
        client: OllamaClient | None = None,
    ) -> None:
        super().__init__(provider_settings)
        self.__client: OllamaClient = client or OllamaClient(
            host=self.provider_settings.base_url
        )

    @property
    def is_available(self) -> bool:
        try:
            httpx.get(
                self.provider_settings.base_url + '/api/tags',
                timeout=1
            )
            return True
        except:
            return False

    def _request_options(self, options: Mapping[str, Any]) -> dict[str, Any]:
        configured_options: Any = options.get('options', {})
        if configured_options is None:
            configured_options = {}
        if not isinstance(configured_options, Mapping):
            raise LLMProviderError(
                self.provider,
                'Ollama options must be a mapping',
            )

        request_options: dict[str, Any] = dict(configured_options)
        if 'temperature' in options:
            request_options['temperature'] = options['temperature']
        if 'top_p' in options:
            request_options['top_p'] = options['top_p']
        if 'num_ctx' in options:
            request_options['num_ctx'] = options['num_ctx']
        elif self.provider_settings.context_size is not None:
            request_options['num_ctx'] = self.provider_settings.context_size
        if 'num_predict' in options:
            request_options['num_predict'] = options['num_predict']
        else:
            request_options['num_predict'] = _max_tokens(
                options,
                self.provider_settings,
            )
        return request_options

    async def chat(
        self,
        system_prompt: str,
        user_prompt: str,
        **options: Any,
    ) -> Response:
        request: dict[str, Any] = {
            'model': self.provider_settings.model,
            'messages': _messages(system_prompt, user_prompt),
            'stream': False,
            'options': self._request_options(options),
        }
        if 'format' in options:
            request['format'] = options['format']
        elif options.get('json_mode'):
            request['format'] = 'json'

        try:
            response: OllamaResponse = await self.__client.chat(**request)
        except (OllamaRequestError, OllamaResponseError) as e:
            raise LLMProviderError(self.provider, str(e)) from e
        except (AttributeError, IndexError, TypeError, ValueError) as e:
            raise LLMProviderError(
                self.provider,
                f'invalid provider response: {e}',
            ) from e

        content: Any = getattr(getattr(response, 'message', None), 'content', None)
        if not isinstance(content, str) or not content.strip():
            raise LLMProviderError(self.provider, 'the response did not include text content')
        return Response(message=content, provider=self.provider)


class AnthropicStrategy(LLMStrategy):
    provider: str = 'anthropic'

    def __init__(
        self,
        provider_settings: LLMModelSettings,
        api_key: str | None = None,
        client: Any | None = None,
    ) -> None:
        super().__init__(provider_settings)
        self.__api_key: str = (api_key or '').strip()
        self.__client: Any | None = client

    @property
    def is_available(self) -> bool:
        return bool(self.__api_key) or self.__client is not None

    def _headers(self) -> dict[str, str]:
        return {
            'content-type': 'application/json',
            'anthropic-version': self.provider_settings.api_version or '2023-06-01',
            'x-api-key': self.__api_key,
        }

    def _payload(
        self,
        system_prompt: str,
        user_prompt: str,
        options: Mapping[str, Any],
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            'model': self.provider_settings.model,
            'max_tokens': _max_tokens(options, self.provider_settings),
            'messages': [{'role': 'user', 'content': user_prompt}],
        }
        if system_prompt:
            payload['system'] = system_prompt
        if 'temperature' in options:
            payload['temperature'] = options['temperature']
        if 'top_p' in options:
            payload['top_p'] = options['top_p']
        return payload

    async def _post(self, payload: Mapping[str, Any]) -> Any:
        if self.__client is not None:
            return await self.__client.post(
                '/v1/messages',
                headers=self._headers(),
                json=payload,
            )

        async with httpx.AsyncClient(
            base_url=self.provider_settings.base_url,
            timeout=self.provider_settings.timeout_seconds,
        ) as client:
            return await client.post(
                '/v1/messages',
                headers=self._headers(),
                json=payload,
            )

    async def chat(
        self,
        system_prompt: str,
        user_prompt: str,
        **options: Any,
    ) -> Response:
        if not self.is_available:
            raise LLMProviderError(self.provider, 'API key is not configured')

        try:
            response: Any = await self._post(
                self._payload(system_prompt, user_prompt, options)
            )
            response.raise_for_status()
        except httpx.HTTPError as e:
            raise LLMProviderError(self.provider, str(e)) from e
        except (AttributeError, TypeError, ValueError) as e:
            raise LLMProviderError(
                self.provider,
                f'invalid provider response: {e}',
            ) from e

        try:
            payload: Any = response.json()
        except (TypeError, ValueError) as e:
            raise LLMProviderError(
                self.provider,
                f'invalid JSON response: {e}',
            ) from e

        if not isinstance(payload, Mapping):
            raise LLMProviderError(self.provider, 'the response body is not an object')
        content_blocks: Any = payload.get('content')
        if not isinstance(content_blocks, list):
            raise LLMProviderError(self.provider, 'the response did not include content')

        text_blocks: list[str] = [
            block['text']
            for block in content_blocks
            if isinstance(block, Mapping)
            and block.get('type') == 'text'
            and isinstance(block.get('text'), str)
            and block['text'].strip()
        ]
        if not text_blocks:
            raise LLMProviderError(self.provider, 'the response did not include text content')
        return Response(
            message='\n'.join(text_blocks),
            provider=self.provider,
        )



class LLMService:
    def __init__(
        self,
        strategies: Mapping[str, LLMStrategy],
        provider_priority: Sequence[str],
        default_options: Mapping[str, Any] | None = None,
    ) -> None:
        if not provider_priority:
            raise InvalidProviderPriorityError(provider_priority)
        
        self.last_provider: str | None = None
        self.__provider_priority: tuple[str, ...] = tuple(provider_priority)
        self.__default_options: dict[str, Any] = dict(default_options or {})
        self.__strategies: dict[str, LLMStrategy] = dict(strategies)

    @property
    def preferred_provider(self) -> str | None:
        for provider in self.__provider_priority:
            strategy: LLMStrategy | None = self.__strategies.get(provider)
            if strategy is not None and strategy.is_available:
                return provider
        return None

    @property
    def available_providers(self) -> tuple[str, ...]:
        return tuple(
            provider
            for provider in self.__provider_priority
            if (
                (strategy := self.__strategies.get(provider)) is not None
                and strategy.is_available
            )
        )

    async def chat(
        self,
        system_prompt: str,
        user_prompt: str,
        **options: Any,
    ) -> Response:
        if not isinstance(system_prompt, str) or not system_prompt.strip():
            raise InvalidPromptError('system_prompt')
        if not isinstance(user_prompt, str) or not user_prompt.strip():
            raise InvalidPromptError('user_prompt')

        request_options: dict[str, Any] = {
            **self.__default_options,
            **options,
        }
        errors: list[str] = []
        self.last_provider = None
        is_last_provider_ollama: bool = self.__provider_priority[-1].lower() == 'ollama'
        for provider in self.__provider_priority:
            strategy: LLMStrategy | None = self.__strategies.get(provider)
            is_available: bool = strategy.is_available
            
            # Raise an special error if Ollama is the last provider and is not available
            # This is useful for inform if the user wants to download and install llama.cpp
            if (
                isinstance(strategy, OllamaStrategy)
                and is_last_provider_ollama
                and not is_available
            ):
                raise OllamaNotInstalledError()

            if strategy is None or not is_available:
                continue

            try:
                response: Response = await strategy.chat(
                    system_prompt,
                    user_prompt,
                    **request_options,
                )
            except LLMProviderError as e:
                errors.append(str(e))
                continue

            if response.message is None or not response.message.strip():
                errors.append(
                    f'{provider}: the response did not include text content'
                )
                continue
            self.last_provider = provider
            return response

        if not errors:
            errors.append('no configured provider has usable credentials')
        raise LLMUnavailableError(errors)


def create_llm_service(
    configured_settings: Settings | None = None,
    *,
    openai_api_key: str | None = None,
    deepseek_api_key: str | None = None,
    anthropic_api_key: str | None = None,
    openai__client: Any | None = None,
    deepseek__client: Any | None = None,
    anthropic__client: Any | None = None,
    ollama__client: OllamaClient | None = None,
) -> LLMService:
    current_settings: Settings = (
        configured_settings
        if configured_settings is not None
        else application_settings
    )
    resolved_openai_key: str | None = (
        OPENAI_API_KEY if openai_api_key is None else openai_api_key
    )
    resolved_deepseek_key: str | None = (
        DEEPSEEK_API_KEY if deepseek_api_key is None else deepseek_api_key
    )
    resolved_anthropic_key: str | None = (
        ANTHROPIC_API_KEY if anthropic_api_key is None else anthropic_api_key
    )
    try:
        provider_settings: dict[str, LLMModelSettings] = {
            provider: current_settings.llm.get_provider_model(provider)
            for provider in current_settings.llm.provider_priority
        }
    except (KeyError, ValueError) as e:
        raise LLMInitializationError(
            'Unable to select an LLM model for the configured effort level'
        ) from e

    strategies: dict[str, LLMStrategy] = {
        'ollama': OllamaStrategy(
            provider_settings['ollama'],
            ollama__client,
        ),
    }
    if resolved_anthropic_key or anthropic__client is not None:
        strategies['anthropic'] = AnthropicStrategy(
            provider_settings['anthropic'],
            resolved_anthropic_key,
            anthropic__client,
        )
    if resolved_deepseek_key or deepseek__client is not None:
        strategies['deepseek'] = DeepSeekStrategy(
            provider_settings['deepseek'],
            resolved_deepseek_key,
            deepseek__client,
        )
    if resolved_openai_key or openai__client is not None:
        strategies['chatgpt'] = ChatGPTStrategy(
            provider_settings['chatgpt'],
            resolved_openai_key,
            openai__client,
        )

    return LLMService(
        strategies,
        current_settings.llm.provider_priority,
        default_options={
            'temperature': current_settings.llm.generation.temperature,
            'max_tokens': current_settings.llm.generation.max_tokens,
        },
    )


OllamaLLMStrategy = OllamaStrategy
OpenAIStrategy = ChatGPTStrategy
ChatGPTLLMStrategy = ChatGPTStrategy
DeepSeekLLMStrategy = DeepSeekStrategy
AnthropicLLMStrategy = AnthropicStrategy


__all__: list[str] = [
    'AnthropicLLMStrategy',
    'AnthropicStrategy',
    'ChatGPTLLMStrategy',
    'ChatGPTStrategy',
    'DeepSeekLLMStrategy',
    'DeepSeekStrategy',
    'LLMProviderError',
    'LLMService',
    'LLMStrategy',
    'LLMUnavailableError',
    'OllamaLLMStrategy',
    'OllamaStrategy',
    'OpenAIStrategy',
    'Response',
    'create_llm_service',
]
