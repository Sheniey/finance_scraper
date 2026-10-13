
import os, sys
from datetime import UTC, datetime
from typing import Literal

import joblib, numpy as np, pandas as pd
from pydantic import BaseModel
from joblib import Parallel, delayed
from sklearn.metrics import classification_report, mean_absolute_error, mean_squared_error
from sklearn.impute import SimpleImputer
from sklearn.model_selection import TimeSeriesSplit
from designkit.behavioral.verboser import VerboseSystem

from datatypes import Ticker, Percentage
from nexis.models.classifier import TradingAction
from nexis.config import (
    console,
    MODEL_PATH,
    MODEL_SETTINGS_PATH,
    IS_DEV,
    settings
)
from nexis.classifier import ACTION_ORDINAL, ActionClassifier, ESTIMATOR_NAMES, build_estimator
from nexis.dataset import DatasetConfig, build_training_dataset
from nexis.errors import ModelException
from nexis.settings import (
    CatBoostHyperparameters,
    LightGBMHyperparameters,
    RandomForestHyperparameters,
    ModelSettings, ModelHyperparameters,
    save_nexis_settings,
    stamp_training_metadata,
)


# Ordinal encoding used to score the classifier as if it were a regressor
# (BUY is "more bullish" than HOLD, which is "more bullish" than SELL). This
# lets `trainer.py` compute MAE/RMSE for an otherwise categorical model.
ACTION_ORDINAL: dict[str, int] = {
    TradingAction.SELL.value: -1,
    TradingAction.HOLD.value: 0,
    TradingAction.BUY.value: 1,
}

# ================================================== #
# TRAINING METRICS MODEL                             #
# ================================================== #

class TrainMetrics(BaseModel):
    classification_report: str
    action_distribution: dict[str, float]
    samples: int
    model_path: str
    trained_tickers: list[str]
    mae: float
    rmse: float



# ================================================== #
# DEEP TRAIN TUNING CONSTANTS                        #
# ================================================== #

# Bounds are intentionally generous but finite, so `deep_train` can never
# runaway into absurdly expensive models.
LEAF_PARAM_BOUNDS: tuple[int, int] = (1, 50)
ESTIMATORS_PARAM_BOUNDS: tuple[int, int] = (100, 1000)
DEPTH_PARAM_BOUNDS: tuple[int, int] = (2, 12)

# Name of the "leaf", "estimators" and "depth" hyperparameter for each
# classifier, since sklearn/LightGBM/CatBoost don't share a common name.
LEAF_PARAM_NAME: dict[str, str]         = {'rf': 'min_samples_leaf', 'lgbm': 'num_leaves', 'catboost': 'min_data_in_leaf'}
ESTIMATORS_PARAM_NAME: dict[str, str]   = {'rf': 'n_estimators', 'lgbm': 'n_estimators', 'catboost': 'iterations'}
DEPTH_PARAM_NAME: dict[str, str]        = {'rf': 'max_depth', 'lgbm': 'max_depth', 'catboost': 'depth'}



# ================================================== #
# HELPER FUNCTIONS                                   #
# ================================================== #

def _parallel_jobs(item_count: int) -> int:
    default_workers = 2 if os.name == 'nt' else (os.cpu_count() or 1)
    configured_workers = int(os.getenv('ML_MAX_WORKERS', str(default_workers)))
    if configured_workers <= 0:
        raise ValueError('ML_MAX_WORKERS must be positive.')
    return max(1, min(item_count, configured_workers, os.cpu_count() or 1))


def _parallel_preference() -> Literal['threads', 'processes']:
    configured_backend = os.getenv('ML_PARALLEL_BACKEND')
    if configured_backend is None:
        return 'threads' if sys.platform == 'win32' else 'processes'

    backend_aliases: dict[str, Literal['threads', 'processes']] = {
        'thread': 'threads',
        'threads': 'threads',
        'threading': 'threads',
        'process': 'processes',
        'processes': 'processes',
        'loky': 'processes',
    }
    preference = backend_aliases.get(configured_backend.strip().lower())
    if preference is None:
        raise ValueError('ML_PARALLEL_BACKEND must be one of: threads, threading, processes, loky.')
    return preference


