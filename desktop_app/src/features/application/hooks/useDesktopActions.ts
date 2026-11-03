
import type {
    ApiStatus,
    AppSettings,
    Locale,
    UserProfile,
} from '#/types.js';
import type { ToastKind } from '@/features/common/types/index.js';
import {
    formatError,
    getLocaleName,
    translate,
} from '@/features/common/i18n/messages.js';
import type { AppStage } from '@/features/application/types/index.js';

interface UseDesktopActionsOptions {
    locale: Locale;
    profile: UserProfile | null;
    setLocale: (locale: Locale) => void;
    setSettings: (settings: AppSettings) => void;
    setApiStatus: (status: ApiStatus) => void;
    setProfile: (profile: UserProfile | null) => void;
    setStage: (stage: AppStage) => void;
    setActiveView: (view: 'overview') => void;
    setBootstrapError: (error: string | null) => void;
    accountEpoch: { current: number };
    activeProfileId: { current: string | null };
    clearWorkspaceData: () => void;
    notify: (message: string, kind?: ToastKind) => void;
}

export function useDesktopActions({
    locale,
    profile,
    setLocale,
    setSettings,
    setApiStatus,
    setProfile,
    setStage,
    setActiveView,
    setBootstrapError,
    accountEpoch,
    activeProfileId,
    clearWorkspaceData,
    notify,
}: UseDesktopActionsOptions) {
    function setAuthenticatedProfile(authenticatedProfile: UserProfile) {
        accountEpoch.current += 1;
        activeProfileId.current = authenticatedProfile.id;
        setProfile(authenticatedProfile);
        setStage('workspace');
        setActiveView('overview');
        setBootstrapError(null);
    }

    async function login(credentials: {
        email: string;
        password: string;
    }) {
        const authenticatedProfile =
            await window.desktopApi.login(credentials);
        setAuthenticatedProfile(authenticatedProfile);
    }

    async function register(credentials: {
        name: string;
        email: string;
        password: string;
        language: Locale;
    }) {
        await window.desktopApi.register(credentials);
    }

    async function logout() {
        accountEpoch.current += 1;
        activeProfileId.current = null;
        setStage('boot');
        setProfile(null);
        clearWorkspaceData();
        setActiveView('overview');
        try {
            await window.desktopApi.logout();
            notify(translate(locale, 'auth.signedOut'), 'success');
        } catch (error) {
            notify(formatError(locale, error), 'error');
        } finally {
            setStage('auth');
        }
    }

    async function changeLocale(nextLocale: Locale): Promise<boolean> {
        if (nextLocale === locale) {
            return true;
        }

        const previousLocale = locale;
        let settingsWereSaved = false;
        try {
            const bootstrap = await window.desktopApi.saveSettings({
                locale: nextLocale,
            });
            setSettings(bootstrap.settings);
            settingsWereSaved = true;
            if (profile) {
                const updatedProfile = await window.desktopApi.updateProfile({
                    ...profile,
                    language: {
                        ...profile.language,
                        code: nextLocale,
                        name: getLocaleName(nextLocale),
                    },
                });
                if (updatedProfile.id === activeProfileId.current) {
                    setProfile(updatedProfile);
                }
            }
            setLocale(nextLocale);
            return true;
        } catch (error) {
            setLocale(previousLocale);
            if (settingsWereSaved) {
                try {
                    const restored = await window.desktopApi.saveSettings({
                        locale: previousLocale,
                    });
                    setSettings(restored.settings);
                } catch (rollbackError) {
                    notify(formatError(previousLocale, rollbackError), 'error');
                    return false;
                }
            }
            notify(formatError(previousLocale, error), 'error');
            return false;
        }
    }

    async function saveSettings(
        nextSettings: Partial<AppSettings>,
    ): Promise<void> {
        const bootstrap = await window.desktopApi.saveSettings(nextSettings);
        setSettings(bootstrap.settings);
        setApiStatus(bootstrap.api);
        setLocale(bootstrap.settings.locale);
        if (bootstrap.error) {
            setBootstrapError(bootstrap.error);
        }
    }

    async function retryApi() {
        setBootstrapError(null);
        const status = await window.desktopApi.retryApi();
        setApiStatus(status);
    }

    async function chooseExecutable() {
        const executable = await window.desktopApi.chooseFinanceScraper();
        if (!executable) {
            return;
        }
        const bootstrap = await window.desktopApi.saveSettings({
            financeScraperExecutable: executable,
        });
        setSettings(bootstrap.settings);
        setApiStatus(bootstrap.api);
        setBootstrapError(bootstrap.error);
        if (bootstrap.api.state !== 'online') {
            await retryApi();
        }
    }

    async function profileChanged(updatedProfile: UserProfile) {
        if (updatedProfile.id === activeProfileId.current) {
            setProfile(updatedProfile);
        }
    }

    async function saveCustomReport(sections: string[]) {
        if (!profile) {
            throw new Error('Sign in before updating report preferences.');
        }
        const updatedProfile = await window.desktopApi.updateProfile({
            ...profile,
            custom_report: sections,
        });
        if (updatedProfile.id === activeProfileId.current) {
            setProfile(updatedProfile);
        }
    }

    return {
        changeLocale,
        chooseExecutable,
        login,
        logout,
        profileChanged,
        register,
        retryApi,
        saveCustomReport,
        saveSettings,
    };
}
