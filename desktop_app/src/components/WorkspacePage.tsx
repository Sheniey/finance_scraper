import type { ReactNode } from 'react';

import type {
    ApiStatus,
    AppSettings,
    DashboardView,
    GoogleAccountStatus,
    Locale,
    ReportEntry,
    ReportPage,
    ReportSchedule,
    UserProfile,
} from '#/types.js';
import { formatError } from '@/i18n/messages.js';
import { AnalysisPage } from '@/pages/AnalysisPage.js';
import { OverviewPage } from '@/pages/OverviewPage.js';
import { ReportsPage } from '@/pages/ReportsPage.js';
import { SchedulesPage } from '@/pages/SchedulesPage.js';
import { SettingsPage } from '@/pages/SettingsPage.js';
import { WatchlistPage } from '@/pages/WatchlistPage.js';

interface WorkspacePageProps {
    activeView: DashboardView;
    apiStatus: ApiStatus;
    locale: Locale;
    profile: UserProfile;
    settings: AppSettings;
    reports: ReportPage | null;
    reportsLoading: boolean;
    reportsError: string | null;
    schedules: ReportSchedule[];
    googleStatus: GoogleAccountStatus | null;
    onNavigate: (view: DashboardView) => void;
    onNotify: (message: string) => void;
    onReportOpen: (report: ReportEntry) => Promise<void>;
    onReportDelete: (report: ReportEntry) => Promise<void>;
    onReportCreate: Parameters<typeof AnalysisPage>[0]['onCreate'];
    onReportsChanged: () => Promise<unknown>;
    onSchedulesChanged: () => Promise<void>;
    onProfileChange: (profile: UserProfile) => Promise<void>;
    onSettingsSave: (settings: Partial<AppSettings>) => Promise<void>;
    onChooseExecutable: () => Promise<string | null>;
    onLoadMore: (cursor: string) => void;
}

export function WorkspacePage({
    activeView,
    apiStatus,
    locale,
    profile,
    settings,
    reports,
    reportsLoading,
    reportsError,
    schedules,
    googleStatus,
    onNavigate,
    onNotify,
    onReportOpen,
    onReportDelete,
    onReportCreate,
    onReportsChanged,
    onSchedulesChanged,
    onProfileChange,
    onSettingsSave,
    onChooseExecutable,
    onLoadMore,
}: WorkspacePageProps): ReactNode {
    switch (activeView) {
        case 'overview':
            return (
                <OverviewPage
                    googleStatus={googleStatus}
                    loading={reportsLoading}
                    locale={locale}
                    onNavigate={onNavigate}
                    onOpenReport={(report) =>
                        void onReportOpen(report).catch((error) =>
                            onNotify(formatError(locale, error)),
                        )
                    }
                    onDeleteReport={(report) =>
                        void onReportDelete(report).catch((error) =>
                            onNotify(formatError(locale, error)),
                        )
                    }
                    profile={profile}
                    reports={reports}
                    schedules={schedules}
                />
            );
        case 'analysis':
            return (
                <AnalysisPage
                    locale={locale}
                    onCreate={onReportCreate}
                    onOpen={onReportOpen}
                    onReportsChanged={onReportsChanged}
                />
            );
        case 'reports':
            return (
                <ReportsPage
                    error={reportsError}
                    loading={reportsLoading}
                    locale={locale}
                    onDelete={(report) =>
                        void onReportDelete(report).catch((error) =>
                            onNotify(formatError(locale, error)),
                        )
                    }
                    onLoadMore={() => {
                        const cursor = reports?.pagination.next_cursor;
                        if (cursor) {
                            onLoadMore(cursor);
                        }
                    }}
                    onOpen={(report) =>
                        void onReportOpen(report).catch((error) =>
                            onNotify(formatError(locale, error)),
                        )
                    }
                    reports={reports}
                />
            );
        case 'watchlist':
            return (
                <WatchlistPage
                    locale={locale}
                    onNavigate={onNavigate}
                    onProfileChange={onProfileChange}
                    profile={profile}
                />
            );
        case 'schedules':
            return (
                <SchedulesPage
                    googleStatus={googleStatus}
                    locale={locale}
                    onNotify={onNotify}
                    onRefresh={onSchedulesChanged}
                    schedules={schedules}
                />
            );
        case 'settings':
            return (
                <SettingsPage
                    apiStatus={apiStatus}
                    locale={locale}
                    onChooseExecutable={onChooseExecutable}
                    onSave={onSettingsSave}
                    settings={settings}
                />
            );
        default:
            return null;
    }
}
