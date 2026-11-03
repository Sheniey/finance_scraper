
import { Component, type ErrorInfo, type ReactNode } from 'react';
import { AlertTriangle, RotateCw } from 'lucide-react';

import { getBrowserLocale, translate } from '@/features/common/i18n/messages.js';
import { APP_NAME_UPPER } from '@/config.js';



interface AppErrorBoundaryProps {
    children: ReactNode;
}

interface AppErrorBoundaryState {
    error: Error | null;
}


export class AppErrorBoundary extends Component<
    AppErrorBoundaryProps,
    AppErrorBoundaryState
> {
    state: AppErrorBoundaryState = { error: null };

    static getDerivedStateFromError(error: Error): AppErrorBoundaryState {
        return { error };
    }

    componentDidCatch(error: Error, info: ErrorInfo) {
        console.error('The desktop renderer failed to render.', error, info);
    }

    render() {
        if (!this.state.error) {
            return this.props.children;
        }

        const locale = getBrowserLocale(navigator.language);
        return (
            <main className='boot-screen' id='main-content' role='alert' tabIndex={-1}>
                <span className='boot-mark'>
                    <AlertTriangle size={25} aria-hidden='true' />
                </span>
                <p className='field-kicker'>{APP_NAME_UPPER}</p>
                <h1>
                    {translate(locale, 'application.rendererErrorTitle')}
                </h1>
                <p>{this.state.error.message}</p>
                <button
                    className='button-primary'
                    onClick={() => window.location.reload()}
                    type='button'
                >
                    <RotateCw size={15} aria-hidden='true' />
                    {translate(locale, 'common.retry')}
                </button>
            </main>
        );
    }
}
