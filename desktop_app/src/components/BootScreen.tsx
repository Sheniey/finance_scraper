import type { ApiStatus, Locale } from '#/types.js';
import { translate } from '@/i18n/messages.js';

interface BootScreenProps {
    locale: Locale;
    apiStatus: ApiStatus;
}

export function BootScreen({ locale, apiStatus }: BootScreenProps) {
    return (
        <main className='boot-screen' id='main-content' tabIndex={-1}>
            <span className='boot-mark'>
                <img src='/icons/favicon.svg' alt='' />
            </span>
            <p className='field-kicker'>FINANCE SCRAPER / LOCAL</p>
            <h1>{translate(locale, 'common.apiStarting')}</h1>
            <div
                className='boot-progress'
                role='progressbar'
                aria-label={translate(locale, 'common.apiStarting')}
            >
                <span />
            </div>
            <small>{apiStatus.state}</small>
        </main>
    );
}
