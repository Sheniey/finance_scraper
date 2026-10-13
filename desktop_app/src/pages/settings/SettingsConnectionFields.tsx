import { FolderCog, Mail, ShieldCheck } from 'lucide-react';

import type { Locale } from '#/types.js';
import { translate } from '@/i18n/messages.js';
import { SettingsPanel } from '@/pages/settings/SettingsPanel.js';

interface SettingsConnectionFieldsProps {
    locale: Locale;
    googleClientId: string;
    executable: string;
    onGoogleClientIdChange: (value: string) => void;
    onExecutableChange: (value: string) => void;
    onChooseExecutable: () => void;
}

export function SettingsConnectionFields({
    locale,
    googleClientId,
    executable,
    onGoogleClientIdChange,
    onExecutableChange,
    onChooseExecutable,
}: SettingsConnectionFieldsProps) {
    const t = (key: string) => translate(locale, key);

    return (
        <>
            <SettingsPanel
                icon={<Mail size={13} aria-hidden='true' />}
                label='GMAIL / OAUTH 2.0'
                title={t('settings.googleClientId')}
                wide
            >
                <label className='form-field'>
                    <span>{t('settings.googleClientId')}</span>
                    <input
                        autoComplete='off'
                        onChange={(event) =>
                            onGoogleClientIdChange(event.target.value)
                        }
                        placeholder='1234567890-abc.apps.googleusercontent.com'
                        value={googleClientId}
                    />
                    <small className='field-hint'>
                        {t('settings.googleClientHint')}
                    </small>
                </label>
                <p className='manual-setup-note'>
                    <ShieldCheck size={16} aria-hidden='true' />
                    {t('settings.googleSetup')}
                </p>
            </SettingsPanel>

            <SettingsPanel
                icon={<FolderCog size={13} aria-hidden='true' />}
                label={t('common.local')}
                title={t('settings.executable')}
                wide
            >
                <label className='form-field'>
                    <span>{t('settings.executable')}</span>
                    <span className='executable-control'>
                        <input
                            onChange={(event) =>
                                onExecutableChange(event.target.value)
                            }
                            placeholder={t('settings.notConfigured')}
                            value={executable}
                        />
                        <button
                            className='button-secondary'
                            onClick={onChooseExecutable}
                            type='button'
                        >
                            {t('settings.chooseExecutable')}
                        </button>
                    </span>
                </label>
                <p className='manual-setup-note subtle'>
                    <ShieldCheck size={16} aria-hidden='true' />
                    {t('settings.dataLocal')}
                </p>
            </SettingsPanel>
        </>
    );
}
