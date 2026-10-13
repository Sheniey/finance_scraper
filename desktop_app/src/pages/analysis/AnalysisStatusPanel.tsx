import { ArrowUpRight, FileOutput, ShieldCheck } from 'lucide-react';

import type { Locale, ReportEntry } from '#/types.js';
import { translate } from '@/i18n/messages.js';

interface AnalysisStatusPanelProps {
    locale: Locale;
    report: ReportEntry | null;
    isOpening: boolean;
    onOpen: () => void;
}

export function AnalysisStatusPanel({
    locale,
    report,
    isOpening,
    onOpen,
}: AnalysisStatusPanelProps) {
    const t = (key: string) => translate(locale, key);

    return (
        <aside className='analysis-side'>
            <div className='analysis-side-card'>
                <span className='side-card-icon'>
                    <FileOutput size={18} aria-hidden='true' />
                </span>
                {report ? (
                    <>
                        <h2>{report.ticker}</h2>
                        <p>{report.filename}</p>
                        <span
                            className={`status-chip status-${report.status.toLowerCase().replace('_', '-')}`}
                        >
                            <span className='status-chip-dot' />
                            {translate(locale, reportStatusKeys[report.status])}
                        </span>
                        {report.status === 'COMPLETED' && (
                            <button
                                className='button-secondary side-open-button'
                                disabled={isOpening}
                                onClick={onOpen}
                                type='button'
                            >
                                {isOpening
                                    ? t('common.loading')
                                    : t('analysis.open')}
                                <ArrowUpRight
                                    size={15}
                                    aria-hidden='true'
                                />
                            </button>
                        )}
                    </>
                ) : (
                    <>
                        <h2>{t('analysis.resultTitle')}</h2>
                        <p>{t('analysis.resultEmpty')}</p>
                    </>
                )}
            </div>
            <div className='analysis-disclaimer'>
                <ShieldCheck size={16} aria-hidden='true' />
                <p>{t('overview.systemNote')}</p>
            </div>
        </aside>
    );
}

const reportStatusKeys: Record<ReportEntry['status'], string> = {
    PENDING: 'status.pending',
    IN_PROGRESS: 'status.inProgress',
    COMPLETED: 'status.completed',
    FAILED: 'status.failed',
};
