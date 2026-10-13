
import os, yaml
from pathlib import Path
from typing import Final as Const
from designkit.structural.environment import EnvMode, EnvironmentMachine
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    PositiveInt,
    field_validator,
)


# ================================================== #
# CONFIGURATION FILES LOADING                        #
# ================================================== #

__paths__                   = Path(__file__).resolve().parents
PROJECT_ROOT: Const[Path]   = __paths__[2]  # ./
API_ROOT: Const[Path]       = __paths__[1]  # ./api
DESKTOP_LOCAL_ONLY: Const[bool] = (
    os.getenv('FINANCE_DESKTOP_LOCAL_ONLY', '').casefold()
    in {'1', 'true', 'yes', 'on'}
)
if not DESKTOP_LOCAL_ONLY:
    EnvironmentMachine.loadenv(PROJECT_ROOT / '.env')
envm: EnvironmentMachine    = EnvironmentMachine.from_env('APP_ENV')
IS_DEV: Const[bool]         = envm.environment == EnvMode.DEVELOPMENT


# ================================================== #
# APPLICATION DATA                                   #
# ================================================== #

API_TITLE: Const[str]       = 'Finance Scraper - API'
API_NAME: Const[str]        = 'FINANCE SCRAPER - API'
API_NAME_SHORT: Const[str]  = 'FSCRAPER - API'
API_NAME_CODING: Const[str] = 'finance_scraper - API'
API_AUTHOR: Const[str]      = 'Sheñey'
API_VERSION: Const[str]     = '1.0.0'
DESCRIPTION: Const[str]     = 'REST API for the Finance Scraper application.'


# ================================================== #
# SETTINGS MODELS                                    #
# ================================================== #

class _SettingsModel(BaseModel):
    model_config = ConfigDict(extra='forbid', frozen=True)

class APISettings(_SettingsModel):
    report_retention_seconds: PositiveInt = 15 * 24 * 60 * 60
    report_worker_poll_seconds: PositiveInt = 1
    report_worker_max_concurrency: PositiveInt = 4
    database_path: Path = Field(default='data/api.sqlite3')

    @field_validator('report_retention_seconds')
    @classmethod
    def validate_report_retention_seconds(cls, value: int) -> int:
        if not 10 * 60 <= value <= 30 * 24 * 60 * 60:
            raise ValueError(
                'report_retention_seconds must be between 600 and 2592000',
            )
        return value

    @field_validator('report_worker_max_concurrency')
    @classmethod
    def validate_report_worker_max_concurrency(cls, value: int) -> int:
        if value > 16:
            raise ValueError('report_worker_max_concurrency must not exceed 16')
        return value

class RateLimitSettings(_SettingsModel):
    login_per_minute: PositiveInt = 5
    register_per_minute: PositiveInt = 3
    report_generation_per_minute: PositiveInt = 3
    default_per_minute: PositiveInt = 60

class JWTSettings(_SettingsModel):
    algorithm: str = 'HS256'
    issuer: str = 'finance_scraper'

class SecuritySettings(_SettingsModel):
    access_token_expire_minutes: PositiveInt = 15
    refresh_token_expire_days: PositiveInt = 30
    jwt_config: JWTSettings = Field(default_factory=JWTSettings)
    rate_limits: RateLimitSettings = Field(default_factory=RateLimitSettings)

class APIConfig(_SettingsModel):
    api: APISettings = Field(default_factory=APISettings)
    security: SecuritySettings = Field(default_factory=SecuritySettings)


# ================================================== #
# CONFIGURATION & SETTINGS                           #
# ================================================== #

def get_api_settings() -> APIConfig:
    config_path: Path = Path(os.getenv('API_CONFIG_PATH', API_ROOT / 'env.yaml'))
    if not config_path.is_absolute():
        config_path = PROJECT_ROOT / config_path

    with config_path.open('r', encoding='utf-8') as config_file:
        yaml_config: object = yaml.safe_load(config_file)
    if not isinstance(yaml_config, dict):
        raise ValueError(f'API settings file {config_path} must contain a mapping')
    api_settings: APISettings = APISettings(**yaml_config.get('api', {}))
    security_settings: SecuritySettings = SecuritySettings(**yaml_config.get('security', {}))
    database_path: Path = api_settings.database_path
    if not database_path.is_absolute():
        database_path = API_ROOT / database_path
    return APIConfig(
        api=api_settings.model_copy(
            update={
                'database_path': database_path,
            },
        ),
        security=security_settings,
    )


settings: APIConfig = get_api_settings()

JWT_ALGORITHM: Const[str]               = envm.getenv('JWT_ALGORITHM', default='HS256')
DEFAULT_JWT_SECRET_KEY: Const[str]      = 'development-secret-change-this-before-deploying'
JWT_SECRET_KEY: Const[str]              = envm.getenv('JWT_SECRET_KEY', default=DEFAULT_JWT_SECRET_KEY)
JWT_ISSUER: Const[str]                  = settings.security.jwt_config.issuer
