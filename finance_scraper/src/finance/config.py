
import logging
import os
import sys
from pathlib import Path
from functools import partial
from typing import Final as Const

from rich.console import Console
from rich.theme import Theme as RichTheme

from designkit.behavioral.cache import cached, LRUCache
from designkit.structural.environment import EnvironmentMachine, EnvMode

from finance.settings import EffortLevel, LLMModelSettings, Settings, load_settings


# ================================================== #
# CONFIGURATION FILES LOADING                        #
# ================================================== #

__paths__                   = Path(__file__).resolve().parents
PROJECT_ROOT: Const[Path]   = __paths__[2] # ./
MODULE_ROOT: Const[Path]    = __paths__[0] # ./src/finance
DESKTOP_LOCAL_ONLY: Const[bool] = (
    os.getenv('FINANCE_DESKTOP_LOCAL_ONLY', '').casefold()
    in {'1', 'true', 'yes', 'on'}
)
ENV_FILE_PATH: Const[Path] = (
    Path(sys.executable).resolve().parent / '.env'
    if getattr(sys, 'frozen', False)
    else PROJECT_ROOT / '.env'
)
if not DESKTOP_LOCAL_ONLY:
    EnvironmentMachine.loadenv(ENV_FILE_PATH)
settings: Const[Settings]   = load_settings()
envm: EnvironmentMachine    = EnvironmentMachine.from_env('APP_ENV')
IS_DEV: Const[bool]         = envm.environment == EnvMode.DEVELOPMENT


# ================================================== #
# APPLICATION DATA                                   #
# ================================================== #

APP_NAME: Const[str]        = 'FINANCE SCRAPER'
APP_NAME_SHORT: Const[str]  = 'FSCRAPER'
APP_NAME_CODING: Const[str] = 'finance_scraper'
APP_AUTHOR: Const[str]      = 'Sheñey'
DESCRIPTION: Const[str]     = 'Financial Research and Analysis Tool.'


# ================================================== #
# ENVIRONMENT VARIABLES & SETTINGS                   #
# ================================================== #

EMAIL_ADDRESS: Const[str | None]    = envm.getenv('EMAIL_ADDRESS')
EMAIL_PASSWORD: Const[str | None]   = envm.getenv('EMAIL_PASSWORD')
EMAIL_HOST: Const[str | None]       = envm.getenv('EMAIL_HOST')
EMAIL_PORT: Const[str]              = envm.getenv('EMAIL_PORT', default='587', validate=lambda v: v.isdigit() and 0 < int(v) < 65536)
EMAIL_TIMEOUT: Const[str]           = envm.getenv('EMAIL_TIMEOUT', default='30')
EMAIL_USE_SSL: Const[str | None]    = envm.getenv('EMAIL_USE_SSL')
EMAIL_USE_TLS: Const[str | None]    = envm.getenv('EMAIL_USE_TLS')

LLM_EFFORT: Const[EffortLevel]              = settings.llm.effort
LLM_EFFORT_LVL: Const[int]                  = { 'low': 0, 'medium': 1, 'high': 2 }.get(LLM_EFFORT, 1)
LOCAL_LLM_SETTINGS: Const[LLMModelSettings] = settings.llm.get_provider_model('ollama')
LOCAL_LLM_CTX_SIZE: Const[int]              = LOCAL_LLM_SETTINGS.context_size or 6144
LOCAL_LLM: Const[str]                       = LOCAL_LLM_SETTINGS.model
LLM_MODEL: Const[str]                       = LOCAL_LLM
OPENAI_API_KEY: Const[str | None]           = envm.getenv('CHATGPT_API_KEY', 'OPENAI_API_KEY')
CHATGPT_API_KEY: Const[str | None]          = OPENAI_API_KEY
DEEPSEEK_API_KEY: Const[str | None]         = envm.getenv('DEEPSEEK_API_KEY')
ANTHROPIC_API_KEY: Const[str | None]        = envm.getenv('ANTHROPIC_API_KEY')
OPENAI_MODEL: Const[str]                    = settings.llm.get_provider_model('chatgpt').model
DEEPSEEK_MODEL: Const[str]                  = settings.llm.get_provider_model('deepseek').model
ANTHROPIC_MODEL: Const[str]                 = settings.llm.get_provider_model('anthropic').model
LLM_PROVIDER_PRIORITY: Const[tuple[str, ...]] = settings.llm.provider_priority
LLM_TEMPERATURE: Const[float]               = settings.llm.generation.temperature
LLM_MAX_TOKENS: Const[int]                  = settings.llm.generation.max_tokens

