
import { useEffect, useRef, useState, type FormEvent } from 'react';
import { createPortal } from 'react-dom';
import { AnimatePresence, motion } from 'motion/react';
import { X } from 'lucide-react';

import type {
    AiProviderStatus,
    CreateReportRequest,
    Locale,
    OllamaStatus,
    ReportEntry,
    ReportFormat,
    UserProfile,
} from '#/types.js';
import { formatError, translate } from '@/features/common/i18n/messages.js';
import { AnalysisForm } from '@/features/analysis/components/AnalysisForm.js';
import { AnalysisStatusPanel } from '@/features/analysis/components/AnalysisStatusPanel.js';
import {
    customReportSectionOptions,
    normalizeCustomReportSections,
} from '@/features/analysis/lib/analysis-utils.js';
import type {
    AnalysisMode,
    CustomReportSection,
} from '@/features/analysis/types/index.js';
import { useReportPolling } from '@/features/analysis/hooks/useReportPolling.js';



interface AnalysisPageProps {
    locale: Locale;
    profile: UserProfile;
    isOpen: boolean;
    onClose: () => void;
    onCreate: (request: CreateReportRequest) => Promise<ReportEntry>;
    onOpen: (report: ReportEntry) => Promise<void>;
    onReportsChanged: () => Promise<unknown>;
    onSaveCustomReport: (sections: string[]) => Promise<void>;
}


function createReportFilename(
    name: string,
    ticker: string,
    date: string,
    format: ReportFormat,
): string {
    const safeTicker = ticker.replaceAll('.', '-');
    const normalizedName = name
        .normalize('NFKD')
        .replace(/[\u0300-\u036f]/g, '');
    const safeName = normalizedName
        .replace(/[^A-Za-z0-9._ -]/g, '-')
        .replace(/\s+/g, '-')
        .replace(/-+/g, '-')
        .replace(/^[^A-Za-z0-9]+/, '')
        .slice(0, 60);
    return `${safeName || safeTicker}-${safeTicker}-${date}.${format}`;
}


function localReportDate(): string {
    const now = new Date();
    const localTime = new Date(
        now.getTime() - now.getTimezoneOffset() * 60_000,
    );
    return localTime.toISOString().slice(0, 10);
}


function hasConfiguredAiProvider(
    providerStatus: AiProviderStatus | null,
    ollamaStatus: OllamaStatus | null,
): boolean {
    return (
        (providerStatus !== null &&
            Object.values(providerStatus).some(Boolean)) ||
        (ollamaStatus?.running === true && ollamaStatus.models.length > 0)
    );
}


