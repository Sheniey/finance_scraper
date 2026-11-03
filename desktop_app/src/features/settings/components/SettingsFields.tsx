
import {
    Cpu,
    Languages,
    RotateCw,
} from 'lucide-react';

import type { Locale } from '#/types.js';
import {
    localeOptions,
    parseLocale,
    translate,
} from '@/features/common/i18n/messages.js';
import { SettingsConnectionFields } from '@/features/settings/components/SettingsConnectionFields.js';
import { SettingsPanel } from '@/features/settings/components/SettingsPanel.js';



interface SettingsFieldsProps {
    locale: Locale;
    retentionMinutes: number;
    workerMaxConcurrency: number;
    executable: string;
    onLocaleChange: (locale: Locale) => void;
    onRetentionChange: (value: number) => void;
    onConcurrencyChange: (value: number) => void;
    onExecutableChange: (value: string) => void;
    onChooseExecutable: () => void;
}


export function SettingsFields({
    locale,
    retentionMinutes,
    workerMaxConcurrency,
    executable,
    onLocaleChange,
    onRetentionChange,
    onConcurrencyChange,
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
                            onLocaleChange(parseLocale(event.currentTarget.value))
                        }
                        value={locale}
                    >
                        {localeOptions.map(
                            ({ locale: optionLocale, name }) => (
                                <option
                                    key={optionLocale}
                                    value={optionLocale}
                                >
                                    {name}
                                </option>
                            ),
                        )}
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
                        <small>{t('settings.minutes')}</small>
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
                        <small>{t('settings.maximum')}</small>
                    </span>
                    <small className='field-hint'>
                        {t('settings.concurrencyHint')}
                    </small>
                </label>
            </SettingsPanel>

            <SettingsConnectionFields
                executable={executable}
                locale={locale}
                onChooseExecutable={onChooseExecutable}
                onExecutableChange={onExecutableChange}
            />
        </>
    );
}
