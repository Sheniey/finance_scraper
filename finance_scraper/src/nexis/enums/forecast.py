
from enum import StrEnum


# ================================================== #
# ENUMS                                              #
# ================================================== #

class ForecastTrend(StrEnum):
    """
    A coarse trend read from the forecast's expected return at the
    requested horizon. This is *not* a trading action: it only describes
    what TimesFM expects the price path to look like.
    """

    UP      = 'up'   # alza
    DOWN    = 'down' # baja
    FLAT    = 'flat' # lateral
