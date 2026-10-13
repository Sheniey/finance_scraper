"""Account preference choices exposed by the account service."""


# ================================================== #
# MODULE: preferences
# ================================================== #

from pathlib import Path

from finance.types.language import Language
from finance.types.report_mode import ReportMode


LANGUAGE_NAMES: dict[str, str] = {
    'chilango': 'Chilango',
    'en': 'English',
    'es': 'Español',
    'fr': 'Français',
}
LANGUAGE_STYLES: tuple[str, ...] = (
    'friendly',
    'professional',
    'technical',
)


def get_available_languages() -> list[Language]:
    language_paths: set[Path] = set()
    i18n_root: Path = Path(__file__).resolve().parents[1]
    for path in i18n_root.glob('**/i18n/*.json'):
        language_paths.add(path)

    codes: list[str] = sorted({path.stem for path in language_paths})
    return [
        Language(
            code=code,
            name=LANGUAGE_NAMES.get(code, code),
        )
        for code in codes
    ]


def get_available_language_styles() -> list[str]:
    return list(LANGUAGE_STYLES)


def get_available_report_modes() -> list[ReportMode]:
    return list(ReportMode)


__all__: list[str] = [
    'LANGUAGE_NAMES',
    'LANGUAGE_STYLES',
    'get_available_languages',
    'get_available_language_styles',
    'get_available_report_modes',
]