DEFAULT_LANGUAGE: Const[dict[str, str]] = {
    'code': settings.app.default_language.code,
    'name': settings.app.default_language.name,
    'style': settings.app.default_language.style,
}
DB_LOCATION: Const[str] = (
    ''
    if DESKTOP_LOCAL_ONLY
    else envm.getenv('DB_LOCATION', 'DB_URL', default='')
)
DB_AUTH_TOKEN: Const[str | None] = (
    None
    if DESKTOP_LOCAL_ONLY
    else envm.getenv('DB_AUTH_TOKEN', 'TURSO_AUTH_TOKEN')
)
DB_POOL_SIZE: Const[int]                = settings.db.pool_size
DB_POOL_TIMEOUT: Const[float]           = settings.db.pool_timeout
DB_PROFILE: Const[bool]                 = settings.db.profile
_DB_LOCAL_LOCATION: Path = Path(
    envm.getenv(
        'DB_LOCAL_PATH',
        default=str(MODULE_ROOT / 'db' / 'sync' / 'financescraper.sqlite3'),
    ),
).expanduser()
DB_LOCAL_PATH: Const[Path] = (
    _DB_LOCAL_LOCATION
    if _DB_LOCAL_LOCATION.is_absolute()
    else PROJECT_ROOT / _DB_LOCAL_LOCATION
)
_REPORT_STORE_LOCATION: Path = Path(
    envm.getenv(
        'REPORT_STORE_PATH',
        default=str(MODULE_ROOT / 'db' / 'report_store.sqlite3'),
    ),
).expanduser()
REPORT_STORE_PATH: Const[Path] = (
    _REPORT_STORE_LOCATION
    if _REPORT_STORE_LOCATION.is_absolute()
    else PROJECT_ROOT / _REPORT_STORE_LOCATION
)

LICENSE: Const[str]         = 'MIT LICENSE'
LICENSE_PATH: Const[Path]   = Path(getattr(sys, '_MEIPASS', PROJECT_ROOT)) / 'LICENSE'
LICENSE_TEXT: Const[str]    = ''
with open(LICENSE_PATH, 'r', encoding='utf-8') as f:
    LICENSE_TEXT = f.read()



# ================================================== #
# MAIN COLORS, FONTS & LINKS                         #
# ================================================== #

