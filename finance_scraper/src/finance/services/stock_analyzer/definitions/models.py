# ================================================== #
# MODULE: models
# ================================================== #


from enum import Enum
from typing import Literal, Callable, TypedDict
from dataclasses import dataclass, field

from datatypes import Percentage


type DefinitionMap = dict[str, DefinitionEntry]
type DefSnapshot = Callable[[str], Definition]

type ThreadholdsType = Literal['numeric', 'percentage', 'none']

@dataclass
class DefArguments:
    type: ThreadholdsType = 'numeric'

@dataclass
class DefEntryArguments:
    excellent_is_lowest: bool = False

class Definition(TypedDict):
    excellent: float | Percentage
    very_good: float | Percentage
    good: float | Percentage
    meh: float | Percentage
    bad: float | Percentage
    very_bad: float | Percentage
    awful: float | Percentage

    def __get__(self, key: str | Enum) -> float | None:
        if isinstance(key, Enum):
            key = key.value
        return super().__getitem__(key)
    
    def __set__(self, key: str | Enum, value: float | None) -> None:
        if isinstance(key, Enum):
            key = key.value
        super().__setitem__(key, value)

    def __del__(self, key: str | Enum) -> None:
        if isinstance(key, Enum):
            key = key.value
        super().__delitem__(key)

    def __contains__(self, key: str | Enum) -> bool:
        if isinstance(key, Enum):
            key = key.value
        return super().__contains__(key)

@dataclass
class _SpecDefinition:
    definition: Definition
    arguments: DefArguments

@dataclass
class DefRating(_SpecDefinition):
    definition: Definition
    arguments: DefArguments

@dataclass
class DefComparison(_SpecDefinition):
    definition: Definition
    arguments: DefArguments 

@dataclass
class DefinitionEntry:
    rating: DefRating
    comparison: DefComparison
    arguments: DefEntryArguments
    mnemonic: str
