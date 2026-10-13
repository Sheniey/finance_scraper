import type { ReportFormat } from '#/types.js';

export type AnalysisMode =
    | 'custom'
    | 'classic'
    | 'growth'
    | 'validation'
    | 'full'
    | 'info';

export const outputFormats: ReportFormat[] = ['pdf', 'json', 'yaml', 'xlsx'];
export const analysisModes: AnalysisMode[] = [
    'custom',
    'classic',
    'growth',
    'validation',
    'full',
    'info',
];
