
from decimal import Decimal
from typing import Any
from pydantic import GetCoreSchemaHandler
from pydantic_core import core_schema
from designkit.creational.types import Percentage


# ================================================== #
# WRAPPER CLASSES FOR PYDANTIC MODELS                #
# ================================================== #

class PercentageWrapper(Percentage):
    @classmethod
    def __get_pydantic_core_schema__(
        cls,
        source_type: Any,
        handler: GetCoreSchemaHandler
    ) -> core_schema.CoreSchema:
        def validate(value):
            if isinstance(value, cls):
                return value

            if isinstance(value, Decimal):
                return cls(value)

            return cls(Decimal(value))

        return core_schema.no_info_plain_validator_function(
            validate,
            serialization=core_schema.plain_serializer_function_ser_schema(
                lambda v: Decimal(v.value)
            ),
        )
