import {
    ArrowUpRight,
    FileJson2,
    FileSpreadsheet,
    FileText,
    MoreHorizontal,
    Trash2,
} from 'lucide-react';

import type { Locale, ReportEntry, ReportFormat } from '#/types.js';
import { translate } from '@/i18n/messages.js';

interface ReportTableProps {
    locale: Locale;
    reports: ReportEntry[];
    onOpen: (report: ReportEntry) => void;
    onDelete?: (report: ReportEntry) => void;
}

function formatLabel(locale: Locale, format: ReportFormat) {
    return translate(locale, `email.${format}`);
}

function FormatMark({ format }: { format: ReportFormat }) {
    if (format === 'xlsx') {
        return <FileSpreadsheet size={17} aria-hidden='true' />;
    }
    if (format === 'json' || format === 'yaml') {
        return <FileJson2 size={17} aria-hidden='true' />;
    }
    return <FileText size={17} aria-hidden='true' />;
}

function statusLabel(locale: Locale, status: ReportEntry['status']) {
    const key = {
        PENDING: 'status.pending',
        IN_PROGRESS: 'status.inProgress',
        COMPLETED: 'status.completed',
        FAILED: 'status.failed',
    }[status];
    return translate(locale, key);
}

function statusClass(status: ReportEntry['status']) {
    return status.toLowerCase().replace('_', '-');
}

function formatDate(locale: Locale, value: string) {
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) {
        return value;
    }
    return new Intl.DateTimeFormat(locale === 'es' ? 'es-MX' : 'en-US', {
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
    }).format(date);
}

export function ReportTable({
    locale,
    reports,
    onOpen,
    onDelete,
}: ReportTableProps) {
    const t = (key: string) => translate(locale, key);
    return (
        <div className='report-table-scroll'>
            <table className='report-table'>
                <thead>
                    <tr>
                        <th>{t('analysis.ticker')}</th>
                        <th>{t('reports.date')}</th>
                        <th>{t('reports.format')}</th>
                        <th>{t('reports.status')}</th>
                        <th>
                            <span className='sr-only'>{t('reports.action')}</span>
                        </th>
                    </tr>
                </thead>
                <tbody>
                    {reports.map((report) => (
                        <tr key={report.report_id}>
                            <td>
                                <span className='report-ticker'>{report.ticker}</span>
                                <small className='report-filename'>
                                    {report.filename}
                                </small>
                            </td>
                            <td className='report-date'>
                                {formatDate(locale, report.created_at)}
                            </td>
                            <td>
                                <span className='format-tag'>
                                    <FormatMark format={report.report_format} />
                                    {formatLabel(locale, report.report_format)}
                                </span>
                            </td>
                            <td>
                                <span
                                    className={`status-chip status-${statusClass(report.status)}`}
                                >
                                    <span className='status-chip-dot' />
                                    {statusLabel(locale, report.status)}
                                </span>
                            </td>
                            <td>
                                <details className='report-more'>
                                    <summary
                                        aria-label={`${t('reports.moreActions')}: ${report.ticker}`}
                                        title={t('reports.moreActions')}
                                    >
                                        <MoreHorizontal
                                            size={20}
                                            aria-hidden='true'
                                        />
                                    </summary>
                                    <div
                                        className='report-more-menu'
                                        role='group'
                                        aria-label={`${t('reports.moreActions')}: ${report.ticker}`}
                                    >
                                        <button
                                            disabled={report.status !== 'COMPLETED'}
                                            onClick={(event) => {
                                                onOpen(report);
                                                event.currentTarget
                                                    .closest('details')
                                                    ?.removeAttribute('open');
                                            }}
                                            type='button'
                                        >
                                            <ArrowUpRight
                                                size={16}
                                                aria-hidden='true'
                                            />
                                            {t('reports.open')}
                                        </button>
                                        {onDelete && (
                                            <button
                                                className='danger'
                                                onClick={(event) => {
                                                    onDelete(report);
                                                    event.currentTarget
                                                        .closest('details')
                                                        ?.removeAttribute('open');
                                                }}
                                                type='button'
                                            >
                                                <Trash2
                                                    size={16}
                                                    aria-hidden='true'
                                                />
                                                {t('reports.delete')}
                                            </button>
                                        )}
                                    </div>
                                </details>
                            </td>
                        </tr>
                    ))}
                </tbody>
            </table>
        </div>
    );
}
