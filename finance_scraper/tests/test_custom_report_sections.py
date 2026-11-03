from finance.types.report_presets import ordered_custom_report_sections


def test_custom_report_order_preserves_selected_sections() -> None:
    assert ordered_custom_report_sections(
        [
            'growth',
            'explanation',
            'valuation',
            'charts',
            'news',
        ],
    ) == [
        'growth',
        'explanation',
        'valuation',
        'charts',
        'news',
    ]


def test_legacy_metric_preferences_resolve_to_ordered_sections() -> None:
    assert ordered_custom_report_sections(
        ['roic', 'pe_ratio', 'revenue_growth', 'dividends'],
    ) == [
        'profitability',
        'valuation',
        'growth',
        'dividends_and_splits',
    ]
