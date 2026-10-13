import { Mail } from 'lucide-react';

import type {
    GoogleAccountStatus,
    GoogleOAuthFlow,
    Locale,
} from '#/types.js';
import { translate } from '@/i18n/messages.js';

interface GoogleConnectionCardProps {
    locale: Locale;
    googleStatus: GoogleAccountStatus | null;
    flowStatus: GoogleOAuthFlow | null;
    isConnecting: boolean;
    onConnect: () => void;
    onDisconnect: () => void;
}

export function GoogleConnectionCard({
    locale,
    googleStatus,
    flowStatus,
    isConnecting,
    onConnect,
    onDisconnect,
}: GoogleConnectionCardProps) {
    const t = (key: string) => translate(locale, key);

    return (
        <section className='google-connection-card'>
            <div className='google-mark'>
                <Mail size={20} aria-hidden='true' />
            </div>
            <div className='google-copy'>
                <p className='field-kicker'>GMAIL / OAUTH 2.0</p>
                <h2>
                    {googleStatus?.connected
                        ? t('schedules.connectedAs')
                        : t('schedules.notConnected')}
                </h2>
                <p>
                    {googleStatus?.connected
                        ? googleStatus.email
                        : t('schedules.connectCopy')}
                </p>
                {flowStatus?.status === 'pending' && (
                    <span className='inline-pending'>
                        <span className='status-chip-dot' />
                        {t('schedules.oauthPending')}
                    </span>
                )}
            </div>
            {googleStatus?.connected ? (
                <button
                    className='button-secondary'
                    onClick={onDisconnect}
                    type='button'
                >
                    {t('schedules.disconnect')}
                </button>
            ) : (
                <button
                    className='button-primary'
                    disabled={isConnecting}
                    onClick={onConnect}
                    type='button'
                >
                    <Mail size={16} aria-hidden='true' />
                    {isConnecting
                        ? t('common.loading')
                        : t('schedules.connect')}
                </button>
            )}
        </section>
    );
}
