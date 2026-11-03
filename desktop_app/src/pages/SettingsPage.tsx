
import { useEffect, useState, type FormEvent } from 'react';
import { RotateCw, Save } from 'lucide-react';

import type { ApiStatus, AppSettings, Locale } from '#/types.js';
import { formatError, translate } from '@/features/common/i18n/messages.js';
import { SettingsFields } from '@/features/settings/components/SettingsFields.js';
import PageTitle from '@/features/common/components/PageTitle.js';



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
    const [executable, setExecutable] = useState(
        settings.financeScraperExecutable,
    );
    const [isSaving, setIsSaving] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [notice, setNotice] = useState<string | null>(null);

    useEffect(() => {
        setRetentionMinutes(Math.round(settings.reportRetentionSeconds / 60));
        setWorkerMaxConcurrency(settings.workerMaxConcurrency);
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
                <PageTitle
                    sectionName={t('nav.settings')}
                    title={t('settings.title')}
                    copy={t('settings.copy')}
                />
            </header>

            <form className='settings-grid' onSubmit={save}>
                <SettingsFields
                    executable={executable}
                    locale={locale}
                    onChooseExecutable={() => void chooseExecutable()}
                    onConcurrencyChange={setWorkerMaxConcurrency}
                    onExecutableChange={setExecutable}
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
