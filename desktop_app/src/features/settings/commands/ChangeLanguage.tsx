
import { useState } from 'react';
import { Check, Languages } from 'lucide-react';
import { motion } from 'motion/react';

import type { Locale } from '#/types.js';
import { CommandDialog } from '@/features/command-palette/components/CommandDialog.js';
import {
    formatError,
    localeOptions,
    translate,
} from '@/features/common/i18n/messages.js';



interface ChangeLanguageProps {
    isOpen: boolean;
    locale: Locale;
    returnFocusTarget: HTMLElement | null;
    onChangeLocale: (locale: Locale) => Promise<boolean>;
    onClose: () => void;
    onNotify: (message: string, kind?: 'success' | 'error' | 'info') => void;
}


export function ChangeLanguage({
    isOpen,
    locale,
    returnFocusTarget,
    onChangeLocale,
    onClose,
    onNotify,
}: ChangeLanguageProps) {
    const [isSaving, setIsSaving] = useState(false);

    async function chooseLocale(nextLocale: Locale) {
        if (nextLocale === locale || isSaving) {
            onClose();
            return;
        }

        setIsSaving(true);
        try {
            const changed = await onChangeLocale(nextLocale);
            if (changed) {
                onNotify(
                    translate(nextLocale, 'command.languageChanged'),
                    'success',
                );
                onClose();
            }
        } catch (changeError) {
            onNotify(formatError(locale, changeError), 'error');
        } finally {
            setIsSaving(false);
        }
    }

    return (
        <CommandDialog
            description={translate(locale, 'command.changeLanguageDescription')}
            isOpen={isOpen}
            locale={locale}
            onClose={onClose}
            returnFocusTarget={returnFocusTarget}
            title={translate(locale, 'command.changeLanguage')}
        >
            <div
                aria-label={translate(locale, 'common.language')}
                className='command-language-options'
                role='radiogroup'
            >
                {localeOptions.map(({ locale: optionLocale, code, name }) => (
                    <motion.button
                        aria-checked={optionLocale === locale}
                        className='command-language-option'
                        disabled={isSaving}
                        key={optionLocale}
                        lang={optionLocale}
                        onClick={() => void chooseLocale(optionLocale)}
                        role='radio'
                        type='button'
                        whileHover={{ x: 2 }}
                        whileTap={{ scale: 0.99 }}
                    >
                        <span className='command-language-icon'>
                            <Languages size={16} aria-hidden='true' />
                        </span>
                        <span className='command-language-code'>{code}</span>
                        <span className='command-language-name'>{name}</span>
                        {optionLocale === locale && (
                            <Check
                                className='command-language-check'
                                size={16}
                                aria-hidden='true'
                            />
                        )}
                    </motion.button>
                ))}
            </div>
        </CommandDialog>
    );
}
