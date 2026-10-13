from types import SimpleNamespace
from unittest.mock import patch

from finance.cli.forms import prompt_signup
from finance.cli.i18n import translate


# ================================================== #
# CLI TRANSLATIONS                                   #
# ================================================== #

def test_cli_translation_loads_selected_language() -> None:
    assert translate('es', 'signup.name') == 'Escribe tu nombre: '


def test_cli_translation_falls_back_to_english() -> None:
    assert translate('missing', 'signup.email') == 'Enter your email: '


# ================================================== #
# CLI FORMS                                          #
# ================================================== #

def test_signup_form_returns_localized_values() -> None:
    def answer(value):
        return SimpleNamespace(ask=lambda: value)

    with (
        patch(
            'finance.cli.forms.quest.select',
            side_effect=[
                answer('es - Español'),
                answer('professional'),
            ],
        ),
        patch(
            'finance.cli.forms.quest.text',
            side_effect=[
                answer('Ana'),
                answer('ana@example.com'),
            ],
        ),
        patch(
            'finance.cli.forms.quest.password',
            side_effect=[
                answer('secure-password'),
                answer('secure-password'),
            ],
        ),
        patch(
            'finance.cli.forms.quest.checkbox',
            return_value=answer(['AAPL', 'MSFT']),
        ),
    ):
        form = prompt_signup()

    assert form is not None
    assert form.name == 'Ana'
    assert form.language.code == 'es'
    assert form.style == 'professional'
    assert form.watchlist_symbols == ('AAPL', 'MSFT')
