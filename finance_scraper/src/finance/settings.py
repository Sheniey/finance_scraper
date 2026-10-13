
import yaml
from collections.abc import Mapping
from typing import Any, Literal
from pathlib import Path
from pydantic import (
    BaseModel, ConfigDict, Field,
    PositiveInt, ValidationError, model_validator
)


# ================================================== #
# CONSTANTS & DEFAULTS                               #
# ================================================== #

SUPPORTED_LLM_PROVIDERS: frozenset[str] = frozenset(
    {'anthropic', 'deepseek', 'chatgpt', 'ollama'}
)
DEFAULT_SETTINGS_PATH: Path = Path(__file__).resolve().with_name('settings.yaml')


# ================================================== #
# TYPE ALIASES                                       #
# ================================================== #

type LanguageStyle = Literal['friendly', 'professional', 'technical']
type LLMProviderName = Literal['anthropic', 'deepseek', 'chatgpt', 'ollama']
type EffortLevel = Literal['low', 'medium', 'high']


# ================================================== #
# SETTING SECTION MODELS                             #
# ================================================== #

class _SettingsModel(BaseModel):
    model_config = ConfigDict(extra='forbid', frozen=True)

class DefaultLanguageSettings(_SettingsModel):
    code: str = Field(default='en', min_length=2)
    name: str = Field(default='English', min_length=1)
    style: LanguageStyle = 'friendly'

class DefaultAccountSettings(_SettingsModel):
    email: str = Field(default='testing@example.com', min_length=1)
    name: str = Field(default='testing', min_length=1)
    password: str = Field(default='an-account-for-testing', min_length=1)

class ApplicationSettings(_SettingsModel):
    default_language: DefaultLanguageSettings = Field(
        default_factory=DefaultLanguageSettings
    )
    default_account: DefaultAccountSettings = Field(
        default_factory=DefaultAccountSettings
    )

class DatabaseSettings(_SettingsModel):
    default_location: str = Field(default='file:src/db/financescraper.sqlite3', min_length=1)
    pool_size: PositiveInt = Field(default=2)
    pool_timeout: float = Field(default=5.0, gt=0)
    profile: bool = Field(default=False)

class SecuritySettings(_SettingsModel):
    jwt_algorithm: str = Field(default='HS256', min_length=1)
    jwt_issuer: str = Field(default='finance_scraper', min_length=1)
    access_token_expire_minutes: PositiveInt = 60

class LLMGenerationSettings(_SettingsModel):
    temperature: float = Field(default=0.2, ge=0, le=2)
    max_tokens: PositiveInt = 364

class LLMModelSettings(_SettingsModel):
    effort: EffortLevel = Field(default='medium')
    model: str = Field(min_length=1)
    base_url: str = Field(min_length=1)
    timeout_seconds: float = Field(default=60, gt=0)
    max_tokens: PositiveInt = 364
    context_size: PositiveInt | None = None
    api_version: str | None = None

class LLMSettings(_SettingsModel):
    provider_priority: tuple[LLMProviderName, ...] = (
        'anthropic',
        'deepseek',
        'chatgpt',
        'ollama',
    )
    generation: LLMGenerationSettings = Field(default_factory=LLMGenerationSettings)
    effort: EffortLevel = Field(default='medium')
    providers: dict[LLMProviderName, LLMModelSettings]

    model_config = ConfigDict(extra='forbid', frozen=False)

    @model_validator(mode='before')
    @classmethod
    def select_provider_effort(cls, value: Any) -> Any:
        if not isinstance(value, Mapping):
            return value

        effort: str = str(value.get('effort', 'medium'))
        raw_providers: Any = value.get('providers')
        if not isinstance(raw_providers, Mapping):
            return value

        providers: dict[str, Any] = {}
        for provider, models in raw_providers.items():
            if isinstance(models, list):
                selected: Any = next(
                    (
                        model
                        for model in models
                        if isinstance(model, Mapping)
                        and model.get('effort') == effort
                    ),
                    None,
                )
                if selected is None:
                    raise ValueError(
                        f'No model configured for provider {provider!r} '
                        f'at effort {effort!r}'
                    )
                providers[str(provider)] = selected
            else:
                providers[str(provider)] = models

        return {**value, 'providers': providers}

    @model_validator(mode='after')
    def validate_provider_hierarchy(self) -> LLMSettings:
        priority = tuple(self.provider_priority)

        if (
            len(priority) != len(SUPPORTED_LLM_PROVIDERS)
            or set(priority) != SUPPORTED_LLM_PROVIDERS
        ):
            raise ValueError(
                'llm.provider_priority must contain anthropic, deepseek, '
                'chatgpt and ollama exactly once'
            )

        if priority[-1] != 'ollama':
            raise ValueError(
                'ollama must be the last LLM provider in the hierarchy'
            )

        configured_providers = set(self.providers)
        if configured_providers != SUPPORTED_LLM_PROVIDERS:
            raise ValueError(
                'llm.providers must configure anthropic, deepseek, '
                'chatgpt and ollama'
            )

        return self

    def get_provider_model(self, provider: LLMProviderName) -> LLMModelSettings:
        return self.providers[provider]


# ================================================== #
# SETTING MODEL                                      #
# ================================================== #

class Settings(_SettingsModel):
    app: ApplicationSettings    = Field(default_factory=ApplicationSettings)
    db: DatabaseSettings        = Field(default_factory=DatabaseSettings)
    security: SecuritySettings  = Field(default_factory=SecuritySettings)
    llm: LLMSettings


# ================================================== #
# EXCEPTIONS                                         #
# ================================================== #

class SettingsError(RuntimeError):
    '''Raised when the application settings file cannot be loaded or validated.'''


# ================================================== #
# FEATURES                                           #
# ================================================== #

def load_settings(path: Path | None = None) -> Settings:
    settings_path: Path = path or DEFAULT_SETTINGS_PATH
    try:
        with settings_path.open(encoding='utf-8') as settings_file:
            raw_settings: object = yaml.safe_load(settings_file)
    except OSError as e:
        raise SettingsError(
            f'Unable to read settings file at {settings_path}'
        ) from e
    except yaml.YAMLError as e:
        raise SettingsError(
            f'Unable to parse YAML settings file at {settings_path}'
        ) from e

    if not isinstance(raw_settings, dict):
        raise SettingsError(
            f'Settings file at {settings_path} must contain a YAML mapping'
        )

    try:
        return Settings.model_validate(raw_settings)
    except ValidationError as e:
        raise SettingsError(
            f'Settings file at {settings_path} does not match the expected schema: {e}'
        ) from e


# ================================================== #
# SETTING LOADED SETTINGS                            #
# ================================================== #

settings: Settings = load_settings()

# ...
__all__: list[str] = [
    'ApplicationSettings',
    'DEFAULT_SETTINGS_PATH',
    'DefaultLanguageSettings',
    'LLMGenerationSettings',
    'LLMProviderName',
    'LLMModelSettings',
    'LLMSettings',
    'SecuritySettings',
    'Settings',
    'SettingsError',
    'load_settings',
    'settings',
]