class Theme:
    # ── Rating ─────────────────────────────────────
    COLOR_EXCELLENT = '#00C853'    # verde brillante
    COLOR_VERY_GOOD = '#64DD17'    # verde lima
    COLOR_GOOD = '#FFD600'         # amarillo intenso
    COLOR_MEH = '#FF9100'          # naranja
    COLOR_BAD = '#FF5252'          # rojo suave
    COLOR_VERY_BAD = "#A42F2F"     # rojo oscuro
    COLOR_AWFUL = "#642985"        # púrpura oscuro

    # ── Financial ──────────────────────────────────
    COLOR_GAIN = '#00E676'         # verde ganancia
    COLOR_NEUTRAL = "#7E868B"      # gris azulado
    COLOR_LOSS = "#E1284D"         # rojo pérdida

    # ── Sentiment ──────────────────────────────────
    COLOR_POSITIVE = '#00C853'     # verde
    COLOR_NEGATIVE = '#FF5252'     # rojo

    # ── UI ─────────────────────────────────────────
    COLOR_NUMBER = '#FF6D00'       # naranja vivo
    COLOR_LINK = '#2994FF'         # azul brillante
    COLOR_DATE = '#00D4BB'         # verde azulado (aqua)
    COLOR_PAGE_BACKGROUND = '#0D1726' # muy negro
    COLOR_SURFACE = '#F4F7FB'      # superficie clara
    COLOR_CARD = '#FFFFFF'         # blanco
    COLOR_INK = '#172033'          # negro
    COLOR_MUTED = '#667085'        # gris apagado
    COLOR_RULE = '#D9E1EC'         # casi blanco
    COLOR_ACCENT = '#FF6D00'       # naranja vivo
    COLOR_WHITE = '#FFFFFF'        # blanco
    COLOR_COVER_MUTED = '#B8C5D8'  # gris para azul claro
    COLOR_COVER_LINE = "#282C32"   # algo negro
    COLOR_CHART_PRIMARY = '#2563EB' # azul ultramar
    COLOR_CHART_SECONDARY = '#14B8A6' # verde chicle
    COLOR_CHART_TERTIARY = '#F97316' # naranja
    COLOR_CHART_QUATERNARY = '#8B5CF6' # púrpura
    COLOR_CHART_GRID = '#E5E7EB'   # gris claro

    # ── LOGGING ──────────────────────────────────────
    COLOR_INFO = "green"            # verde
    COLOR_WARNING = '#FF9800'     # naranja
    COLOR_ERROR = '#F44336'       # rojo
    COLOR_DEBUG = '#2196F3'       # púrpura

    # ── External sources ─────────────────────────────
    GBM_URL             = 'https://www.appgbm.com/market/details/offshore/{symbol}'
    GBM_FAVICON_URL     = 'https://www.appgbm.com/favicon.ico'
    GBM_SYMBOL_LOGO_URL = 'https://cdn.gbm.com/instruments/logo/{symbol}'
    ARQ_URL             = 'https://www.arqfinance.com/es-MX'
    TRADINGVIEW_URL     = 'https://www.tradingview.com/symbols/{symbol}/'
    TRADINGVIEW_FAVICON_URL     = 'https://s3.tradingview.com/favicon.ico'
    TRADINGVIEW_WIDGET_URL      = 'https://s3.tradingview.com/external-embedding/embed-widget-advanced-chart.js'
    TRADINGVIEW_SUPPORT_HOST    = 'https://www.tradingview.com'
    SP500_SYMBOL        = '^GSPC'

    # ── Font ───────────────────────────────────────
    FONT_WEB_STYLESHEET = (
        'https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&'
        'family=Manrope:wght@600;700;800&display=swap'
    )
    FONT_BODY_CSS       = '"DM Sans", "Segoe UI", Arial, sans-serif'
    FONT_DISPLAY_CSS    = '"Manrope", "Segoe UI", Arial, sans-serif'
    FONT_BODY_STACK     = ('DM Sans', 'Segoe UI', 'Arial', 'sans-serif')
    FONT_DISPLAY_STACK  = ('Manrope', 'Segoe UI', 'Arial', 'sans-serif')
    FONT_FAMILY_CSS     = FONT_BODY_CSS
    FONT_TITLE          = 'Helvetica-Bold'
    FONT_TEXT           = 'Helvetica'
    FONT_MONO           = 'Consolas'
    FONT_COVER_TICKER   = FONT_TITLE
    FONT_COVER_COMPANY  = FONT_TEXT
    FONT_COVER_PRICE    = FONT_TITLE
    FONT_COVER_META     = FONT_TEXT
    FONT_HEADER         = FONT_TITLE
    FONT_BODY           = FONT_TEXT
    FONT_FOOTER         = FONT_TEXT


# ================================================== #
# CONSOLE MAIN THEME                                 #
# ================================================== #

colorful: RichTheme = RichTheme({
    'excellent': Theme.COLOR_EXCELLENT,
    'very_good': Theme.COLOR_VERY_GOOD,
    'good': Theme.COLOR_GOOD,
    'meh': Theme.COLOR_MEH,
    'bad': Theme.COLOR_BAD,
    'very_bad': Theme.COLOR_VERY_BAD,
    'awful': Theme.COLOR_AWFUL,

    'gain': Theme.COLOR_GAIN,
    'neutral': Theme.COLOR_NEUTRAL,
    'loss': Theme.COLOR_LOSS,

    'positive': Theme.COLOR_POSITIVE,
    'negative': Theme.COLOR_NEGATIVE,

    'number': Theme.COLOR_NUMBER,
    'link': Theme.COLOR_LINK,
    'date': Theme.COLOR_DATE,

    'log:info': Theme.COLOR_INFO,
    'log:warning': Theme.COLOR_WARNING,
    'log:error': Theme.COLOR_ERROR,
    'log:debug': Theme.COLOR_DEBUG
})


# ================================================== #
# LOGGING & RICH INITIALIZATION                      #
# ================================================== #

logger: logging.Logger = logging.getLogger('finance_scraper')
logger.setLevel(logging.DEBUG)
console: Console = Console(theme=colorful)


lru_cache = partial(cached, cache=LRUCache, capacity=48)