def _group_ticker_datasets(dataset: pd.DataFrame) -> list[pd.DataFrame]:
    if 'ticker' not in dataset.columns: return [ dataset ]
    return [
        ticker_dataset
        for _, ticker_dataset in dataset.groupby('ticker', sort=False)
    ]


def _build_ticker_dataset(
    ticker: Ticker,
    config: DatasetConfig,
    *,
    verboser: VerboseSystem,
) -> pd.DataFrame | None:
    try:
        dataset: pd.DataFrame = build_training_dataset(ticker=ticker, config=config)
        dataset['ticker'] = ticker.ticker
        return dataset
    except ModelException as e:
        verboser.error(f'Error building dataset for {ticker.ticker}: {e}')
        return


def _ordinal_encode(labels: pd.Series) -> np.ndarray:
    return labels.map(ACTION_ORDINAL).to_numpy(dtype=float)


def _ordinal_mae_rmse(y_true: pd.Series, y_pred: pd.Series) -> tuple[Percentage, Percentage]:
    """
    Scores an otherwise categorical BUY/HOLD/SELL model as if it were a
    regressor, by encoding actions ordinally (SELL=-1, HOLD=0, BUY=1). This
    is the metric `deep_train` optimizes and that `train` reports.
    """

    true_ordinal: np.ndarray = _ordinal_encode(y_true)
    pred_ordinal: np.ndarray = _ordinal_encode(y_pred)
    mae: Percentage = Percentage.from_fraction(mean_absolute_error(true_ordinal, pred_ordinal))
    rmse: Percentage = Percentage.from_fraction(np.sqrt(mean_squared_error(true_ordinal, pred_ordinal)))
    return mae, rmse


def _build_ticker_oof_predictions(
    ticker_dataset: pd.DataFrame,
    n_splits: int,
    hyperparameters: ModelHyperparameters,
) -> tuple[pd.Series, pd.Series, dict[str, pd.Series]] | None:
    if len(ticker_dataset) < n_splits + 1:
        return None

    y_true_chunks: list[pd.Series] = []
    y_pred_chunks: list[pd.Series] = []
    estimator_pred_chunks: dict[str, list[pd.Series]] = {name: [] for name in ESTIMATOR_NAMES}
    tscv: TimeSeriesSplit = TimeSeriesSplit(n_splits=n_splits)
    for train_idx, test_idx in tscv.split(ticker_dataset):
        train_df: pd.DataFrame = ticker_dataset.iloc[train_idx]
        test_df: pd.DataFrame = ticker_dataset.iloc[test_idx]
        if train_df['target'].nunique() < 2:
            continue

        fold_model: ActionClassifier = ActionClassifier(hyperparameters=hyperparameters)
        fold_model.fit(train_df)
        x_test: pd.DataFrame = test_df[fold_model.feature_columns]
        fold_pred: pd.Series = pd.Series(
            fold_model.pipeline.predict(x_test),
            index=test_df.index,
        )
        y_true_chunks.append(test_df['target'])
        y_pred_chunks.append(fold_pred)

        imputer = fold_model.pipeline.named_steps['imputer']
        classifier = fold_model.pipeline.named_steps['classifier']
        x_test_imputed = imputer.transform(x_test)
        for name, estimator in classifier.named_estimators_.items():
            # `VotingClassifier` fits sub-estimators on integer-encoded labels
            # (its `le_`), so decode back to action strings before scoring.
            raw_predictions: np.ndarray = classifier.le_.inverse_transform(estimator.predict(x_test_imputed))
            estimator_pred_chunks[name].append(
                pd.Series(raw_predictions, index=test_df.index)
            )

    if not y_true_chunks:
        return None

    return (
        pd.concat(y_true_chunks).sort_index(),
        pd.concat(y_pred_chunks).sort_index(),
        {
            name: pd.concat(chunks).sort_index()
            for name, chunks in estimator_pred_chunks.items()
            if chunks
        },
    )


