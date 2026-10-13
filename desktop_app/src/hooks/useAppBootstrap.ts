import { useEffect, useRef, useState } from 'react';

import type {
    ApiStatus,
    AppSettings,
    DashboardView,
    DesktopBootstrap,
    Locale,
    UserProfile,
} from '#/types.js';
import { formatError, translate } from '@/i18n/messages.js';

export type AppStage = 'boot' | 'auth' | 'workspace';

export const DEFAULT_SETTINGS: AppSettings = {
    locale: 'es',
    reportRetentionSeconds: 15 * 24 * 60 * 60,
    workerMaxConcurrency: 4,
    googleClientId: '',
    financeScraperExecutable: '',
};

export const DEFAULT_API_STATUS: ApiStatus = {
    state: 'starting',
    baseUrl: null,
    workerConcurrency: null,
};

export function useAppBootstrap(notify: (message: string) => void) {
    const [stage, setStage] = useState<AppStage>('boot');
    const [locale, setLocale] = useState<Locale>('es');
    const [settings, setSettings] = useState<AppSettings>(DEFAULT_SETTINGS);
    const [apiStatus, setApiStatus] = useState<ApiStatus>(DEFAULT_API_STATUS);
    const [profile, setProfile] = useState<UserProfile | null>(null);
    const [activeView, setActiveView] = useState<DashboardView>('overview');
    const [bootstrapError, setBootstrapError] = useState<string | null>(null);
    const localeRef = useRef(locale);
    const accountEpoch = useRef(0);
    const activeProfileId = useRef<string | null>(null);
    localeRef.current = locale;

    useEffect(() => {
        let isMounted = true;
        const unsubscribeStatus = window.desktopApi.onApiState((status) => {
            if (isMounted) {
                setApiStatus(status);
            }
        });
        const unsubscribeNotification =
            window.desktopApi.onNotification((message) => {
                if (isMounted) {
                    notify(
                        message === 'SCHEDULE_RECOVERY_FAILED'
                            ? translate(
                                  localeRef.current,
                                  'error.scheduleRecovery',
                              )
                            : message,
                    );
                }
            });

        void window.desktopApi
            .bootstrap()
            .then((bootstrap: DesktopBootstrap) => {
                if (!isMounted) {
                    return;
                }
                setApiStatus(bootstrap.api);
                setSettings(bootstrap.settings);
                setLocale(bootstrap.settings.locale);
                setBootstrapError(bootstrap.error);
                setProfile(bootstrap.profile);
                activeProfileId.current = bootstrap.profile?.id ?? null;
                setStage(bootstrap.profile ? 'workspace' : 'auth');
            })
            .catch((error: unknown) => {
                if (!isMounted) {
                    return;
                }
                setBootstrapError(formatError(localeRef.current, error));
                setStage('auth');
            });

        return () => {
            isMounted = false;
            unsubscribeStatus();
            unsubscribeNotification();
        };
    }, [notify]);

    return {
        accountEpoch,
        activeProfileId,
        activeView,
        apiStatus,
        bootstrapError,
        locale,
        profile,
        setActiveView,
        setApiStatus,
        setBootstrapError,
        setLocale,
        setProfile,
        setSettings,
        setStage,
        settings,
        stage,
    };
}
