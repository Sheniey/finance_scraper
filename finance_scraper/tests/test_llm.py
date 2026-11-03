# ================================================== #
# MODULE: test_llm
# ================================================== #


import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

from finance.services.llm import repository as llm_repository
from finance.services.llm.repository import _parse_explanation, chat
from finance.services.llm.strategy import (
    AnthropicStrategy,
    ChatGPTStrategy,
    LLMProviderError,
    LLMService,
    LLMStrategy,
    OllamaStrategy,
    Response,
    create_llm_service_for_account
)
from finance.settings import settings


class _FakeStrategy(LLMStrategy):
    def __init__(
        self,
        provider: str,
        response: Response | None = None,
        error: bool = False,
    ) -> None:
        super().__init__(settings.llm.providers['ollama'])
        self.provider = provider
        self.response = response
        self.error = error
        self.calls = 0

    @property
    def is_available(self) -> bool:
        return True

    async def chat(
        self,
        system_prompt: str,
        user_prompt: str,
        **options: object,
    ) -> Response:
        self.calls += 1
        if self.error:
            raise LLMProviderError(self.provider, 'simulated failure')
        if self.response is None:
            raise LLMProviderError(self.provider, 'missing test response')
        return self.response


class LLMStrategyTests(unittest.IsolatedAsyncioTestCase):
    async def test_account_service_keeps_provider_keys_request_scoped(self) -> None:
        primary = _FakeStrategy(
            'anthropic',
            response=Response(message='account response', provider='anthropic'),
        )
        account_service = LLMService(
            {'anthropic': primary},
            ('anthropic',),
        )

        response = await account_service.chat('system', 'user')

        self.assertEqual(response.message, 'account response')
        self.assertEqual(account_service.last_provider, 'anthropic')
        self.assertEqual(primary.calls, 1)

    async def test_chat_uses_account_service_without_mutating_global_service(
        self,
    ) -> None:
        default_strategy = _FakeStrategy(
            'ollama',
            response=Response(message='global response', provider='ollama'),
        )
        account_strategy = _FakeStrategy(
            'anthropic',
            response=Response(
                message='account response',
                provider='anthropic',
            ),
        )
        default_service = LLMService(
            {'ollama': default_strategy},
            ('ollama',),
        )
        account_service = LLMService(
            {'anthropic': account_strategy},
            ('anthropic',),
        )
        with (
            patch.object(llm_repository, 'llm_service', default_service),
            patch.object(
                llm_repository,
                'client_provider',
                'global-provider',
            ),
        ):
            response = await chat(
                'system',
                'user',
                service_override=account_service,
            )
            self.assertEqual(
                llm_repository.client_provider,
                'global-provider',
            )

        self.assertEqual(response.message, 'account response')
        self.assertEqual(account_strategy.calls, 1)
        self.assertEqual(default_strategy.calls, 0)
        self.assertIsNone(default_service.last_provider)

    def test_account_key_factory_maps_chatgpt_to_openai(self) -> None:
        with patch(
            'finance.services.llm.strategy.create_llm_service',
            return_value=None,
        ) as create_service:
            result = create_llm_service_for_account(
                {'chatgpt': 'account-openai-key'},
            )

        self.assertIsNone(result)
        create_service.assert_called_once_with(
            openai_api_key='account-openai-key',
            deepseek_api_key=None,
            anthropic_api_key=None,
            use_environment_keys=False,
        )

    async def test_service_falls_back_in_configured_order(self) -> None:
        primary = _FakeStrategy('anthropic', error=True)
        fallback = _FakeStrategy(
            'ollama',
            response=Response(message='fallback', provider='ollama'),
        )
        service = LLMService(
            {'anthropic': primary, 'ollama': fallback},
            ('anthropic', 'ollama'),
        )

        response = await service.chat('system', 'user')

        self.assertEqual(response.message, 'fallback')
        self.assertEqual(service.last_provider, 'ollama')
        self.assertEqual(primary.calls, 1)
        self.assertEqual(fallback.calls, 1)

    async def test_chatgpt_strategy_uses_openai_json_options(self) -> None:
        create = AsyncMock(
            return_value=SimpleNamespace(
                choices=[
                    SimpleNamespace(
                        message=SimpleNamespace(content='{"ok": true}')
                    )
                ]
            )
        )
        client = SimpleNamespace(
            chat=SimpleNamespace(
                completions=SimpleNamespace(create=create)
            )
        )
        strategy = ChatGPTStrategy(
            settings.llm.providers['chatgpt'],
            api_key='test-key',
            client=client,
        )

        response = await strategy.chat(
            'system',
            'user',
            max_tokens=12,
            json_mode=True,
        )

        self.assertEqual(response.message, '{"ok": true}')
        request = create.await_args.kwargs
        self.assertEqual(
            request['model'],
            settings.llm.providers['chatgpt'].model,
        )
        self.assertEqual(request['max_tokens'], 12)
        self.assertEqual(request['response_format'], {'type': 'json_object'})

    async def test_ollama_strategy_maps_context_and_json_options(self) -> None:
        chat = AsyncMock(
            return_value=SimpleNamespace(
                message=SimpleNamespace(content='{"ok": true}')
            )
        )
        client = SimpleNamespace(chat=chat)
        strategy = OllamaStrategy(
            settings.llm.providers['ollama'],
            client=client,
        )

        response = await strategy.chat(
            'system',
            'user',
            max_tokens=12,
            json_mode=True,
        )

        self.assertEqual(response.message, '{"ok": true}')
        request = chat.await_args.kwargs
        self.assertEqual(request['model'], 'llama3.1:8b')
        self.assertEqual(request['format'], 'json')
        self.assertEqual(request['options']['num_ctx'], 6144)
        self.assertEqual(request['options']['num_predict'], 12)

    async def test_anthropic_strategy_extracts_text_blocks(self) -> None:
        response = SimpleNamespace(
            raise_for_status=Mock(),
            json=lambda: {
                'content': [
                    {'type': 'text', 'text': 'first'},
                    {'type': 'tool_use', 'id': 'ignored'},
                    {'type': 'text', 'text': 'second'},
                ]
            },
        )
        post = AsyncMock(return_value=response)
        strategy = AnthropicStrategy(
            settings.llm.providers['anthropic'],
            api_key='test-key',
            client=SimpleNamespace(post=post),
        )

        result = await strategy.chat('system', 'user', max_tokens=12)

        self.assertEqual(result.message, 'first\nsecond')
        request = post.await_args
        self.assertEqual(request.args[0], '/v1/messages')
        self.assertEqual(request.kwargs['json']['max_tokens'], 12)
        self.assertEqual(request.kwargs['headers']['x-api-key'], 'test-key')

    def test_settings_define_models_and_ollama_as_last_fallback(self) -> None:
        self.assertEqual(
            settings.llm.provider_priority,
            ('anthropic', 'deepseek', 'chatgpt', 'ollama'),
        )
        self.assertEqual(settings.llm.providers['ollama'].model, 'llama3.1:8b')
        self.assertEqual(settings.llm.providers['deepseek'].model, 'deepseek-chat')

    def test_parse_explanation_accepts_json_code_fences(self) -> None:
        explanation = _parse_explanation(
            '''```json
            {
              "summary": "COMPRA por señales favorables",
              "points": [
                {"reasoning": "positive", "content": "Crecimiento sostenido"},
                {"reasoning": "neutral", "content": "Volatilidad estable"},
                {"reasoning": "negative", "content": "Riesgo de valoración"}
              ]
            }
            ```'''
        )

        self.assertEqual(explanation.summary, 'COMPRA por señales favorables')
        self.assertEqual(len(explanation.points), 3)


if __name__ == '__main__':
    unittest.main()