def _build_oof_predictions(
    dataset: pd.DataFrame,
    hyperparameters: ModelHyperparameters,
    n_splits: int = 5,
    *,
    verboser: VerboseSystem,
) -> tuple[pd.Series, pd.Series, dict[str, pd.Series]]:
    ticker_datasets: list[pd.DataFrame] = _group_ticker_datasets(dataset)
    for ticker_dataset in ticker_datasets:
        label: str = ticker_dataset['ticker'].iloc[0] if 'ticker' in ticker_dataset.columns else '<global>'
        verboser.just_info(f'Building OOF predictions for ticker: [green]{label}[/green] with {len(ticker_dataset)} samples.')

    results: list[tuple[pd.Series, pd.Series, dict[str, pd.Series]] | None] = (
        Parallel(
            n_jobs=_parallel_jobs(len(ticker_datasets)),
            prefer=_parallel_preference(),
        )(
            delayed(_build_ticker_oof_predictions)(ticker_dataset, n_splits, hyperparameters)
            for ticker_dataset in ticker_datasets
        )
        if len(ticker_datasets) > 1
        else [_build_ticker_oof_predictions(ticker_datasets[0], n_splits, hyperparameters)]
    )
    valid_results = [result for result in results if result is not None]
    if not valid_results:
        raise ValueError('Not enough data/classes to apply TimeSeriesSplit.')

    y_true: pd.Series = pd.concat([result[0] for result in valid_results]).sort_index()
    y_pred: pd.Series = pd.concat([result[1] for result in valid_results]).sort_index()
    estimator_predictions: dict[str, pd.Series] = {
        name: pd.concat(
            [result[2][name] for result in valid_results if name in result[2]]
        ).sort_index()
        for name in ESTIMATOR_NAMES
        if any(name in result[2] for result in valid_results)
    }
    return y_true, y_pred, estimator_predictions


def _build_global_dataset(tickers: list[Ticker], config: DatasetConfig, *, verboser: VerboseSystem) -> pd.DataFrame:
    datasets: list[pd.DataFrame] = [
        dataset
        for dataset in Parallel(
            n_jobs=_parallel_jobs(len(tickers)),
            prefer='threads',
        )(
            delayed(_build_ticker_dataset)(ticker, config, verboser=verboser)
            for ticker in tickers
        )
        if dataset is not None
    ]

    if not datasets:
        raise ValueError('Failed to build any dataset.')

    verboser.info(f'Dataset construction completed. Total samples: {sum(len(ds) for ds in datasets)}')
    return pd.concat(datasets, ignore_index=True)


