
from enum import StrEnum


# ================================================== #
# MODELS                                             #
# ================================================== #

class TradingAction(StrEnum):
    """The complete action vocabulary exposed by the trading model."""

    BUY = 'buy'
    HOLD = 'hold'
    SELL = 'sell'
    WAIT = 'wait'


MODEL_ACTIONS: tuple[TradingAction, ...] = (
    TradingAction.BUY,
    TradingAction.HOLD,
    TradingAction.SELL,
)
"""The subset of actions that the trading model is capable of predicting."""

ALL_ACTION_LABELS: tuple[str, ...] = tuple(action.value for action in TradingAction)
"""All possible action labels exposed by the trading model."""

MODEL_ACTION_LABELS: tuple[str, ...] = tuple(action.value for action in MODEL_ACTIONS)
"""The subset of action labels that the trading model is capable of predicting."""
