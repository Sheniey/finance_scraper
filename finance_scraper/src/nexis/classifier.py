
import os
from decimal import Decimal
from designkit.behavioral.typing import Assertion

import numpy as np
import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline

# === classifiers === #
from lightgbm import LGBMClassifier
from catboost import CatBoostClassifier
from sklearn.ensemble import RandomForestClassifier, VotingClassifier

from datatypes import Percentage

from nexis.actions import MODEL_ACTION_LABELS, MODEL_ACTIONS, TradingAction
from nexis.models.classifier import (
    TradingDecision,
    TradingSignal,
    ClassifierMetadata,
    TradingPeriodUnit
)
from nexis.dataset import FEATURE_COLUMNS
from nexis.errors import (
    InvalidDecisionContextError,
    InvalidModelProbabilitiesError,
    MissingFeatureColumnsError,
    MissingTargetColumnError,
)
from nexis.settings import (
    CatBoostHyperparameters,
    LightGBMHyperparameters,
    ModelHyperparameters,
    RandomForestHyperparameters,
)


def _to_percentage(fraction: float) -> Percentage:
    """`Percentage.from_fraction` expects a `Decimal`, not a raw `float`."""
    return Percentage.from_fraction(Decimal(str(fraction)))


# ================================================== #
# CONSTANTS                                          #
# ================================================== #

ESTIMATOR_NAMES: tuple[str, ...] = ('rf', 'lgbm', 'catboost')



# ================================================== #
# ESTIMATOR FACTORY                                  #
# ================================================== #

def build_estimator(
    name: str,
    settings: RandomForestHyperparameters | LightGBMHyperparameters | CatBoostHyperparameters,
    estimator_threads: int = 1,
) -> RandomForestClassifier | LGBMClassifier | CatBoostClassifier:
    """Builds a single, unfitted estimator from its own hyperparameters model.
    Shared by `ActionClassifier._build_pipeline` (which assembles the full
    voting ensemble) and `trainer.deep_train` (which tunes each estimator in
    isolation before assembling the final ensemble)."""

    match name, settings:
        case 'rf', RandomForestHyperparameters():
            return RandomForestClassifier(
                n_estimators=settings.n_estimators,
                max_depth=settings.max_depth,
                min_samples_leaf=settings.min_samples_leaf,
                class_weight='balanced',
                random_state=42,
                n_jobs=estimator_threads,
            )
        case 'lgbm', LightGBMHyperparameters():
            return LGBMClassifier(
                n_estimators=settings.n_estimators,
                learning_rate=settings.learning_rate,
                num_leaves=settings.num_leaves,
                max_depth=settings.max_depth,
                subsample=settings.subsample,
                colsample_bytree=settings.colsample_bytree,
                class_weight='balanced',
                verbosity=-1,
                force_row_wise=True,
                random_state=42,
                n_jobs=estimator_threads,
            )
        case 'catboost', CatBoostHyperparameters():
            return CatBoostClassifier(
                iterations=settings.iterations,
                learning_rate=settings.learning_rate,
                depth=settings.depth,
                min_data_in_leaf=settings.min_data_in_leaf,
                loss_function='MultiClass',
                auto_class_weights='Balanced',
                random_seed=42,
                verbose=False,
                thread_count=estimator_threads,
            )
        case _:
            raise ValueError(
                f'Unknown estimator name/settings combination: {name!r} / {type(settings).__name__}. '
                f'Expected one of {ESTIMATOR_NAMES}.'
            )

