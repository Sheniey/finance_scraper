
from enum import Enum
from typing import Callable, TypedDict, Optional
from dataclasses import dataclass, field
from pathlib import Path



# ================================================== #
# TYPE ALIASES                                    #
# ================================================== #

type Mnemonic = str
type TranslationMap = dict[Mnemonic, TranslationEntry]
type I18nSnapshot = Callable[[str], Translation]



# ================================================== #
# MODELS                                          #
# ================================================== #

@dataclass
class TranslationEntry:
    content: Translation
    mnemonic: Mnemonic
    language: str
    i18n_path: Path

class _ThresholdsTranslation(TypedDict):
    excellent: Optional[str]    = None
    very_good: Optional[str]    = None
    good: Optional[str]         = None
    meh: Optional[str]          = None
    bad: Optional[str]          = None
    very_bad: Optional[str]     = None
    awful: Optional[str]        = None

    def __get__(self, key: str | Enum) -> str | None:
        if isinstance(key, Enum):
            key = key.value
        return super().__getitem__(key)
    
    def __set__(self, key: str | Enum, value: str | None) -> None:
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
class Translation:
    text: str | None = field(default=None)
    title: str | None = field(default=None)
    description: str | None = field(default=None)
    rating_thresholds: _ThresholdsTranslation = field(default_factory=_ThresholdsTranslation)
    comparison_thresholds: _ThresholdsTranslation = field(default_factory=_ThresholdsTranslation)
