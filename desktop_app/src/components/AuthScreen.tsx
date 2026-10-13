import { useState } from 'react';
import { Languages } from 'lucide-react';

import type { ApiStatus, Locale } from '#/types.js';
import { AuthArtPanel } from '@/components/auth/AuthArtPanel.js';
import { AuthFormPanel } from '@/components/auth/AuthFormPanel.js';
import { formatError, translate } from '@/i18n/messages.js';

interface AuthScreenProps {
    locale: Locale;
    apiStatus: ApiStatus;
    initialError: string | null;
    googleClientId: string;
    onLocaleChange: (locale: Locale) => void;
    onRetryApi: () => Promise<void>;
    onChooseExecutable: () => Promise<void>;
    onLogin: (credentials: { email: string; password: string }) => Promise<void>;
    onGoogleLogin: () => Promise<void>;
    onSaveGoogleClientId: (clientId: string) => Promise<void>;
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
    googleClientId,
    onLocaleChange,
    onRetryApi,
    onChooseExecutable,
    onLogin,
    onGoogleLogin,
    onSaveGoogleClientId,
    onRegister,
}: AuthScreenProps) {
    const [serviceError, setServiceError] = useState<string | null>(null);
    const t = (key: string) => translate(locale, key);
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
                <div className='brand-lockup' aria-label={t('brand.name')}>
                    <span className='brand-mark'>
                        <img src='/icons/favicon.svg' alt='' />
                    </span>
                    <span className='brand-wordmark'>
                        <strong>{t('brand.name')}</strong>
                        <small>{t('brand.tagline')}</small>
                    </span>
                </div>
                <label className='language-switch'>
                    <Languages size={15} aria-hidden='true' />
                    <span className='sr-only'>{t('common.language')}</span>
                    <select
                        value={locale}
                        onChange={(event) =>
                            onLocaleChange(event.target.value as Locale)
                        }
                        aria-label={t('common.language')}
                    >
                        <option value='es'>ES</option>
                        <option value='en'>EN</option>
                    </select>
                </label>
            </header>

            <section className='auth-main'>
                <div className='auth-intro'>
                    <p className='eyebrow'>
                        <span className='signal-mark' />
                        {t('auth.eyebrow')}
                    </p>
                    <h1>{t('auth.title')}</h1>
                    <p>{t('auth.copy')}</p>
                </div>
                <div className='auth-card'>
                    <AuthFormPanel
                        initialError={serviceError ?? initialError}
                        isOnline={isOnline}
                        googleClientId={googleClientId}
                        locale={locale}
                        onGoogleLogin={onGoogleLogin}
                        onLogin={onLogin}
                        onRegister={onRegister}
                        onSaveGoogleClientId={onSaveGoogleClientId}
                    />
                    <AuthArtPanel
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
                <span>© Finance Scraper</span>
            </footer>
        </main>
    );
}