export function AnalysisPage({
    locale,
    profile,
    isOpen,
    onClose,
    onCreate,
    onOpen,
    onReportsChanged,
    onSaveCustomReport,
}: AnalysisPageProps) {
    const [ticker, setTicker] = useState('');
    const [reportName, setReportName] = useState('');
    const [format, setFormat] = useState<ReportFormat>('pdf');
    const [mode, setMode] = useState<AnalysisMode>('custom');
    const [customSections, setCustomSections] = useState<
        CustomReportSection[]
    >(() => normalizeCustomReportSections(profile.custom_report));
    const [explain, setExplain] = useState(
        profile.custom_report.includes('explanation'),
    );
    const [charts, setCharts] = useState(
        profile.custom_report.includes('charts') ||
            profile.custom_report.length === 0,
    );
    const [horizon, setHorizon] = useState(15);
    const [currentReport, setCurrentReport] = useState<ReportEntry | null>(null);
    const [isSubmitting, setIsSubmitting] = useState(false);
    const [isOpening, setIsOpening] = useState(false);
    const [isSavingPreference, setIsSavingPreference] = useState(false);
    const [preferenceSaved, setPreferenceSaved] = useState(
        profile.custom_report.length > 0 &&
            profile.custom_report.every((value) =>
                customReportSectionOptions.some(
                    ({ id }) => id === value,
                ),
            ),
    );
    const [error, setError] = useState<string | null>(null);
    const [providerStatus, setProviderStatus] =
        useState<AiProviderStatus | null>(null);
    const [ollamaStatus, setOllamaStatus] = useState<OllamaStatus | null>(null);
    const [isCheckingProviders, setIsCheckingProviders] = useState(false);
    const dialogRef = useRef<HTMLElement | null>(null);
    const onCloseRef = useRef(onClose);
    onCloseRef.current = onClose;
    const t = (key: string, values?: Record<string, string | number>) =>
        translate(locale, key, values);
    const aiAvailable = hasConfiguredAiProvider(providerStatus, ollamaStatus);

    useReportPolling({
        report: currentReport,
        locale,
        onUpdate: setCurrentReport,
        onCompleted: onReportsChanged,
        onError: setError,
    });

    useEffect(() => {
        if (!isOpen) {
            return;
        }

        const previousFocus =
            document.activeElement instanceof HTMLElement
                ? document.activeElement
                : null;
        const previousOverflow = document.body.style.overflow;
        document.body.style.overflow = 'hidden';
        setProviderStatus(null);
        setOllamaStatus(null);

        const focusDialog = () => {
            const firstField =
                dialogRef.current?.querySelector<HTMLElement>(
                    'input:not([disabled]), select:not([disabled]), button:not([disabled])',
                );
            firstField?.focus();
        };
        window.requestAnimationFrame(focusDialog);

        const handleKeyDown = (event: KeyboardEvent) => {
            if (event.key === 'Escape') {
                onCloseRef.current();
                return;
            }
            if (event.key !== 'Tab' || !dialogRef.current) {
                return;
            }
            const focusable = Array.from(
                dialogRef.current.querySelectorAll<HTMLElement>(
                    'input:not([disabled]), select:not([disabled]), button:not([disabled]), [tabindex="0"]',
                ),
            );
            if (!focusable.length) {
                event.preventDefault();
                return;
            }
            const first = focusable[0];
            const last = focusable[focusable.length - 1];
            if (!first || !last) {
                event.preventDefault();
                return;
            }
            if (event.shiftKey && document.activeElement === first) {
                event.preventDefault();
                last.focus();
            } else if (!event.shiftKey && document.activeElement === last) {
                event.preventDefault();
                first.focus();
            }
        };
        document.addEventListener('keydown', handleKeyDown);

        let isCurrent = true;
        async function loadProviderStatus() {
            setIsCheckingProviders(true);
            setError(null);
            try {
                const [nextProviderStatus, nextOllamaStatus] =
                    await Promise.all([
                        window.desktopApi.getAiProviderStatus(),
                        window.desktopApi.getOllamaStatus(),
                    ]);
                if (!isCurrent) {
                    return;
                }
                setProviderStatus(nextProviderStatus);
                setOllamaStatus(nextOllamaStatus);
            } catch (statusError) {
                if (isCurrent) {
                    setError(formatError(locale, statusError));
                }
            } finally {
                if (isCurrent) {
                    setIsCheckingProviders(false);
                }
            }
        }
        void loadProviderStatus();

        return () => {
            isCurrent = false;
            document.removeEventListener('keydown', handleKeyDown);
            document.body.style.overflow = previousOverflow;
            previousFocus?.focus();
        };
    }, [isOpen, locale]);

    async function submit(event: FormEvent<HTMLFormElement>) {
        event.preventDefault();
        setError(null);
        const normalizedTicker = ticker.trim().toUpperCase();
        if (!normalizedTicker) {
            setError(t('analysis.tickerRequired'));
            return;
        }
        if (mode === 'custom' && customSections.length === 0) {
            setError(t('analysis.sectionsRequired'));
            return;
        }
        if (isCheckingProviders && customSections.includes('explanation')) {
            setError(t('analysis.aiStatusLoading'));
            return;
        }

        const savedSections =
            mode === 'custom'
                ? customSections.filter(
                      (section) =>
                          section !== 'explanation' || aiAvailable,
                  )
                : customSections;
        const shouldExplain =
            mode === 'custom'
                ? savedSections.includes('explanation')
                : explain;
        if (shouldExplain && !aiAvailable) {
            setError(t('analysis.aiUnavailable'));
            return;
        }
        const includeCharts =
            mode === 'custom' ? savedSections.includes('charts') : charts;

        setIsSubmitting(true);
        try {
            if (mode === 'custom') {
                await persistCustomSections(savedSections);
                setCustomSections(savedSections);
                setExplain(shouldExplain);
                setCharts(includeCharts);
            }
            const date = localReportDate();
            const report = await onCreate({
                ticker: normalizedTicker,
                filename: createReportFilename(
                    reportName.trim(),
                    normalizedTicker,
                    date,
                    format,
                ),
                explain: shouldExplain,
                mode,
                charts: includeCharts,
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

    function changeMode(nextMode: AnalysisMode) {
        setMode(nextMode);
        setExplain(
            aiAvailable && customSections.includes('explanation'),
        );
        setCharts(customSections.includes('charts'));
    }

    function changeCustomSections(nextSections: CustomReportSection[]) {
        setCustomSections(nextSections);
        setExplain(nextSections.includes('explanation'));
        setCharts(nextSections.includes('charts'));
        setPreferenceSaved(false);
    }

    async function persistCustomSections(
        sections: CustomReportSection[],
    ): Promise<void> {
        setIsSavingPreference(true);
        try {
            await onSaveCustomReport(sections);
            setPreferenceSaved(true);
        } finally {
            setIsSavingPreference(false);
        }
    }

    async function saveCustomPreference() {
        setError(null);
        const savedSections = customSections.filter(
            (section) => section !== 'explanation' || aiAvailable,
        );
        try {
            await persistCustomSections(savedSections);
            setCustomSections(savedSections);
            setExplain(savedSections.includes('explanation'));
            setCharts(savedSections.includes('charts'));
        } catch (saveError) {
            setError(formatError(locale, saveError));
        }
    }

    return createPortal(
        <AnimatePresence initial={false}>
            {isOpen && (
                <motion.div
                    animate={{ opacity: 1 }}
                    className='report-modal-backdrop'
                    exit={{ opacity: 0 }}
                    initial={{ opacity: 0 }}
                    key='report-generation'
                    onMouseDown={(event) => {
                        if (event.target === event.currentTarget) {
                            onClose();
                        }
                    }}
                    transition={{ duration: 0.16, ease: 'easeOut' }}
                >
                    <motion.section
                        animate={{ opacity: 1, scale: 1, y: 0 }}
                        aria-labelledby='report-generation-title'
                        aria-modal='true'
                        className='report-generation-modal'
                        exit={{ opacity: 0, scale: 0.985, y: 12 }}
                        initial={{ opacity: 0, scale: 0.985, y: 12 }}
                        ref={dialogRef}
                        role='dialog'
                        transition={{
                            type: 'spring',
                            stiffness: 360,
                            damping: 30,
                        }}
                    >
                        <header className='report-modal-heading'>
                            <div>
                                <p className='eyebrow dark'>
                                    <span className='signal-mark' />
                                    {t('analysis.generate')}
                                </p>
                                <h2 id='report-generation-title'>
                                    {t('analysis.modalTitle')}
                                </h2>
                                <p>{t('analysis.modalCopy')}</p>
                            </div>
                            <button
                                aria-label={t('common.close')}
                                className='report-modal-close'
                                onClick={onClose}
                                type='button'
                            >
                                <X size={19} aria-hidden='true' />
                            </button>
                        </header>

                        {error && (
                            <p className='form-message error-message' role='alert'>
                                {error}
                            </p>
                        )}

                        <div className='analysis-layout report-modal-layout'>
                            <AnalysisForm
                                aiAvailable={aiAvailable}
                                charts={charts}
                                customSections={customSections}
                                error={null}
                                explain={explain}
                                format={format}
                                horizon={horizon}
                                isSavingPreference={isSavingPreference}
                                preferenceSaved={preferenceSaved}
                                isSubmitting={isSubmitting}
                                locale={locale}
                                mode={mode}
                                onChartsChange={setCharts}
                                onCustomSectionsChange={changeCustomSections}
                                onCustomSectionsSave={() =>
                                    void saveCustomPreference()
                                }
                                onExplainChange={setExplain}
                                onFormatChange={setFormat}
                                onHorizonChange={setHorizon}
                                onModeChange={changeMode}
                                onReportNameChange={setReportName}
                                onSubmit={submit}
                                onTickerChange={setTicker}
                                reportName={reportName}
                                ticker={ticker}
                            />
                            <AnalysisStatusPanel
                                isOpening={isOpening}
                                locale={locale}
                                onOpen={() => void openCurrentReport()}
                                report={currentReport}
                            />
                        </div>
                    </motion.section>
                </motion.div>
            )}
        </AnimatePresence>,
        document.body,
    );
}
