import { useEffect, useState, type FormEvent } from 'react';
import { Save } from 'lucide-react';

import type { Locale } from '#/types.js';
import { formatError, translate } from '@/i18n/messages.js';

interface GoogleClientSetupProps {
    locale: Locale;
    clientId: string;
    onSave: (clientId: string) => Promise<void>;
}

export function GoogleClientSetup({
    locale,
    clientId,
    onSave,
}: GoogleClientSetupProps) {
    const [value, setValue] = useState(clientId);
    const [error, setError] = useState<string | null>(null);
    const [isSaving, setIsSaving] = useState(false);
    const t = (key: string) => translate(locale, key);

    useEffect(() => setValue(clientId), [clientId]);

    async function save(event: FormEvent<HTMLFormElement>) {
        event.preventDefault();
        setError(null);
        setIsSaving(true);
        try {
            await onSave(value.trim());
        } catch (saveError) {
            setError(formatError(locale, saveError));
        } finally {
            setIsSaving(false);
        }
    }

    return (
        <details className='google-client-setup' open={!clientId}>
            <summary>{t('auth.configureGoogle')}</summary>
            <form onSubmit={save}>
                <label className='form-field'>
                    <span>{t('settings.googleClientId')}</span>
                    <input
                        autoComplete='off'
                        onChange={(event) => setValue(event.target.value)}
                        placeholder='1234567890-abc.apps.googleusercontent.com'
                        value={value}
                    />
                </label>
                {error && (
                    <p className='form-message error-message' role='alert'>
                        {error}
                    </p>
                )}
                <p className='google-client-help'>
                    {t('auth.googleClientHelp')}
                </p>
                <button
                    className='button-secondary'
                    disabled={isSaving || value.trim().length === 0}
                    type='submit'
                >
                    <Save size={15} aria-hidden='true' />
                    {isSaving ? t('common.saving') : t('common.save')}
                </button>
            </form>
        </details>
    );
}
