
import yaml, os
from datetime import datetime
from pathlib import Path
from typing import Any

from datatypes import Percentage
from pydantic import BaseModel, ConfigDict, Field, PositiveFloat, PositiveInt


# ================================================== #
# HYPERPARAMETER MODELS                              #
# ================================================== #

class _SettingSection(BaseModel):
    model_config: ConfigDict = ConfigDict(extra='forbid', frozen=True)

class ForecastSettings(_SettingSection):
    default_checkpoint: str = 'google/timesfm-3.0-pytorch'
    default_move_threshold: float = 0.02
    min_context: int = 64
    return_checkpoints_days: tuple[int, ...] = (1, 5, 10, 20, 30)
    quantile_levels: tuple[float, ...] = (0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9)
    median_quantile_index: int = 4


class TrainingMetadata(_SettingSection):
    asset_lookback_days: PositiveInt = 2520 # over 10 years of trading days
    mae: Percentage | None = None
    rmse: Percentage | None = None
    horizon_days: PositiveInt = 5
    trained_at: str | None = None
    trained_tickers: tuple[str, ...] = Field(default_factory=tuple)


class RandomForestHyperparameters(_SettingSection):
    n_estimators: PositiveInt = 575
    max_depth: PositiveInt = 12
    min_samples_leaf: PositiveInt = 1

class LightGBMHyperparameters(_SettingSection):
    n_estimators: PositiveInt = 425
    learning_rate: PositiveFloat = 0.04
    num_leaves: PositiveInt = 33
    max_depth: PositiveInt = 10
    subsample: PositiveFloat = 0.8
    colsample_bytree: PositiveFloat = 0.8

class CatBoostHyperparameters(_SettingSection):
    iterations: PositiveInt = 320
    learning_rate: PositiveFloat = 0.05
    depth: PositiveInt = 6
    min_data_in_leaf: PositiveInt = 1

class ModelHyperparameters(_SettingSection):
    rf: RandomForestHyperparameters = Field(default_factory=RandomForestHyperparameters)
    lgbm: LightGBMHyperparameters = Field(default_factory=LightGBMHyperparameters)
    catboost: CatBoostHyperparameters = Field(default_factory=CatBoostHyperparameters)



class ModelSettings(_SettingSection):
    hyperparameters: ModelHyperparameters = Field(default_factory=ModelHyperparameters)
    forecast: ForecastSettings = Field(default_factory=ForecastSettings)
    training: TrainingMetadata = Field(default_factory=TrainingMetadata)

    def with_updates(
        self,
        *,
        hyperparameters: ModelHyperparameters | None = None,
        forecast: ForecastSettings | None = None,
        training: TrainingMetadata | None = None,
    ) -> ModelSettings:
        return ModelSettings(
            hyperparameters=hyperparameters or self.hyperparameters,
            forecast=forecast or self.forecast,
            training=training or self.training,
        )



# ================================================== #
# FEATURES                                           #
# ================================================== #

def load_nexis_settings(path: str | os.PathLike[str]) -> ModelSettings:
    """Loads `ModelSettings` from `path`, falling back to defaults when the
    file is missing, empty, or does not match the expected schema."""
    resolved_path: Path = Path(path)
    if not resolved_path.exists():
        return ModelSettings()

    try:
        raw_settings: Any = yaml.safe_load(resolved_path.read_text(encoding='utf-8') or '{}')
    except yaml.YAMLError:
        return ModelSettings()

    if not isinstance(raw_settings, dict) or not raw_settings:
        return ModelSettings()

    try:
        return ModelSettings.model_validate(raw_settings)
    except Exception:
        print(f'Failed to validate model settings at: {resolved_path}, using defaults.')
        return ModelSettings()


def save_nexis_settings(settings: ModelSettings, path: str | os.PathLike[str]) -> None:
    """Atomically persists `settings` as YAML to `path`."""

    resolved_path: Path = Path(path)
    resolved_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: Path = resolved_path.with_suffix(f'{resolved_path.suffix}.tmp')
    temporary_path.write_text(
        yaml.safe_dump(settings.model_dump(mode='python'), indent=4),
        encoding='utf-8',
    )
    os.replace(temporary_path, resolved_path)


def stamp_training_metadata(
    settings: ModelSettings,
    *,
    mae: Percentage,
    rmse: Percentage,
    horizon_days: int,
    trained_tickers: list[str],
) -> ModelSettings:
    return settings.with_updates(
        training=TrainingMetadata(
            mae=mae,
            rmse=rmse,
            horizon_days=horizon_days,
            trained_at=datetime.now().astimezone().isoformat(),
            trained_tickers=tuple(trained_tickers),
        )
    )
