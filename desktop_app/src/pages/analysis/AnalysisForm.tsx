import type { FormEvent } from 'react';
import {
    BarChart3,
    BrainCircuit,
    FileOutput,
    Sparkles,
} from 'lucide-react';

import type { Locale, ReportFormat } from '#/types.js';
import { translate } from '@/i18n/messages.js';
import {
    analysisModes,
    outputFormats,
    type AnalysisMode,
} from '@/pages/analysis/analysis-utils.js';

interface AnalysisFormProps {
    locale: Locale;
    ticker: string;
    format: ReportFormat;
    mode: AnalysisMode;
    horizon: number;
    explain: boolean;
    charts: boolean;
    isSubmitting: boolean;
    error: string | null;
    onTickerChange: (value: string) => void;
    onFormatChange: (value: ReportFormat) => void;
    onModeChange: (value: AnalysisMode) => void;
    onHorizonChange: (value: number) => void;
    onExplainChange: (value: boolean) => void;
    onChartsChange: (value: boolean) => void;
    onSubmit: (event: FormEvent<HTMLFormElement>) => void;
}

export function AnalysisForm({
    locale,
    ticker,
    format,
    mode,
    horizon,
    explain,
    charts,
    isSubmitting,
    error,
    onTickerChange,
    onFormatChange,
    onModeChange,
    onHorizonChange,
    onExplainChange,
    onChartsChange,
    onSubmit,
}: AnalysisFormProps) {
    const t = (key: string) => translate(locale, key);

    return (
        <form className='content-panel analysis-form' onSubmit={onSubmit}>
            <div className='panel-heading-row'>
                <div>
                    <p className='field-kicker'>{t('analysis.ticker')}</p>
                    <h2>{t('analysis.title')}</h2>
                </div>
                <span className='panel-symbol'>
                    <Sparkles size={18} aria-hidden='true' />
                </span>
            </div>
            <label className='form-field ticker-field'>
                <span>{t('analysis.ticker')}</span>
                <input
                    autoCapitalize='characters'
                    autoComplete='off'
                    maxLength={20}
                    onChange={(event) =>
                        onTickerChange(event.target.value.toUpperCase())
                    }
                    placeholder={t('analysis.tickerPlaceholder')}
                    required
                    value={ticker}
                />
                <small>
                    {locale === 'es'
                        ? 'Símbolo de mercado, por ejemplo AAPL o FMX23.MX.'
                        : 'Market symbol, for example AAPL or FMX23.MX.'}
                </small>
            </label>

            <div className='form-grid two-column'>
                <label className='form-field'>
                    <span>{t('analysis.format')}</span>
                    <select
                        onChange={(event) =>
                            onFormatChange(event.target.value as ReportFormat)
                        }
                        value={format}
                    >
                        {outputFormats.map((item) => (
                            <option key={item} value={item}>
                                {translate(locale, `email.${item}`)}
                            </option>
                        ))}
                    </select>
                </label>
                <label className='form-field'>
                    <span>{t('analysis.mode')}</span>
                    <select
                        onChange={(event) =>
                            onModeChange(event.target.value as AnalysisMode)
                        }
                        value={mode}
                    >
                        {analysisModes.map((item) => (
                            <option key={item} value={item}>
                                {item.charAt(0).toUpperCase() + item.slice(1)}
                            </option>
                        ))}
                    </select>
                </label>
            </div>

            <label className='form-field horizon-field'>
                <span>{t('analysis.horizon')}</span>
                <input
                    max={365}
                    min={1}
                    onChange={(event) =>
                        onHorizonChange(Number(event.target.value))
                    }
                    type='number'
                    value={horizon}
                />
            </label>
            <label className='choice-row'>
                <span className='choice-icon'>
                    <BrainCircuit size={17} aria-hidden='true' />
                </span>
                <span className='choice-copy'>
                    <strong>{t('analysis.explain')}</strong>
                    <small>{t('analysis.explainCopy')}</small>
                </span>
                <input
                    checked={explain}
                    onChange={(event) => onExplainChange(event.target.checked)}
                    type='checkbox'
                />
                <span className='toggle-track' aria-hidden='true' />
            </label>
            <label className='choice-row'>
                <span className='choice-icon'>
                    <BarChart3 size={17} aria-hidden='true' />
                </span>
                <span className='choice-copy'>
                    <strong>{t('analysis.charts')}</strong>
                    <small>
                        {locale === 'es'
                            ? 'Incluye visualizaciones en el reporte.'
                            : 'Include visualizations in the report.'}
                    </small>
                </span>
                <input
                    checked={charts}
                    onChange={(event) => onChartsChange(event.target.checked)}
                    type='checkbox'
                />
                <span className='toggle-track' aria-hidden='true' />
            </label>

            {error && (
                <p className='form-message error-message' role='alert'>
                    {error}
                </p>
            )}
            <button
                className='button-primary form-primary'
                disabled={isSubmitting}
                type='submit'
            >
                <FileOutput size={17} aria-hidden='true' />
                {isSubmitting
                    ? t('analysis.generating')
                    : t('analysis.generate')}
            </button>
        </form>
    );
}
