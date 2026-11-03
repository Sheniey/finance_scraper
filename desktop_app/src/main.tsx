
import React from 'react';
import ReactDOM from 'react-dom/client';
import { MotionConfig } from 'motion/react';
import { App } from '@/App.js';
import { AppErrorBoundary } from '@/features/common/components/AppErrorBoundary.js';
import {
    getBrowserLocale,
    translate,
} from '@/features/common/i18n/messages.js';
import '@/assets/global.css';
import '@/assets/app.css';


const initialLocale = getBrowserLocale(navigator.language);
document.documentElement.lang = initialLocale;

ReactDOM.createRoot(document.getElementById('root')!).render(
    <React.StrictMode>
        <a className='skip-link' href='#main-content'>
            {translate(initialLocale, 'common.skipToContent')}
        </a>
        <MotionConfig reducedMotion='user'>
            <AppErrorBoundary>
                <App />
            </AppErrorBoundary>
        </MotionConfig>
    </React.StrictMode>
);
