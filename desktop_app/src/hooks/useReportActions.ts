import type { CreateReportRequest, Locale, ReportEntry } from '#/types.js';
import { translate } from '@/i18n/messages.js';

interface UseReportActionsOptions {
    locale: Locale;
    accountEpoch: { current: number };
    refreshReports: () => Promise<unknown>;
    notify: (message: string) => void;
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
            notify(translate(locale, 'toast.opened'));
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
        notify(translate(locale, 'toast.reportDeleted'));
    }

    async function createReport(request: CreateReportRequest) {
        const requestEpoch = accountEpoch.current;
        const report = await window.desktopApi.createReport(request);
        if (requestEpoch === accountEpoch.current) {
            notify(translate(locale, 'toast.reportQueued'));
        }
        return report;
    }

    return { createReport, deleteReport, openReport };
}
