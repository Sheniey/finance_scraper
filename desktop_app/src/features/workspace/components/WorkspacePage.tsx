
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
    CreateReportRequest,
} from '#/types.js';
import { formatError } from '@/features/common/i18n/messages.js';
import type { ToastKind } from '@/features/common/types/index.js';
import { ReportsPage } from '@/pages/ReportsPage.js';
import { SchedulesPage } from '@/pages/SchedulesPage.js';
import { SettingsPage } from '@/pages/SettingsPage.js';
import { WatchlistPage } from '@/pages/WatchlistPage.js';
import { PortfolioPage } from '@/pages/PortfolioPage.js';
import { AiProvidersPage } from '@/pages/AiProvidersPage.js';



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
    portfolioRefreshToken: number;
    onNavigate: (view: DashboardView) => void;
    onNotify: (message: string, kind?: ToastKind) => void;
    onReportOpen: (report: ReportEntry) => Promise<void>;
    onReportExport: (report: ReportEntry) => Promise<void>;
    onReportDelete: (report: ReportEntry) => Promise<void>;
    onExportAllReports: () => Promise<void>;
    onReportCreate: (request: CreateReportRequest) => Promise<ReportEntry>;
    onReportsChanged: () => Promise<unknown>;
    onCustomReportSave: (sections: string[]) => Promise<void>;
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
    onReportExport,
    onReportDelete,
    onExportAllReports,
    portfolioRefreshToken,
    onReportCreate,
    onReportsChanged,
    onCustomReportSave,
    onSchedulesChanged,
    onProfileChange,
    onSettingsSave,
    onChooseExecutable,
    onLoadMore,
}: WorkspacePageProps): ReactNode {
    switch (activeView) {
        case 'overview':
            return (
                <ReportsPage
                    error={reportsError}
                    loading={reportsLoading}
                    locale={locale}
                    onCreate={onReportCreate}
                    onDelete={(report) =>
                        void onReportDelete(report).catch((error) =>
                            onNotify(formatError(locale, error), 'error'),
                        )
                    }
                    onExportAll={onExportAllReports}
                    onExport={(report) =>
                        void onReportExport(report).catch((error) =>
                            onNotify(formatError(locale, error), 'error'),
                        )
                    }
                    onLoadMore={() => {
                        const cursor = reports?.pagination.next_cursor;
                        if (cursor) onLoadMore(cursor);
                    }}
                    onOpen={async (report) => {
                        try {
                            await onReportOpen(report);
                        } catch (error) {
                            onNotify(formatError(locale, error), 'error');
                        }
                    }}
                    onReportsChanged={onReportsChanged}
                    onSaveCustomReport={onCustomReportSave}
                    onCreateNewSchedule={() => onNavigate('schedules')}
                    profile={profile}
                    reports={reports}
                />
            );
        case 'watchlist':
            return (
                <WatchlistPage
                    locale={locale}
                    onNavigate={onNavigate}
                    onNotify={onNotify}
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
        case 'portfolio':
            return (
                <PortfolioPage
                    locale={locale}
                    refreshToken={portfolioRefreshToken}
                />
            );
        case 'aiProviders':
            return <AiProvidersPage locale={locale} />;
        default:
            return null;
    }
}
