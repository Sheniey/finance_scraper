
import { useEffect, useRef, useState } from 'react';
import {
    ArrowUpRight,
    Download,
    FileJson2,
    FileSpreadsheet,
    FileText,
    MoreHorizontal,
    Trash2,
} from 'lucide-react';

import type { Locale, ReportEntry, ReportFormat } from '#/types.js';
import { getIntlLocale, translate } from '@/features/common/i18n/messages.js';
import { ReportStatusIndicator } from '@/features/reports/components/ReportStatusIndicator.js';
import { ResourceContextMenu } from '@/features/command-palette/components/ResourceContextMenu.js';
import type { ResourceContextAction } from '@/features/command-palette/types/index.js';



interface ReportTableProps {
    locale: Locale;
    reports: ReportEntry[];
    onOpen: (report: ReportEntry) => void;
    onExport?: (report: ReportEntry) => void;
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
    return new Intl.DateTimeFormat(getIntlLocale(locale), {
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
    onExport,
    onDelete,
}: ReportTableProps) {
    const t = (key: string) => translate(locale, key);
    const [contextMenu, setContextMenu] = useState<{
        report: ReportEntry;
        x: number;
        y: number;
        focusFirstItem: boolean;
        returnFocusTarget: HTMLElement | null;
    } | null>(null);
    const hoverOpenTimer = useRef<number | null>(null);
    const hoverCloseTimer = useRef<number | null>(null);

    function clearContextMenuTimers() {
        if (hoverOpenTimer.current !== null) {
            window.clearTimeout(hoverOpenTimer.current);
            hoverOpenTimer.current = null;
        }
        if (hoverCloseTimer.current !== null) {
            window.clearTimeout(hoverCloseTimer.current);
            hoverCloseTimer.current = null;
        }
    }

    function openContextMenu(
        report: ReportEntry,
        x: number,
        y: number,
        focusFirstItem = false,
        returnFocusTarget: HTMLElement | null = null,
    ) {
        clearContextMenuTimers();
        setContextMenu({
            report,
            x,
            y,
            focusFirstItem,
            returnFocusTarget,
        });
    }

    function closeContextMenu() {
        clearContextMenuTimers();
        setContextMenu(null);
    }

    function scheduleContextMenuClose() {
        if (hoverCloseTimer.current !== null) {
            window.clearTimeout(hoverCloseTimer.current);
        }
        hoverCloseTimer.current = window.setTimeout(
            () => setContextMenu(null),
            160,
        );
    }

    useEffect(() => {
        return () => clearContextMenuTimers();
    }, []);

    const contextActions: ResourceContextAction[] = contextMenu
        ? [
              {
                  id: 'open',
                  label: t('reports.open'),
                  icon: ArrowUpRight,
                  disabled: contextMenu.report.status !== 'COMPLETED',
                  onSelect: () => onOpen(contextMenu.report),
              },
              ...(onExport
                  ? [
                        {
                            id: 'export',
                            label: t('reports.export'),
                            icon: Download,
                            disabled:
                                contextMenu.report.status !== 'COMPLETED',
                            onSelect: () =>
                                onExport(contextMenu.report),
                        },
                    ]
                  : []),
              ...(onDelete
                  ? [
                        {
                            id: 'delete',
                            label: t('reports.delete'),
                            icon: Trash2,
                            danger: true,
                            separatorBefore: true,
                            onSelect: () =>
                                onDelete(contextMenu.report),
                        },
                    ]
                  : []),
          ]
        : [];

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
                        <tr
                            key={report.report_id}
                            tabIndex={-1}
                            onContextMenu={(event) => {
                                event.preventDefault();
                                openContextMenu(
                                    report,
                                    event.clientX + 8,
                                    event.clientY + 8,
                                    true,
                                    event.currentTarget,
                                );
                            }}
                            onMouseEnter={(event) => {
                                if (
                                    contextMenu?.report.report_id ===
                                    report.report_id
                                ) {
                                    clearContextMenuTimers();
                                    return;
                                }
                                const x = event.clientX + 10;
                                const y = event.clientY + 10;
                                if (hoverOpenTimer.current !== null) {
                                    window.clearTimeout(hoverOpenTimer.current);
                                }
                                hoverOpenTimer.current = window.setTimeout(
                                    () =>
                                        openContextMenu(
                                            report,
                                            x,
                                            y,
                                        ),
                                    340,
                                );
                            }}
                            onMouseLeave={(event) => {
                                if (
                                    event.relatedTarget instanceof Node &&
                                    event.relatedTarget instanceof HTMLElement &&
                                    event.relatedTarget.closest(
                                        '[data-resource-context-menu]',
                                    )
                                ) {
                                    clearContextMenuTimers();
                                    return;
                                }
                                if (hoverOpenTimer.current !== null) {
                                    window.clearTimeout(hoverOpenTimer.current);
                                    hoverOpenTimer.current = null;
                                }
                                scheduleContextMenuClose();
                            }}
                        >
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
                                    <ReportStatusIndicator
                                        status={report.status}
                                    />
                                    {statusLabel(locale, report.status)}
                                </span>
                            </td>
                            <td>
                                <div className='report-more'>
                                    <button
                                        aria-label={`${t('reports.moreActions')}: ${report.ticker}`}
                                        aria-haspopup='menu'
                                        aria-expanded={
                                            contextMenu?.report.report_id ===
                                            report.report_id
                                        }
                                        className='report-more-trigger'
                                        data-resource-context-trigger=''
                                        onClick={(event) => {
                                            const button = event.currentTarget;
                                            if (
                                                contextMenu?.report.report_id ===
                                                report.report_id
                                            ) {
                                                setContextMenu((current) =>
                                                    current
                                                        ? {
                                                              ...current,
                                                              focusFirstItem: true,
                                                              returnFocusTarget:
                                                                  button,
                                                          }
                                                        : current,
                                                );
                                            } else {
                                                const rect =
                                                    button.getBoundingClientRect();
                                                openContextMenu(
                                                    report,
                                                    rect.right - 218,
                                                    rect.bottom + 5,
                                                    true,
                                                    button,
                                                );
                                            }
                                        }}
                                        title={t('reports.moreActions')}
                                        type='button'
                                    >
                                        <MoreHorizontal
                                            size={20}
                                            aria-hidden='true'
                                        />
                                    </button>
                                </div>
                            </td>
                        </tr>
                    ))}
                </tbody>
            </table>
            <ResourceContextMenu
                actions={contextActions}
                focusFirstItem={contextMenu?.focusFirstItem ?? false}
                isOpen={contextMenu !== null}
                label={
                    contextMenu
                        ? `${t('reports.moreActions')}: ${contextMenu.report.ticker}`
                        : t('reports.moreActions')
                }
                onClose={closeContextMenu}
                onMouseEnter={clearContextMenuTimers}
                onMouseLeave={scheduleContextMenuClose}
                position={{
                    x: contextMenu?.x ?? 8,
                    y: contextMenu?.y ?? 8,
                }}
                returnFocusTarget={contextMenu?.returnFocusTarget ?? null}
            />
        </div>
    );
}