def _fit_and_save(
    global_dataset: pd.DataFrame,
    config: DatasetConfig,
    hyperparameters: ModelHyperparameters,
    *,
    verboser: VerboseSystem,
) -> tuple[ActionClassifier, TrainMetrics]:
    y_true, y_pred, estimator_predictions = _build_oof_predictions(global_dataset, hyperparameters, verboser=verboser)
    report: str = classification_report(y_true, y_pred, digits=4, zero_division=0)
    mae, rmse = _ordinal_mae_rmse(y_true, y_pred)

    model: ActionClassifier = ActionClassifier(
        feature_columns=[
            col
            for col in global_dataset.columns
            if col not in ['future_return', 'target', 'ticker']
        ],
        horizon_days=config.horizon_days,
        hyperparameters=hyperparameters,
    )
    model.fit(global_dataset)
    trained_tickers: list[str] = global_dataset['ticker'].drop_duplicates().tolist()
    model.metadata = {
        'trained_at': datetime.now(UTC).isoformat(),
        'lookback_days': config.lookback_days,
        'horizon_days': config.horizon_days,
        'move_threshold': config.move_threshold,
        'trained_tickers': trained_tickers,
        'samples': len(global_dataset),
        'estimators': {
            name: dict(zip(('mae', 'rmse'), _ordinal_mae_rmse(y_true.loc[predictions.index], predictions)))
            for name, predictions in estimator_predictions.items()
        },
    }

    metrics: TrainMetrics = TrainMetrics(
        classification_report=report,
        action_distribution=(
            global_dataset['target']
                .value_counts(normalize=True)
                .to_dict()
        ),
        trained_tickers=trained_tickers,
        samples=len(global_dataset),
        model_path=str(MODEL_PATH),
        mae=mae,
        rmse=rmse,
    )

    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    temporary_model_path = MODEL_PATH.with_suffix(f'{MODEL_PATH.suffix}.tmp')
    joblib.dump(model, temporary_model_path)
    os.replace(temporary_model_path, MODEL_PATH)

    return model, metrics


def _evaluate_estimator_oof(
    name: str,
    settings: RandomForestHyperparameters | LightGBMHyperparameters | CatBoostHyperparameters,
    ticker_datasets: list[pd.DataFrame],
    n_splits: int,
) -> tuple[Percentage, Percentage]:
    """
    Trains and scores a single estimator (not the full ensemble) via
    walk-forward OOF, used by `deep_train` to search hyperparameters cheaply.
    """

    estimator_threads = int(os.getenv('ML_ESTIMATOR_THREADS', '2'))
    y_true_chunks: list[pd.Series] = []
    y_pred_chunks: list[pd.Series] = []

    for ticker_dataset in ticker_datasets:
        if len(ticker_dataset) < n_splits + 1:
            continue

        feature_columns: list[str] = [
            col for col in ticker_dataset.columns
            if col not in ('future_return', 'target', 'ticker')
        ]
        tscv: TimeSeriesSplit = TimeSeriesSplit(n_splits=n_splits)
        for train_idx, test_idx in tscv.split(ticker_dataset):
            train_df: pd.DataFrame = ticker_dataset.iloc[train_idx]
            test_df: pd.DataFrame = ticker_dataset.iloc[test_idx]
            if train_df['target'].nunique() < 2:
                continue

            imputer: SimpleImputer = SimpleImputer(strategy='median')
            x_train = imputer.fit_transform(train_df[feature_columns])
            x_test = imputer.transform(test_df[feature_columns])

            estimator = build_estimator(name, settings, estimator_threads)
            estimator.fit(x_train, train_df['target'])
            y_true_chunks.append(test_df['target'])
            predictions = np.asarray(estimator.predict(x_test)).reshape(-1)
            y_pred_chunks.append(
                pd.Series(predictions, index=test_df.index)
            )

    if not y_true_chunks:
        raise ValueError(f'Not enough data/classes to evaluate estimator {name!r}.')

    return _ordinal_mae_rmse(
        pd.concat(y_true_chunks).sort_index(),
        pd.concat(y_pred_chunks).sort_index(),
    )

