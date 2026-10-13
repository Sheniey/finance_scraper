import { useEffect, useState, type FormEvent } from 'react';
import { RotateCw, Save } from 'lucide-react';

import type { ApiStatus, AppSettings, Locale } from '#/types.js';
import { formatError, translate } from '@/i18n/messages.js';
import { AiProviderKeysPanel } from '@/pages/settings/AiProviderKeysPanel.js';
import { SettingsFields } from '@/pages/settings/SettingsFields.js';

interface SettingsPageProps {
    locale: Locale;
    settings: AppSettings;
    apiStatus: ApiStatus;
    onSave: (settings: Partial<AppSettings>) => Promise<void>;
    onChooseExecutable: () => Promise<string | null>;
}

export function SettingsPage({
    locale,
    settings,
    apiStatus,
    onSave,
    onChooseExecutable,
}: SettingsPageProps) {
    const t = (key: string) => translate(locale, key);
    const [retentionMinutes, setRetentionMinutes] = useState(
        Math.round(settings.reportRetentionSeconds / 60),
    );
    const [workerMaxConcurrency, setWorkerMaxConcurrency] = useState(
        settings.workerMaxConcurrency,
    );
    const [googleClientId, setGoogleClientId] = useState(
        settings.googleClientId,
    );
    const [executable, setExecutable] = useState(
        settings.financeScraperExecutable,
    );
    const [isSaving, setIsSaving] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [notice, setNotice] = useState<string | null>(null);

    useEffect(() => {
        setRetentionMinutes(Math.round(settings.reportRetentionSeconds / 60));
        setWorkerMaxConcurrency(settings.workerMaxConcurrency);
        setGoogleClientId(settings.googleClientId);
        setExecutable(settings.financeScraperExecutable);
    }, [settings]);

    async function save(event: FormEvent<HTMLFormElement>) {
        event.preventDefault();
        setError(null);
        setNotice(null);
        setIsSaving(true);
        try {
            await onSave({
                reportRetentionSeconds: retentionMinutes * 60,
                workerMaxConcurrency,
                googleClientId: googleClientId.trim(),
                financeScraperExecutable: executable,
            });
            setNotice(t('settings.saved'));
        } catch (saveError) {
            setError(formatError(locale, saveError));
        } finally {
            setIsSaving(false);
        }
    }

    async function chooseExecutable() {
        try {
            const selectedPath = await onChooseExecutable();
            if (selectedPath) {
                setExecutable(selectedPath);
            }
        } catch (selectionError) {
            setError(formatError(locale, selectionError));
        }
    }

    return (
        <div className='page-stack'>
            <header className='page-heading'>
                <p className='eyebrow dark'>
                    <span className='signal-mark' />
                    {t('nav.settings')}
                </p>
                <h1>{t('settings.title')}</h1>
                <p>{t('settings.copy')}</p>
            </header>

            <form className='settings-grid' onSubmit={save}>
                <SettingsFields
                    executable={executable}
                    googleClientId={googleClientId}
                    locale={locale}
                    onChooseExecutable={() => void chooseExecutable()}
                    onConcurrencyChange={setWorkerMaxConcurrency}
                    onExecutableChange={setExecutable}
                    onGoogleClientIdChange={setGoogleClientId}
                    onLocaleChange={(nextLocale) =>
                        void onSave({ locale: nextLocale }).catch(
                            (saveError: unknown) =>
                                setError(formatError(locale, saveError)),
                        )
                    }
                    onRetentionChange={setRetentionMinutes}
                    retentionMinutes={retentionMinutes}
                    workerMaxConcurrency={workerMaxConcurrency}
                />
                <AiProviderKeysPanel locale={locale} />
                {error && (
                    <p
                        className='form-message error-message settings-wide'
                        role='alert'
                    >
                        {error}
                    </p>
                )}
                {notice && (
                    <p
                        className='form-message success-message settings-wide'
                        role='status'
                    >
                        {notice}
                    </p>
                )}
                {apiStatus.state === 'online' && (
                    <p className='restart-note settings-wide'>
                        <RotateCw size={14} aria-hidden='true' />
                        {t('settings.restartNotice')}
                    </p>
                )}
                <div className='settings-actions settings-wide'>
                    <button
                        className='button-primary'
                        disabled={isSaving}
                        type='submit'
                    >
                        <Save size={16} aria-hidden='true' />
                        {isSaving ? t('common.saving') : t('common.save')}
                    </button>
                </div>
            </form>
        </div>
    );
}
