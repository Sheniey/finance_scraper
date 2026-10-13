import { Component, type ErrorInfo, type ReactNode } from 'react';
import { AlertTriangle, RotateCw } from 'lucide-react';

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

        const isSpanish = navigator.language.toLowerCase().startsWith('es');
        return (
            <main className='boot-screen' id='main-content' role='alert' tabIndex={-1}>
                <span className='boot-mark'>
                    <AlertTriangle size={25} aria-hidden='true' />
                </span>
                <p className='field-kicker'>FINANCE SCRAPER / LOCAL</p>
                <h1>
                    {isSpanish
                        ? 'La interfaz no pudo cargarse'
                        : 'The interface could not load'}
                </h1>
                <p>{this.state.error.message}</p>
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
}
