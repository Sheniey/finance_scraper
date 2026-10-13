import { AuthScreen } from '@/components/AuthScreen.js';
import { BootScreen } from '@/components/BootScreen.js';
import { DesktopBridgeUnavailable } from '@/components/DesktopBridgeUnavailable.js';
import { ToastMessage } from '@/components/ToastMessage.js';
import { WorkspacePage } from '@/components/WorkspacePage.js';
import { WorkspaceShell } from '@/components/WorkspaceShell.js';
import { hasCompleteDesktopBridge } from '@/desktopBridge.js';
import { useAppBootstrap } from '@/hooks/useAppBootstrap.js';
import { useAppNotifications } from '@/hooks/useAppNotifications.js';
import { useDesktopActions } from '@/hooks/useDesktopActions.js';
import { useReportActions } from '@/hooks/useReportActions.js';
import { useWorkspaceData } from '@/hooks/useWorkspaceData.js';

export default function App() {
    if (!hasCompleteDesktopBridge(window.desktopApi)) {
        return <DesktopBridgeUnavailable />;
    }

    return <DesktopApplication />;
}

function DesktopApplication() {
    const { dismissToast, notify, toast } = useAppNotifications();
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
                    googleClientId={bootstrap.settings.googleClientId}
                    initialError={bootstrap.bootstrapError}
                    locale={bootstrap.locale}
                    onChooseExecutable={actions.chooseExecutable}
                    onGoogleLogin={actions.loginWithGoogle}
                    onLocaleChange={(locale) =>
                        void actions.changeLocale(locale)
                    }
                    onLogin={actions.login}
                    onRegister={actions.register}
                    onRetryApi={actions.retryApi}
                    onSaveGoogleClientId={(clientId) =>
                        actions.saveSettings({ googleClientId: clientId })
                    }
                />
                {toast && (
                    <ToastMessage
                        locale={bootstrap.locale}
                        message={toast}
                        onClose={dismissToast}
                    />
                )}
            </>
        );
    }

    return (
        <>
            <WorkspaceShell
                activeView={bootstrap.activeView}
                apiStatus={bootstrap.apiStatus}
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
                    onReportOpen={reportActions.openReport}
                    onReportsChanged={workspace.refreshReports}
                    onSchedulesChanged={workspace.refreshSchedulesAndGoogle}
                    onSettingsSave={actions.saveSettings}
                    profile={bootstrap.profile}
                    reports={workspace.reports}
                    reportsError={workspace.reportsError}
                    reportsLoading={workspace.reportsLoading}
                    schedules={workspace.schedules}
                    settings={bootstrap.settings}
                />
            </WorkspaceShell>
            {toast && (
                <ToastMessage
                    locale={bootstrap.locale}
                    message={toast}
                    onClose={dismissToast}
                />
            )}
        </>
    );
}
