
import numpy as np, pandas as pd
from dataclasses import dataclass
from designkit.behavioral.typing import Assertion, classname

from nexis.classifier import ActionClassifier, TradingAction, TradingDecision
from nexis.dataset import DatasetConfig, build_training_dataset
from datatypes import Ticker


# ================================================== #
# DATACLASSES                                        #
# ================================================== #

@dataclass(frozen=True)
class BacktestMetrics:
    observations: int
    cumulative_return: float
    average_return: float
    win_rate: float
    max_drawdown: float
    sharpe_ratio: float


# ================================================== #
# FEATURES                                           #
# ================================================== #

def run_backtest(
    symbol: str,
    config: DatasetConfig | None = None,
    initial_train_ratio: float = 0.7,
    transaction_cost: float = 0.0,
) -> BacktestMetrics:
    Assertion(symbol).must_be(str)
    Assertion(initial_train_ratio).must_comply(
        lambda x: 0 < x < 1,
        custom_expt=ValueError('initial_train_ratio must be between 0 and 1.'))
    Assertion(transaction_cost).must_comply(
        lambda x: x >= 0,
        custom_expt=ValueError('transaction_cost must be non-negative.'))
    
    resolved_config = config or DatasetConfig()
    dataset: pd.DataFrame = build_training_dataset(
        ticker=Ticker(ticker=symbol),
        config=resolved_config,
    )
    initial_train_size: int = int(len(dataset) * initial_train_ratio)

    if initial_train_size < 60:
        raise ValueError('Dataset insuficiente para iniciar el backtest walk-forward.')
    if initial_train_size >= len(dataset):
        raise ValueError('No quedaron muestras para evaluación en backtest.')

    action_to_position: dict[str, float] = {
        TradingAction.BUY.value: 1.0,
        TradingAction.HOLD.value: 0.0,
        TradingAction.SELL.value: -1.0,
        TradingAction.WAIT.value: 0.0,
    }
    returns: list[float] = []
    has_shares: bool = False
    previous_position: float = 0.0

    for split_idx in range(initial_train_size, len(dataset)):
        train_df: pd.DataFrame = dataset.iloc[:split_idx]
        test_row: pd.Series = dataset.iloc[split_idx]

        model: ActionClassifier = ActionClassifier()
        model.fit(train_df)
        decision: TradingDecision = model.predict(
            test_row[model.feature_columns].to_dict(),
            has_shares=has_shares,
            horizon=resolved_config.horizon_days,
        )
        
        position: float
        has_shares: bool
        action: TradingAction = decision.top_signal.action
        match action:
            case TradingAction.BUY:
                position = 1.0
                has_shares = True
            case TradingAction.HOLD:
                position = 1.0 if has_shares else 0.0
            case TradingAction.SELL:
                position = 0.0
                has_shares = False
            case TradingAction.WAIT:
                position = 0.0
            case _:
                position = action_to_position[action.value]

        realized_return: float = (
            float(test_row['future_return']) * position
            - abs(position - previous_position) * transaction_cost
        )
        returns.append(realized_return)
        previous_position = position

    result: np.ndarray          = np.array(returns, dtype=float)
    equity_curve: np.ndarray    = np.cumprod(1.0 + result)
    running_peak: np.ndarray    = np.maximum.accumulate(equity_curve)
    drawdowns: np.ndarray       = equity_curve / running_peak - 1.0
    standard_deviation: float   = float(result.std()) if result.size else 0.0
    return BacktestMetrics(
        observations=int(result.size),
        cumulative_return=float(equity_curve[-1] - 1.0) if result.size else 0.0,
        average_return=float(result.mean()) if result.size else 0.0,
        win_rate=float((result > 0).mean()) if result.size else 0.0,
        max_drawdown=float(drawdowns.min()) if result.size else 0.0,
        sharpe_ratio=(
            float(result.mean() / standard_deviation * np.sqrt(252))
            if standard_deviation > 0
            else 0.0
        ),
    )
