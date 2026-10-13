
# ================================================== #
# BASE EXCEPTIONS                                 #
# ================================================== #

class I18nException(Exception):
    """Global exception for the i18n service."""
    pass



# ================================================== #
# CONCRETE EXCEPTIONS                             #
# ================================================== #

class LanguageNotLoadedError(I18nException):
    """Raised when a language is not loaded."""

    def __init__(self, language: str) -> None:
        self.language: str = language
        super().__init__(f'Language "{language}" not loaded yet.')


class LanguageNotSupportedError(I18nException):
    """Raised when a language is not supported."""

    def __init__(self, language: str) -> None:
        self.language: str = language
        super().__init__(f'Language "{language}" not supported.')


class MnemonicNotFoundError(I18nException):
    """Raised when a mnemonic is not found for a given language."""

    def __init__(self, mnemonic: str, language: str) -> None:
        self.mnemonic: str = mnemonic
        self.language: str = language
        super().__init__(f'Mnemonic "{mnemonic}" not found for language "{language}".')
