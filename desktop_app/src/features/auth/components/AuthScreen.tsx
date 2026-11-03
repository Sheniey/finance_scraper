
import { useState } from 'react';

import type { ApiStatus, Locale } from '#/types.js';
import {
    formatError,
    translate,
} from '@/features/common/i18n/messages.js';

import { AuthHeroPanel } from '@/features/auth/components/AuthHeroPanel.js';
import { AuthFormPanel } from '@/features/auth/components/AuthFormPanel.js';
import { LanguageToggle } from '@/features/common/components/LanguageToggle.js';
import { APP_NAME } from '@/config.js';


export interface AuthScreenProps {
    locale: Locale;
    apiStatus: ApiStatus;
    initialError: string | null;
    onLocaleChange: (locale: Locale) => void;
    onRetryApi: () => Promise<void>;
    onChooseExecutable: () => Promise<void>;
    onLogin: (credentials: { email: string; password: string }) => Promise<void>;
    onRegister: (credentials: {
        name: string;
        email: string;
        password: string;
        language: Locale;
    }) => Promise<void>;
}


export function AuthScreen({
    locale,
    apiStatus,
    initialError,
    onLocaleChange,
    onRetryApi,
    onChooseExecutable,
    onLogin,
    onRegister,
}: AuthScreenProps) {
    const [serviceError, setServiceError] = useState<string | null>(null);
    const t = (key: string, values?: Record<string, string | number>) => translate(locale, key, values);
    const isOnline = apiStatus.state === 'online';

    async function runApiAction(action: () => Promise<void>) {
        setServiceError(null);
        try {
            await action();
        } catch (error) {
            setServiceError(formatError(locale, error));
        }
    }

    return (
        <main className='auth-screen' id='main-content' tabIndex={-1}>
            <div className='auth-atmosphere' aria-hidden='true' />
            <header className='auth-topbar'>
                <div className='brand-lockup' aria-label={t('brand.name', { app_name: APP_NAME })}>
                    <span className='brand-mark'>
                        <img src='/icons/favicon.svg' alt='' />
                    </span>
                    <span className='brand-wordmark'>
                        <strong>{t('brand.name', { app_name: APP_NAME })}</strong>
                    </span>
                </div>

                <LanguageToggle locale={locale} onLocaleChange={onLocaleChange} />
            </header>

            <section className='auth-main'>
                <div className='auth-card'>
                    <AuthFormPanel
                        initialError={serviceError ?? initialError}
                        isOnline={isOnline}
                        locale={locale}
                        onLogin={onLogin}
                        onRegister={onRegister}
                    />
                    <AuthHeroPanel
                        isOnline={isOnline}
                        locale={locale}
                        onChooseExecutable={() =>
                            void runApiAction(onChooseExecutable)
                        }
                        onRetryApi={() => void runApiAction(onRetryApi)}
                    />
                </div>
            </section>

            <footer className='auth-bottom'>
                <span>{t('auth.footer')}</span>
                <span>© {APP_NAME}</span>
            </footer>
        </main>
    );
}
