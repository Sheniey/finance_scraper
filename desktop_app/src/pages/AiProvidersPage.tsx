
import { useEffect, useState } from 'react';
import { Cpu, Download, Play, RefreshCw } from 'lucide-react';

import type { Locale, OllamaStatus } from '#/types.js';
import { formatError, translate } from '@/features/common/i18n/messages.js';
import { AiProviderKeysPanel } from '@/features/ai-providers/components/AiProviderKeysPanel.js';
import { subscribeToOllamaStatus } from '@/features/ai-providers/lib/ollama-events.js';
import PageTitle from '@/features/common/components/PageTitle.js';
import { LoadingSpinner } from '@/features/common/components/LoadingSpinner.js';



interface AiProvidersPageProps {
    locale: Locale;
}


export function AiProvidersPage({ locale }: AiProvidersPageProps) {
    const [ollamaStatus, setOllamaStatus] = useState<OllamaStatus | null>(null);
    const [isChecking, setIsChecking] = useState(true);
    const [isInstalling, setIsInstalling] = useState(false);
    const [isStarting, setIsStarting] = useState(false);
    const [isInstallPromptOpen, setIsInstallPromptOpen] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [notice, setNotice] = useState<string | null>(null);
    const t = (key: string, values?: Record<string, string | number>) =>
        translate(locale, key, values);

    useEffect(
        () => subscribeToOllamaStatus(setOllamaStatus),
        [],
    );

    async function refreshOllamaStatus() {
        setError(null);
        setNotice(null);
        setIsChecking(true);
        try {
            const nextStatus = await window.desktopApi.getOllamaStatus();
            setOllamaStatus(nextStatus);
            if (!nextStatus.installed) {
                setIsInstallPromptOpen(true);
            }
        } catch (statusError) {
            setError(formatError(locale, statusError));
        } finally {
            setIsChecking(false);
        }
    }

    useEffect(() => {
        let isCurrent = true;
        void window.desktopApi
            .getOllamaStatus()
            .then((nextStatus) => {
                if (!isCurrent) {
                    return;
                }
                setOllamaStatus(nextStatus);
                if (!nextStatus.installed) {
                    setIsInstallPromptOpen(true);
                }
            })
            .catch((statusError: unknown) => {
                if (isCurrent) {
                    setError(formatError(locale, statusError));
                }
            })
            .finally(() => {
                if (isCurrent) {
                    setIsChecking(false);
                }
            });
        return () => {
            isCurrent = false;
        };
    }, [locale]);

    async function installOllama() {
        setIsInstalling(true);
        setError(null);
        setNotice(null);
        try {
            const nextStatus = await window.desktopApi.installOllama();
            setOllamaStatus(nextStatus);
            if (nextStatus.installed) {
                setIsInstallPromptOpen(false);
                setNotice(t('settings.ollamaInstalled'));
            } else {
                setError(t('settings.ollamaInstallNotDetected'));
            }
        } catch (installError) {
            setError(formatError(locale, installError));
        } finally {
            setIsInstalling(false);
        }
    }

    async function startOllama() {
        setIsStarting(true);
        setError(null);
        setNotice(null);
        try {
            const nextStatus = await window.desktopApi.startOllama();
            setOllamaStatus(nextStatus);
            if (!nextStatus.running) {
                setError(t('settings.ollamaStartFailed'));
            }
        } catch (startError) {
            setError(formatError(locale, startError));
        } finally {
            setIsStarting(false);
        }
    }

    const statusLabel = isChecking
        ? t('common.loading')
        : ollamaStatus?.running
          ? t('settings.ollamaRunning')
          : ollamaStatus?.installed
            ? t('settings.ollamaStopped')
            : t('settings.ollamaNotInstalled');

    return (
        <div className='page-stack'>
            <header className='page-heading'>
                <PageTitle
                    sectionName={t('nav.aiProviders')}
                    title={t('settings.aiProviders')}
                    copy={t('settings.aiProvidersPageCopy')}
                />
            </header>

            <AiProviderKeysPanel locale={locale} />

            <section className='content-panel settings-panel settings-wide ollama-panel'>
                <div className='panel-heading-row'>
                    <div>
                        <p className='field-kicker'>
                            <Cpu size={14} aria-hidden='true' />
                            {t('settings.localProvider')}
                        </p>
                        <h2>Ollama</h2>
                    </div>
                    <span
                        className={`ollama-status ${ollamaStatus?.running ? 'running' : ''}`}
                        role='status'
                    >
                        <span className='health-dot' aria-hidden='true' />
                        {statusLabel}
                    </span>
                </div>
                <p className='ai-provider-copy'>
                    {t('settings.ollamaCopy')}
                </p>
                {ollamaStatus?.running && ollamaStatus.models.length > 0 && (
                    <div className='ollama-model-list'>
                        <strong>{t('settings.ollamaModels')}</strong>
                        <ul>
                            {ollamaStatus.models.map((model) => (
                                <li key={model}>{model}</li>
                            ))}
                        </ul>
                    </div>
                )}
                {ollamaStatus?.running && ollamaStatus.models.length === 0 && (
                    <p className='field-hint ollama-model-hint'>
                        {t('settings.ollamaNoModels')}
                    </p>
                )}
                {(error || notice) && (
                    <p
                        className={`form-message ${error ? 'error-message' : 'success-message'}`}
                        role={error ? 'alert' : 'status'}
                    >
                        {error ?? notice}
                    </p>
                )}
                <div className='ollama-actions'>
                    {!ollamaStatus?.installed && !isChecking && (
                        <button
                            className='button-primary'
                            onClick={() => setIsInstallPromptOpen(true)}
                            type='button'
                        >
                            <Download size={16} aria-hidden='true' />
                            {t('settings.ollamaInstall')}
                        </button>
                    )}
                    {ollamaStatus?.installed && !ollamaStatus.running && (
                        <button
                            className='button-primary'
                            disabled={isStarting}
                            onClick={() => void startOllama()}
                            type='button'
                        >
                            {isStarting ? (
                                <LoadingSpinner size={16} />
                            ) : (
                                <Play size={16} aria-hidden='true' />
                            )}
                            {isStarting
                                ? t('common.loading')
                                : t('settings.ollamaStart')}
                        </button>
                    )}
                    <button
                        className='button-secondary'
                        disabled={isChecking || isInstalling || isStarting}
                        onClick={() => void refreshOllamaStatus()}
                        type='button'
                    >
                        <RefreshCw size={15} aria-hidden='true' />
                        {t('common.retry')}
                    </button>
                </div>
            </section>

            {isInstallPromptOpen && (
                <div
                    className='ollama-install-backdrop'
                    onMouseDown={(event) => {
                        if (event.target === event.currentTarget && !isInstalling) {
                            setIsInstallPromptOpen(false);
                        }
                    }}
                >
                    <section
                        aria-labelledby='ollama-install-title'
                        aria-modal='true'
                        className='ollama-install-dialog'
                        role='alertdialog'
                    >
                        <p className='field-kicker'>{t('settings.localProvider')}</p>
                        <h2 id='ollama-install-title'>
                            {t('settings.ollamaNotInstalled')}
                        </h2>
                        <p>{t('settings.ollamaInstallPrompt')}</p>
                        {error && (
                            <p className='form-message error-message' role='alert'>
                                {error}
                            </p>
                        )}
                        <div className='ollama-actions'>
                            <button
                                className='button-secondary'
                                disabled={isInstalling}
                                onClick={() => setIsInstallPromptOpen(false)}
                                type='button'
                            >
                                {t('common.cancel')}
                            </button>
                            <button
                                className='button-primary'
                                disabled={isInstalling}
                                onClick={() => void installOllama()}
                                type='button'
                            >
                                {isInstalling ? (
                                    <LoadingSpinner size={16} />
                                ) : (
                                    <Download size={16} aria-hidden='true' />
                                )}
                                {isInstalling
                                    ? t('settings.ollamaInstalling')
                                    : t('settings.ollamaInstall')}
                            </button>
                        </div>
                    </section>
                </div>
            )}
        </div>
    );
}
