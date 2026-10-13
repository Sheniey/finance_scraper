
from pathlib import Path
from rich.console import Console
from typing import Final as Const
from functools import partial
from designkit.behavioral.cache import cached, LRUCache

from designkit.structural.environment import EnvironmentMachine, EnvMode
from nexis.settings import load_nexis_settings, ModelSettings, ForecastSettings, TrainingMetadata, ModelHyperparameters


# ================================================== #
# CONFIGURATION FILES LOADING                        #
# ================================================== #

__paths__                   = Path(__file__).resolve().parents
PROJECT_ROOT: Const[Path]   = __paths__[2] # ./
MODULE_ROOT: Const[Path]    = __paths__[0] # ./src/nexis
EnvironmentMachine.loadenv(PROJECT_ROOT / '.env')
envm: EnvironmentMachine        = EnvironmentMachine.from_env('APP_ENV')
IS_DEV: Const[bool]             = envm.environment == EnvMode.DEVELOPMENT
console: Console = Console()


# ================================================== #
# ENVIRONMENT VARIABLES & SETTINGS                   #
# ================================================== #

MODEL_SETTINGS_PATH: Const[Path]    = MODULE_ROOT / 'settings.yaml'
MODEL_PATH: Const[Path]             = MODULE_ROOT / 'artifacts' / 'nexis.joblib'

settings: Const[ModelSettings]                  = load_nexis_settings(MODEL_SETTINGS_PATH)
FORECAST_SETTINGS: Const[ForecastSettings]      = settings.forecast
TRAINING_METADATA: Const[TrainingMetadata]      = settings.training
MODEL_HYPERPARAM: Const[ModelHyperparameters]   = settings.hyperparameters


# ================================================== #
# CACHE INITIALIZATION                               #
# ================================================== #

lru_cache = partial(cached, cache=LRUCache, capacity=64)
