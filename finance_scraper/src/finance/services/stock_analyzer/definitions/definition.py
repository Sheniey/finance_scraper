# ================================================== #
# MODULE: definition
# ================================================== #


from pathlib import Path
from enum import Enum
import json

from datatypes import Percentage
from finance.services.stock_analyzer.definitions.models import (
    DefComparison,
    DefArguments,
    DefEntryArguments,
    DefSnapshot,
    Definition, DefinitionEntry, DefinitionMap,
    DefRating,
    ThreadholdsType
)
from finance.services.stock_analyzer.definitions.errors import (
    MnemonicNotFoundError
)
from finance.config import lru_cache


DEFINITION_PATH: Path = Path(__file__).parent / 'definitions.json'
DEFINITIONS: DefinitionMap = {}

@lru_cache()
def rating_def(mnemonic: str) -> DefRating | None:
    if mnemonic not in DEFINITIONS:
        raise MnemonicNotFoundError(mnemonic)
    
    definition: DefinitionEntry = DEFINITIONS[mnemonic]
    return definition.rating.definition

@lru_cache()
def rating_args(mnemonic: str) -> DefArguments | None:
    if mnemonic not in DEFINITIONS:
        raise MnemonicNotFoundError(mnemonic)
    
    definition: DefinitionEntry = DEFINITIONS[mnemonic]
    return definition.rating.arguments

@lru_cache()
def comparison_def(mnemonic: str) -> DefComparison | None:
    if mnemonic not in DEFINITIONS:
        raise MnemonicNotFoundError(mnemonic)
    
    definition: DefinitionEntry = DEFINITIONS[mnemonic]
    return definition.comparison.definition

@lru_cache()
def comparison_args(mnemonic: str) -> DefArguments | None:
    if mnemonic not in DEFINITIONS:
        raise MnemonicNotFoundError(mnemonic)
    
    definition: DefinitionEntry = DEFINITIONS[mnemonic]
    return definition.comparison.arguments

@lru_cache()
def defs(mnemonic: str) -> DefinitionEntry:
    if mnemonic not in DEFINITIONS:
        raise MnemonicNotFoundError(mnemonic)
    
    return DEFINITIONS[mnemonic]

@lru_cache()
def args(mnemonic: str) -> DefEntryArguments:
    if mnemonic not in DEFINITIONS:
        raise MnemonicNotFoundError(mnemonic)
    
    definition: DefinitionEntry = DEFINITIONS[mnemonic]
    return definition.arguments

def _fmt_value(value: float, type: ThreadholdsType) -> float | Percentage | None:
    if value is None:
        return None
    
    match type:
        case 'numeric':
            return float(value)
        case 'percentage':
            return Percentage(value)
        case 'none':
            return None

def load_definitions() -> None:
    global DEFINITIONS
    with open(DEFINITION_PATH, 'r') as f:
        data = json.load(f)

    for key, value in data.items():
        rating_data = value.get("rating") or {}
        comparison_data = value.get("comparison") or {}

        rating = rating_data.get("thresholds", {})
        comparison = comparison_data.get("thresholds", {})

        rating_type = rating_data.get("type", DefArguments().type)
        comparison_type = comparison_data.get("type", DefArguments().type)

        DEFINITIONS[key] = DefinitionEntry(
            rating=DefRating(
                definition=Definition(
                    **{
                        k: _fmt_value(v, rating_type)
                        for k, v
                        in rating.items()
                    }
                ),
                arguments=DefArguments(
                    type=rating_type
                )
            ),
            comparison=DefComparison(
                definition=Definition(
                    **{
                        k: _fmt_value(v, comparison_type)
                        for k, v
                        in comparison.items()
                    }
                ),
                arguments=DefArguments(
                    type=comparison_type
                )
            ),
            arguments=DefEntryArguments(
                excellent_is_lowest=value.get('excellent_is_lowest', DefEntryArguments().excellent_is_lowest)
            ),
            mnemonic=key
        )

    for cached_lookup in (
        rating_def,
        rating_args,
        comparison_def,
        comparison_args,
        defs,
        args,
    ):
        cached_lookup.cache.clear()
