"""
Questionary forms used by the finance CLI.
"""

import questionary as quest
from dataclasses import dataclass
from designkit.creational.types import Email

from finance.services.account import get_available_languages, get_available_language_styles
from finance.types.language import Language
from finance.services.i18n import translate


# ================================================== #
# FORM MODELS                                        #
# ================================================== #

@dataclass(frozen=True, slots=True)
class SignupForm:
    """Validated values collected by the account signup form."""

    name: str
    email: str
    password: str
    language: Language
    style: str
    watchlist_symbols: tuple[str, ...]


# ================================================== #
# SIGNUP FORM                                        #
# ================================================== #

def prompt_signup() -> SignupForm | None:
    """Collect signup values interactively, returning None on cancellation."""

    languages: list[Language] = get_available_languages()
    language_choice: str | None = quest.select(
        translate('en', 'signup.language', throw_error=True),
        choices=[
            f'{language.code} - {language.name}'
            for language in languages
        ],
    ).ask()
    if language_choice is None:
        return None

    language_code: str = language_choice.split(' - ', 1)[0]
    selected_language: Language = next(
        language
        for language in languages
        if language.code == language_code
    )
    language_text = lambda key: translate(language_code, key, throw_error=True)

    name: str | None = quest.text(
        language_text('signup.name'),
        validate=lambda value: bool(value.strip()),
    ).ask()
    email: str | None = quest.text(
        language_text('signup.email'),
        validate=Email.validate,
    ).ask()
    password: str | None = quest.password(
        language_text('signup.password'),
        validate=lambda value: len(value) >= 8,
    ).ask()
    confirm_password: str | None = quest.password(
        language_text('signup.confirm_password'),
    ).ask()
    if not name or not email or not password or not confirm_password:
        return None
    if password != confirm_password:
        raise ValueError(language_text('signup.password_mismatch'))

    style: str | None = quest.select(
        language_text('signup.style'),
        choices=get_available_language_styles(),
    ).ask()
    if style is None:
        return None

    watchlist_symbols: list[str] = quest.checkbox(
        language_text('signup.watchlist'),
        choices=['AAPL', 'GOOGL', 'MSFT', 'AMZN', 'TSLA'],
    ).ask() or []
    return SignupForm(
        name=name,
        email=email,
        password=password,
        language=selected_language,
        style=style,
        watchlist_symbols=tuple(watchlist_symbols),
    )


__all__: list[str] = ['SignupForm', 'prompt_signup']
