import {
    ArrowUpRight,
    WifiOff,
} from 'lucide-react';

import type { Locale } from '#/types.js';
import { translate } from '@/i18n/messages.js';

interface AuthArtPanelProps {
    locale: Locale;
    isOnline: boolean;
    onRetryApi: () => void;
    onChooseExecutable: () => void;
}

export function AuthArtPanel({
    locale,
    isOnline,
    onRetryApi,
    onChooseExecutable,
}: AuthArtPanelProps) {
    const t = (key: string) => translate(locale, key);

    return (
        <aside className='auth-art-panel'>
            <div className='art-grid' aria-hidden='true' />
            <div className='art-copy'>
                <span className='art-label'>
                    <span className='signal-mark' />
                    {t('brand.tagline')}
                </span>
                <h2>
                    {locale === 'es' ? (
                        <>Un mercado complejo.<br />Una lectura más clara.</>
                    ) : (
                        <>A complex market.<br />A clearer read.</>
                    )}
                </h2>
                <p>{t('overview.systemNote')}</p>
            </div>
            <img
                className='auth-hero-image'
                src='/images/login-hero.png'
                alt=''
            />
            {!isOnline && (
                <div className='connection-chip offline' role='status'>
                    <WifiOff size={16} aria-hidden='true' />
                    <span>
                        <strong>{t('common.apiError')}</strong>
                        <button onClick={onRetryApi} type='button'>
                            {t('common.retry')}
                            <ArrowUpRight size={13} aria-hidden='true' />
                        </button>
                        <button onClick={onChooseExecutable} type='button'>
                            {t('auth.chooseExecutable')}
                        </button>
                    </span>
                </div>
            )}
        </aside>
    );
}