def _tune_estimator(
    name: str,
    base_settings: RandomForestHyperparameters | LightGBMHyperparameters | CatBoostHyperparameters,
    ticker_datasets: list[pd.DataFrame],
    n_splits: int,
    *,
    leaf_step: int,
    estimators_step: int,
    depth_step: int,
    max_iterations: int,
    verboser: VerboseSystem,
) -> tuple[
    RandomForestHyperparameters
    | LightGBMHyperparameters
    | CatBoostHyperparameters,
    float,
    float,
]:
    """
    Coordinate-descent (hill-climbing) search over the "leaf", "n_estimators"
    (iterations for CatBoost) and "depth" hyperparameters of a single
    estimator, evaluated via ordinal MAE on walk-forward OOF predictions.
    Stops once a full pass over every parameter yields no improvement, or
    after `max_iterations` passes.
    """
    tunables: list[tuple[str, int, tuple[int, int]]] = [
        (LEAF_PARAM_NAME[name], leaf_step, LEAF_PARAM_BOUNDS),
        (ESTIMATORS_PARAM_NAME[name], estimators_step, ESTIMATORS_PARAM_BOUNDS),
        (DEPTH_PARAM_NAME[name], depth_step, DEPTH_PARAM_BOUNDS),
    ]

    current = base_settings

    best_mae, best_rmse = _evaluate_estimator_oof(
        name,
        current,
        ticker_datasets,
        n_splits,
    )

    console.print(
        f'[cyan]{name}[/cyan] '
        f'baseline MAE={best_mae:.4f} '
        f'RMSE={best_rmse:.4f} '
        f'params="{current}"'
    )

    with verboser.info_status(f'Tuning {name} estimator model...'):
        for _iteration in range(max_iterations):
            improved = False

            for param_name, step, (lower, upper) in tunables:
                candidates = []

                # Construimos +step y -step a partir del CURRENT actual
                for direction in (1, -1):
                    candidate_value = (
                        getattr(current, param_name)
                        + direction * step
                    )

                    if not lower <= candidate_value <= upper:
                        continue

                    candidate = current.model_copy(
                        update={param_name: candidate_value}
                    )

                    candidates.append(candidate)

                if not candidates:
                    continue

                # Evaluar +step y -step simultáneamente
                results = Parallel(
                    n_jobs=len(candidates),
                    prefer='processes',
                )(
                    delayed(_evaluate_estimator_oof)(
                        name,
                        candidate,
                        ticker_datasets,
                        n_splits,
                    )
                    for candidate in candidates
                )

                best_candidate = min(
                    zip(candidates, results),
                    key=lambda item: item[1][0],
                )

                # Buscar el mejor candidato
                candidate, (mae, rmse) = best_candidate
                if mae < best_mae - 1e-6:
                    previous_value = getattr(current, param_name)

                    current = candidate
                    best_mae = mae
                    best_rmse = rmse
                    improved = True

                    console.print(
                        f'[green]{name}[/green] '
                        f'improved via {param_name}='
                        f'{previous_value} -> '
                        f'{getattr(candidate, param_name)} '
                        f'with MAE={mae:.4f}'
                    )

            if not improved:
                break

    console.print(
        f'[cyan]{name}[/cyan] '
        f'optimum MAE={best_mae:.4f} '
        f'RMSE={best_rmse:.4f} '
        f'params="{current}"\n'
    )

    return current, best_mae, best_rmse


# ================================================== #
# TRAINING FUNCTIONS                                 #
# ================================================== #

def train(
    tickers: list[Ticker],
    config: DatasetConfig | None = None,
    *,
    verboser: VerboseSystem | None = None,
) -> tuple[ActionClassifier, TrainMetrics]:
    """
    Trains the model once, reading its hyperparameters
    from `artifacts/settings.json` without tuning them.
    Use `deep_train` to search for better hyperparameters.
    """

    _verbose = verboser or VerboseSystem(True, is_dev=IS_DEV)
    _verbose.just_info(f'Starting model training with {len(tickers)} tickers...')

    resolved_config: DatasetConfig = config or DatasetConfig()

    global_dataset: pd.DataFrame = _build_global_dataset(tickers, resolved_config, verboser=_verbose)
    model, metrics = _fit_and_save(global_dataset, resolved_config, settings.hyperparameters, verboser=_verbose)

    _verbose.just_info('Model training completed.')
    return model, metrics


