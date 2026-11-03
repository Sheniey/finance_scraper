
import {
    ArrowUpRight,
    WifiOff,
} from 'lucide-react';

import type { Locale } from '#/types.js';
import { translate } from '@/features/common/i18n/messages.js';



export interface AuthHeroPanelProps {
    locale: Locale;
    isOnline: boolean;
    onRetryApi: () => void;
    onChooseExecutable: () => void;
}


export function AuthHeroPanel({
    locale,
    isOnline,
    onRetryApi,
    onChooseExecutable,
}: AuthHeroPanelProps) {
    const t = (key: string) => translate(locale, key);

    return (
        <aside className='auth-art-panel'>
            <div className='art-grid' aria-hidden='true' />
            <img
                className='auth-hero-image h-full'
                src='/images/warren_buffet.jpg'
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
