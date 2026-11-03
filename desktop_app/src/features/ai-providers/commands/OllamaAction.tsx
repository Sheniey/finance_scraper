
import { useEffect, useState } from 'react';
import { Check, Cpu, Download, Play } from 'lucide-react';

import type { Locale, OllamaStatus } from '#/types.js';
import type { ToastKind } from '@/features/common/types/index.js';
import { CommandDialog } from '@/features/command-palette/components/CommandDialog.js';
import { LoadingSpinner } from '@/features/common/components/LoadingSpinner.js';
import { formatError, translate } from '@/features/common/i18n/messages.js';
import { announceOllamaStatus } from '@/features/ai-providers/lib/ollama-events.js';
import type { OllamaOperation } from '@/features/ai-providers/types/index.js';



interface OllamaActionProps {
    isOpen: boolean;
    operation: OllamaOperation;
    locale: Locale;
    returnFocusTarget: HTMLElement | null;
    onClose: () => void;
    onNotify: (message: string, kind?: ToastKind) => void;
}


export function OllamaAction({
    isOpen,
    operation,
    locale,
    returnFocusTarget,
    onClose,
    onNotify,
}: OllamaActionProps) {
    const [status, setStatus] = useState<OllamaStatus | null>(null);
    const [isChecking, setIsChecking] = useState(false);
    const [isWorking, setIsWorking] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [notice, setNotice] = useState<string | null>(null);
    const t = (key: string) => translate(locale, key);
    const title = t(
        operation === 'install'
            ? 'command.installOllama'
            : 'command.startOllama',
    );
    const description = t(
        operation === 'install'
            ? 'command.installOllamaDescription'
            : 'command.startOllamaDescription',
    );
    const statusLabel = isChecking
        ? t('common.loading')
        : status?.running
          ? t('settings.ollamaRunning')
          : status?.installed
            ? t('settings.ollamaStopped')
            : t('settings.ollamaNotInstalled');

    useEffect(() => {
        if (!isOpen) {
            return;
        }
        let isCurrent = true;
        setIsChecking(true);
        setError(null);
        setNotice(null);
        void window.desktopApi
            .getOllamaStatus()
            .then((nextStatus) => {
                if (isCurrent) {
                    setStatus(nextStatus);
                    announceOllamaStatus(nextStatus);
                }
            })
            .catch((statusError: unknown) => {
                if (isCurrent) {
                    const message = formatError(locale, statusError);
                    setError(message);
                    onNotify(message, 'error');
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
    }, [isOpen, locale, onNotify]);

    async function runAction(nextOperation: OllamaOperation) {
        setIsWorking(true);
        setError(null);
        setNotice(null);
        try {
            const nextStatus =
                nextOperation === 'install'
                    ? await window.desktopApi.installOllama()
                    : await window.desktopApi.startOllama();
            setStatus(nextStatus);
            announceOllamaStatus(nextStatus);
            if (
                (nextOperation === 'install' && !nextStatus.installed) ||
                (nextOperation === 'start' && !nextStatus.running)
            ) {
                const message = t(
                    nextOperation === 'install'
                        ? 'settings.ollamaInstallNotDetected'
                        : 'settings.ollamaStartFailed',
                );
                setError(message);
                onNotify(message, 'error');
                return;
            }

            const message = t(
                nextOperation === 'install'
                    ? 'settings.ollamaInstalled'
                    : 'settings.ollamaRunning',
            );
            setNotice(message);
            onNotify(message, 'success');
        } catch (actionError) {
            const message = formatError(locale, actionError);
            setError(message);
            onNotify(message, 'error');
        } finally {
            setIsWorking(false);
        }
    }

    const canInstall =
        !isChecking && !isWorking && status !== null && !status.installed;
    const canStart =
        !isChecking &&
        !isWorking &&
        status?.installed === true &&
        status.running === false;

    return (
        <CommandDialog
            description={description}
            isOpen={isOpen}
            locale={locale}
            onClose={onClose}
            returnFocusTarget={returnFocusTarget}
            title={title}
        >
            <div className='ollama-command-content'>
                <div className='ollama-command-status'>
                    <span className='ollama-command-icon'>
                        <Cpu size={18} aria-hidden='true' />
                    </span>
                    <span className='ollama-command-copy'>
                        <strong>Ollama</strong>
                        <small>{statusLabel}</small>
                    </span>
                    {isChecking || isWorking ? (
                        <LoadingSpinner size={17} />
                    ) : status?.running ? (
                        <Check
                            className='ollama-command-ready'
                            size={17}
                            aria-hidden='true'
                        />
                    ) : null}
                </div>
                {status?.running && status.models.length > 0 && (
                    <p className='ollama-command-models'>
                        {t('settings.ollamaModels')}: {status.models.join(', ')}
                    </p>
                )}
                {error && (
                    <p className='form-message error-message' role='alert'>
                        {error}
                    </p>
                )}
                {notice && (
                    <p className='form-message success-message' role='status'>
                        {notice}
                    </p>
                )}
                <div className='command-dialog-actions'>
                    <button
                        className='button-secondary'
                        disabled={isWorking}
                        onClick={onClose}
                        type='button'
                    >
                        {t('common.cancel')}
                    </button>
                    {operation === 'install' && (
                        <button
                            className='button-primary'
                            disabled={!canInstall}
                            onClick={() => void runAction('install')}
                            type='button'
                        >
                            {isWorking ? (
                                <LoadingSpinner size={16} />
                            ) : (
                                <Download size={16} aria-hidden='true' />
                            )}
                            {t('settings.ollamaInstall')}
                        </button>
                    )}
                    {operation === 'start' &&
                        status?.installed &&
                        !status.running && (
                                <button
                                    className='button-primary'
                                    disabled={!canStart}
                                    onClick={() => void runAction('start')}
                                    type='button'
                                >
                                    {isWorking ? (
                                        <LoadingSpinner size={16} />
                                    ) : (
                                        <Play size={16} aria-hidden='true' />
                                    )}
                                    {t('settings.ollamaStart')}
                                </button>
                        )}
                    {operation === 'start' && status && !status.installed && (
                        <button
                            className='button-primary'
                            disabled={!canInstall}
                            onClick={() => void runAction('install')}
                            type='button'
                        >
                            {isWorking ? (
                                <LoadingSpinner size={16} />
                            ) : (
                                <Download size={16} aria-hidden='true' />
                            )}
                            {t('settings.ollamaInstall')}
                        </button>
                    )}
                    {operation === 'start' && status?.running && (
                        <span className='ollama-command-ready-copy'>
                            {t('settings.ollamaRunning')}
                        </span>
                    )}
                </div>
            </div>
        </CommandDialog>
    );
}
