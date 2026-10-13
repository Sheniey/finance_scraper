import { useEffect, useState } from 'react';
import { Eye, EyeOff, KeyRound, Save, Trash2 } from 'lucide-react';

import type {
    AiProviderKeyUpdates,
    AiProviderName,
    AiProviderStatus,
    Locale,
} from '#/types.js';
import { formatError, translate } from '@/i18n/messages.js';

const providers: Array<{ id: AiProviderName; label: string }> = [
    { id: 'openai', label: 'settings.openai' },
    { id: 'deepseek', label: 'settings.deepseek' },
    { id: 'anthropic', label: 'settings.anthropic' },
];

const emptyStatus: AiProviderStatus = {
    openai: false,
    deepseek: false,
    anthropic: false,
};

const emptyKeys: Record<AiProviderName, string> = {
    openai: '',
    deepseek: '',
    anthropic: '',
};

interface AiProviderKeysPanelProps {
    locale: Locale;
}

export function AiProviderKeysPanel({ locale }: AiProviderKeysPanelProps) {
    const [status, setStatus] = useState<AiProviderStatus>(emptyStatus);
    const [keys, setKeys] = useState<Record<AiProviderName, string>>(emptyKeys);
    const [visible, setVisible] = useState<Record<AiProviderName, boolean>>(
        { openai: false, deepseek: false, anthropic: false },
    );
    const [remove, setRemove] = useState<Record<AiProviderName, boolean>>(
        { openai: false, deepseek: false, anthropic: false },
    );
    const [isSaving, setIsSaving] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [notice, setNotice] = useState<string | null>(null);
    const t = (key: string, values?: Record<string, string | number>) =>
        translate(locale, key, values);
    const hasChanges = providers.some(
        ({ id }) => remove[id] || keys[id].trim().length > 0,
    );

    useEffect(() => {
        let isMounted = true;
        void window.desktopApi
            .getAiProviderStatus()
            .then((nextStatus) => {
                if (isMounted) {
                    setStatus(nextStatus);
                }
            })
            .catch((statusError: unknown) => {
                if (isMounted) {
                    setError(formatError(locale, statusError));
                }
            });
        return () => {
            isMounted = false;
        };
    }, [locale]);

    function updateKey(provider: AiProviderName, value: string) {
        setKeys((previous) => ({ ...previous, [provider]: value }));
        setRemove((previous) => ({ ...previous, [provider]: false }));
        setError(null);
        setNotice(null);
    }

    async function saveKeys() {
        const updates: AiProviderKeyUpdates = {};
        for (const { id } of providers) {
            if (remove[id]) {
                updates[id] = null;
            } else if (keys[id].trim()) {
                updates[id] = keys[id].trim();
            }
        }
        if (Object.keys(updates).length === 0) {
            return;
        }

        setIsSaving(true);
        setError(null);
        setNotice(null);
        try {
            setStatus(await window.desktopApi.saveAiProviderKeys(updates));
            setKeys({ ...emptyKeys });
            setRemove({ openai: false, deepseek: false, anthropic: false });
            setVisible({ openai: false, deepseek: false, anthropic: false });
            setNotice(t('settings.keysSaved'));
        } catch (saveError) {
            setError(formatError(locale, saveError));
        } finally {
            setIsSaving(false);
        }
    }

    return (
        <section className='content-panel settings-panel settings-wide ai-provider-panel'>
            <div className='panel-heading-row'>
                <div>
                    <p className='field-kicker'>
                        <KeyRound size={14} aria-hidden='true' />
                        {t('settings.integrations')}
                    </p>
                    <h2>{t('settings.aiProviders')}</h2>
                </div>
            </div>
            <p className='ai-provider-copy'>{t('settings.aiProvidersCopy')}</p>
            <div className='ai-provider-list'>
                {providers.map(({ id, label }) => (
                    <div className='ai-provider-row' key={id}>
                        <div className='ai-provider-label'>
                            <strong>{t(label)}</strong>
                            <span className={status[id] ? 'configured' : ''}>
                                {status[id]
                                    ? t('settings.keyConfigured')
                                    : t('settings.keyMissing')}
                            </span>
                        </div>
                        <div className='ai-provider-input'>
                            <label className='sr-only' htmlFor={`provider-${id}`}>
                                {t('settings.apiKey')} — {t(label)}
                            </label>
                            <input
                                autoComplete='off'
                                id={`provider-${id}`}
                                onChange={(event) =>
                                    updateKey(id, event.target.value)
                                }
                                type={visible[id] ? 'text' : 'password'}
                                value={keys[id]}
                            />
                            <button
                                aria-label={t(
                                    visible[id]
                                        ? 'auth.hidePassword'
                                        : 'auth.showPassword',
                                )}
                                aria-pressed={visible[id]}
                                className='key-action-button'
                                onClick={() =>
                                    setVisible((previous) => ({
                                        ...previous,
                                        [id]: !previous[id],
                                    }))
                                }
                                type='button'
                            >
                                {visible[id] ? (
                                    <EyeOff size={18} aria-hidden='true' />
                                ) : (
                                    <Eye size={18} aria-hidden='true' />
                                )}
                            </button>
                            {status[id] && (
                                <button
                                    aria-label={t('settings.clearKey', {
                                        provider: t(label),
                                    })}
                                    aria-pressed={remove[id]}
                                    className='key-action-button danger'
                                    onClick={() => {
                                        setRemove((previous) => ({
                                            ...previous,
                                            [id]: !previous[id],
                                        }));
                                        setKeys((previous) => ({
                                            ...previous,
                                            [id]: '',
                                        }));
                                    }}
                                    type='button'
                                >
                                    <Trash2 size={17} aria-hidden='true' />
                                </button>
                            )}
                        </div>
                        {remove[id] && (
                            <p className='ai-provider-remove-note' role='status'>
                                {t('settings.keyWillBeRemoved', {
                                    provider: t(label),
                                })}
                            </p>
                        )}
                    </div>
                ))}
            </div>
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
            <div className='ai-provider-footer'>
                <p>{t('settings.keysLocalNote')}</p>
                <button
                    className='button-primary'
                    disabled={isSaving || !hasChanges}
                    onClick={() => void saveKeys()}
                    type='button'
                >
                    <Save size={16} aria-hidden='true' />
                    {isSaving ? t('common.saving') : t('settings.saveKeys')}
                </button>
            </div>
        </section>
    );
}
