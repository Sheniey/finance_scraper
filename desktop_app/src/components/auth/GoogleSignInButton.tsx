import { useState } from 'react';

import type { Locale } from '#/types.js';
import { formatError, translate } from '@/i18n/messages.js';

interface GoogleSignInButtonProps {
    locale: Locale;
    configured: boolean;
    disabled: boolean;
    onSignIn: () => Promise<void>;
    onError: (message: string) => void;
}

export function GoogleSignInButton({
    locale,
    configured,
    disabled,
    onSignIn,
    onError,
}: GoogleSignInButtonProps) {
    const [isConnecting, setIsConnecting] = useState(false);
    const t = (key: string) => translate(locale, key);

    async function signIn() {
        setIsConnecting(true);
        onError('');
        try {
            await onSignIn();
        } catch (error) {
            onError(formatError(locale, error));
        } finally {
            setIsConnecting(false);
        }
    }

    return (
        <div className='google-sign-in'>
            <div className='auth-divider'>
                <span>{t('auth.or')}</span>
            </div>
            <button
                aria-describedby={
                    configured ? undefined : 'google-sign-in-help'
                }
                className='button-google'
                disabled={!configured || disabled || isConnecting}
                onClick={() => void signIn()}
                type='button'
            >
                <span className='google-letter' aria-hidden='true'>
                    G
                </span>
                {isConnecting
                    ? t('auth.googleWaiting')
                    : t('auth.googleSignIn')}
            </button>
            {!configured && (
                <p className='google-sign-in-help' id='google-sign-in-help'>
                    {t('auth.googleNotConfigured')}
                </p>
            )}
            {isConnecting && (
                <p className='google-sign-in-help' aria-live='polite'>
                    {t('auth.googleOpenBrowser')}
                </p>
            )}
        </div>
    );
}
