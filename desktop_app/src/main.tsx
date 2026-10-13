import React from 'react';
import ReactDOM from 'react-dom/client';
import App from '@/App.js';
import { AppErrorBoundary } from '@/components/AppErrorBoundary.js';
import '@/assets/global.css';
import '@/assets/desktop.css';

ReactDOM.createRoot(document.getElementById('root')!).render(
    <React.StrictMode>
        <a className='skip-link' href='#main-content'>
            {navigator.language.toLowerCase().startsWith('es')
                ? 'Saltar al contenido'
                : 'Skip to content'}
        </a>
        <AppErrorBoundary>
            <App />
        </AppErrorBoundary>
    </React.StrictMode>
);
