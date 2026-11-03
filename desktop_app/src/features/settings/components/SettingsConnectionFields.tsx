
import { FolderCog, ShieldCheck } from 'lucide-react';

import type { Locale } from '#/types.js';
import { translate } from '@/features/common/i18n/messages.js';
import { SettingsPanel } from '@/features/settings/components/SettingsPanel.js';



interface SettingsConnectionFieldsProps {
    locale: Locale;
    executable: string;
    onExecutableChange: (value: string) => void;
    onChooseExecutable: () => void;
}


export function SettingsConnectionFields({
    locale,
    executable,
    onExecutableChange,
    onChooseExecutable,
}: SettingsConnectionFieldsProps) {
    const t = (key: string) => translate(locale, key);

    return (
        <>
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
