# ================================================== #
# MODULE: colors
# ================================================== #


from reportlab.lib.colors import HexColor

from finance.config import Theme


EXCELLENT_COLOR: HexColor = HexColor(Theme.COLOR_EXCELLENT)
VERY_GOOD_COLOR: HexColor = HexColor(Theme.COLOR_VERY_GOOD)
GOOD_COLOR: HexColor = HexColor(Theme.COLOR_GOOD)
MEH_COLOR: HexColor = HexColor(Theme.COLOR_MEH)
BAD_COLOR: HexColor = HexColor(Theme.COLOR_BAD)
VERY_BAD_COLOR: HexColor = HexColor(Theme.COLOR_VERY_BAD)
AWFUL_COLOR: HexColor = HexColor(Theme.COLOR_AWFUL)

GAIN_COLOR: HexColor = HexColor(Theme.COLOR_GAIN)
NEUTRAL_COLOR: HexColor = HexColor(Theme.COLOR_NEUTRAL)
LOSS_COLOR: HexColor = HexColor(Theme.COLOR_LOSS)

POSITIVE_COLOR: HexColor = HexColor(Theme.COLOR_POSITIVE)
NEGATIVE_COLOR: HexColor = HexColor(Theme.COLOR_NEGATIVE)

NUMBER_COLOR: HexColor = HexColor(Theme.COLOR_NUMBER)
LINK_COLOR: HexColor = HexColor(Theme.COLOR_LINK)
DATE_COLOR: HexColor = HexColor(Theme.COLOR_DATE)

PAGE_BACKGROUND: HexColor = HexColor(Theme.COLOR_PAGE_BACKGROUND)
SURFACE_COLOR: HexColor = HexColor(Theme.COLOR_SURFACE)
CARD_COLOR: HexColor = HexColor(Theme.COLOR_CARD)
INK_COLOR: HexColor = HexColor(Theme.COLOR_INK)
MUTED_COLOR: HexColor = HexColor(Theme.COLOR_MUTED)
RULE_COLOR: HexColor = HexColor(Theme.COLOR_RULE)
ACCENT_COLOR: HexColor = HexColor(Theme.COLOR_ACCENT)
WHITE_COLOR: HexColor = HexColor(Theme.COLOR_WHITE)
COVER_MUTED_COLOR: HexColor = HexColor(Theme.COLOR_COVER_MUTED)
COVER_LINE_COLOR: HexColor = HexColor(Theme.COLOR_COVER_LINE)
CHART_PRIMARY_COLOR: HexColor = HexColor(Theme.COLOR_CHART_PRIMARY)
CHART_SECONDARY_COLOR: HexColor = HexColor(Theme.COLOR_CHART_SECONDARY)
CHART_TERTIARY_COLOR: HexColor = HexColor(Theme.COLOR_CHART_TERTIARY)
CHART_QUATERNARY_COLOR: HexColor = HexColor(Theme.COLOR_CHART_QUATERNARY)
CHART_GRID_COLOR: HexColor = HexColor(Theme.COLOR_CHART_GRID)
