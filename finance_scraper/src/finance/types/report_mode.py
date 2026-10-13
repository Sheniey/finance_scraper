
from enum import StrEnum


# ================================================== #
# ENUMS                                              #
# ================================================== #

class ReportMode(StrEnum):
    GROWTH = 'growth'
    VALIDATION = 'validation'
    FULL = 'full'
    CLASSIC = 'classic'
    INFO = 'info'
    CUSTOM = 'custom'
