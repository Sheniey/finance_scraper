# ================================================== #
# MODULE: testing
# ================================================== #


from typing import Literal
from asyncio import run

from finance.services.llm.config import ROLE_TEMPLATE, STYLE_TEMPLATES
from finance.services.llm.exceptions import EmptyExplanationError
from finance.services.ml.models import Actions
from finance.services.llm.strategy import LLMService, create_llm_service

client: LLMService = create_llm_service()


def build_system(
        possible_actions: tuple[Actions, ...],
        style: Literal['friendly', 'professional', 'technical'],
        language: str
    ) -> str:

    BASE_ROLE: str = ROLE_TEMPLATE.format(
        actions=', '.join(action.name for action in possible_actions),
        language=language
    )
    STYLE: str = STYLE_TEMPLATES[style]

    return f'{BASE_ROLE}\n\n{STYLE}'

def build_user(ticker: str, data: dict[str, object]) -> str:
    return f"""
Los datos de entrada para el ticker {ticker} son:
{data}
""".strip()

async def explain_ticker() -> str:
    response = await client.chat(
        system_prompt=build_system(
            possible_actions=tuple(Actions),
            style='friendly',
            language='Spanish',
        ),
        user_prompt=build_user(
            ticker='AAPL',
            data={
                'price': 150,
                'volume': 1000,
                'news': 'Apple lanza nuevo iPhone 16 dentro de 3 meses',
                'earnings': 'Apple reporta ingresos de $100B en el último trimestre',
            },
        ),
        json_mode=True,
    )
    if response.message is None:
        raise EmptyExplanationError()
    return response.message

if __name__ == '__main__':
    answer: str = run(explain_ticker())
    print(answer)
