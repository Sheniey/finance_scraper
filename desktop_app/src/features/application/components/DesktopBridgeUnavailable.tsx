
import { AlertTriangle, RotateCw } from 'lucide-react';

import { getBrowserLocale, translate } from '@/features/common/i18n/messages.js';
import { APP_NAME, APP_NAME_UPPER } from '@/config.js';


export function DesktopBridgeUnavailable() {
    const locale = getBrowserLocale(navigator.language);
    const t = (key: string, values?: Record<string, string | number>) => translate(locale, key, values);

    return (
        <main className='boot-screen' id='main-content' role='alert' tabIndex={-1}>
            <span className='boot-mark'>
                <AlertTriangle size={25} aria-hidden='true' />
            </span>
            <p className='field-kicker'>{APP_NAME_UPPER}</p>
            <h1>
                {t('application.bridgeUnavailableTitle')}
            </h1>
            <p>{t('application.bridgeUnavailableCopy', { app_name: APP_NAME })}</p>
            <button
                className='button-primary'
                onClick={() => window.location.reload()}
                type='button'
            >
                <RotateCw size={15} aria-hidden='true' />
                {t('common.retry')}
            </button>
        </main>
    );
}