class ActionClassifier:
    def __init__(
        self,
        feature_columns: list[str] | None = None,
        horizon_days: int = 5,
        hyperparameters: ModelHyperparameters | None = None,
    ) -> None:
        if horizon_days <= 0:
            raise ValueError('horizon_days must be positive.')

        estimator_threads = int(os.getenv('ML_ESTIMATOR_THREADS', '1'))
        if estimator_threads <= 0:
            raise ValueError('ML_ESTIMATOR_THREADS must be positive.')

        self.feature_columns: list[str] = list(feature_columns) if feature_columns else list(FEATURE_COLUMNS)
        self.horizon_days = horizon_days
        self.estimator_threads = estimator_threads
        self.hyperparameters: ModelHyperparameters = hyperparameters or ModelHyperparameters()
        self.metadata: dict[str, object] = {}
        self.pipeline: Pipeline = self._build_pipeline()

    @property
    def feature_names_in_(self) -> list[str]:
        return self.pipeline.named_steps['imputer'].get_feature_names_out(self.feature_columns).tolist()

    def _build_pipeline(self) -> Pipeline:
        voting: VotingClassifier = VotingClassifier(
            estimators=[
                ('rf', build_estimator('rf', self.hyperparameters.rf, self.estimator_threads)),
                ('lgbm', build_estimator('lgbm', self.hyperparameters.lgbm, self.estimator_threads)),
                ('catboost', build_estimator('catboost', self.hyperparameters.catboost, self.estimator_threads)),
            ],
            voting='soft',
            n_jobs=1,
        )
        return Pipeline(
            steps=[
                ('imputer', SimpleImputer(strategy='median')),
                ('classifier', voting),
            ]
        )

    def fit(self, dataset: pd.DataFrame) -> None:
        if 'target' not in dataset.columns:
            raise MissingTargetColumnError()

        missing_cols: list[str] = [column for column in self.feature_columns if column not in dataset.columns]
        if missing_cols:
            raise MissingFeatureColumnsError(missing_columns=missing_cols)

        self.feature_columns = [column for column in self.feature_columns if column in dataset.columns]
        x_train: pd.DataFrame = dataset[self.feature_columns]
        y_train: pd.Series = dataset['target']
        invalid_labels: set[str] = set(y_train.astype(str)) - set(MODEL_ACTION_LABELS)
        if invalid_labels:
            raise ValueError(
                f'Unsupported target labels: {sorted(invalid_labels)}. '
                f'Expected only {MODEL_ACTION_LABELS}.'
            )
        if y_train.nunique() < 2:
            raise ValueError('At least two action classes are required to train the model.')

        self.pipeline.fit(x_train, y_train)

    def _to_feature_frame(self, features: pd.Series | dict[str, float]) -> pd.DataFrame:
        feature_input = features.to_dict() if isinstance(features, pd.Series) else features
        return pd.DataFrame([feature_input], columns=self.feature_columns)

    @staticmethod
    def decision_engine(model_probabilities: dict[TradingAction, float], has_shares: bool) -> TradingAction:
        if has_shares:
            if model_probabilities[TradingAction.SELL] > model_probabilities[TradingAction.HOLD]:
                return TradingAction.SELL
            return TradingAction.HOLD
        else:
            if model_probabilities[TradingAction.BUY] > model_probabilities[TradingAction.HOLD]:
                return TradingAction.BUY
            return TradingAction.HOLD

    def _estimator_metadata(self, x_live: pd.DataFrame) -> tuple[ClassifierMetadata, ...]:
        """Builds one `ClassifierMetadata` per underlying estimator (rf/lgbm/
        catboost), pairing its own top signal with the MAE/RMSE recorded for
        it during training (see `trainer._build_oof_predictions`)."""

        classifier: VotingClassifier = self.pipeline.named_steps['classifier']
        fitted_estimators: dict[str, object] = getattr(classifier, 'named_estimators_', {})
        label_encoder = classifier.le_
        estimator_metrics: dict[str, dict[str, float]] = self.metadata.get('estimators', {})  # type: ignore[assignment]

        imputer: SimpleImputer = self.pipeline.named_steps['imputer']
        x_imputed: np.ndarray = imputer.transform(x_live)

        metadata: list[ClassifierMetadata] = []
        for name in ESTIMATOR_NAMES:
            estimator = fitted_estimators.get(name)
            if estimator is None or not hasattr(estimator, 'predict_proba'):
                continue

            probabilities_raw: np.ndarray = estimator.predict_proba(x_imputed)[0]
            # Sub-estimators are fitted by `VotingClassifier` on integer-encoded
            # labels (its `le_`), not the original action strings.
            classes: np.ndarray = label_encoder.inverse_transform(estimator.classes_)
            top_index: int = int(np.argmax(probabilities_raw))
            top_action: TradingAction = TradingAction(str(classes[top_index]))
            metrics: dict[str, float] = estimator_metrics.get(name, {})

            metadata.append(
                ClassifierMetadata(
                    name=name,
                    signals=(
                        TradingSignal(
                            action=top_action,
                            probability=_to_percentage(float(probabilities_raw[top_index])),
                        ),
                    ),
                    mae=metrics.get('mae'),
                    rmse=metrics.get('rmse'),
                )
            )

        return tuple(metadata)

    def predict(self,
            features: pd.Series | dict[str, float],
            has_shares: bool,
            *,
            horizon: int = 10,
            horizon_unit: TradingPeriodUnit = 'day'
        ) -> TradingDecision:

        Assertion(features).must_be(pd.Series, dict)
        Assertion(has_shares).must_be(bool)
        Assertion(horizon).must_be(int)
        Assertion(horizon).must_comply(
            lambda x: x > 0,
            custom_expt=ValueError('horizon must be positive.')
        )
        Assertion(horizon_unit).must_be(str)

        x_live: pd.DataFrame = self._to_feature_frame(features)
        probabilities_raw: np.ndarray = self.pipeline.predict_proba(x_live)[0]
        if (
            not np.isfinite(probabilities_raw).all()
            or probabilities_raw.sum() <= 0
        ):
            raise InvalidModelProbabilitiesError()
        classifier: VotingClassifier = self.pipeline.named_steps['classifier']
        classes: np.ndarray = classifier.classes_

        model_probabilities: dict[TradingAction, float] = dict.fromkeys(MODEL_ACTIONS, 0.0)
        for label, probability in zip(classes.tolist(), probabilities_raw.tolist()):
            if label not in MODEL_ACTION_LABELS:
                raise InvalidModelProbabilitiesError()

            action: TradingAction = TradingAction(label)
            model_probabilities[action] = float(probability)

        match has_shares:
            case True:
                class_probabilities: dict[TradingAction, float] = {
                    TradingAction.BUY: model_probabilities[TradingAction.BUY],
                    TradingAction.HOLD: model_probabilities[TradingAction.HOLD],
                    TradingAction.SELL: model_probabilities[TradingAction.SELL],
                }
            case False:
                class_probabilities: dict[TradingAction, float] = {
                    TradingAction.BUY: model_probabilities[TradingAction.BUY] + (model_probabilities[TradingAction.SELL] / 2),
                    TradingAction.WAIT: (
                        model_probabilities[TradingAction.HOLD] + (model_probabilities[TradingAction.SELL] / 2)
                    ),
                }
            case _:
                raise InvalidDecisionContextError()

        if not class_probabilities:
            raise InvalidModelProbabilitiesError()

        signals: tuple[TradingSignal, ...] = tuple(
            TradingSignal(
                action=action,
                probability=_to_percentage(probability)
            )
            for action, probability in sorted(
                class_probabilities.items(),
                key=lambda item: item[1],
                reverse=True,
            )
        )
        return TradingDecision(
            signals=signals,
            horizon=horizon,
            horizon_unit=horizon_unit,
            metadata=self._estimator_metadata(x_live),
        )
