import { useCallback, useEffect, useState } from 'react';

import type {
    GoogleAccountStatus,
    Locale,
    ReportPage,
    ReportSchedule,
    UserProfile,
} from '#/types.js';
import { formatError } from '@/i18n/messages.js';
import type { AppStage } from '@/hooks/useAppBootstrap.js';

interface UseWorkspaceDataOptions {
    locale: Locale;
    stage: AppStage;
    profile: UserProfile | null;
    accountEpoch: { current: number };
    notify: (message: string) => void;
}

export function useWorkspaceData({
    locale,
    stage,
    profile,
    accountEpoch,
    notify,
}: UseWorkspaceDataOptions) {
    const [reports, setReports] = useState<ReportPage | null>(null);
    const [reportsLoading, setReportsLoading] = useState(false);
    const [reportsError, setReportsError] = useState<string | null>(null);
    const [schedules, setSchedules] = useState<ReportSchedule[]>([]);
    const [googleStatus, setGoogleStatus] =
        useState<GoogleAccountStatus | null>(null);

    const refreshReports = useCallback(
        async (cursor: string | null = null) => {
            const requestEpoch = accountEpoch.current;
            setReportsLoading(true);
            setReportsError(null);
            try {
                const page = await window.desktopApi.listReports(cursor);
                if (requestEpoch !== accountEpoch.current) {
                    return page;
                }
                setReports((previous) =>
                    cursor && previous
                        ? {
                              ...page,
                              items: [...previous.items, ...page.items],
                          }
                        : page,
                );
                return page;
            } catch (error) {
                if (requestEpoch !== accountEpoch.current) {
                    throw error;
                }
                setReportsError(formatError(locale, error));
                throw error;
            } finally {
                setReportsLoading(false);
            }
        },
        [accountEpoch, locale],
    );

    const refreshWorkspaceData = useCallback(async () => {
        const requestEpoch = accountEpoch.current;
        const [reportResult, scheduleResult, googleResult] =
            await Promise.allSettled([
                window.desktopApi.listReports(),
                window.desktopApi.listSchedules(),
                window.desktopApi.getGoogleStatus(),
            ]);
        if (requestEpoch !== accountEpoch.current) {
            return;
        }

        if (reportResult.status === 'fulfilled') {
            setReports(reportResult.value);
            setReportsError(null);
        } else {
            setReportsError(formatError(locale, reportResult.reason));
        }
        if (scheduleResult.status === 'fulfilled') {
            setSchedules(scheduleResult.value);
        } else {
            notify(formatError(locale, scheduleResult.reason));
        }
        if (googleResult.status === 'fulfilled') {
            setGoogleStatus(googleResult.value);
        } else {
            notify(formatError(locale, googleResult.reason));
        }
    }, [accountEpoch, locale, notify]);

    const refreshSchedulesAndGoogle = useCallback(async () => {
        const requestEpoch = accountEpoch.current;
        const [nextSchedules, nextGoogleStatus] = await Promise.all([
            window.desktopApi.listSchedules(),
            window.desktopApi.getGoogleStatus(),
        ]);
        if (requestEpoch !== accountEpoch.current) {
            return;
        }
        setSchedules(nextSchedules);
        setGoogleStatus(nextGoogleStatus);
    }, [accountEpoch]);

    useEffect(() => {
        if (stage === 'workspace' && profile) {
            void refreshWorkspaceData();
        }
    }, [profile?.id, refreshWorkspaceData, stage]);

    function clearWorkspaceData() {
        setReports(null);
        setSchedules([]);
        setGoogleStatus(null);
        setReportsError(null);
    }

    return {
        clearWorkspaceData,
        googleStatus,
        refreshReports,
        refreshSchedulesAndGoogle,
        reports,
        reportsError,
        reportsLoading,
        schedules,
        setGoogleStatus,
        setReports,
        setReportsError,
        setSchedules,
    };
}
