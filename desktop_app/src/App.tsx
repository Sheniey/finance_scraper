
import { useCallback, useState } from 'react';

import { AuthScreen } from '@/features/auth/components/AuthScreen.js';
import { BootScreen } from '@/features/application/components/BootScreen.js';
import { DesktopBridgeUnavailable } from '@/features/application/components/DesktopBridgeUnavailable.js';
import { ToastStack } from '@/features/common/components/ToastStack.js';
import { CommandPalette } from '@/features/command-palette/components/CommandPalette.js';
import { WorkspacePage } from '@/features/workspace/components/WorkspacePage.js';
import { WorkspaceShell } from '@/features/workspace/components/WorkspaceShell.js';
import { hasCompleteDesktopBridge } from '@/features/common/lib/desktopBridge.js';
import { useAppBootstrap } from '@/features/application/hooks/useAppBootstrap.js';
import { useAppNotifications } from '@/features/application/hooks/useAppNotifications.js';
import { useDesktopActions } from '@/features/application/hooks/useDesktopActions.js';
import { useReportActions } from '@/features/reports/hooks/useReportActions.js';
import { useWorkspaceData } from '@/features/workspace/hooks/useWorkspaceData.js';


export function App() {
    if (!hasCompleteDesktopBridge(window.desktopApi)) {
        return <DesktopBridgeUnavailable />;
    }

    return <DesktopApplication />;
}


function DesktopApplication() {
    const { dismissToast, notify, toasts } = useAppNotifications();
    const [portfolioRefreshToken, setPortfolioRefreshToken] = useState(0);
    const notifyPortfolioChanged = useCallback(
        () => setPortfolioRefreshToken((token) => token + 1),
        [],
    );
    const bootstrap = useAppBootstrap(notify);
    const workspace = useWorkspaceData({
        accountEpoch: bootstrap.accountEpoch,
        locale: bootstrap.locale,
        notify,
        profile: bootstrap.profile,
        stage: bootstrap.stage,
    });
    const actions = useDesktopActions({
        accountEpoch: bootstrap.accountEpoch,
        activeProfileId: bootstrap.activeProfileId,
        clearWorkspaceData: workspace.clearWorkspaceData,
        locale: bootstrap.locale,
        notify,
        profile: bootstrap.profile,
        setActiveView: bootstrap.setActiveView,
        setApiStatus: bootstrap.setApiStatus,
        setBootstrapError: bootstrap.setBootstrapError,
        setLocale: bootstrap.setLocale,
        setProfile: bootstrap.setProfile,
        setSettings: bootstrap.setSettings,
        setStage: bootstrap.setStage,
    });
    const reportActions = useReportActions({
        accountEpoch: bootstrap.accountEpoch,
        locale: bootstrap.locale,
        notify,
        refreshReports: workspace.refreshReports,
    });

    if (bootstrap.stage === 'boot') {
        return (
            <BootScreen
                apiStatus={bootstrap.apiStatus}
                locale={bootstrap.locale}
            />
        );
    }

    if (bootstrap.stage === 'auth' || !bootstrap.profile) {
        return (
            <>
                <AuthScreen
                    apiStatus={bootstrap.apiStatus}
                    initialError={bootstrap.bootstrapError}
                    locale={bootstrap.locale}
                    onChooseExecutable={actions.chooseExecutable}
                    onLocaleChange={(locale) =>
                        void actions.changeLocale(locale)
                    }
                    onLogin={actions.login}
                    onRegister={actions.register}
                    onRetryApi={actions.retryApi}
                />
                <ToastStack
                    locale={bootstrap.locale}
                    notifications={toasts}
                    onDismiss={dismissToast}
                />
            </>
        );
    }

    return (
        <>
            <WorkspaceShell
                activeView={bootstrap.activeView}
                locale={bootstrap.locale}
                onLocaleChange={(locale) => void actions.changeLocale(locale)}
                onLogout={actions.logout}
                onNavigate={bootstrap.setActiveView}
                profile={bootstrap.profile}
            >
                <WorkspacePage
                    activeView={bootstrap.activeView}
                    apiStatus={bootstrap.apiStatus}
                    googleStatus={workspace.googleStatus}
                    locale={bootstrap.locale}
                    onChooseExecutable={() =>
                        window.desktopApi.chooseFinanceScraper()
                    }
                    onLoadMore={(cursor) => {
                        void workspace
                            .refreshReports(cursor)
                            .catch(() => undefined);
                    }}
                    onNavigate={bootstrap.setActiveView}
                    onNotify={notify}
                    onProfileChange={actions.profileChanged}
                    onReportCreate={reportActions.createReport}
                    onReportDelete={reportActions.deleteReport}
                    onReportExport={reportActions.exportReport}
                    onReportOpen={reportActions.openReport}
                    onReportsChanged={workspace.refreshReports}
                    onSchedulesChanged={workspace.refreshSchedulesAndGoogle}
                    onCustomReportSave={actions.saveCustomReport}
                    onExportAllReports={reportActions.exportAllReports}
                    onSettingsSave={actions.saveSettings}
                    portfolioRefreshToken={portfolioRefreshToken}
                    profile={bootstrap.profile}
                    reports={workspace.reports}
                    reportsError={workspace.reportsError}
                    reportsLoading={workspace.reportsLoading}
                    schedules={workspace.schedules}
                    settings={bootstrap.settings}
                />
            </WorkspaceShell>
            <CommandPalette
                locale={bootstrap.locale}
                onCustomReportSave={actions.saveCustomReport}
                onExportAllReports={reportActions.exportAllReports}
                onLocaleChange={actions.changeLocale}
                onNavigate={bootstrap.setActiveView}
                onNotify={notify}
                onPortfolioChanged={notifyPortfolioChanged}
                onProfileChange={actions.profileChanged}
                onReportCreate={reportActions.createReport}
                onReportOpen={reportActions.openReport}
                onReportsChanged={workspace.refreshReports}
                onSchedulesChanged={workspace.refreshSchedulesAndGoogle}
                googleStatus={workspace.googleStatus}
                profile={bootstrap.profile}
            />
            <ToastStack
                locale={bootstrap.locale}
                notifications={toasts}
                onDismiss={dismissToast}
            />
        </>
    );
}
