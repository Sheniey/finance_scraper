
import json
from pathlib import Path
from collections.abc import Mapping

from finance.config import DEFAULT_LANGUAGE
from finance.types.language import Language
from finance.services.i18n.models import (
    Translation, TranslationEntry, TranslationMap
)



# ================================================== #
# CONSTANTS                                       #
# ================================================== #

SRC_DIR: Path = Path(__file__).resolve().parents[2]



# ================================================== #
# /I18N/*.JSON DEEP SEARCHER                      #
# ================================================== #

def load_translation(language: str | Language = Language(**DEFAULT_LANGUAGE)) -> TranslationMap:
    translations: TranslationMap = {}
    lang: str = language.code if isinstance(language, Language) else language
    i18n_files: list[Path] = sorted(SRC_DIR.glob(f'**/i18n/{lang}.json'))

    for file in i18n_files:
        with open(file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        if not isinstance(data, Mapping):
            raise ValueError(f'Invalid i18n catalog: {file}')

        for mnemonic, content in data.items():
            if not isinstance(mnemonic, str):
                raise ValueError(f'Invalid i18n mnemonic in catalog: {file}')
            if mnemonic in translations:
                previous_path: Path = translations[mnemonic].i18n_path
                raise ValueError(
                    f'Duplicate i18n mnemonic "{mnemonic}" in '
                    f'{previous_path} and {file}.'
                )

            if isinstance(content, str):
                translation = Translation(text=content)
            elif isinstance(content, Mapping):
                translation = Translation(
                    title=content.get("title"),
                    description=content.get("description"),
                    rating_thresholds=content.get("rating_thresholds", {}),
                    comparison_thresholds=content.get("comparison_thresholds", {}),
                )
            else:
                raise ValueError(
                    f'Invalid translation for mnemonic "{mnemonic}" in {file}.'
                )

            translations[mnemonic] = TranslationEntry(
                content=translation,
                mnemonic=mnemonic,
                language=lang,
                i18n_path=file,
            )
    
    return translations
