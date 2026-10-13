import {
    Cpu,
    Languages,
    RotateCw,
} from 'lucide-react';

import type { Locale } from '#/types.js';
import { translate } from '@/i18n/messages.js';
import { SettingsConnectionFields } from '@/pages/settings/SettingsConnectionFields.js';
import { SettingsPanel } from '@/pages/settings/SettingsPanel.js';

interface SettingsFieldsProps {
    locale: Locale;
    retentionMinutes: number;
    workerMaxConcurrency: number;
    googleClientId: string;
    executable: string;
    onLocaleChange: (locale: Locale) => void;
    onRetentionChange: (value: number) => void;
    onConcurrencyChange: (value: number) => void;
    onGoogleClientIdChange: (value: string) => void;
    onExecutableChange: (value: string) => void;
    onChooseExecutable: () => void;
}

export function SettingsFields({
    locale,
    retentionMinutes,
    workerMaxConcurrency,
    googleClientId,
    executable,
    onLocaleChange,
    onRetentionChange,
    onConcurrencyChange,
    onGoogleClientIdChange,
    onExecutableChange,
    onChooseExecutable,
}: SettingsFieldsProps) {
    const t = (key: string) => translate(locale, key);

    return (
        <>
            <SettingsPanel
                icon={<Languages size={13} aria-hidden='true' />}
                label={t('common.language')}
                title={t('settings.language')}
            >
                <label className='form-field'>
                    <span>{t('settings.language')}</span>
                    <select
                        onChange={(event) =>
                            onLocaleChange(event.target.value as Locale)
                        }
                        value={locale}
                    >
                        <option value='es'>Español</option>
                        <option value='en'>English</option>
                    </select>
                </label>
            </SettingsPanel>

            <SettingsPanel
                icon={<RotateCw size={13} aria-hidden='true' />}
                label={t('reports.title')}
                title={t('settings.retention')}
            >
                <label className='form-field'>
                    <span>{t('settings.retention')}</span>
                    <span className='number-control'>
                        <input
                            max={43_200}
                            min={10}
                            onChange={(event) =>
                                onRetentionChange(Number(event.target.value))
                            }
                            required
                            step={10}
                            type='number'
                            value={retentionMinutes}
                        />
                        <small>
                            {locale === 'es' ? 'minutos' : 'minutes'}
                        </small>
                    </span>
                    <small className='field-hint'>
                        {t('settings.retentionHint')}
                    </small>
                </label>
            </SettingsPanel>

            <SettingsPanel
                icon={<Cpu size={13} aria-hidden='true' />}
                label={t('schedules.active')}
                title={t('settings.concurrency')}
            >
                <label className='form-field'>
                    <span>{t('settings.concurrency')}</span>
                    <span className='number-control'>
                        <input
                            max={16}
                            min={1}
                            onChange={(event) =>
                                onConcurrencyChange(Number(event.target.value))
                            }
                            required
                            type='number'
                            value={workerMaxConcurrency}
                        />
                        <small>{locale === 'es' ? 'máximo' : 'max'}</small>
                    </span>
                    <small className='field-hint'>
                        {t('settings.concurrencyHint')}
                    </small>
                </label>
            </SettingsPanel>

            <SettingsConnectionFields
                executable={executable}
                googleClientId={googleClientId}
                locale={locale}
                onChooseExecutable={onChooseExecutable}
                onExecutableChange={onExecutableChange}
                onGoogleClientIdChange={onGoogleClientIdChange}
            />
        </>
    );
}
