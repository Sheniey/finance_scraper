import { useEffect } from 'react';

import type { Locale, ReportEntry } from '#/types.js';
import { formatError } from '@/i18n/messages.js';

interface UseReportPollingOptions {
    report: ReportEntry | null;
    locale: Locale;
    onUpdate: (report: ReportEntry) => void;
    onCompleted: () => Promise<unknown>;
    onError: (message: string) => void;
}

export function useReportPolling({
    report,
    locale,
    onUpdate,
    onCompleted,
    onError,
}: UseReportPollingOptions) {
    useEffect(() => {
        if (
            !report ||
            report.status === 'COMPLETED' ||
            report.status === 'FAILED'
        ) {
            return;
        }

        let isMounted = true;
        const timer = window.setInterval(() => {
            void window.desktopApi
                .getReport(report.report_id)
                .then((updatedReport) => {
                    if (!isMounted) {
                        return;
                    }
                    onUpdate(updatedReport);
                    if (
                        updatedReport.status === 'COMPLETED' ||
                        updatedReport.status === 'FAILED'
                    ) {
                        void onCompleted();
                    }
                })
                .catch((pollError: unknown) => {
                    if (isMounted) {
                        onError(formatError(locale, pollError));
                    }
                });
        }, 1_500);

        return () => {
            isMounted = false;
            window.clearInterval(timer);
        };
    }, [
        locale,
        onCompleted,
        onError,
        onUpdate,
        report?.report_id,
        report?.status,
    ]);
}
