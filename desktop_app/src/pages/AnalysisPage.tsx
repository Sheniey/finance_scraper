import { useState, type FormEvent } from 'react';
import {
    type CreateReportRequest,
    type Locale,
    type ReportEntry,
    type ReportFormat,
} from '#/types.js';
import { translate, formatError } from '@/i18n/messages.js';
import { AnalysisForm } from '@/pages/analysis/AnalysisForm.js';
import { AnalysisStatusPanel } from '@/pages/analysis/AnalysisStatusPanel.js';
import {
    type AnalysisMode,
} from '@/pages/analysis/analysis-utils.js';
import { useReportPolling } from '@/pages/analysis/useReportPolling.js';

interface AnalysisPageProps {
    locale: Locale;
    onCreate: (request: CreateReportRequest) => Promise<ReportEntry>;
    onOpen: (report: ReportEntry) => Promise<void>;
    onReportsChanged: () => Promise<unknown>;
}

export function AnalysisPage({
    locale,
    onCreate,
    onOpen,
    onReportsChanged,
}: AnalysisPageProps) {
    const [ticker, setTicker] = useState('');
    const [format, setFormat] = useState<ReportFormat>('pdf');
    const [mode, setMode] = useState<AnalysisMode>('custom');
    const [explain, setExplain] = useState(false);
    const [charts, setCharts] = useState(true);
    const [horizon, setHorizon] = useState(15);
    const [currentReport, setCurrentReport] = useState<ReportEntry | null>(null);
    const [isSubmitting, setIsSubmitting] = useState(false);
    const [isOpening, setIsOpening] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const t = (key: string) => translate(locale, key);

    useReportPolling({
        report: currentReport,
        locale,
        onUpdate: setCurrentReport,
        onCompleted: onReportsChanged,
        onError: setError,
    });

    async function submit(event: FormEvent<HTMLFormElement>) {
        event.preventDefault();
        setError(null);
        const normalizedTicker = ticker.trim().toUpperCase();
        if (!normalizedTicker) {
            setError(t('analysis.tickerRequired'));
            return;
        }

        setIsSubmitting(true);
        try {
            const date = new Date().toISOString().slice(0, 10);
            const safeTicker = normalizedTicker.replaceAll('.', '-');
            const report = await onCreate({
                ticker: normalizedTicker,
                filename: `${safeTicker}-${date}.${format}`,
                explain,
                mode,
                charts,
                ml_horizon: horizon,
            });
            setCurrentReport(report);
            await onReportsChanged();
        } catch (requestError) {
            setError(formatError(locale, requestError));
        } finally {
            setIsSubmitting(false);
        }
    }

    async function openCurrentReport() {
        if (!currentReport) {
            return;
        }

        setIsOpening(true);
        setError(null);
        try {
            await onOpen(currentReport);
        } catch (openError) {
            setError(formatError(locale, openError));
        } finally {
            setIsOpening(false);
        }
    }

    return (
        <div className='page-stack'>
            <header className='page-heading'>
                <p className='eyebrow dark'>
                    <span className='signal-mark' />
                    {t('nav.analysis')}
                </p>
                <h1>{t('analysis.title')}</h1>
                <p>{t('analysis.copy')}</p>
            </header>
            <div className='analysis-layout'>
                <AnalysisForm
                    charts={charts}
                    error={error}
                    explain={explain}
                    format={format}
                    horizon={horizon}
                    isSubmitting={isSubmitting}
                    locale={locale}
                    mode={mode}
                    onChartsChange={setCharts}
                    onExplainChange={setExplain}
                    onFormatChange={setFormat}
                    onHorizonChange={setHorizon}
                    onModeChange={setMode}
                    onSubmit={submit}
                    onTickerChange={setTicker}
                    ticker={ticker}
                />
                <AnalysisStatusPanel
                    isOpening={isOpening}
                    locale={locale}
                    onOpen={() => void openCurrentReport()}
                    report={currentReport}
                />
            </div>
        </div>
    );
}
