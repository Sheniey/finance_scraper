
from decimal import Decimal
from typing import Any
from pydantic import GetCoreSchemaHandler
from pydantic_core import core_schema
from designkit.creational.types import (
    Currencies,
    Money as _Money,
    Currency as _Currency,
)


# ================================================== #
# WRAPPER CLASSES FOR PYDANTIC MODELS                #
# ================================================== #

class MoneyWrapper(_Money):

    @classmethod
    def __get_pydantic_core_schema__(
        cls,
        source_type: Any,
        handler: GetCoreSchemaHandler,
    ) -> core_schema.CoreSchema:

        def validate(value) -> MoneyWrapper:
            match value:
                case cls():
                    return value

                case _Money():
                    return cls(
                        value.money,
                        value.currency,
                        _skip_parser=True,
                    )

                case int() | float() | Decimal():
                    return cls(
                        Decimal(value),
                        Currencies.USD,
                        _skip_parser=True,
                    )

                case str():
                    return cls(_Money.parse(value, value))

                case _:
                    return cls(_Money('this will raise an error'))

        def serialize(value: MoneyWrapper) -> dict[str, str]:
            return {
                'money': str(value.money),
                'currency': str(value.currency.code),
            }

        return core_schema.no_info_plain_validator_function(
            validate,
            serialization=core_schema.plain_serializer_function_ser_schema(
                serialize,
                when_used='json',
            ),
        )

class CurrencyWrapper(_Currency):
    @classmethod
    def __get_pydantic_core_schema__(
        cls,
        source_type: Any,
        handler: GetCoreSchemaHandler
    ) -> core_schema.CoreSchema:
        def validate(value):
            if isinstance(value, cls):
                return value

            if isinstance(value, _Currency):
                return value

            currency = _Currency.get_by_code(str(value).upper())
            if currency is None:
                raise ValueError(f'Unknown currency code: {value!r}')
            return currency

        return core_schema.no_info_plain_validator_function(
            validate,
            serialization=core_schema.plain_serializer_function_ser_schema(
                lambda v: str(v.code)
            ),
        )


# ================================================== #
# MONEY CONVERSION                                   #
# ================================================== #

def to_money(value: str | int | float | Decimal | MoneyWrapper) -> MoneyWrapper | None:
    """Parse a money value into the application's Pydantic wrapper."""

    if isinstance(value, MoneyWrapper):
        return value
    parsed: _Money | None = _Money.parse(value)
    if parsed is None:
        return None
    return MoneyWrapper(
        parsed.money,
        parsed.currency,
        _skip_parser=True,
    )


__all__: list[str] = [
    'CurrencyWrapper',
    'MoneyWrapper',
    'to_money',
]
