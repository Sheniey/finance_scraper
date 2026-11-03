
import type { ReportFormat } from '#/types.js';
import type { AnalysisMode, CustomReportSection } from '@/features/analysis/types/index.js';

export const customReportSectionOptions = [
    { id: 'valuation', labelKey: 'analysis.sections.valuation' },
    { id: 'profitability', labelKey: 'analysis.sections.profitability' },
    { id: 'cash_flow', labelKey: 'analysis.sections.cashFlow' },
    { id: 'growth', labelKey: 'analysis.sections.growth' },
    { id: 'financial_health', labelKey: 'analysis.sections.financialHealth' },
    {
        id: 'capital_allocation',
        labelKey: 'analysis.sections.capitalAllocation',
    },
    { id: 'working_capital', labelKey: 'analysis.sections.workingCapital' },
    {
        id: 'dividends_and_splits',
        labelKey: 'analysis.sections.dividends',
    },
    { id: 'news', labelKey: 'analysis.sections.news' },
    { id: 'charts', labelKey: 'analysis.sections.charts' },
    { id: 'explanation', labelKey: 'analysis.explain' },
] as const;

export const defaultCustomReportSections: CustomReportSection[] = [
    'valuation',
    'profitability',
    'cash_flow',
    'growth',
    'financial_health',
    'capital_allocation',
    'working_capital',
    'dividends_and_splits',
    'news',
    'charts',
];

export function normalizeCustomReportSections(
    values: readonly string[],
): CustomReportSection[] {
    const optionIds = new Set<string>(
        customReportSectionOptions.map(({ id }) => id),
    );
    const sectionIds = new Set<string>([
        'valuation',
        'profitability',
        'cash_flow',
        'growth',
        'financial_health',
        'capital_allocation',
        'working_capital',
    ]);
    const recognized: CustomReportSection[] = values.filter(
        (value): value is CustomReportSection => optionIds.has(value),
    );
    const recognizedSections = recognized.filter((value) =>
        sectionIds.has(value),
    );
    const recognizedFeatures = recognized.filter(
        (value) => !sectionIds.has(value),
    );
    const initialSections = recognizedSections.length
        ? recognizedSections
        : defaultCustomReportSections;
    return Array.from(new Set([...initialSections, ...recognizedFeatures]));
}

export const outputFormats: ReportFormat[] = ['pdf', 'json', 'yaml', 'xlsx'];
export const analysisModes: AnalysisMode[] = [
    'custom',
    'classic',
    'growth',
    'validation',
    'full',
    'info',
];
