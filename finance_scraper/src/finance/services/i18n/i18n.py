
from designkit.behavioral.typing import Assertion

from finance.services.i18n.models import (
    I18nSnapshot,
    Translation, TranslationMap,
)
from finance.types.language import Language
from finance.config import DEFAULT_LANGUAGE
from finance.services.i18n.exceptions import MnemonicNotFoundError
from finance.services.i18n.deep_search import load_translation


# ================================================== #
# IN-MALLOC DATA                                     #
# ================================================== #

TRANSLATIONS: dict[str, TranslationMap] = {}



# ================================================== #
# HELPER I18N FUNCTIONS                              #
# ================================================== #

def _create_snapshot(
    master_mnemonic: str,
    translation_map: TranslationMap,
    lang: str,
    mnemonic: str = '.',
    throw_error: bool = True,
) -> Translation:
    Assertion(master_mnemonic).must_be(str)
    Assertion(translation_map).must_be(dict)
    Assertion(lang).must_be(str)
    Assertion(mnemonic).must_be(str)
    Assertion(throw_error).must_be(bool)
    
    if mnemonic in ('.', '', ' '):
        mnemonic = master_mnemonic

    is_valid_mnemonic: bool = mnemonic in translation_map

    if throw_error and not is_valid_mnemonic:
        raise MnemonicNotFoundError(mnemonic, lang)
    if not is_valid_mnemonic:
        return Translation()

    return translation_map[mnemonic].content



# ================================================== #
# I18N FEATURES                                      #
# ================================================== #

def i18n(mnemonic: str, language: str | Language, *, throw_error: bool = True) -> I18nSnapshot:
    """
    Get a snapshot of the i18n translation for a given mnemonic and language.
    If the mnemonic is not found, it will raise a `MnemonicNotFoundError` if `throw_error` is True, otherwise it will return an empty `Translation`.
    """
    Assertion(mnemonic).must_be(str)
    Assertion(language).must_be(str, Language)

    lang: str = language.code if isinstance(language, Language) else language

    if lang not in TRANSLATIONS:
        load_i18n(language)

    translation_map: TranslationMap = TRANSLATIONS[lang]
    if throw_error and mnemonic not in translation_map:
        raise MnemonicNotFoundError(mnemonic, lang)
    
    return lambda requested_mnemonic='.', throw_error=True: _create_snapshot(
        master_mnemonic=mnemonic,
        translation_map=translation_map,
        lang=lang,
        mnemonic=requested_mnemonic,
        throw_error=throw_error
    )

def get_translation(language: str | Language, mnemonic: str) -> Translation:
    """
    Get a translation entry for a given language and mnemonic.
    If the language is not loaded, it will be loaded by the service.
    If the mnemonic is not found, it will raise a `MnemonicNotFoundError`.
    """
    Assertion(language).must_be(str, Language)
    Assertion(mnemonic).must_be(str)

    lang: str = language.code if isinstance(language, Language) else language

    if lang not in TRANSLATIONS:
        load_i18n(language)
    
    translation_map: TranslationMap = TRANSLATIONS[lang]
    if mnemonic not in translation_map:
        raise MnemonicNotFoundError(mnemonic, lang)
    
    return translation_map[mnemonic].content

def load_i18n(language: str | Language) -> None:
    """
    Load the i18n translations for a given language.
    If the language is already loaded, it will do nothing.
    """
    Assertion(language).must_be(str, Language)
    global TRANSLATIONS

    lang: str = language.code if isinstance(language, Language) else language
    if lang in TRANSLATIONS:
        return
    TRANSLATIONS[lang] = load_translation(language)


def translate(
    language: str | Language,
    mnemonic: str,
    fallback: str | None = None,
    *,
    throw_error: bool = True,
    **values: object,
) -> str:
    """
    Resolve a text translation through the central i18n service.

    Structured analyzer translations remain available through :func:`i18n`;
    scalar catalog entries are exposed as text here. Missing entries use the
    default language before applying the supplied fallback.
    """
    if not isinstance(mnemonic, str):
        raise TypeError('The i18n mnemonic must be a string.')
    if not isinstance(fallback, str) and fallback is not None:
        raise TypeError('The i18n fallback must be a string or None.')
    if not isinstance(throw_error, bool):
        raise TypeError('The i18n throw_error flag must be a boolean.')

    lang: str = language.code if isinstance(language, Language) else language
    if not isinstance(lang, str):
        raise TypeError('The i18n language must be a string or Language.')

    load_i18n(lang)
    entry: Translation | None = (
        TRANSLATIONS[lang][mnemonic].content
        if mnemonic in TRANSLATIONS[lang]
        else None
    )

    if entry is None and lang != DEFAULT_LANGUAGE['code']:
        default_language: str = DEFAULT_LANGUAGE['code']
        load_i18n(default_language)
        entry = (
            TRANSLATIONS[default_language][mnemonic].content
            if mnemonic in TRANSLATIONS[default_language]
            else None
        )

    template: str | None = (
        entry.text
        if entry is not None and entry.text is not None
        else fallback
    )
    if template is None:
        if throw_error:
            raise MnemonicNotFoundError(mnemonic, lang)
        return mnemonic

    return template.format(**values) if values else template