def deep_train(
    tickers: list[Ticker],
    config: DatasetConfig | None = None,
    *,
    n_splits: int = 5,
    leaf_step: int = 1,
    estimators_step: int = 25,
    depth_step: int = 1,
    max_iterations: int = 50,
    settings_path: str | os.PathLike[str] | None = None,
    verboser: VerboseSystem | None = None,
) -> tuple[ActionClassifier, TrainMetrics, ModelSettings]:
    """
    Searches, per classifier (rf/lgbm/catboost), for the hyperparameters
    that minimize the ordinal MAE on walk-forward OOF predictions, adjusting
    "leaf" parameters, `n_estimators`/`iterations` (step `estimators_step`,
    25 by default) and `depth`, then retrains with the winning combination
    until no further improvement is found. The winning hyperparameters are
    persisted to `artifacts/settings.json` for future calls to `train()`.
    """

    _verbose = verboser or VerboseSystem(True, is_dev=IS_DEV)
    _verbose.just_info(f'Starting deep_train with {len(tickers)} tickers...')

    resolved_config: DatasetConfig = config or DatasetConfig()
    resolved_settings_path = settings_path or MODEL_SETTINGS_PATH

    global_dataset: pd.DataFrame = _build_global_dataset(tickers, resolved_config, verboser=_verbose)
    ticker_datasets: list[pd.DataFrame] = _group_ticker_datasets(global_dataset)

    # with _verbose.info_status('Tunning rf estimator model...'):
    #     tuned_rf, _rf_mae, _rf_rmse = _tune_estimator(
    #         'rf', base_settings.rf, ticker_datasets, n_splits,
    #         leaf_step=leaf_step, estimators_step=estimators_step, depth_step=depth_step,
    #         max_iterations=max_iterations,
    #     )
    # with _verbose.info_status('Tunning lgbm estimator model...'):
    #     tuned_lgbm, _lgbm_mae, _lgbm_rmse = _tune_estimator(
    #         'lgbm', base_settings.lgbm, ticker_datasets, n_splits,
    #         leaf_step=leaf_step, estimators_step=estimators_step, depth_step=depth_step,
    #         max_iterations=max_iterations,
    #     )
    # with _verbose.info_status('Tunning catboost estimator model...'):
    #     tuned_catboost, _catboost_mae, _catboost_rmse = _tune_estimator(
    #         'catboost', base_settings.catboost, ticker_datasets, n_splits,
    #         leaf_step=leaf_step, estimators_step=estimators_step, depth_step=depth_step,
    #         max_iterations=max_iterations,
    #     )
    
    tuned_results = Parallel(
        n_jobs=3,
        prefer='processes',
    )(
        delayed(_tune_estimator)(
            name,
            stt,
            ticker_datasets,
            n_splits,
            leaf_step=leaf_step,
            estimators_step=estimators_step,
            depth_step=depth_step,
            max_iterations=max_iterations,
            verboser=_verbose,
        )
        for name, stt in (
            ('rf', settings.hyperparameters.rf),
            ('lgbm', settings.hyperparameters.lgbm),
            ('catboost', settings.hyperparameters.catboost),
        )
    )

    (
        (tuned_rf, _rf_mae, _rf_rmse),
        (tuned_lgbm, _lgbm_mae, _lgbm_rmse),
        (tuned_catboost, _catboost_mae, _catboost_rmse),
    ) = tuned_results

    tuned_settings: ModelSettings = settings.with_updates(
        rf=tuned_rf,
        lgbm=tuned_lgbm,
        catboost=tuned_catboost,
    )

    model, metrics = _fit_and_save(global_dataset, resolved_config, tuned_settings, verboser=verboser)

    final_settings: ModelSettings = stamp_training_metadata(
        tuned_settings,
        mae=metrics.mae,
        rmse=metrics.rmse,
        horizon_days=resolved_config.horizon_days,
        trained_tickers=metrics.trained_tickers,
    )
    save_nexis_settings(final_settings, resolved_settings_path)

    _verbose.just_info(f'deep_train completed. Best ensemble MAE={metrics.mae:.4f} RMSE={metrics.rmse:.4f}.')
    return model, metrics, final_settings
