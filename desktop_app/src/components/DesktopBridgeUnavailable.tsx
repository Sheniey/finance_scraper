import { AlertTriangle, RotateCw } from 'lucide-react';

export function DesktopBridgeUnavailable() {
    const isSpanish = navigator.language.toLowerCase().startsWith('es');

    return (
        <main className='boot-screen' id='main-content' role='alert' tabIndex={-1}>
            <span className='boot-mark'>
                <AlertTriangle size={25} aria-hidden='true' />
            </span>
            <p className='field-kicker'>FINANCE SCRAPER / LOCAL</p>
            <h1>
                {isSpanish
                    ? 'No se pudo iniciar la aplicación'
                    : 'The application could not start'}
            </h1>
            <p>
                {isSpanish
                    ? 'Esta instalación necesita actualizarse. Instala la versión más reciente de Finance Scraper.'
                    : 'This installation needs an update. Install the latest version of Finance Scraper.'}
            </p>
            <button
                className='button-primary'
                onClick={() => window.location.reload()}
                type='button'
            >
                <RotateCw size={15} aria-hidden='true' />
                {isSpanish ? 'Reintentar' : 'Try again'}
            </button>
        </main>
    );
}
