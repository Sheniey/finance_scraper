
import type { CreateReportRequest, Locale, ReportEntry } from '#/types.js';
import type { ToastKind } from '@/features/common/types/index.js';
import { formatError, translate } from '@/features/common/i18n/messages.js';

interface UseReportActionsOptions {
    locale: Locale;
    accountEpoch: { current: number };
    refreshReports: () => Promise<unknown>;
    notify: (message: string, kind?: ToastKind) => void;
}

export function useReportActions({
    locale,
    accountEpoch,
    refreshReports,
    notify,
}: UseReportActionsOptions) {
    async function openReport(report: ReportEntry) {
        const requestEpoch = accountEpoch.current;
        await window.desktopApi.openReport(report.report_id);
        if (requestEpoch === accountEpoch.current) {
            notify(translate(locale, 'toast.opened'), 'success');
        }
    }

    async function deleteReport(report: ReportEntry) {
        if (!window.confirm(translate(locale, 'reports.confirmDelete'))) {
            return;
        }
        const requestEpoch = accountEpoch.current;
        await window.desktopApi.deleteReport(report.report_id);
        if (requestEpoch !== accountEpoch.current) {
            return;
        }
        await refreshReports();
        notify(translate(locale, 'toast.reportDeleted'), 'success');
    }

    async function exportReport(report: ReportEntry) {
        const result = await window.desktopApi.exportReport(report.report_id);
        if (result) {
            notify(translate(locale, 'toast.exported'), 'success');
        }
    }

    async function exportAllReports() {
        const requestEpoch = accountEpoch.current;
        const reports: ReportEntry[] = [];
        const seenCursors = new Set<string>();
        let cursor: string | null = null;

        try {
            while (true) {
                const page = await window.desktopApi.listReports(cursor);
                if (requestEpoch !== accountEpoch.current) {
                    return;
                }
                reports.push(...page.items);
                if (!page.pagination.has_more) {
                    break;
                }
                const nextCursor = page.pagination.next_cursor;
                if (!nextCursor || seenCursors.has(nextCursor)) {
                    throw new Error(
                        'The report list returned an invalid pagination cursor.',
                    );
                }
                seenCursors.add(nextCursor);
                cursor = nextCursor;
            }

            if (reports.length === 0) {
                notify(translate(locale, 'reports.empty'), 'info');
                return;
            }
            const exportableReports = reports.filter(
                (report) =>
                    report.status === 'COMPLETED' &&
                    ['pdf', 'json', 'yaml', 'txt', 'xlsx'].some(
                        (format) => format === report.report_format,
                    ),
            );
            const skipped = reports.length - exportableReports.length;
            if (exportableReports.length === 0) {
                notify(
                    translate(locale, 'toast.noExportableReports', {
                        count: skipped,
                    }),
                    'info',
                );
                return;
            }

            notify(
                translate(locale, 'toast.exportAllStarted', {
                    count: exportableReports.length,
                }),
                'info',
            );
            let exported = 0;
            for (const report of exportableReports) {
                if (requestEpoch !== accountEpoch.current) {
                    return;
                }
                const result = await window.desktopApi.exportReport(
                    report.report_id,
                );
                if (requestEpoch !== accountEpoch.current) {
                    return;
                }
                if (!result) {
                    notify(
                        translate(locale, 'toast.exportAllCancelled', {
                            count: exported,
                        }),
                        'info',
                    );
                    return;
                }
                exported += 1;
            }

            notify(
                skipped > 0
                    ? translate(locale, 'toast.exportAllPartial', {
                          count: exported,
                          skipped,
                      })
                    : translate(locale, 'toast.exportAllComplete', {
                          count: exported,
                      }),
                'success',
            );
        } catch (error) {
            if (requestEpoch === accountEpoch.current) {
                notify(formatError(locale, error), 'error');
            }
        }
    }

    async function createReport(request: CreateReportRequest) {
        const requestEpoch = accountEpoch.current;
        const report = await window.desktopApi.createReport(request);
        if (requestEpoch === accountEpoch.current) {
            notify(translate(locale, 'toast.reportQueued'), 'success');
        }
        return report;
    }

    return {
        createReport,
        deleteReport,
        exportAllReports,
        exportReport,
        openReport,
    };
}
